import { type CSSProperties, type PropsWithChildren, type ReactNode, useState } from "react";
import { Link } from "react-router-dom";
import {
  Activity,
  AlertTriangle,
  BadgeCheck,
  BarChart3,
  Brain,
  ChevronDown,
  ClipboardList,
  Database,
  Gauge,
  LayoutDashboard,
  ListChecks,
  LogOut,
  Package,
  Shield,
  Tags,
  TrendingUp,
  UserCircle,
  Users,
  type LucideIcon,
} from "lucide-react";

import { logout } from "../lib/api";
import { SidebarData, StatCardData, Tone } from "../lib/types";
import { clearSession, getSession } from "../lib/session";
import { cn, formatPercent, formatScore, hrefForSidebarItem, toneClassMap } from "../lib/utils";

export function Surface({ className, children }: PropsWithChildren<{ className?: string }>) {
  return <section className={cn("surface reveal", className)}>{children}</section>;
}

export function ToneBadge({ tone, children, subtle = false }: PropsWithChildren<{ tone: Tone; subtle?: boolean }>) {
  return <span className={cn("tone-badge", toneClassMap[tone], subtle && "subtle")}>{children}</span>;
}

const sidebarIconMap: Record<string, LucideIcon> = {
  dashboard: LayoutDashboard,
  review: ClipboardList,
  classifier: Tags,
  admin: Shield,
  monitoring: Activity,
  versions: Package,
  dataset: Database,
};

function iconForStat(label: string): LucideIcon {
  const normalized = label.toLowerCase();
  if (normalized.includes("review")) {
    return ClipboardList;
  }
  if (normalized.includes("auto") || normalized.includes("coverage")) {
    return BadgeCheck;
  }
  if (normalized.includes("confidence")) {
    return Gauge;
  }
  if (normalized.includes("prediction")) {
    return Brain;
  }
  if (normalized.includes("decision") || normalized.includes("account")) {
    return Users;
  }
  if (normalized.includes("f1") || normalized.includes("drift")) {
    return TrendingUp;
  }
  if (normalized.includes("error") || normalized.includes("low")) {
    return AlertTriangle;
  }
  if (normalized.includes("stored") || normalized.includes("corpus") || normalized.includes("stories")) {
    return Database;
  }
  return BarChart3;
}

export function ToneButton({
  tone = "navy",
  children,
  className,
  icon,
  ...props
}: PropsWithChildren<React.ButtonHTMLAttributes<HTMLButtonElement> & { tone?: Tone; icon?: ReactNode }>) {
  return (
    <button className={cn("tone-button", toneClassMap[tone], className)} {...props}>
      {icon ? <span className="button-icon">{icon}</span> : null}
      {children}
    </button>
  );
}

export function AppShell({
  chips,
  heading,
  subheading,
  sidebar,
  children,
}: PropsWithChildren<{
  chips: Array<{ label: string; tone: Tone }>;
  heading: string;
  subheading: string;
  sidebar: SidebarData;
}>) {
  const session = getSession();
  const [menuOpen, setMenuOpen] = useState(false);
  const sidebarItems = sidebar.items.flatMap((item) => {
    const href = hrefForSidebarItem(item.id, session?.role);
    return href ? [{ ...item, href }] : [];
  });
  const displayName = session?.name || session?.email || "Account";
  const displayRole = session?.displayRole || session?.role || "";

  function handleLogout() {
    logout().catch(() => undefined);
    clearSession();
    window.location.assign("/");
  }

  return (
    <div className="screen-shell">
      <header className="screen-header reveal">
        <div className="screen-topbar">
          <div className="chip-row">
            {chips.map((chip) => (
              <ToneBadge key={chip.label} tone={chip.tone} subtle>
                {chip.label}
              </ToneBadge>
            ))}
          </div>
          {session ? (
            <div className="user-menu">
              <button aria-expanded={menuOpen} aria-haspopup="menu" aria-label="Account menu" className="user-menu-trigger" onClick={() => setMenuOpen((value) => !value)} type="button">
                <UserCircle aria-hidden="true" size={17} />
                <span>{displayName}</span>
                <ChevronDown aria-hidden="true" className={menuOpen ? "rotated" : undefined} size={15} />
              </button>
              {menuOpen ? (
                <div className="user-menu-popover" role="menu">
                  <div className="user-menu-meta">
                    <strong>{displayName}</strong>
                    <span>{displayRole}</span>
                  </div>
                  <button onClick={handleLogout} role="menuitem" type="button">
                    <LogOut aria-hidden="true" size={15} />
                    Sign out
                  </button>
                </div>
              ) : null}
            </div>
          ) : null}
        </div>
        <h1>{heading}</h1>
        <p>{subheading}</p>
      </header>
      <div className="workspace-grid">
        <aside className="sidebar reveal">
          <div className="brand-lockup">
            <span className="brand-mark" />
            <strong>{sidebar.brand}</strong>
          </div>
          <div className="sidebar-role">
            <small>Current role</small>
            <strong>{sidebar.currentRole}</strong>
            <span>{sidebar.activeModel}</span>
          </div>
          <nav className="sidebar-nav">
            {sidebarItems.map((item) => {
              const Icon = sidebarIconMap[item.id] ?? ListChecks;
              return (
                <Link key={item.id} className={cn("sidebar-link", item.active && "active")} to={item.href}>
                  <Icon aria-hidden="true" size={16} strokeWidth={2} />
                  {item.label}
                </Link>
              );
            })}
          </nav>
          <div className="sidebar-summary">
            <small>{sidebar.summaryTitle}</small>
            <strong>{sidebar.summaryValue}</strong>
            <span>{sidebar.summaryBody}</span>
          </div>
        </aside>
        <main className="workspace-content">{children}</main>
      </div>
    </div>
  );
}

export function StatCard({ item, index }: { item: StatCardData; index: number }) {
  const Icon = iconForStat(item.label);
  return (
    <Surface className="stat-card" >
      <span className={cn("stat-icon", toneClassMap[item.tone])} style={{ animationDelay: `${index * 70}ms` }}>
        <Icon aria-hidden="true" size={17} strokeWidth={2.1} />
      </span>
      <span className="stat-label">{item.label}</span>
      <strong className="stat-value">{item.value}</strong>
      <span className={cn("stat-delta", toneClassMap[item.tone])}>{item.delta}</span>
    </Surface>
  );
}

export function ProgressList({
  items,
  suffix = "value",
  compact = false,
}: {
  items: Array<{ label: string; value: number; tone: Tone }>;
  suffix?: "value" | "percent";
  compact?: boolean;
}) {
  if (!items.length) {
    return <p className="empty-state">N/A</p>;
  }

  return (
    <div className={cn("progress-list", compact && "compact")}>
      {items.map((item, index) => (
        <div className="progress-row reveal" key={item.label} style={{ animationDelay: `${index * 60}ms` }}>
          <span>{item.label}</span>
          <div className="progress-track">
            <div className={cn("progress-fill", toneClassMap[item.tone])} style={{ width: `${item.value * 100}%` }} />
          </div>
          <strong>{suffix === "percent" ? formatPercent(item.value) : formatScore(item.value)}</strong>
        </div>
      ))}
    </div>
  );
}

export function VerticalBars({ values }: { values: number[] }) {
  if (!values.length) {
    return <p className="empty-state">N/A</p>;
  }

  return (
    <div className="spark-bars">
      {values.map((value, index) => (
        <div className="spark-bar-shell" key={`${value}-${index}`}>
          <div className="spark-bar" style={{ height: `${Math.max(16, value * 160)}px` }} />
        </div>
      ))}
    </div>
  );
}

export function HeatMatrix({ values, labels }: { values: number[][]; labels?: string[] }) {
  if (!values.length) {
    return <p className="empty-state">N/A</p>;
  }

  const hasLabels = Boolean(labels?.length);
  const columns = values[0]?.length ?? 1;
  const maxValue = Math.max(...values.flat(), 1);
  const gridStyle: CSSProperties = {
    gridTemplateColumns: hasLabels ? `minmax(8rem, 1.25fr) repeat(${labels?.length ?? columns}, minmax(3rem, 1fr))` : `repeat(${columns}, minmax(0, 1fr))`,
  };

  function opacityFor(cell: number) {
    const normalized = maxValue > 1 ? cell / maxValue : cell;
    return Math.max(0.08, Math.min(0.92, normalized));
  }

  if (hasLabels && labels) {
    return (
      <div className="heat-matrix-scroll">
        <div className="heat-matrix labeled" style={gridStyle}>
          <div className="heat-axis heat-corner">Actual / Pred</div>
          {labels.map((label) => (
            <div className="heat-axis heat-axis-column" key={`pred-${label}`} title={label}>
              {label}
            </div>
          ))}
          {values.flatMap((row, rowIndex) => [
            <div className="heat-axis heat-axis-row" key={`actual-${labels[rowIndex]}`} title={labels[rowIndex]}>
              {labels[rowIndex]}
            </div>,
            ...row.map((cell, cellIndex) => (
              <div
                className="heat-cell reveal"
                key={`${rowIndex}-${cellIndex}`}
                style={{
                  background: `rgba(24, 59, 107, ${opacityFor(cell)})`,
                  animationDelay: `${(rowIndex * row.length + cellIndex) * 18}ms`,
                }}
                title={`${labels[rowIndex]} predicted as ${labels[cellIndex]}: ${cell}`}
              >
                {cell}
              </div>
            )),
          ])}
        </div>
      </div>
    );
  }

  return (
    <div className="heat-matrix" style={gridStyle}>
      {values.flatMap((row, rowIndex) =>
        row.map((cell, cellIndex) => (
          <div
            key={`${rowIndex}-${cellIndex}`}
            className="heat-cell reveal"
            style={{
              background: `rgba(24, 59, 107, ${opacityFor(cell)})`,
              animationDelay: `${(rowIndex * row.length + cellIndex) * 24}ms`,
            }}
          />
        )),
      )}
    </div>
  );
}
