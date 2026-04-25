import {
  AdminOpsScreen,
  DatasetLabScreen,
  EditorDashboardScreen,
  InferenceResponse,
  LoginResponse,
  ModelVersionsScreen,
  MonitoringScreen,
  RoleType,
  ReviewArticleScreen,
  WorkerJobResponse,
} from "./types";
import { getSession } from "./session";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const session = getSession();
  const isFormData = init?.body instanceof FormData;
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      ...(isFormData ? {} : { "Content-Type": "application/json" }),
      ...(session?.token ? { Authorization: `Bearer ${session.token}` } : {}),
      ...(init?.headers ?? {}),
    },
    ...init,
  });
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return (await response.json()) as T;
}

export function login(payload: { email: string; password: string; role: RoleType }) {
  return request<LoginResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function logout() {
  return request<{ status: string }>("/auth/logout", {
    method: "POST",
  });
}

export function fetchEditorDashboard(page = 1) {
  return request<EditorDashboardScreen>(`/editor/dashboard?page=${page}`);
}

export function importArticle(payload: { title?: string; content?: string; source_url?: string; source?: string; label_hint?: string; run_inference?: boolean }) {
  return request<WorkerJobResponse>(`/editor/articles/jobs`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function fetchReviewArticle(articleId: string) {
  return request<ReviewArticleScreen>(`/editor/articles/${articleId}`);
}

export function inferArticle(articleId: string, payload: { title: string; content: string; source_url?: string; top_k?: number }) {
  return request<InferenceResponse>(`/editor/articles/${articleId}/infer`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function submitDecision(articleId: string, payload: { action: string; selected_label?: string; notes?: string }) {
  return request<{ status: string }>(`/editor/articles/${articleId}/decision`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function fetchAdminOps() {
  return request<AdminOpsScreen>("/admin/ops");
}

export function inviteUser(payload: { email: string; name: string; role: RoleType; queue: string; password: string }) {
  return request<{ email: string; name: string; role: string; queue: string; status: string }>("/admin/users", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateThresholds(payload: { auto_approve: number; review_floor: number }) {
  return request<{ auto_approve: number; review_floor: number }>("/admin/ops/thresholds", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function promoteModelFromAdmin(runId: string) {
  return request<{ status: string; activeModel: string; runId: string }>(`/admin/ops/model-runs/${runId}/activate`, {
    method: "POST",
  });
}

export function fetchMonitoring() {
  return request<MonitoringScreen>("/scientist/monitoring");
}

export function recomputeMonitoring() {
  return request<WorkerJobResponse>("/scientist/monitoring/jobs/recompute", {
    method: "POST",
  });
}

export function fetchWorkerJob(jobId: string) {
  return request<WorkerJobResponse & { result?: unknown; error?: string | null }>(`/jobs/${jobId}`);
}

export function fetchModelVersions() {
  return request<ModelVersionsScreen>("/scientist/model-versions");
}

export function uploadModelArtifacts(payload: { runId: string; backbone: string; f1: number; uploadedLabel: string; files: FileList | File[] }) {
  const form = new FormData();
  form.append("run_id", payload.runId);
  form.append("backbone", payload.backbone);
  form.append("f1", String(payload.f1));
  form.append("uploaded_label", payload.uploadedLabel);
  Array.from(payload.files).forEach((file) => {
    form.append("files", file, (file as File & { webkitRelativePath?: string }).webkitRelativePath || file.name);
  });
  return request<{ status: string; run: { id: string; backbone: string; uploaded: string; f1: number; state: string } }>("/scientist/model-versions/upload", {
    method: "POST",
    body: form,
  });
}

export function activateModel(runId: string) {
  return request<{ status: string; activeModel: string; runId: string }>(`/scientist/model-versions/${runId}/activate`, {
    method: "POST",
  });
}

export async function downloadModelExport(runId: string, filename: string) {
  const session = getSession();
  const response = await fetch(`${API_BASE_URL}/scientist/model-versions/${runId}/exports/${encodeURIComponent(filename)}`, {
    headers: {
      ...(session?.token ? { Authorization: `Bearer ${session.token}` } : {}),
    },
  });
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}

export function fetchDatasetLab() {
  return request<DatasetLabScreen>("/scientist/dataset-lab");
}
