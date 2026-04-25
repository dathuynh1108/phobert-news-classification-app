#!/usr/bin/env python3
"""Materialize VietNamNet article parquet files from data_URLs.json.

The upstream GitHub repo ships URL lists in Dataset/data_URLs.json, not the
article parquet files expected by the PhoBERT notebook. This helper crawls the
article title/content for each category and writes one parquet file per class.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import re
import threading
import time
from pathlib import Path
from typing import Iterable


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

_THREAD_LOCAL = threading.local()
pa = None
pq = None
requests = None
BeautifulSoup = None
tqdm = None
SCHEMA = None


def _ensure_deps() -> None:
    global pa, pq, requests, BeautifulSoup, tqdm, SCHEMA
    if requests is not None:
        return
    try:
        import pyarrow as _pa
        import pyarrow.parquet as _pq
        import requests as _requests
        from bs4 import BeautifulSoup as _BeautifulSoup
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "Missing crawler dependency. Run: "
            "pip install pyarrow requests beautifulsoup4 lxml tqdm"
        ) from exc

    try:
        from tqdm.auto import tqdm as _tqdm
    except Exception:  # pragma: no cover - fallback only used in minimal envs
        _tqdm = None

    pa = _pa
    pq = _pq
    requests = _requests
    BeautifulSoup = _BeautifulSoup
    tqdm = _tqdm
    SCHEMA = pa.schema(
        [
            pa.field("class", pa.string()),
            pa.field("url", pa.string()),
            pa.field("title", pa.string()),
            pa.field("content", pa.string()),
        ]
    )


def _session() -> requests.Session:
    _ensure_deps()
    sess = getattr(_THREAD_LOCAL, "session", None)
    if sess is None:
        sess = requests.Session()
        sess.headers.update(HEADERS)
        _THREAD_LOCAL.session = sess
    return sess


def _clean_text(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", value).strip()


def _unique_in_order(urls: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for url in urls:
        if not isinstance(url, str):
            continue
        url = url.strip()
        if not url or url in seen:
            continue
        seen.add(url)
        out.append(url)
    return out


def _fetch_html(url: str, timeout: int = 15, retries: int = 2) -> str:
    last_exc: Exception | None = None
    for _ in range(max(1, retries)):
        try:
            resp = _session().get(url, timeout=timeout)
            if resp.status_code >= 400:
                return ""
            resp.encoding = resp.apparent_encoding or resp.encoding or "utf-8"
            return resp.text
        except Exception as exc:  # network failures are expected at this scale
            last_exc = exc
            time.sleep(0.2)
    if last_exc:
        return ""
    return ""


def _extract_article(html: str) -> tuple[str, str]:
    if not html:
        return "", ""

    _ensure_deps()
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "iframe"]):
        tag.decompose()

    title = ""
    for selector in (
        "h1.content-detail-title",
        "h1.article-detail-title",
        "h1.ArticleTitle",
        "h1.title-detail",
        "h1.title",
        "h1",
    ):
        node = soup.select_one(selector)
        text = _clean_text(node.get_text(" ", strip=True) if node else "")
        if len(text) > 5:
            title = text
            break

    content_parts: list[str] = []
    for selector in (
        ".content-detail-sapo",
        ".article-sapo",
        ".vnn-sapo",
        "h2.sapo",
        ".sapo",
    ):
        node = soup.select_one(selector)
        text = _clean_text(node.get_text(" ", strip=True) if node else "")
        if len(text) > 20:
            content_parts.append(text)
            break

    container = None
    for selector in (
        "div.maincontent.main-content",
        "div.maincontent",
        "div.main-content",
        "div.ArticleContent",
        "div.content-detail-body",
        "div.article-content",
        "article",
        "main",
    ):
        container = soup.select_one(selector)
        if container:
            break

    search_root = container or soup
    for node in search_root.find_all(["p", "li"]):
        text = _clean_text(node.get_text(" ", strip=True))
        if len(text) < 25:
            continue
        if text.lower() in {"vietnamnet", "theo vietnamnet"}:
            continue
        content_parts.append(text)

    if not content_parts:
        meta = soup.select_one('meta[name="description"], meta[property="og:description"]')
        text = _clean_text(meta.get("content") if meta else "")
        if len(text) > 20:
            content_parts.append(text)

    return title, _clean_text(" ".join(content_parts))


def fetch_article(url: str) -> dict[str, str] | None:
    html = _fetch_html(url)
    title, content = _extract_article(html)
    if not title and not content:
        return None
    return {"url": url, "title": title, "content": content}


def _write_batch(writer: pq.ParquetWriter, batch: list[dict[str, str]]) -> None:
    if not batch:
        return
    _ensure_deps()
    writer.write_table(
        pa.table(
            {
                "class": [row["class"] for row in batch],
                "url": [row["url"] for row in batch],
                "title": [row["title"] for row in batch],
                "content": [row["content"] for row in batch],
            },
            schema=SCHEMA,
        )
    )
    batch.clear()


def materialize_category(
    category: str,
    urls: Iterable[str],
    out_path: Path,
    *,
    workers: int = 24,
    batch_size: int = 128,
    force: bool = False,
) -> int:
    _ensure_deps()
    urls = _unique_in_order(urls)
    if out_path.exists() and not force:
        meta = pq.read_metadata(out_path)
        print(f"[skip] {out_path.name}: {meta.num_rows:,} rows")
        return int(meta.num_rows)
    if not urls:
        print(f"[warn] {category}: no URLs")
        return 0

    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = out_path.with_suffix(out_path.suffix + ".tmp")
    if tmp_path.exists():
        tmp_path.unlink()

    iterator = None
    count = 0
    batch: list[dict[str, str]] = []
    progress = tqdm(total=len(urls), desc=category, unit="url") if tqdm else None

    try:
        with pq.ParquetWriter(tmp_path, SCHEMA) as writer:
            with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
                futures = [pool.submit(fetch_article, url) for url in urls]
                iterator = concurrent.futures.as_completed(futures)
                for future in iterator:
                    if progress:
                        progress.update(1)
                    try:
                        row = future.result()
                    except Exception:
                        row = None
                    if not row:
                        continue
                    batch.append(
                        {
                            "class": category,
                            "url": row["url"],
                            "title": row["title"],
                            "content": row["content"],
                        }
                    )
                    count += 1
                    if len(batch) >= batch_size:
                        _write_batch(writer, batch)
            _write_batch(writer, batch)
    finally:
        if progress:
            progress.close()

    if count == 0:
        if tmp_path.exists():
            tmp_path.unlink()
        print(f"[warn] {category}: extracted 0 articles")
        return 0

    tmp_path.replace(out_path)
    print(f"[ok] {out_path.name}: {count:,} rows")
    return count


def materialize_dataset(
    dataset_dir: str | Path,
    *,
    categories: Iterable[str] | None = None,
    urls_file: str = "data_URLs.json",
    workers: int = 24,
    batch_size: int = 128,
    max_urls_per_category: int | None = None,
    force: bool = False,
) -> dict[str, int]:
    _ensure_deps()
    dataset_dir = Path(dataset_dir)
    urls_path = dataset_dir / urls_file
    if not urls_path.exists():
        raise FileNotFoundError(f"Missing URL dataset: {urls_path}")

    with urls_path.open(encoding="utf-8") as f:
        all_urls = json.load(f)

    if categories is None:
        categories = all_urls.keys()

    summary: dict[str, int] = {}
    for category in categories:
        urls = _unique_in_order(all_urls.get(category, []))
        if max_urls_per_category is not None:
            urls = urls[:max_urls_per_category]
        print(f"\n[materialize] {category}: {len(urls):,} URLs")
        summary[category] = materialize_category(
            category,
            urls,
            dataset_dir / f"{category}.parquet",
            workers=workers,
            batch_size=batch_size,
            force=force,
        )
    return summary


def parse_args() -> argparse.Namespace:
    default_dataset_dir = Path(__file__).resolve().parents[2] / "dataset"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-dir", default=str(default_dataset_dir))
    parser.add_argument("--urls-file", default="data_URLs.json")
    parser.add_argument("--workers", type=int, default=24)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--max-urls-per-category", type=int)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("categories", nargs="*")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    materialize_dataset(
        args.dataset_dir,
        categories=args.categories or None,
        urls_file=args.urls_file,
        workers=args.workers,
        batch_size=args.batch_size,
        max_urls_per_category=args.max_urls_per_category,
        force=args.force,
    )


if __name__ == "__main__":
    main()
