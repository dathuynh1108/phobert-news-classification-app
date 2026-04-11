from __future__ import annotations

from copy import deepcopy


LABELS = [
    "Bạn đọc",
    "Bảo vệ người tiêu dùng",
    "Bất động sản",
    "Chính trị",
    "Công nghệ",
    "Dân tộc - Tôn giáo",
    "Đời sống",
    "Du lịch",
    "Giáo dục",
    "Kinh doanh",
    "Ô tô - Xe máy",
    "Pháp luật",
    "Sức khỏe",
    "Thế giới",
    "Thể thao",
    "Thị trường tiêu dùng",
    "Thời sự",
    "Tuần Việt Nam",
    "Văn hóa - Giải trí",
]


def create_seed_state() -> dict:
    editor_articles = [
        {
            "id": "art-001",
            "label": "Chính trị",
            "title": "Government speeds up work on a decree for shared public data",
            "source": "Source: VietnamNet · 28/03/2026 · Author: Politics Desk",
            "content": [
                "The draft decree focuses on sharing data across ministries, agencies, and local governments to shorten processing time for digital public services.",
                "Editors flagged the story as policy-heavy because it contains multiple statements from public authorities and very little market or lifestyle framing.",
                "The article was routed for review because it still includes several technology infrastructure terms, even though the primary context is government coordination.",
            ],
            "confidence": 0.78,
            "margin": 0.11,
            "top_candidates": [
                {"label": "Chính trị", "score": 0.78},
                {"label": "Công nghệ", "score": 0.67},
                {"label": "Kinh doanh", "score": 0.41},
            ],
            "similar_articles": [
                {"title": "National Assembly debates open-data rules for public services", "score": 0.79, "note": "Cleared 2 manual reviews in the last 7 days."},
                {"title": "Local governments pilot interoperable data hubs for operations", "score": 0.73, "note": "Originally routed to Technology before the final correction."},
            ],
            "rationale_blocks": [
                {
                    "title": "Prediction rationale",
                    "body": "PhoBERT prioritizes Politics because the story is dense with policy language and quotes from public authorities.",
                    "chips": ["decree", "government", "public data"],
                    "bullets": [
                        "Terms such as decree, government, and public agencies appear heavily in the title and opening section.",
                        "The top-1 vs top-2 gap is wide enough to keep the article above the escalation band.",
                    ],
                }
            ],
            "history": "Review history: 2 manual checks · last confirmed 2h ago",
            "selected_label": "Chính trị",
        },
        {
            "id": "art-002",
            "label": "Công nghệ",
            "title": "Digital newsroom accelerates auto-labeling with Vietnamese language models",
            "source": "Source: VietnamNet · 29/03/2026 · Author: Technology Desk",
            "content": [
                "More newsrooms are moving Vietnamese language models into the editorial pipeline to predict categories before a story reaches a human editor.",
                "PhoBERT base v2 is packaged as a gRPC service so the api-service can request inference reliably even when traffic spikes.",
                "The operations team also tracks drift between live traffic and the validation set to decide when retraining should begin.",
            ],
            "confidence": 0.82,
            "margin": 0.20,
            "top_candidates": [
                {"label": "Công nghệ", "score": 0.82},
                {"label": "Thời sự", "score": 0.62},
                {"label": "Kinh doanh", "score": 0.41},
            ],
            "similar_articles": [
                {"title": "Newsroom GPU capacity doubled in the first quarter", "score": 0.81, "note": "Previously auto-approved at the 0.75 threshold."},
                {"title": "New PhoBERT pipeline cuts review time by 18%", "score": 0.77, "note": "Was overridden once by the Business desk."},
            ],
            "rationale_blocks": [
                {
                    "title": "Prediction rationale",
                    "body": "The story focuses on inference infrastructure, pipelines, and Vietnamese language models, so it leans strongly toward Technology.",
                    "chips": ["AI", "gRPC", "PhoBERT"],
                    "bullets": [
                        "GPU, service, inference, and pipeline appear in both the headline and the body.",
                        "The gap to the second-ranked label is wide enough to treat this as a stable auto-approve candidate.",
                    ],
                }
            ],
            "history": "Review history: 2 manual checks · last confirmed 2h ago",
            "selected_label": "Công nghệ",
        },
        {
            "id": "art-003",
            "label": "Giáo dục",
            "title": "Nationwide online mock-exam schedule is announced",
            "source": "Source: VietnamNet · 27/03/2026 · Author: Education Desk",
            "content": [
                "Universities and high schools are publishing online mock-exam schedules so students can prepare for the upcoming admissions cycle.",
                "The education desk wants to keep this queue separate because the story contains several technology keywords while remaining centered on students and exams.",
                "This article currently sits in the review band because the gap between the top two labels is still narrow.",
            ],
            "confidence": 0.66,
            "margin": 0.04,
            "top_candidates": [
                {"label": "Giáo dục", "score": 0.66},
                {"label": "Công nghệ", "score": 0.62},
                {"label": "Thời sự", "score": 0.39},
            ],
            "similar_articles": [
                {"title": "More universities open new majors tied to semiconductor design", "score": 0.71, "note": "The Education desk kept the label after 2 manual reviews."},
            ],
            "rationale_blocks": [
                {
                    "title": "Prediction rationale",
                    "body": "The story clearly signals schools, students, and exams, but also includes enough technology terms to keep the margin narrow.",
                    "chips": ["schools", "students", "mock exams"],
                    "bullets": [
                        "The low top-1 vs top-2 gap pushes this story to the front of the review queue.",
                        "If desk policy changes, editors can still override the label to Technology from the review screen.",
                    ],
                }
            ],
            "history": "Review history: 3 manual checks · threshold conflict still unresolved",
            "selected_label": "Giáo dục",
        },
    ]

    state = {
        "active_model": "PhoBERT base v2",
        "thresholds": {
            "auto_approve": 0.75,
            "review_floor": 0.68,
        },
        "editor_articles": editor_articles,
        "editor_dashboard": {
            "stats": [
                {"label": "Stories today", "value": "1,286", "delta": "+12% vs yesterday", "tone": "teal"},
                {"label": "Needs review", "value": "128", "delta": "+18 flagged stories", "tone": "coral"},
                {"label": "Auto-approved", "value": "74%", "delta": "+6 pts", "tone": "green"},
                {"label": "Avg confidence", "value": "0.82", "delta": "PhoBERT top-1 score", "tone": "violet"},
            ],
            "category_distribution": [
                {"label": "Thời sự", "value": 0.88, "tone": "navy"},
                {"label": "Công nghệ", "value": 0.72, "tone": "teal"},
                {"label": "Giáo dục", "value": 0.64, "tone": "violet"},
                {"label": "Kinh doanh", "value": 0.58, "tone": "gold"},
                {"label": "Văn hóa - Giải trí", "value": 0.46, "tone": "coral"},
            ],
            "shared_signals": [
                {"label": "Education overrides are up", "pill": "+14%", "tone": "coral"},
                {"label": "Desk disagreement rate", "pill": "9%", "tone": "gold"},
                {"label": "News drift under watch", "pill": "Editors + DS", "tone": "teal"},
            ],
            "feedback_loop": [
                {"title": "Editor override", "body": "Grouped for the DS team every hour", "pill": "Synced", "tone": "green"},
                {"title": "DS review", "body": "Disagreement cases stay visible in the queue", "pill": "Inspect", "tone": "gold"},
                {"title": "Rule refresh", "body": "Updated rules flow back into the review queue", "pill": "Watching", "tone": "pink"},
            ],
        },
        "admin_ops": {
            "users": [
                {"name": "Nguyễn An", "role": "Editor", "queue": "Politics", "status": "Active"},
                {"name": "Trần Bình", "role": "Admin", "queue": "All queues", "status": "Idle"},
                {"name": "Phạm Chi", "role": "Data Scientist", "queue": "Monitoring", "status": "Active"},
                {"name": "Lê Dương", "role": "Editor", "queue": "Education", "status": "Active"},
            ],
            "routing": [
                {"label": "Auto-approve ≥ 0.75", "value": 0.75, "tone": "navy"},
                {"label": "Review 0.68–0.75", "value": 0.72, "tone": "gold"},
                {"label": "Escalate to DS < 0.68", "value": 0.61, "tone": "coral"},
            ],
            "audit_log": [
                "16:20 Applied threshold package v2.0.3 to the editorial queue.",
                "15:50 The DS team tightened monitoring refresh cadence to 15 minutes.",
                "14:05 Education override rule sent to version review.",
            ],
            "deployment_snapshot": [
                {"label": "Version", "value": "v2.0.3"},
                {"label": "Threshold file", "value": "thresholds.json"},
                {"label": "Users online", "value": "12 accounts"},
                {"label": "Exports", "value": "PDF + CSV"},
            ],
        },
        "monitoring": {
            "stats": [
                {"label": "Macro F1", "value": "0.82", "delta": "PhoBERT best", "tone": "teal"},
                {"label": "Error share", "value": "0.06", "delta": "24h queue drift", "tone": "coral"},
                {"label": "Drift score", "value": "0.19", "delta": "near the watch threshold", "tone": "gold"},
                {"label": "Coverage", "value": "74%", "delta": "stories auto-approved", "tone": "green"},
            ],
            "macro_f1_series": [0.68, 0.72, 0.74, 0.77, 0.79, 0.82],
            "label_scores": [
                {"label": "Thời sự", "value": 0.86, "tone": "navy"},
                {"label": "Công nghệ", "value": 0.79, "tone": "teal"},
                {"label": "Giáo dục", "value": 0.71, "tone": "gold"},
                {"label": "Kinh doanh", "value": 0.69, "tone": "coral"},
            ],
            "article_analysis": [
                {"label": "Homepage feed", "value": "F1 0.86", "note": "Routing stayed stable in the last 7 days"},
                {"label": "Breaking news", "value": "F1 0.71", "note": "Prediction margins are narrowing"},
                {"label": "Long-form stories", "value": "F1 0.79", "note": "Head-tail context still helps"},
            ],
            "drift_breakdown": [
                {"label": "Semantics", "detail": "Keywords are tilting harder toward startups, AI, and digital infrastructure", "tone": "coral"},
                {"label": "Source mix", "detail": "More regional desks are feeding the same queue", "tone": "pink"},
                {"label": "Time of day", "detail": "Morning traffic is heavier than the current validation window", "tone": "gold"},
            ],
        },
        "model_versions": {
            "runs": [
                {"id": "run_024", "backbone": "vinai/phobert-base-v2", "uploaded": "09:40", "f1": 0.82, "state": "inactive"},
                {"id": "run_023", "backbone": "vinai/phobert-base-v2", "uploaded": "yesterday", "f1": 0.80, "state": "active"},
                {"id": "run_022", "backbone": "vinai/phobert-base-v2", "uploaded": "2 days ago", "f1": 0.78, "state": "archived"},
            ],
            "confusion_matrix": [
                [0.82, 0.07, 0.03, 0.02, 0.01],
                [0.08, 0.79, 0.06, 0.03, 0.01],
                [0.04, 0.07, 0.76, 0.05, 0.03],
                [0.03, 0.04, 0.05, 0.81, 0.02],
                [0.02, 0.03, 0.04, 0.05, 0.84],
            ],
            "package_details": [
                {"label": "Backbone", "value": "vinai/phobert-base-v2"},
                {"label": "Tokenizer", "value": "PhoBERT sentencepiece"},
                {"label": "Loss", "value": "weighted cross entropy"},
                {"label": "Calibration", "value": "temperature scaling"},
                {"label": "Best checkpoint", "value": "epoch-5"},
            ],
        },
        "dataset_lab": {
            "stats": [
                {"label": "Train / Val / Test", "value": "72 / 14 / 14", "delta": "balanced split", "tone": "muted"},
                {"label": "Low-confidence pool", "value": "214", "delta": "needs relabeling", "tone": "coral"},
                {"label": "Drift score", "value": "0.19", "delta": "watch threshold 0.20", "tone": "teal"},
            ],
            "imbalance": [
                {"label": "Công nghệ", "value": 0.82, "tone": "navy"},
                {"label": "Thời sự", "value": 0.76, "tone": "navy"},
                {"label": "Giáo dục", "value": 0.48, "tone": "teal"},
                {"label": "Dân tộc - Tôn giáo", "value": 0.22, "tone": "coral"},
                {"label": "Bạn đọc", "value": 0.19, "tone": "coral"},
            ],
            "hard_samples": [
                {"title": "AI in agriculture reshapes rural employment patterns", "score": 0.54},
                {"title": "More universities launch majors tied to semiconductor chips", "score": 0.54},
                {"title": "Electric motorbike sales jump sharply at the start of the year", "score": 0.54},
            ],
            "active_learning": [
                {"title": "Low-confidence pool", "value": "214", "body": "Stories with very low scores or tight top-2 gaps.", "pill": "Input", "tone": "coral"},
                {"title": "Override queue", "value": "48", "body": "Stories edited by humans and waiting for annotation refresh.", "pill": "Review", "tone": "gold"},
                {"title": "Drift clusters", "value": "3", "body": "Label groups that are clearly drifting in review.", "pill": "Watch", "tone": "teal"},
                {"title": "Relabel batch", "value": "32", "body": "Priority samples for the next training cycle.", "pill": "Ready", "tone": "green"},
            ],
            "priority_labels": ["Giáo dục", "Công nghệ", "Thời sự"],
        },
    }

    return deepcopy(state)
