import { useEffect, useState } from "react";
import { ChevronLeft, ChevronRight, Eye, Pencil, Rocket, Save, UserPlus } from "lucide-react";

import { fetchAdminOps, inviteUser, previewThresholdImpact, promoteModelFromAdmin, updateThresholds, updateUser } from "../lib/api";
import { AdminOpsScreen, RoleType, ThresholdImpact } from "../lib/types";
import { AppShell, ProgressList, Surface, ToneBadge, ToneButton } from "../components/ui";

function statusLabel(status: string) {
  return status === "Active" ? "online" : "idle";
}

function roleValue(role: string): RoleType {
  if (role === "Admin") {
    return "admin";
  }
  if (role === "Data Scientist") {
    return "data-scientist";
  }
  return "editor";
}

function ImpactPreview({ impact }: { impact: ThresholdImpact }) {
  return (
    <div className="impact-preview">
      <div>
        <span>Auto-ready</span>
        <strong>{impact.autoReady}</strong>
        <small>{Math.round(impact.autoRate * 100)}%</small>
      </div>
      <div>
        <span>Manual review</span>
        <strong>{impact.needsReview}</strong>
        <small>{Math.round(impact.reviewRate * 100)}%</small>
      </div>
      <div>
        <span>Escalate to DS</span>
        <strong>{impact.escalated}</strong>
        <small>{Math.round(impact.escalationRate * 100)}%</small>
      </div>
    </div>
  );
}

export function AdminOpsPage() {
  const [data, setData] = useState<AdminOpsScreen | null>(null);
  const [autoApprove, setAutoApprove] = useState(0.75);
  const [reviewFloor, setReviewFloor] = useState(0.68);
  const [thresholdImpact, setThresholdImpact] = useState<ThresholdImpact | null>(null);
  const [userPage, setUserPage] = useState(1);
  const [auditPage, setAuditPage] = useState(1);
  const [isSavingRules, setIsSavingRules] = useState(false);
  const [isPreviewingRules, setIsPreviewingRules] = useState(false);
  const [isPromoting, setIsPromoting] = useState(false);
  const [inviteOpen, setInviteOpen] = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteName, setInviteName] = useState("");
  const [inviteRole, setInviteRole] = useState<RoleType>("editor");
  const [inviteQueue, setInviteQueue] = useState("All queues");
  const [invitePassword, setInvitePassword] = useState("vnn-password");
  const [isInviting, setIsInviting] = useState(false);
  const [editingEmail, setEditingEmail] = useState("");
  const [editName, setEditName] = useState("");
  const [editRole, setEditRole] = useState<RoleType>("editor");
  const [editQueue, setEditQueue] = useState("");
  const [editStatus, setEditStatus] = useState("Active");
  const [editPassword, setEditPassword] = useState("");
  const [isUpdatingUser, setIsUpdatingUser] = useState(false);

  async function load(nextUserPage = userPage, nextAuditPage = auditPage) {
    const payload = await fetchAdminOps({ userPage: nextUserPage, auditPage: nextAuditPage });
    setData(payload);
    setAutoApprove(payload.thresholds.autoApprove);
    setReviewFloor(payload.thresholds.reviewFloor);
    setThresholdImpact(payload.thresholdImpact);
  }

  useEffect(() => {
    load(userPage, auditPage).catch(console.error);
  }, [userPage, auditPage]);

  if (!data) {
    return <div className="loading-state">Loading admin operations...</div>;
  }

  function openEdit(user: AdminOpsScreen["users"][number]) {
    setEditingEmail(user.email);
    setEditName(user.name);
    setEditRole(roleValue(user.role));
    setEditQueue(user.queue);
    setEditStatus(user.status);
    setEditPassword("");
  }

  async function handleSave() {
    setIsSavingRules(true);
    try {
      const next = await updateThresholds({ autoApprove, reviewFloor });
      setAutoApprove(next.autoApprove);
      setReviewFloor(next.reviewFloor);
      await load();
    } finally {
      setIsSavingRules(false);
    }
  }

  async function handlePreviewImpact() {
    setIsPreviewingRules(true);
    try {
      setThresholdImpact(await previewThresholdImpact({ autoApprove, reviewFloor }));
    } finally {
      setIsPreviewingRules(false);
    }
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
      setUserPage(1);
      await load(1, auditPage);
      setInviteEmail("");
      setInviteName("");
      setInviteRole("editor");
      setInviteQueue("All queues");
      setInvitePassword("vnn-password");
      setInviteOpen(false);
    } finally {
      setIsInviting(false);
    }
  }

  async function handleUpdateUser() {
    if (!editingEmail) {
      return;
    }
    setIsUpdatingUser(true);
    try {
      await updateUser(editingEmail, {
        name: editName,
        role: editRole,
        queue: editQueue,
        status: editStatus,
        ...(editPassword ? { password: editPassword } : {}),
      });
      setEditingEmail("");
      await load();
    } finally {
      setIsUpdatingUser(false);
    }
  }

  async function handlePromote() {
    const candidate = data?.candidateModelRun;
    if (!candidate) {
      return;
    }
    setIsPromoting(true);
    try {
      await promoteModelFromAdmin(candidate.id);
      await load();
    } finally {
      setIsPromoting(false);
    }
  }

  return (
    <AppShell chips={data.chips} heading={data.heading} subheading={data.subheading} sidebar={data.sidebar}>
      <div className="two-column">
        <Surface className="table-panel">
          <div className="section-heading">
            <div>
              <h3>Users & permissions</h3>
              <p>{data.userPagination.summary}</p>
            </div>
            <ToneButton className="compact-button" icon={<UserPlus aria-hidden="true" size={15} />} onClick={() => setInviteOpen((value) => !value)}>
              Create user
            </ToneButton>
          </div>
          {inviteOpen ? (
            <div className="inline-form admin-form">
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
                <select value={inviteRole} onChange={(event) => setInviteRole(event.target.value as RoleType)}>
                  <option value="editor">Editor</option>
                  <option value="admin">Admin</option>
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
              <ToneButton disabled={isInviting || !inviteEmail || invitePassword.length < 8} icon={<UserPlus aria-hidden="true" size={15} />} onClick={handleInvite}>
                {isInviting ? "Creating..." : "Create user"}
              </ToneButton>
            </div>
          ) : null}
          {editingEmail ? (
            <div className="inline-form admin-form edit-panel">
              <label>
                <span>Edit account</span>
                <input readOnly value={editingEmail} />
              </label>
              <label>
                <span>Name</span>
                <input value={editName} onChange={(event) => setEditName(event.target.value)} />
              </label>
              <label>
                <span>Role</span>
                <select value={editRole} onChange={(event) => setEditRole(event.target.value as RoleType)}>
                  <option value="editor">Editor</option>
                  <option value="admin">Admin</option>
                  <option value="data-scientist">Data Scientist</option>
                </select>
              </label>
              <label>
                <span>Queue</span>
                <input value={editQueue} onChange={(event) => setEditQueue(event.target.value)} />
              </label>
              <label>
                <span>Status</span>
                <select value={editStatus} onChange={(event) => setEditStatus(event.target.value)}>
                  <option value="Active">Active</option>
                  <option value="Standby">Standby</option>
                </select>
              </label>
              <label>
                <span>New password</span>
                <input placeholder="Leave blank to keep current" type="password" value={editPassword} onChange={(event) => setEditPassword(event.target.value)} />
              </label>
              <div className="inline-actions">
                <ToneButton disabled={isUpdatingUser} icon={<Save aria-hidden="true" size={15} />} onClick={handleUpdateUser}>
                  {isUpdatingUser ? "Updating..." : "Update user"}
                </ToneButton>
                <ToneButton tone="muted" onClick={() => setEditingEmail("")}>Cancel</ToneButton>
              </div>
            </div>
          ) : null}
          <div className="data-table-shell">
            <table className="data-table admin-users-table">
              <thead>
                <tr>
                  <th>User</th>
                  <th>Role</th>
                  <th>Queue</th>
                  <th>Status</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {data.users.map((user) => (
                  <tr className={editingEmail === user.email ? "selected-row" : undefined} key={user.email}>
                    <td>
                      <strong className="table-title">{user.name}</strong>
                      <small className="table-subtitle">{user.email}</small>
                    </td>
                    <td>{user.role}</td>
                    <td>{user.queue}</td>
                    <td>
                      <ToneBadge tone={user.status === "Active" ? "green" : "muted"} subtle>{statusLabel(user.status)}</ToneBadge>
                    </td>
                    <td className="table-action-cell">
                      <ToneButton className="pagination-button" icon={<Pencil aria-hidden="true" size={15} />} onClick={() => openEdit(user)} tone="muted">
                        Edit
                      </ToneButton>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="pagination-bar">
            <span>
              Page {data.userPagination.page} of {data.userPagination.totalPages}
            </span>
            <div className="inline-actions">
              <ToneButton className="pagination-button" disabled={userPage <= 1} icon={<ChevronLeft aria-hidden="true" size={15} />} onClick={() => setUserPage((value) => Math.max(1, value - 1))} tone="muted">
                Previous
              </ToneButton>
              <ToneButton className="pagination-button" disabled={userPage >= data.userPagination.totalPages} icon={<ChevronRight aria-hidden="true" size={15} />} onClick={() => setUserPage((value) => value + 1)}>
                Next
              </ToneButton>
            </div>
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
          {thresholdImpact ? <ImpactPreview impact={thresholdImpact} /> : null}
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
              <ToneButton disabled={isSavingRules} icon={<Save aria-hidden="true" size={15} />} onClick={handleSave}>
                {isSavingRules ? "Saving..." : "Update rules"}
              </ToneButton>
              <ToneButton disabled={isPreviewingRules} icon={<Eye aria-hidden="true" size={15} />} onClick={handlePreviewImpact} tone="muted">
                {isPreviewingRules ? "Previewing..." : "Preview impact"}
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
              <p>{data.auditPagination.summary}</p>
            </div>
          </div>
          <ul className="detail-list">
            {data.auditLog.map((entry, index) => (
              <li key={`${entry}-${index}`}>{entry}</li>
            ))}
          </ul>
          <div className="pagination-bar embedded-pagination">
            <span>
              Page {data.auditPagination.page} of {data.auditPagination.totalPages}
            </span>
            <div className="inline-actions">
              <ToneButton className="pagination-button" disabled={auditPage <= 1} icon={<ChevronLeft aria-hidden="true" size={15} />} onClick={() => setAuditPage((value) => Math.max(1, value - 1))} tone="muted">
                Previous
              </ToneButton>
              <ToneButton className="pagination-button" disabled={auditPage >= data.auditPagination.totalPages} icon={<ChevronRight aria-hidden="true" size={15} />} onClick={() => setAuditPage((value) => value + 1)}>
                Next
              </ToneButton>
            </div>
          </div>
        </Surface>

        <Surface>
          <div className="section-heading">
            <div>
              <h3>Deployment snapshot</h3>
              <p>The current package, config files, user load, and exported documents.</p>
            </div>
            <ToneButton disabled={!data.candidateModelRun || isPromoting} icon={<Rocket aria-hidden="true" size={15} />} onClick={handlePromote} tone="muted">
              {isPromoting ? "Promoting..." : data.candidateModelRun ? `Promote ${data.candidateModelRun.id}` : "No package"}
            </ToneButton>
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
