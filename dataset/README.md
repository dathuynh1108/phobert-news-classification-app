# Dataset

This directory stores the dataset inputs and generated parquet files used by the PhoBERT notebook in `train/`.
The dataset directory is ignored by git except this README. Keep model packages in `train/artifacts/`, not here.

The materialized dataset is hosted on Hugging Face:

- `https://huggingface.co/datasets/dathuynh1108/vietnamnet-news`

The upstream URL lists are included here:

- `data_URLs.json`
- `data_URLs_empty_content.json`
- `data_URLs_empty_title.json`

The upstream GitHub repository provides URL lists, not ready-to-train article content in parquet format. `train/notebooks/main_PhoBERT.ipynb` uses `data_URLs.json` to crawl article title/content and create any missing parquet files.

Expected files after materialization include:

- `dataset/ban-doc.parquet`
- `dataset/bao-ve-nguoi-tieu-dung.parquet`
- `dataset/bat-dong-san.parquet`
- `...`
- `dataset/van-hoa-giai-tri.parquet`

Materialize the dataset manually with:

```bash
python train/scripts/materialize_vietnamnet_dataset.py
```

Useful options:

```bash
python train/scripts/materialize_vietnamnet_dataset.py --max-urls-per-category 100
python train/scripts/materialize_vietnamnet_dataset.py --force
python train/scripts/materialize_vietnamnet_dataset.py --dataset-dir dataset
```
