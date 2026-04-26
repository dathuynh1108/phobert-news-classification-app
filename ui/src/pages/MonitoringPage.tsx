import { useEffect, useState } from "react";

import { fetchMonitoring, fetchWorkerJob, recomputeMonitoring } from "../lib/api";
import { MonitoringScreen, WorkerJobResponse } from "../lib/types";
import { formatScore, translateLabel } from "../lib/utils";
import { AppShell, HeatMatrix, ProgressList, StatCard, Surface, ToneBadge, ToneButton, VerticalBars } from "../components/ui";

const MONITORING_JOB_POLL_INTERVAL_MS = 1000;
const MONITORING_JOB_MAX_POLLS = 60;

type MonitoringJob = WorkerJobResponse & {
  result?: unknown;
  error?: string | null;
};

function delay(milliseconds: number) {
  return new Promise((resolve) => window.setTimeout(resolve, milliseconds));
}

function formatMonitoringJobResult(job: MonitoringJob) {
  if (job.status === "failed") {
    return `Failed ${job.jobType} job ${job.jobId}: ${job.error || "unknown error"}`;
  }
  if (job.status !== "completed") {
    return `${job.status} ${job.jobType} job ${job.jobId}`;
  }
  const result = job.result && typeof job.result === "object" ? (job.result as Record<string, unknown>) : {};
  if (result.status === "skipped") {
    return `Skipped ${job.jobType} job ${job.jobId}: ${String(result.reason || "no monitoring data")}`;
  }
  if (result.snapshotId) {
    return `Completed ${job.jobType} job ${job.jobId}; snapshot #${String(result.snapshotId)}`;
  }
  return `Completed ${job.jobType} job ${job.jobId}`;
}

async function waitForMonitoringJob(jobId: string, onStatus: (job: MonitoringJob) => void): Promise<MonitoringJob> {
  for (let attempt = 0; attempt < MONITORING_JOB_MAX_POLLS; attempt += 1) {
    const job = await fetchWorkerJob(jobId);
    onStatus(job);
    if (job.status === "completed" || job.status === "failed") {
      return job;
    }
    await delay(MONITORING_JOB_POLL_INTERVAL_MS);
  }
  throw new Error(`Monitoring job ${jobId} is still running`);
}

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
      setJobStatus(`Queued ${job.jobType} job ${job.jobId}; waiting for worker`);
      const completedJob = await waitForMonitoringJob(job.jobId, (nextJob) => {
        setJobStatus(formatMonitoringJobResult(nextJob));
      });
      if (completedJob.status === "completed") {
        setData(await fetchMonitoring());
      }
    } catch (error) {
      setJobStatus(error instanceof Error ? error.message : "Monitoring recompute failed");
    } finally {
      setIsRecomputing(false);
    }
  }

  const lastRunLabel = data.lastRunAt ? new Date(data.lastRunAt).toLocaleString() : "N/A";
  const confusionLabels = data.confusionMatrix.labels.map(translateLabel);
  const confusionValues = data.confusionMatrix.matrix;

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
              <p>Label-level F1 from the latest reviewed prediction snapshot.</p>
            </div>
          </div>
          <ProgressList items={data.labelScores.map((item) => ({ ...item, label: translateLabel(item.label) }))} />
        </Surface>
      </div>

      <div className="two-column">
        <Surface>
          <div className="section-heading">
            <div>
              <h3>Overall confusion matrix</h3>
              <p>Rows are editor decisions, columns are model predictions from the latest reviewed traffic.</p>
            </div>
          </div>
          {confusionValues.length ? <HeatMatrix labels={confusionLabels} values={confusionValues} /> : <p className="empty-state">No reviewed prediction pairs yet.</p>}
        </Surface>

        <Surface>
          <div className="section-heading">
            <div>
              <h3>Slice analysis</h3>
              <p>Operational slices tied to the same monitoring recompute.</p>
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
      </div>

      <Surface className="table-panel">
        <div className="section-heading">
          <div>
            <h3>Per-class metrics</h3>
            <p>Precision, recall, F1, and support are computed from the same reviewed prediction set.</p>
          </div>
        </div>
        <div className="data-table-shell">
          <table className="data-table metrics-table">
            <thead>
              <tr>
                <th>Class</th>
                <th>Precision</th>
                <th>Recall</th>
                <th>F1</th>
                <th>Support</th>
                <th>TP</th>
                <th>FP</th>
                <th>FN</th>
              </tr>
            </thead>
            <tbody>
              {data.perClassMetrics.length ? (
                data.perClassMetrics.map((item) => (
                  <tr key={item.label}>
                    <td>
                      <strong className="table-title">{translateLabel(item.label)}</strong>
                    </td>
                    <td className="metric-cell">{formatScore(item.precision)}</td>
                    <td className="metric-cell">{formatScore(item.recall)}</td>
                    <td className="metric-cell">{formatScore(item.f1)}</td>
                    <td className="metric-cell">{item.support}</td>
                    <td className="metric-cell">{item.tp}</td>
                    <td className="metric-cell">{item.fp}</td>
                    <td className="metric-cell">{item.fn}</td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={8}>No per-class metrics yet.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Surface>

      <div className="lower-panels">
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
