import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { AlertTriangle, CheckCircle2, Play, RotateCcw } from "lucide-react";

import { fetchReviewArticle, inferArticle, refreshArticleFromUrl, submitDecision } from "../lib/api";
import { InferenceResponse, ReviewArticleScreen } from "../lib/types";
import { formatScore, translateLabel } from "../lib/utils";
import { AppShell, ProgressList, Surface, ToneBadge, ToneButton } from "../components/ui";

export function ArticleReviewPage() {
  const { articleId } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState<ReviewArticleScreen | null>(null);
  const [selectedLabel, setSelectedLabel] = useState("");
  const [sourceUrl, setSourceUrl] = useState("");
  const [notes, setNotes] = useState("");
  const [lastInference, setLastInference] = useState<InferenceResponse | null>(null);
  const [isInferring, setIsInferring] = useState(false);

  useEffect(() => {
    if (!articleId) {
      navigate("/editor/review");
      return;
    }
    fetchReviewArticle(articleId)
      .then((payload) => {
        setData(payload);
        setSelectedLabel(payload.decisionControls.primaryLabel);
        setSourceUrl(payload.article.url);
        setLastInference(null);
      })
      .catch(console.error);
  }, [articleId, navigate]);

  const content = useMemo(() => data?.article.paragraphs.join("\n\n") ?? "", [data]);

  if (!data) {
    return <div className="loading-state">Loading article review...</div>;
  }

  const ranking = lastInference?.candidates ?? data.candidateRanking;
  const predictionLabel = lastInference?.label ?? data.predictionSummary.label;
  const predictionConfidence = lastInference?.confidence ?? data.predictionSummary.confidence;
  const decisionLabel = lastInference
    ? {
        "auto-approve": "auto-approved",
        review: "under review",
        escalate: "escalated",
      }[lastInference.autoDecision] ?? lastInference.autoDecision
    : null;

  async function handleInference() {
    if (!data) {
      return;
    }
    setIsInferring(true);
    try {
      if (sourceUrl && sourceUrl !== data.article.url) {
        const refreshed = await refreshArticleFromUrl(data.article.id, {
          sourceUrl,
          topK: 3,
        });
        setData(refreshed);
        setSelectedLabel(refreshed.decisionControls.primaryLabel);
        setLastInference(null);
        return;
      }
      const result = await inferArticle(data.article.id, {
        title: data.article.title,
        content,
        sourceUrl,
        topK: 3,
      });
      setLastInference(result);
      setSelectedLabel(result.label);
    } finally {
      setIsInferring(false);
    }
  }

  async function handleDecision(action: "approve" | "override" | "escalate") {
    if (!data) {
      return;
    }
    await submitDecision(data.article.id, {
      action,
      selected_label: action === "override" ? selectedLabel : predictionLabel,
      notes,
    });
    navigate("/editor/review");
  }

  return (
    <AppShell chips={data.chips} heading={data.heading} subheading={data.subheading} sidebar={data.sidebar}>
      <Surface className="review-topbar">
        <label className="review-url">
          <span>Source URL</span>
          <input value={sourceUrl} onChange={(event) => setSourceUrl(event.target.value)} />
        </label>
        <div className="inline-actions">
          <ToneButton icon={<Play aria-hidden="true" size={15} />} onClick={handleInference}>{isInferring ? "Running..." : "Run inference"}</ToneButton>
          <ToneButton icon={<AlertTriangle aria-hidden="true" size={15} />} tone="coral" onClick={() => handleDecision("escalate")}>
            Escalate
          </ToneButton>
        </div>
      </Surface>

      <div className="review-grid">
        <Surface className="article-column">
          <div className="section-heading">
            <div>
              <h3>Article content</h3>
              <p>Read the story, inspect the rationale, and compare similar cases before confirming the label.</p>
            </div>
          </div>
          <article className="article-body">
            <h2>{data.article.title}</h2>
            <span className="article-meta">{data.article.source}</span>
            {data.article.paragraphs.map((paragraph) => (
              <p key={paragraph}>{paragraph}</p>
            ))}
          </article>
          {data.article.rationaleBlocks.map((block) => (
            <div className="analysis-block reveal" key={block.title}>
              <strong>{block.title}</strong>
              <span>{block.body}</span>
              <div className="chip-row">
                {block.chips.map((chip, index) => (
                  <ToneBadge key={chip} tone={index === 0 ? "navy" : index === 1 ? "teal" : "coral"} subtle>
                    {chip}
                  </ToneBadge>
                ))}
              </div>
              <ul className="detail-list">
                {block.bullets.map((bullet) => (
                  <li key={bullet}>{bullet}</li>
                ))}
              </ul>
            </div>
          ))}
          <div className="similar-card reveal">
            <strong>Similar stories & history</strong>
            {data.article.similarArticles.map((item) => (
              <div className="similar-row" key={item.title}>
                <div>
                  <span>{item.title}</span>
                  <small>{item.note}</small>
                </div>
                <ToneBadge tone="teal">{formatScore(item.score)}</ToneBadge>
              </div>
            ))}
          </div>
        </Surface>

        <div className="inspector-column">
          <Surface>
            <div className="section-heading">
              <div>
                <h3>Prediction summary</h3>
                <p>Final output from the PhoBERT package currently serving this environment.</p>
              </div>
            </div>
            <ToneBadge tone="navy" subtle>
              PhoBERT label
            </ToneBadge>
            <div className="prediction-headline">
              <strong>{translateLabel(predictionLabel)}</strong>
              <span>Confidence {formatScore(predictionConfidence)}</span>
            </div>
            <div className="hero-progress">
              <div className="hero-progress-fill" style={{ width: `${predictionConfidence * 100}%` }} />
            </div>
            <small>{lastInference?.modelVersion ?? data.predictionSummary.package}</small>
          </Surface>

          <Surface>
            <div className="section-heading">
              <div>
                <h3>Candidate ranking</h3>
                <p>Top label candidates ranked against the same thresholds used by the editorial queue.</p>
              </div>
            </div>
            <ProgressList
              items={ranking.map((item, index) => ({
                label: `${translateLabel(item.label)}${index === 0 ? " (top-1)" : index === 1 ? " (top-2)" : " (top-3)"}`,
                value: item.score,
                tone: index === 0 ? "navy" : index === 1 ? "gold" : "teal",
              }))}
            />
            <div className="chip-row">
              {data.thresholdBands.map((band) => (
                <ToneBadge key={band.label} tone={band.tone} subtle>
                  {band.label}
                </ToneBadge>
              ))}
            </div>
          </Surface>

          <Surface>
            <div className="section-heading">
              <div>
                <h3>Decision controls</h3>
                <p>Approve when confidence is high, override when top labels are close, or escalate below the review floor.</p>
              </div>
            </div>
            <div className="decision-stack">
              <ToneButton icon={<CheckCircle2 aria-hidden="true" size={15} />} onClick={() => handleDecision("approve")}>Approve label</ToneButton>
              <div className="decision-row">
                <select className="label-select" value={selectedLabel} onChange={(event) => setSelectedLabel(event.target.value)}>
                  {data.decisionControls.labels.map((label) => (
                    <option key={label} value={label}>
                      {translateLabel(label)}
                    </option>
                  ))}
                </select>
                <ToneButton icon={<RotateCcw aria-hidden="true" size={15} />} tone="muted" onClick={() => handleDecision("override")}>
                  Override label
                </ToneButton>
              </div>
              <ToneButton icon={<AlertTriangle aria-hidden="true" size={15} />} tone="coral" onClick={() => handleDecision("escalate")}>
                Flag to DS
              </ToneButton>
              <textarea
                className="note-box"
                value={notes}
                onChange={(event) => setNotes(event.target.value)}
                placeholder="Add notes for the next training cycle or routing rule update..."
              />
              <small className="history-note">
                {lastInference ? `Inference ${decisionLabel} · ${lastInference.latencyMs}ms` : data.decisionControls.history}
              </small>
            </div>
          </Surface>
        </div>
      </div>
    </AppShell>
  );
}
