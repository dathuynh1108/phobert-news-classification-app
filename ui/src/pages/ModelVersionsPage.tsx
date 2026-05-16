import { useEffect, useMemo, useRef, useState } from "react";
import { ChevronLeft, ChevronRight, Eye } from "lucide-react";

import { activateModel, downloadModelExport, fetchModelVersions, uploadModelArtifacts } from "../lib/api";
import { ModelVersionsScreen } from "../lib/types";
import { translateLabel } from "../lib/utils";
import { AppShell, HeatMatrix, Surface, ToneBadge, ToneButton } from "../components/ui";

const RUN_PAGE_SIZE = 4;
const TOKENIZER_MARKERS = new Set(["tokenizer.json", "tokenizer_config.json", "vocab.txt", "bpe.codes", "merges.txt", "sentencepiece.bpe.model"]);

function artifactValidationMessage(files: FileList): string | null {
  const selectedFiles = Array.from(files);
  if (selectedFiles.length === 1 && selectedFiles[0].name.toLowerCase().endsWith(".zip")) {
    return null;
  }
  const names = new Set(selectedFiles.map((file) => file.name));
  const missing: string[] = [];
  if (!names.has("config.json")) {
    missing.push("config.json");
  }
  if (!names.has("label_config.json")) {
    missing.push("label_config.json");
  }
  if (!names.has("model.safetensors") && !names.has("pytorch_model.bin")) {
    missing.push("model.safetensors or pytorch_model.bin");
  }
  if (!Array.from(names).some((name) => TOKENIZER_MARKERS.has(name))) {
    missing.push("tokenizer files");
  }
  return missing.length ? `Missing required artifact file: ${missing.join(", ")}` : null;
}

export function ModelVersionsPage() {
  const [data, setData] = useState<ModelVersionsScreen | null>(null);
  const [selectedRunId, setSelectedRunId] = useState("");
  const [runPage, setRunPage] = useState(1);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadRunId, setUploadRunId] = useState(`run_${Date.now()}`);
  const [uploadLabel, setUploadLabel] = useState("browser upload");
  const [uploadError, setUploadError] = useState("");
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const runTotalPages = useMemo(() => {
    return Math.max(1, Math.ceil((data?.runs.length ?? 0) / RUN_PAGE_SIZE));
  }, [data?.runs.length]);
  const visibleRuns = useMemo(() => {
    const offset = (runPage - 1) * RUN_PAGE_SIZE;
    return data?.runs.slice(offset, offset + RUN_PAGE_SIZE) ?? [];
  }, [data?.runs, runPage]);

  function runStateLabel(state: string) {
    if (state === "active") {
      return "active";
    }
    if (state === "inactive") {
      return "inactive";
    }
    return "archived";
  }

  async function load(runId?: string) {
    const payload = await fetchModelVersions(runId);
    setData(payload);
    setSelectedRunId(payload.selectedRun?.id ?? "");
  }

  useEffect(() => {
    load().catch(console.error);
  }, []);

  useEffect(() => {
    setRunPage((page) => Math.min(page, runTotalPages));
  }, [runTotalPages]);

  if (!data) {
    return <div className="loading-state">Loading model versions...</div>;
  }

  async function handleSelectRun(runId: string) {
    setSelectedRunId(runId);
    await load(runId);
  }

  async function handleActivate(runId: string) {
    await activateModel(runId);
    await load(runId);
  }

  async function handleUpload(files: FileList | null) {
    if (!files?.length || !uploadRunId) {
      return;
    }
    const validationError = artifactValidationMessage(files);
    if (validationError) {
      setUploadError(validationError);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
      return;
    }
    setIsUploading(true);
    setUploadError("");
    try {
      const result = await uploadModelArtifacts({
        runId: uploadRunId,
        backbone: "vinai/phobert-base-v2",
        uploadedLabel: uploadLabel,
        files,
      });
      await load(result.run.id);
      setRunPage(1);
      setUploadRunId(`run_${Date.now()}`);
      setUploadLabel("browser upload");
    } catch (error) {
      setUploadError(error instanceof Error ? error.message : "Upload failed");
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  }

  return (
    <AppShell chips={data.chips} heading={data.heading} subheading={data.subheading} sidebar={data.sidebar}>
      <div className="two-column model-version-detail-grid">
        <Surface className="table-panel">
          <div className="section-heading">
            <div>
              <h3>Uploaded runs</h3>
              <p>
                Showing {visibleRuns.length} of {data.runs.length} packages
              </p>
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
                {isUploading ? "Uploading..." : "Upload artifacts"}
              </ToneButton>
              <ToneButton className="compact-button" disabled={!data.selectedRun} onClick={() => data.selectedRun && handleActivate(data.selectedRun.id)}>
                Set as active
              </ToneButton>
            </div>
          </div>
          <div className="inline-form admin-form">
            <label>
              <span>Run ID</span>
              <input value={uploadRunId} onChange={(event) => setUploadRunId(event.target.value)} />
            </label>
            <label>
              <span>Upload label</span>
              <input value={uploadLabel} onChange={(event) => setUploadLabel(event.target.value)} />
            </label>
          </div>
          <div className="artifact-requirements">
            <strong>Required upload package</strong>
            <p>Upload one .zip, or select the artifact files together.</p>
            <div className="chip-row">
              <ToneBadge tone="navy" subtle>config.json</ToneBadge>
              <ToneBadge tone="navy" subtle>label_config.json</ToneBadge>
              <ToneBadge tone="navy" subtle>model.safetensors or pytorch_model.bin</ToneBadge>
              <ToneBadge tone="navy" subtle>tokenizer files</ToneBadge>
            </div>
            <p>
              Metrics are read from metrics.json or thresholds.json. Confusion matrix is read from confusion_matrix.json.
            </p>
            {uploadError ? <p className="inline-error">{uploadError}</p> : null}
          </div>
          <div className="data-table-shell">
            <table className="data-table model-runs-table">
              <thead>
                <tr>
                  <th>Run</th>
                  <th>Backbone</th>
                  <th>Uploaded</th>
                  <th>F1</th>
                  <th>Status</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {visibleRuns.length ? (
                  visibleRuns.map((run) => (
                    <tr className={run.id === selectedRunId ? "selected-row" : undefined} key={run.id}>
                      <td>
                        <strong className="table-title">{run.id}</strong>
                      </td>
                      <td>{run.backbone}</td>
                      <td>{run.uploaded}</td>
                      <td>{run.f1.toFixed(2)}</td>
                      <td>
                        <ToneBadge tone={run.state === "active" ? "green" : run.state === "inactive" ? "muted" : "gold"} subtle>
                          {runStateLabel(run.state)}
                        </ToneBadge>
                      </td>
                      <td className="table-action-cell">
                        <ToneButton className="pagination-button" icon={<Eye aria-hidden="true" size={15} />} onClick={() => handleSelectRun(run.id)} tone="muted">
                          Select
                        </ToneButton>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={6}>No model package uploaded yet.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
          <div className="pagination-bar">
            <span>
              Page {runPage} of {runTotalPages}
            </span>
            <div className="inline-actions">
              <ToneButton className="pagination-button" disabled={runPage <= 1} icon={<ChevronLeft aria-hidden="true" size={15} />} onClick={() => setRunPage((value) => Math.max(1, value - 1))} tone="muted">
                Previous
              </ToneButton>
              <ToneButton className="pagination-button" disabled={runPage >= runTotalPages} icon={<ChevronRight aria-hidden="true" size={15} />} onClick={() => setRunPage((value) => value + 1)}>
                Next
              </ToneButton>
            </div>
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

      <div className="three-column model-version-detail-grid">
        <Surface>
          <div className="section-heading">
            <div>
              <h3>Confusion matrix snapshot</h3>
              <p>A compact heatmap for the label groups that are most often confused.</p>
            </div>
          </div>
          {data.confusionMatrix.length ? <HeatMatrix labels={data.confusionLabels} values={data.confusionMatrix} /> : <p className="empty-state">No evaluation matrix uploaded yet.</p>}
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
