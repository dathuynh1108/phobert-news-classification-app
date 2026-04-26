import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ChevronLeft, ChevronRight, Eye } from "lucide-react";

import { fetchLabelReview } from "../lib/api";
import { ReviewListScreen, Tone } from "../lib/types";
import { formatScore, toneForLabel, translateLabel } from "../lib/utils";
import { AppShell, StatCard, Surface, ToneBadge, ToneButton } from "../components/ui";

function statusTone(status?: string): Tone {
  if (status === "auto_approved" || status === "approved") {
    return "green";
  }
  if (status === "review" || status === "queued") {
    return "gold";
  }
  if (status === "escalated" || status === "overridden") {
    return "coral";
  }
  return "muted";
}

export function LabelReviewPage() {
  const [data, setData] = useState<ReviewListScreen | null>(null);
  const [page, setPage] = useState(1);

  useEffect(() => {
    fetchLabelReview(page).then(setData).catch(console.error);
  }, [page]);

  if (!data) {
    return <div className="loading-state">Loading label review...</div>;
  }

  return (
    <AppShell chips={data.chips} heading={data.heading} subheading={data.subheading} sidebar={data.sidebar}>
      <section className="stats-grid">
        {data.stats.map((item, index) => (
          <StatCard item={item} index={index} key={item.label} />
        ))}
      </section>

      <Surface className="table-panel">
        <div className="section-heading">
          <div>
            <h3>Classified stories</h3>
            <p>{data.summary}</p>
          </div>
        </div>
        <div className="data-table-shell">
          <table className="data-table">
            <thead>
              <tr>
                <th>Label</th>
                <th>Article</th>
                <th>Confidence</th>
                <th>Margin</th>
                <th>Status</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {data.items.map((item) => (
                <tr key={item.id}>
                  <td>
                    <ToneBadge tone={toneForLabel(item.label)} subtle>
                      {translateLabel(item.label)}
                    </ToneBadge>
                  </td>
                  <td>
                    <strong className="table-title">{item.title}</strong>
                  </td>
                  <td>{formatScore(item.confidence)}</td>
                  <td>{formatScore(item.margin)}</td>
                  <td>
                    <ToneBadge tone={statusTone(item.status)} subtle>
                      {item.status || "unknown"}
                    </ToneBadge>
                  </td>
                  <td className="table-action-cell">
                    <Link className="icon-link" to={`/editor/review/${item.id}`}>
                      <Eye aria-hidden="true" size={15} />
                      Inspect
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {data.items.length === 0 ? <p className="empty-state table-empty">No classified stories yet.</p> : null}
        </div>
        <div className="pagination-bar">
          <span>
            Page {data.page} of {data.totalPages}
          </span>
          <div className="inline-actions">
            <ToneButton
              className="pagination-button"
              disabled={page <= 1}
              icon={<ChevronLeft aria-hidden="true" size={15} />}
              onClick={() => setPage((value) => Math.max(1, value - 1))}
              tone="muted"
            >
              Previous
            </ToneButton>
            <ToneButton
              className="pagination-button"
              disabled={page >= data.totalPages}
              icon={<ChevronRight aria-hidden="true" size={15} />}
              onClick={() => setPage((value) => value + 1)}
            >
              Next
            </ToneButton>
          </div>
        </div>
      </Surface>
    </AppShell>
  );
}
