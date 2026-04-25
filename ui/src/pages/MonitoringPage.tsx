import { useEffect, useState } from "react";

import { fetchMonitoring, recomputeMonitoring } from "../lib/api";
import { MonitoringScreen } from "../lib/types";
import { translateLabel } from "../lib/utils";
import { AppShell, ProgressList, StatCard, Surface, ToneBadge, ToneButton, VerticalBars } from "../components/ui";

export function MonitoringPage() {
  const [data, setData] = useState<MonitoringScreen | null>(null);
  const [isRecomputing, setIsRecomputing] = useState(false);
  const [jobStatus, setJobStatus] = useState("");

  useEffect(() => {
    fetchMonitoring().then(setData).catch(console.error);
  }, []);

  if (!data) {
    return <div className="loading-state">Loading monitoring dashboard...</div>;
  }

  async function handleRecompute() {
    setIsRecomputing(true);
    try {
      const job = await recomputeMonitoring();
      setJobStatus(`Queued ${job.jobType} job ${job.jobId}`);
    } finally {
      setIsRecomputing(false);
    }
  }

  const lastRunLabel = data.lastRunAt ? new Date(data.lastRunAt).toLocaleString() : "N/A";

  return (
    <AppShell chips={data.chips} heading={data.heading} subheading={data.subheading} sidebar={data.sidebar}>
      <Surface>
        <div className="section-heading">
          <div>
            <h3>Evaluation snapshot</h3>
            <p>Last recomputed at {lastRunLabel} from predictions, editor decisions, and live queue state.</p>
          </div>
          <ToneButton className="compact-button" disabled={isRecomputing} onClick={handleRecompute}>
            {isRecomputing ? "Queueing..." : "Recompute"}
          </ToneButton>
        </div>
        {jobStatus ? <p className="job-status">{jobStatus}</p> : null}
      </Surface>

      <section className="stats-grid">
        {data.stats.map((item, index) => (
          <StatCard item={item} index={index} key={item.label} />
        ))}
      </section>

      <div className="two-column">
        <Surface>
          <div className="section-heading">
            <div>
              <h3>Macro F1 over time</h3>
              <p>Track model quality across the evaluation window used to warn production before performance drops.</p>
            </div>
          </div>
          <VerticalBars values={data.macroSeries} />
        </Surface>

        <Surface>
          <div className="section-heading">
            <div>
              <h3>Per-label F1</h3>
              <p>Labels with weaker recall stay visible so the team can react before editorial traffic is affected.</p>
            </div>
          </div>
          <ProgressList items={data.labelScores.map((item) => ({ ...item, label: translateLabel(item.label) }))} />
        </Surface>
      </div>

      <div className="two-column lower-panels">
        <Surface>
          <div className="section-heading">
            <div>
              <h3>Representative article groups</h3>
              <p>Representative clusters explain why drift rises or F1 drops during the day.</p>
            </div>
          </div>
          <div className="analysis-grid">
            {data.articleAnalysis.length ? (
              data.articleAnalysis.map((item) => (
                <div className="analysis-card reveal" key={item.label}>
                  <span>{item.label}</span>
                  <strong>{item.value}</strong>
                  <small>{item.note}</small>
                </div>
              ))
            ) : (
              <p className="empty-state">N/A</p>
            )}
          </div>
        </Surface>

        <Surface>
          <div className="section-heading">
            <div>
              <h3>Drift breakdown</h3>
              <p>These signals are pushing the monitoring score closer to the watch zone.</p>
            </div>
          </div>
          <div className="feedback-list">
            {data.driftBreakdown.length ? (
              data.driftBreakdown.map((item) => (
                <div className="feedback-row reveal" key={item.label}>
                  <div>
                    <strong>{item.label}</strong>
                    <span>{item.detail}</span>
                  </div>
                  <ToneBadge tone={item.tone}>{item.label}</ToneBadge>
                </div>
              ))
            ) : (
              <p className="empty-state">N/A</p>
            )}
          </div>
        </Surface>
      </div>
    </AppShell>
  );
}
