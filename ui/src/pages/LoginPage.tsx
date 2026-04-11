import { FormEvent, useState, startTransition } from "react";
import { useNavigate } from "react-router-dom";

import { login } from "../lib/api";
import { setSession } from "../lib/session";
import { cn } from "../lib/utils";

const roles = [
  {
    id: "editor-admin" as const,
    title: "Editor / Admin",
    description: "Approve auto-labels and manage the review queue",
  },
  {
    id: "data-scientist" as const,
    title: "Data Scientist",
    description: "Monitor drift, metrics, and model versions",
  },
];

export function LoginPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("editor@vnn-lab.edu.vn");
  const [password, setPassword] = useState("demo-password");
  const [role, setRole] = useState<(typeof roles)[number]["id"]>("editor-admin");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSubmitting(true);
    setError(null);
    try {
      const session = await login({ email, password, role });
      setSession(session);
      startTransition(() => {
        navigate(session.redirect);
      });
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Login failed");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="login-page">
      <section className="login-hero reveal">
        <span className="hero-badge">VietnamNet News Classification</span>
        <h1>Newsroom label routing for Vietnamese content</h1>
        <p>
          Sign in by role to review category predictions, confidence bands, editorial queues, and model quality dashboards powered
          by PhoBERT base v2.
        </p>
        <div className="hero-stats">
          <div className="hero-stat">
            <strong>19 labels</strong>
            <span>VietnamNet desks and categories</span>
          </div>
          <div className="hero-stat">
            <strong>Macro F1 0.82</strong>
            <span>Current PhoBERT package</span>
          </div>
          <div className="hero-stat">
            <strong>128 queued stories</strong>
            <span>Editorial queue today</span>
          </div>
        </div>
        <div className="hero-preview">
          <strong>Dashboard preview</strong>
          <div className="preview-line wide" />
          <div className="preview-line" />
          <div className="preview-line short" />
          <div className="preview-actions">
            <button type="button" className="preview-pill primary" />
            <button type="button" className="preview-pill" />
            <div className="preview-block" />
          </div>
        </div>
      </section>
      <section className="login-panel reveal">
        <form onSubmit={handleSubmit}>
          <header>
            <h2>Login</h2>
            <p>Choose the workspace that matches your role in the newsroom loop.</p>
          </header>
          <label>
            <span>Work email</span>
            <input value={email} onChange={(event) => setEmail(event.target.value)} type="email" required />
          </label>
          <label>
            <span>Password</span>
            <input value={password} onChange={(event) => setPassword(event.target.value)} type="password" required />
          </label>
          <div className="role-list">
            <span className="field-label">Workspace role</span>
            {roles.map((entry) => (
              <button
                type="button"
                key={entry.id}
                className={cn("role-card", role === entry.id && "active")}
                onClick={() => setRole(entry.id)}
              >
                <span className="role-radio" />
                <div>
                  <strong>{entry.title}</strong>
                  <p>{entry.description}</p>
                </div>
              </button>
            ))}
          </div>
          {error ? <p className="inline-error">{error}</p> : null}
          <button className="login-submit" disabled={isSubmitting} type="submit">
            <span className="dot" />
            {isSubmitting ? "Signing in..." : "Enter workspace"}
          </button>
        </form>
      </section>
    </main>
  );
}
