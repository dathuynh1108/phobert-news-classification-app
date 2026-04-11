import { useEffect, useState } from "react";

import { activateModel, fetchModelVersions } from "../lib/api";
import { ModelVersionsScreen } from "../lib/types";
import { translateLabel } from "../lib/utils";
import { AppShell, HeatMatrix, Surface, ToneBadge, ToneButton } from "../components/ui";

export function ModelVersionsPage() {
  const [data, setData] = useState<ModelVersionsScreen | null>(null);

  function runStateLabel(state: string) {
    if (state === "active") {
      return "active";
    }
    if (state === "inactive") {
      return "inactive";
    }
    return "archived";
  }

  useEffect(() => {
    fetchModelVersions().then(setData).catch(console.error);
  }, []);

  if (!data) {
    return <div className="loading-state">Loading model versions...</div>;
  }

  async function handleActivate(runId: string) {
    await activateModel(runId);
    const refreshed = await fetchModelVersions();
    setData(refreshed);
  }

  return (
    <AppShell chips={data.chips} heading={data.heading} subheading={data.subheading} sidebar={data.sidebar}>
      <div className="two-column">
        <Surface>
          <div className="section-heading">
            <div>
              <h3>Uploaded runs</h3>
              <p>Offline training packages that are ready to be promoted into the editorial workflow.</p>
            </div>
            <div className="inline-actions">
              <ToneButton className="compact-button" tone="muted">
                Upload artifacts
              </ToneButton>
              <ToneButton className="compact-button" onClick={() => handleActivate("run_024")}>
                Set this package active
              </ToneButton>
            </div>
          </div>
          <div className="table-shell">
            <table>
              <thead>
                <tr>
                  <th>Run</th>
                  <th>Backbone</th>
                  <th>Uploaded</th>
                  <th>F1</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {data.runs.map((run) => (
                  <tr key={run.id}>
                    <td>{run.id}</td>
                    <td>{run.backbone}</td>
                    <td>{run.uploaded}</td>
                    <td>{run.f1.toFixed(2)}</td>
                    <td>
                      <ToneBadge tone={run.state === "active" ? "green" : run.state === "inactive" ? "muted" : "gold"}>
                        {runStateLabel(run.state)}
                      </ToneBadge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Surface>

        <Surface>
          <div className="section-heading">
            <div>
              <h3>Version comparison</h3>
              <p>Key details for the selected run and its readiness to go live in production.</p>
            </div>
          </div>
          <div className="snapshot-grid">
            {data.comparisonCards.map((item) => (
              <div className="snapshot-card reveal" key={item.label}>
                <span>{item.label}</span>
                <strong>{item.value}</strong>
                <small>{item.detail}</small>
              </div>
            ))}
          </div>
        </Surface>
      </div>

      <div className="three-column">
        <Surface>
          <div className="section-heading">
            <div>
              <h3>Confusion matrix snapshot</h3>
              <p>A compact heatmap for the label groups that are most often confused.</p>
            </div>
          </div>
          <HeatMatrix values={data.confusionMatrix} />
        </Surface>

        <Surface>
          <div className="section-heading">
            <div>
              <h3>Package details</h3>
              <p>Config, checkpoint, and artifacts imported from the selected run.</p>
            </div>
          </div>
          <div className="feedback-list">
            {data.packageDetails.map((item) => (
              <div className="feedback-row reveal" key={item.label}>
                <div>
                  <strong>{translateLabel(item.label)}</strong>
                  <span>{item.value}</span>
                </div>
              </div>
            ))}
          </div>
          <div className="chip-row">
            {data.exports.map((item) => (
              <ToneBadge key={item} tone="muted" subtle>
                {item}
              </ToneBadge>
            ))}
          </div>
        </Surface>
      </div>
    </AppShell>
  );
}
