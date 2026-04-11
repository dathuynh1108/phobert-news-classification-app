import { SessionState } from "./types";

const SESSION_KEY = "vnn-ml-session";

export function getSession(): SessionState | null {
  const raw = window.localStorage.getItem(SESSION_KEY);
  if (!raw) {
    return null;
  }
  try {
    return JSON.parse(raw) as SessionState;
  } catch {
    return null;
  }
}

export function setSession(session: SessionState): void {
  window.localStorage.setItem(SESSION_KEY, JSON.stringify(session));
}

export function clearSession(): void {
  window.localStorage.removeItem(SESSION_KEY);
}

