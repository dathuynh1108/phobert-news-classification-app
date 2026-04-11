import { useEffect, useState } from "react";

import { fetchDatasetLab } from "../lib/api";
import { DatasetLabScreen } from "../lib/types";
import { translateLabel } from "../lib/utils";
import { AppShell, ProgressList, StatCard, Surface, ToneBadge } from "../components/ui";

export function DatasetLabPage() {
  const [data, setData] = useState<DatasetLabScreen | null>(null);

  useEffect(() => {
    fetchDatasetLab().then(setData).catch(console.error);
  }, []);

  if (!data) {
    return <div className="loading-state">Loading dataset workspace...</div>;
  }

  return (
    <AppShell chips={data.chips} heading={data.heading} subheading={data.subheading} sidebar={data.sidebar}>
      <section className="stats-grid three-up">
        {data.stats.map((item, index) => (
          <StatCard item={item} index={index} key={item.label} />
        ))}
      </section>

      <div className="two-column">
        <Surface>
          <div className="section-heading">
            <div>
              <h3>Label imbalance</h3>
              <p>Some categories appear far less often and need more samples or relabel work.</p>
            </div>
          </div>
          <ProgressList items={data.imbalance.map((item) => ({ ...item, label: translateLabel(item.label) }))} />
        </Surface>

        <Surface>
          <div className="section-heading">
            <div>
              <h3>Hard samples</h3>
              <p>The lowest-confidence stories are waiting for relabeling or desk policy review.</p>
            </div>
          </div>
          <div className="sample-list">
            {data.hardSamples.map((sample) => (
              <div className="sample-row reveal" key={sample.title}>
                <span>{sample.title}</span>
                <ToneBadge tone="coral">{sample.score.toFixed(2)}</ToneBadge>
              </div>
            ))}
          </div>
          <div className="panel-footer">
            <span>Showing 3 of 214 hard samples</span>
            <span>1/72</span>
          </div>
        </Surface>
      </div>

      <Surface className="active-learning-panel">
        <div className="section-heading">
          <div>
            <h3>Active learning loop</h3>
            <p>Turn overrides, low-confidence samples, and drift signals into the next relabel batch.</p>
          </div>
        </div>
        <div className="chip-row">
          <ToneBadge tone="navy" subtle>
            Refresh batch every 6 hours
          </ToneBadge>
        </div>
        <div className="analysis-grid four-up">
          {data.activeLearning.map((item) => (
            <div className="analysis-card reveal" key={item.title}>
              <span>{item.title}</span>
              <strong>{item.value}</strong>
              <small>{item.body}</small>
              <ToneBadge tone={item.tone}>{item.pill}</ToneBadge>
            </div>
          ))}
        </div>
        <div className="chip-row">
          <span className="priority-label">Priority labels</span>
          {data.priorityLabels.map((label, index) => (
            <ToneBadge key={label} tone={index === 0 ? "coral" : index === 1 ? "teal" : "gold"} subtle>
              {translateLabel(label)}
            </ToneBadge>
          ))}
        </div>
      </Surface>
    </AppShell>
  );
}
