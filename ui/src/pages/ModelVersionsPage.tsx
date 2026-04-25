import { useEffect, useRef, useState } from "react";

import { activateModel, downloadModelExport, fetchModelVersions, uploadModelArtifacts } from "../lib/api";
import { ModelVersionsScreen } from "../lib/types";
import { translateLabel } from "../lib/utils";
import { AppShell, HeatMatrix, Surface, ToneBadge, ToneButton } from "../components/ui";

export function ModelVersionsPage() {
  const [data, setData] = useState<ModelVersionsScreen | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadRunId, setUploadRunId] = useState(`run_${Date.now()}`);
  const [uploadF1, setUploadF1] = useState(0);
  const [uploadLabel, setUploadLabel] = useState("browser upload");
  const fileInputRef = useRef<HTMLInputElement | null>(null);

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

  async function handleUpload(files: FileList | null) {
    if (!files?.length) {
      return;
    }
    if (!uploadRunId) {
      return;
    }
    setIsUploading(true);
    try {
      await uploadModelArtifacts({
        runId: uploadRunId,
        backbone: "vinai/phobert-base-v2",
        f1: uploadF1,
        uploadedLabel: uploadLabel,
        files,
      });
      setData(await fetchModelVersions());
      setUploadRunId(`run_${Date.now()}`);
      setUploadF1(0);
      setUploadLabel("browser upload");
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
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
              <input
                accept=".zip,.json,.bin,.safetensors,.txt,.codes,.model"
                hidden
                multiple
                onChange={(event) => handleUpload(event.target.files)}
                ref={fileInputRef}
                type="file"
              />
              <ToneButton className="compact-button" disabled={isUploading} onClick={() => fileInputRef.current?.click()} tone="muted">
                {isUploading ? "Uploading..." : "Upload artifact"}
              </ToneButton>
              <ToneButton className="compact-button" disabled={!data.selectedRun} onClick={() => data.selectedRun && handleActivate(data.selectedRun.id)}>
                Set this package active
              </ToneButton>
            </div>
          </div>
          <div className="inline-form three-up-form">
            <label>
              <span>Run ID</span>
              <input value={uploadRunId} onChange={(event) => setUploadRunId(event.target.value)} />
            </label>
            <label>
              <span>Validation F1</span>
              <input max="1" min="0" onChange={(event) => setUploadF1(Number(event.target.value))} step="0.01" type="number" value={uploadF1} />
            </label>
            <label>
              <span>Upload label</span>
              <input value={uploadLabel} onChange={(event) => setUploadLabel(event.target.value)} />
            </label>
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
                {data.runs.length ? (
                  data.runs.map((run) => (
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
                  ))
                ) : (
                  <tr>
                    <td colSpan={5}>No model package uploaded yet.</td>
                  </tr>
                )}
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
          {data.confusionMatrix.length ? <HeatMatrix values={data.confusionMatrix} /> : <p className="empty-state">No evaluation matrix uploaded yet.</p>}
        </Surface>

        <Surface>
          <div className="section-heading">
            <div>
              <h3>Package details</h3>
              <p>Config, checkpoint, and artifacts imported from the selected run.</p>
            </div>
          </div>
          <div className="feedback-list">
            {data.packageDetails.length ? (
              data.packageDetails.map((item) => (
                <div className="feedback-row reveal" key={item.label}>
                  <div>
                    <strong>{translateLabel(item.label)}</strong>
                    <span>{item.value}</span>
                  </div>
                </div>
              ))
            ) : (
              <p className="empty-state">No package metadata available.</p>
            )}
          </div>
          <div className="chip-row">
            {data.exports.map((item) => (
              <button className="export-chip" key={item} onClick={() => data.selectedRun && downloadModelExport(data.selectedRun.id, item)} type="button">
                <ToneBadge tone="muted" subtle>
                  {item}
                </ToneBadge>
              </button>
            ))}
          </div>
        </Surface>
      </div>
    </AppShell>
  );
}
