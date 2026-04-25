import { PropsWithChildren } from "react";
import { Link } from "react-router-dom";

import { SidebarData, StatCardData, Tone } from "../lib/types";
import { getSession } from "../lib/session";
import { cn, formatPercent, formatScore, hrefForSidebarItem, toneClassMap } from "../lib/utils";

export function Surface({ className, children }: PropsWithChildren<{ className?: string }>) {
  return <section className={cn("surface reveal", className)}>{children}</section>;
}

export function ToneBadge({ tone, children, subtle = false }: PropsWithChildren<{ tone: Tone; subtle?: boolean }>) {
  return <span className={cn("tone-badge", toneClassMap[tone], subtle && "subtle")}>{children}</span>;
}

export function ToneButton({
  tone = "navy",
  children,
  className,
  ...props
}: PropsWithChildren<React.ButtonHTMLAttributes<HTMLButtonElement> & { tone?: Tone }>) {
  return (
    <button className={cn("tone-button", toneClassMap[tone], className)} {...props}>
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
  const sidebarItems = sidebar.items.flatMap((item) => {
    const href = hrefForSidebarItem(item.id, session?.role);
    return href ? [{ ...item, href }] : [];
  });

  return (
    <div className="screen-shell">
      <header className="screen-header reveal">
        <div className="chip-row">
          {chips.map((chip) => (
            <ToneBadge key={chip.label} tone={chip.tone} subtle>
              {chip.label}
            </ToneBadge>
          ))}
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
            {sidebarItems.map((item) => (
              <Link key={item.id} className={cn("sidebar-link", item.active && "active")} to={item.href}>
                <span className="sidebar-dot" />
                {item.label}
              </Link>
            ))}
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
  return (
    <Surface className="stat-card" >
      <div className={cn("stat-icon", toneClassMap[item.tone])} style={{ animationDelay: `${index * 70}ms` }} />
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

export function HeatMatrix({ values }: { values: number[][] }) {
  return (
    <div className="heat-matrix">
      {values.flatMap((row, rowIndex) =>
        row.map((cell, cellIndex) => (
          <div
            key={`${rowIndex}-${cellIndex}`}
            className="heat-cell reveal"
            style={{
              background: `rgba(24, 59, 107, ${Math.max(0.08, Math.min(0.92, cell))})`,
              animationDelay: `${(rowIndex * row.length + cellIndex) * 24}ms`,
            }}
          />
        )),
      )}
    </div>
  );
}
