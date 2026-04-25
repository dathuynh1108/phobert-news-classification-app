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
  const [password, setPassword] = useState("vnn-password");
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
          by the active PhoBERT package.
        </p>
        <div className="hero-points">
          <span>19-label VietnamNet taxonomy</span>
          <span>Artifact-backed PhoBERT inference only</span>
          <span>Redis + Dramatiq worker for heavy jobs</span>
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
