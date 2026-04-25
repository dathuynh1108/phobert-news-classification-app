import { useEffect, useState } from "react";

import { fetchAdminOps, inviteUser, promoteModelFromAdmin, updateThresholds } from "../lib/api";
import { AdminOpsScreen } from "../lib/types";
import { AppShell, ProgressList, Surface, ToneBadge, ToneButton } from "../components/ui";

export function AdminOpsPage() {
  const [data, setData] = useState<AdminOpsScreen | null>(null);
  const [autoApprove, setAutoApprove] = useState(0.75);
  const [reviewFloor, setReviewFloor] = useState(0.68);
  const [isPromoting, setIsPromoting] = useState(false);
  const [inviteOpen, setInviteOpen] = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteName, setInviteName] = useState("");
  const [inviteRole, setInviteRole] = useState<"editor-admin" | "data-scientist">("editor-admin");
  const [inviteQueue, setInviteQueue] = useState("All queues");
  const [invitePassword, setInvitePassword] = useState("vnn-password");
  const [isInviting, setIsInviting] = useState(false);

  function statusLabel(status: string) {
    return status === "Active" ? "online" : "idle";
  }

  useEffect(() => {
    fetchAdminOps()
      .then((payload) => {
        setData(payload);
        setAutoApprove(payload.thresholds.auto_approve);
        setReviewFloor(payload.thresholds.review_floor);
      })
      .catch(console.error);
  }, []);

  if (!data) {
    return <div className="loading-state">Loading admin operations...</div>;
  }

  async function handleSave() {
    const next = await updateThresholds({ auto_approve: autoApprove, review_floor: reviewFloor });
    setAutoApprove(next.auto_approve);
    setReviewFloor(next.review_floor);
    setData(await fetchAdminOps());
  }

  async function handleInvite() {
    if (!inviteEmail || !invitePassword) {
      return;
    }
    setIsInviting(true);
    try {
      await inviteUser({
        email: inviteEmail,
        name: inviteName || inviteEmail,
        password: invitePassword,
        role: inviteRole,
        queue: inviteQueue,
      });
      setData(await fetchAdminOps());
      setInviteEmail("");
      setInviteName("");
      setInviteRole("editor-admin");
      setInviteQueue("All queues");
      setInvitePassword("vnn-password");
      setInviteOpen(false);
    } finally {
      setIsInviting(false);
    }
  }

  async function handlePromote() {
    if (!data?.candidateModelRun) {
      return;
    }
    setIsPromoting(true);
    try {
      await promoteModelFromAdmin(data.candidateModelRun.id);
      setData(await fetchAdminOps());
    } finally {
      setIsPromoting(false);
    }
  }

  return (
    <AppShell chips={data.chips} heading={data.heading} subheading={data.subheading} sidebar={data.sidebar}>
      <div className="two-column">
        <Surface>
          <div className="section-heading">
            <div>
              <h3>Users & permissions</h3>
              <p>Track who is handling each queue and who can promote a package.</p>
            </div>
            <ToneButton className="compact-button" onClick={() => setInviteOpen((value) => !value)}>
              Invite user
            </ToneButton>
          </div>
          {inviteOpen ? (
            <div className="inline-form">
              <label>
                <span>Work email</span>
                <input value={inviteEmail} onChange={(event) => setInviteEmail(event.target.value)} type="email" />
              </label>
              <label>
                <span>Name</span>
                <input value={inviteName} onChange={(event) => setInviteName(event.target.value)} />
              </label>
              <label>
                <span>Role</span>
                <select value={inviteRole} onChange={(event) => setInviteRole(event.target.value as "editor-admin" | "data-scientist")}>
                  <option value="editor-admin">Editor / Admin</option>
                  <option value="data-scientist">Data Scientist</option>
                </select>
              </label>
              <label>
                <span>Queue</span>
                <input value={inviteQueue} onChange={(event) => setInviteQueue(event.target.value)} />
              </label>
              <label>
                <span>Temporary password</span>
                <input value={invitePassword} onChange={(event) => setInvitePassword(event.target.value)} type="password" />
              </label>
              <ToneButton disabled={isInviting || !inviteEmail || invitePassword.length < 8} onClick={handleInvite}>
                {isInviting ? "Inviting..." : "Create user"}
              </ToneButton>
            </div>
          ) : null}
          <div className="table-shell">
            <table>
              <thead>
                <tr>
                  <th>User</th>
                  <th>Role</th>
                  <th>Queue</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {data.users.map((user) => (
                  <tr key={user.name}>
                    <td>{user.name}</td>
                    <td>{user.role}</td>
                    <td>{user.queue}</td>
                    <td>
                      <ToneBadge tone={user.status === "Active" ? "green" : "muted"}>{statusLabel(user.status)}</ToneBadge>
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
              <h3>Confidence routing</h3>
              <p>Threshold bands decide whether a story is auto-approved, queued for review, or sent to Data Science.</p>
            </div>
          </div>
          <ProgressList items={data.routingRules} />
          <div className="slider-stack">
            <label>
              <span>Auto-approve: {autoApprove.toFixed(2)}</span>
              <input max="0.95" min="0.60" onChange={(event) => setAutoApprove(Number(event.target.value))} step="0.01" type="range" value={autoApprove} />
            </label>
            <label>
              <span>Review floor: {reviewFloor.toFixed(2)}</span>
              <input max="0.85" min="0.50" onChange={(event) => setReviewFloor(Number(event.target.value))} step="0.01" type="range" value={reviewFloor} />
            </label>
            <div className="inline-actions">
              <ToneButton onClick={handleSave}>Save rules</ToneButton>
              <ToneButton disabled={!data.candidateModelRun || isPromoting} onClick={handlePromote} tone="muted">
                {isPromoting ? "Promoting..." : data.candidateModelRun ? `Promote ${data.candidateModelRun.id}` : "No package"}
              </ToneButton>
            </div>
          </div>
        </Surface>
      </div>

      <div className="two-column lower-panels">
        <Surface>
          <div className="section-heading">
            <div>
              <h3>Audit log</h3>
              <p>Recent actions that changed routing rules, thresholds, or the live package.</p>
            </div>
          </div>
          <ul className="detail-list">
            {data.auditLog.map((entry) => (
              <li key={entry}>{entry}</li>
            ))}
          </ul>
        </Surface>

        <Surface>
          <div className="section-heading">
            <div>
              <h3>Deployment snapshot</h3>
              <p>The current package, config files, user load, and exported documents.</p>
            </div>
          </div>
          <div className="snapshot-grid">
            {data.deploymentSnapshot.map((item) => (
              <div className="snapshot-card reveal" key={item.label}>
                <span>{item.label}</span>
                <strong>{item.value}</strong>
              </div>
            ))}
          </div>
        </Surface>
      </div>
    </AppShell>
  );
}
