import { RoleType, SessionState } from "./types";

const SESSION_KEY = "vnn-ml-session";
const VALID_ROLES = new Set<RoleType>(["editor", "admin", "data-scientist"]);

export function getSession(): SessionState | null {
  const raw = window.localStorage.getItem(SESSION_KEY);
  if (!raw) {
    return null;
  }
  try {
    const session = JSON.parse(raw) as SessionState;
    if (!VALID_ROLES.has(session.role)) {
      clearSession();
      return null;
    }
    return {
      ...session,
      name: session.name || session.email,
      displayRole: session.displayRole || session.role,
    };
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
