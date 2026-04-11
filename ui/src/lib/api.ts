import {
  AdminOpsScreen,
  DatasetLabScreen,
  EditorDashboardScreen,
  InferenceResponse,
  LoginResponse,
  ModelVersionsScreen,
  MonitoringScreen,
  ReviewArticleScreen,
} from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    ...init,
  });
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return (await response.json()) as T;
}

export function login(payload: { email: string; password: string; role: "editor-admin" | "data-scientist" }) {
  return request<LoginResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function fetchEditorDashboard(page = 1) {
  return request<EditorDashboardScreen>(`/editor/dashboard?page=${page}`);
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

export function updateThresholds(payload: { auto_approve: number; review_floor: number }) {
  return request<{ auto_approve: number; review_floor: number }>("/admin/ops/thresholds", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function fetchMonitoring() {
  return request<MonitoringScreen>("/scientist/monitoring");
}

export function fetchModelVersions() {
  return request<ModelVersionsScreen>("/scientist/model-versions");
}

export function activateModel(runId: string) {
  return request<{ status: string; activeModel: string; runId: string }>(`/scientist/model-versions/${runId}/activate`, {
    method: "POST",
  });
}

export function fetchDatasetLab() {
  return request<DatasetLabScreen>("/scientist/dataset-lab");
}

