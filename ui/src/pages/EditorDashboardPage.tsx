import { type CSSProperties, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { fetchEditorDashboard, importArticle } from "../lib/api";
import { EditorDashboardScreen } from "../lib/types";
import { cn, formatScore, toneClassMap, toneForLabel, translateLabel } from "../lib/utils";
import { AppShell, ProgressList, StatCard, Surface, ToneBadge, ToneButton } from "../components/ui";

export function EditorDashboardPage() {
  const [data, setData] = useState<EditorDashboardScreen | null>(null);
  const [articleUrl, setArticleUrl] = useState("");
  const [articleTitle, setArticleTitle] = useState("");
  const [articleContent, setArticleContent] = useState("");
  const [isImporting, setIsImporting] = useState(false);
  const [jobStatus, setJobStatus] = useState("");

  useEffect(() => {
    fetchEditorDashboard().then(setData).catch(console.error);
  }, []);

  if (!data) {
    return <div className="loading-state">Loading editor dashboard...</div>;
  }

  async function handleImport() {
    if (!articleUrl && (!articleTitle || !articleContent)) {
      return;
    }
    setIsImporting(true);
    try {
      const job = await importArticle({
        source_url: articleUrl || undefined,
        title: articleTitle || undefined,
        content: articleContent || undefined,
        source: "VietnamNet",
        run_inference: true,
      });
      setJobStatus(`Queued ${job.jobType} job ${job.jobId}`);
      const refreshed = await fetchEditorDashboard();
      setData(refreshed);
      setArticleUrl("");
      setArticleTitle("");
      setArticleContent("");
    } finally {
      setIsImporting(false);
    }
  }

  const confidencePercent = data.confidenceSummary.value === null ? null : Math.round(data.confidenceSummary.value * 100);

  return (
    <AppShell chips={data.chips} heading={data.heading} subheading={data.subheading} sidebar={data.sidebar}>
      <Surface>
        <div className="section-heading">
          <div>
            <h3>Import article</h3>
            <p>Fetch a story URL or paste article text, run inference, and add it to the editorial queue.</p>
          </div>
          <ToneButton className="compact-button" disabled={isImporting} onClick={handleImport}>
            {isImporting ? "Queueing..." : "Queue import"}
          </ToneButton>
        </div>
        <div className="import-grid">
          <label>
            <span>Source URL</span>
            <input value={articleUrl} onChange={(event) => setArticleUrl(event.target.value)} placeholder="https://vietnamnet.vn/..." />
          </label>
          <label>
            <span>Title override</span>
            <input value={articleTitle} onChange={(event) => setArticleTitle(event.target.value)} placeholder="Optional when URL is provided" />
          </label>
          <label className="wide-field">
            <span>Article content</span>
            <textarea value={articleContent} onChange={(event) => setArticleContent(event.target.value)} placeholder="Optional when URL is provided" />
          </label>
        </div>
        {jobStatus ? <p className="job-status">{jobStatus}</p> : null}
      </Surface>

      <section className="stats-grid">
        {data.stats.map((item, index) => (
          <StatCard item={item} index={index} key={item.label} />
        ))}
      </section>

      <div className="two-column">
        <Surface className="queue-panel">
          <div className="section-heading">
            <div>
              <h3>Editorial queue</h3>
              <p>Stories with lower confidence or narrow top-1 vs top-2 gaps are pushed to the top of the review queue.</p>
            </div>
          </div>
          <div className="queue-list">
            {data.reviewQueue.items.map((item) => (
              <article className="queue-row reveal" key={item.id}>
                <ToneBadge tone={toneForLabel(item.label)} subtle>
                  {translateLabel(item.label)}
                </ToneBadge>
                <div className="queue-copy">
                  <strong>{item.title}</strong>
                  <span>
                    PhoBERT {formatScore(item.confidence)} · Margin {formatScore(item.margin)}
                  </span>
                </div>
                <Link
                  className={cn(
                    "tone-button compact-button",
                    item.label === "Giáo dục" ? toneClassMap.muted : toneClassMap.navy,
                  )}
                  to={`/editor/review/${item.id}`}
                >
                  Open story
                </Link>
              </article>
            ))}
          </div>
          <div className="panel-footer">
            <span>{data.reviewQueue.summary}</span>
            <span>
              {data.reviewQueue.page}/{data.reviewQueue.totalPages}
            </span>
          </div>
        </Surface>

        <Surface>
          <div className="section-heading">
            <div>
              <h3>Category distribution</h3>
              <p>Share of labels in the stored article corpus.</p>
            </div>
          </div>
          <ProgressList items={data.categoryDistribution.map((item) => ({ ...item, label: translateLabel(item.label) }))} suffix="percent" />
          <div className="confidence-widget">
            <div className="confidence-ring" style={{ "--confidence": `${confidencePercent ?? 0}%` } as CSSProperties}>
              <div className="ring-core">{confidencePercent === null ? "N/A" : `${confidencePercent}%`}</div>
            </div>
            <span>{data.confidenceSummary.label}</span>
          </div>
        </Surface>
      </div>

      <div className="two-column lower-panels">
        <Surface>
          <div className="section-heading">
            <div>
              <h3>Shared signals</h3>
              <p>Signals that editors and Data Scientists see together from the same feedback loop.</p>
            </div>
          </div>
          <div className="pill-list">
            {data.sharedSignals.map((signal, index) => (
              <div className="signal-row reveal" key={signal.label} style={{ animationDelay: `${index * 80}ms` }}>
                <span>{signal.label}</span>
                <ToneBadge tone={signal.tone}>{signal.pill}</ToneBadge>
              </div>
            ))}
          </div>
        </Surface>

        <Surface>
          <div className="section-heading">
            <div>
              <h3>Feedback loop</h3>
              <p>Overrides, drift, and rule updates feed back into one continuous workflow for both teams.</p>
            </div>
          </div>
          <div className="feedback-list">
            {data.feedbackLoop.map((item, index) => (
              <div className="feedback-row reveal" key={item.title} style={{ animationDelay: `${index * 90}ms` }}>
                <div>
                  <strong>{item.title}</strong>
                  <span>{item.body}</span>
                </div>
                <ToneBadge tone={item.tone}>{item.pill}</ToneBadge>
              </div>
            ))}
          </div>
        </Surface>
      </div>
    </AppShell>
  );
}
