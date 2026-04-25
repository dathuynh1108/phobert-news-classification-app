import { BrowserRouter, Navigate, Outlet, Route, Routes, useLocation } from "react-router-dom";

import { logout } from "../lib/api";
import { clearSession, getSession } from "../lib/session";
import { RoleType } from "../lib/types";
import { defaultPathForRole, isPathAllowedForRole } from "../lib/utils";
import { AdminOpsPage } from "../pages/AdminOpsPage";
import { ArticleReviewPage } from "../pages/ArticleReviewPage";
import { DatasetLabPage } from "../pages/DatasetLabPage";
import { EditorDashboardPage } from "../pages/EditorDashboardPage";
import { LoginPage } from "../pages/LoginPage";
import { ModelVersionsPage } from "../pages/ModelVersionsPage";
import { MonitoringPage } from "../pages/MonitoringPage";

function RequireSession() {
  const session = getSession();
  const location = useLocation();
  if (!session) {
    return <Navigate replace state={{ from: location.pathname }} to="/" />;
  }
  return (
    <div>
      <header className="floating-logout">
        <button onClick={() => {
          logout().catch(console.error);
          clearSession();
          window.location.assign("/");
        }} type="button">
          Sign out
        </button>
      </header>
      <Outlet />
    </div>
  );
}

function RequireRole({ role }: { role: RoleType }) {
  const session = getSession();
  const location = useLocation();
  if (!session) {
    return <Navigate replace state={{ from: location.pathname }} to="/" />;
  }
  if (session.role !== role || !isPathAllowedForRole(location.pathname, session.role)) {
    return <Navigate replace to={defaultPathForRole(session.role)} />;
  }
  return <Outlet />;
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<LoginPage />} path="/" />
        <Route element={<RequireSession />}>
          <Route element={<RequireRole role="editor-admin" />}>
            <Route element={<EditorDashboardPage />} path="/editor/dashboard" />
            <Route element={<ArticleReviewPage />} path="/editor/review/:articleId" />
            <Route element={<AdminOpsPage />} path="/editor/admin" />
          </Route>
          <Route element={<RequireRole role="data-scientist" />}>
            <Route element={<MonitoringPage />} path="/scientist/monitoring" />
            <Route element={<ModelVersionsPage />} path="/scientist/versions" />
            <Route element={<DatasetLabPage />} path="/scientist/dataset" />
          </Route>
        </Route>
        <Route element={<Navigate replace to="/" />} path="*" />
      </Routes>
    </BrowserRouter>
  );
}
