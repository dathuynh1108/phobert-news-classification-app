import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { fetchEditorDashboard } from "../lib/api";
import { EditorDashboardScreen } from "../lib/types";
import { cn, formatScore, toneClassMap, toneForLabel, translateLabel } from "../lib/utils";
import { AppShell, ProgressList, StatCard, Surface, ToneBadge, ToneButton } from "../components/ui";

export function EditorDashboardPage() {
  const [data, setData] = useState<EditorDashboardScreen | null>(null);

  useEffect(() => {
    fetchEditorDashboard().then(setData).catch(console.error);
  }, []);

  if (!data) {
    return <div className="loading-state">Loading editor dashboard...</div>;
  }

  return (
    <AppShell chips={data.chips} heading={data.heading} subheading={data.subheading} sidebar={data.sidebar}>
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
              <p>Share of the most frequent labels predicted by the model in the last 24 hours.</p>
            </div>
          </div>
          <ProgressList items={data.categoryDistribution.map((item) => ({ ...item, label: translateLabel(item.label) }))} suffix="percent" />
          <div className="confidence-ring">
            <div className="ring-core">74%</div>
            <span>High confidence</span>
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
