import sys
import tempfile
import re
from datetime import datetime, timezone
from html import escape
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.api import EmailController
from src.models.schemas import PipelineResult, UserProfile

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="EmailForest",
    page_icon="🌲",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# LOGO HELPER
# ─────────────────────────────────────────────
LOGO_IMG = '<span style="font-size: 2.8rem; line-height: 1;">🌲</span>'

# ─────────────────────────────────────────────
# MONOCHROME PALETTE + GREEN ACCENT
# ─────────────────────────────────────────────
# Background:  #0f1114
# Surfaces:    #171a1f / #1d2127
# Text:        #f3f4f6 / #a7adb5
# Accent:      #27ae7a

# ─────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

:root {
    --bg: #0f1114;
    --sidebar: #111317;
    --panel: #171a1f;
    --panel-soft: #1d2127;
    --text: #f3f4f6;
    --muted: #a7adb5;
    --line: #2a3038;
    --accent: #27ae7a;
    --accent-soft: rgba(39, 174, 122, 0.2);
}

/* Base */
html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }
.stApp { background: var(--bg) !important; color: var(--text) !important; }

/* Sidebar */
[data-testid="stSidebar"] {
    background: var(--sidebar) !important;
    border-right: 1px solid var(--line) !important;
}
[data-testid="stSidebarHeader"] {
    padding: 0.12rem 0.55rem !important;
    min-height: unset !important;
}
[data-testid="stSidebarContent"] {
    padding-top: 0 !important;
}
[data-testid="stSidebarUserContent"] {
    padding-top: 0.15rem !important;
}
[data-testid="stSidebarCollapseButton"] button {
    background: var(--panel) !important;
    border: 1px solid var(--line) !important;
    border-radius: 8px !important;
    transition: all 0.18s !important;
}
[data-testid="stSidebarCollapseButton"] button:hover {
    border-color: var(--accent) !important;
    background: var(--panel-soft) !important;
}
[data-testid="stSidebarCollapseButton"] svg {
    fill: #dde1e6 !important;
    stroke: #dde1e6 !important;
}
[data-testid="stSidebar"] > div:first-child {
    padding: 0.2rem 0.95rem 1.5rem !important;
    overflow-y: auto !important;
}

/* Sidebar labels + inputs */
[data-testid="stSidebar"] label {
    font-size: 0.67rem !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.09em !important;
    color: var(--muted) !important;
    margin-bottom: 0.25rem !important;
}
[data-testid="stSidebar"] .stSelectbox > div > div,
[data-testid="stSidebar"] .stNumberInput > div > div > input,
[data-testid="stSidebar"] .stTextInput > div > div > input,
[data-testid="stSidebar"] .stTextArea > div > div > textarea {
    background: var(--panel) !important;
    border: 1px solid var(--line) !important;
    border-radius: 9px !important;
    color: var(--text) !important;
    font-size: 0.86rem !important;
}
[data-testid="stSidebar"] .stSelectbox > div > div:focus-within,
[data-testid="stSidebar"] .stNumberInput > div > div:focus-within,
[data-testid="stSidebar"] .stTextInput > div > div:focus-within {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 3px var(--accent-soft) !important;
}
[data-testid="stSidebar"] [data-testid="InputInstructions"] {
    display: none !important;
}

/* Student profile */
.profile-intro {
    font-size: 0.79rem;
    color: #c2c8cf;
    background: var(--panel);
    border: 1px solid var(--line);
    border-radius: 10px;
    padding: 0.55rem 0.65rem;
    margin: 0 0 0.65rem;
}
.cgpa-card {
    background: var(--panel);
    border: 1px solid var(--line);
    border-radius: 10px;
    padding: 0.48rem 0.62rem;
    margin-top: 0.12rem;
}
.cgpa-label {
    font-size: 0.64rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--muted);
}
.cgpa-value {
    font-size: 1.22rem;
    font-weight: 800;
    color: #eef1f4;
    line-height: 1.1;
    margin-top: 0.1rem;
}

/* Sidebar form submit */
[data-testid="stSidebar"] .stFormSubmitButton button {
    background: var(--panel-soft) !important;
    border: 1px solid #353b44 !important;
    border-radius: 8px !important;
    color: #eef1f4 !important;
    font-size: 0.74rem !important;
    font-weight: 600 !important;
    width: 100% !important;
    padding: 0.22rem 0.45rem !important;
    transition: all 0.2s !important;
    margin-top: 0.25rem !important;
}
[data-testid="stSidebar"] .stFormSubmitButton button:hover {
    border-color: var(--accent) !important;
    color: #d6f2e5 !important;
    background: #252b34 !important;
}

/* Sidebar inline action buttons */
[data-testid="stSidebar"] div[data-testid="stButton"] > button {
    all: unset !important;
    cursor: pointer !important;
    font-size: 0.76rem !important;
    color: #9ca3af !important;
    padding: 2px 6px !important;
    border-radius: 5px !important;
    transition: all 0.15s !important;
    line-height: 1 !important;
}
[data-testid="stSidebar"] div[data-testid="stButton"] > button:hover {
    color: #d9f3e7 !important;
    background: rgba(39, 174, 122, 0.16) !important;
}

/* Section divider */
.sb-section {
    font-size: 0.68rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.13em;
    color: #c4c9d0;
    margin: 0.92rem 0 0.52rem;
    padding-bottom: 0.35rem;
    border-bottom: 1px solid var(--line);
}
[data-testid="stSidebar"] .sb-section:first-of-type {
    margin-top: 0.18rem;
}
.sb-section-main {
    font-size: 0.9rem;
    letter-spacing: 0.12em;
    color: #f0f3f6;
}

/* Skill and experience rows */
.skill-row {
    display: flex;
    align-items: center;
    background: var(--panel);
    border: 1px solid #313740;
    border-radius: 9px;
    padding: 0.38rem 0.58rem;
    margin-bottom: 0.38rem;
    gap: 0.45rem;
}
.skill-name {
    flex: 1;
    font-size: 0.81rem;
    font-weight: 500;
    color: #e7eaee;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.skill-row--experience {
    background: #15181d;
    border-color: #2b3138;
}

/* Main area */
.block-container { padding: 1.2rem 2rem 3rem !important; }

/* Hero */
.hero-wrap {
    text-align: center;
    padding: 2rem 0 1.4rem;
}
.hero-title {
    font-size: 2.2rem;
    font-weight: 800;
    background: linear-gradient(120deg, #f4f5f7 0%, #d7dbe1 68%, #87d8b6 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    line-height: 1.2;
    margin: 0.3rem 0 0 !important;
}
.hero-sub {
    color: #aeb4bc;
    font-size: 0.88rem;
    margin: 0.42rem 0 0;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    background: #171a1f !important;
    border-radius: 14px 14px 0 0 !important;
    border: 1px solid var(--line) !important;
    border-bottom: 1px solid var(--line) !important;
    gap: 0 !important;
    padding: 0 1rem !important;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    color: #aab1b8 !important;
    border-radius: 0 !important;
    font-size: 0.82rem !important;
    font-weight: 600 !important;
    padding: 0.6rem 1rem !important;
    border-bottom: 2px solid transparent !important;
    margin-bottom: -1px !important;
}
.stTabs [aria-selected="true"] {
    color: #d9f1e5 !important;
    border-bottom: 2px solid var(--accent) !important;
}
.stTabs [data-baseweb="tab-highlight"],
.stTabs [data-baseweb="tab-border"] { display: none !important; }
[data-testid="stTabsContent"] {
    background: var(--panel) !important;
    border: 1px solid var(--line) !important;
    border-top: none !important;
    border-radius: 0 0 14px 14px !important;
    padding: 1rem 1.1rem 1.1rem !important;
}

/* Text area */
.stTextArea textarea {
    background: #12151a !important;
    border: 1px solid var(--line) !important;
    border-radius: 10px !important;
    color: var(--text) !important;
    font-size: 0.88rem !important;
    resize: none !important;
    padding: 0.8rem 1rem !important;
    line-height: 1.6 !important;
}
.stTextArea textarea:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 3px var(--accent-soft) !important;
}
.stTextArea [data-baseweb="base-input"] { border: none !important; background: transparent !important; }
.stTextArea label { display: none !important; }

/* File uploader */
[data-testid="stFileUploader"] section {
    background: #12151a !important;
    border: 1.5px dashed #38404a !important;
    border-radius: 10px !important;
    padding: 1.4rem !important;
    transition: border-color 0.2s !important;
}
[data-testid="stFileUploader"] section:hover { border-color: var(--accent) !important; }
[data-testid="stFileUploader"] label { color: #b9bfc7 !important; font-size: 0.82rem !important; }

/* Primary button */
div[data-testid="stButton"] > button[kind="primary"],
.analyze-btn div[data-testid="stButton"] > button {
    background: linear-gradient(135deg, #20242b 0%, #2a3139 100%) !important;
    color: #eef1f4 !important;
    border: 1px solid #3b4350 !important;
    border-radius: 12px !important;
    font-weight: 700 !important;
    font-size: 0.95rem !important;
    padding: 0.62rem 1.8rem !important;
    box-shadow: 0 6px 18px rgba(0, 0, 0, 0.28) !important;
    transition: all 0.22s ease !important;
}
div[data-testid="stButton"] > button[kind="primary"]:hover {
    transform: translateY(-2px) !important;
    border-color: var(--accent) !important;
    box-shadow: 0 9px 24px rgba(0, 0, 0, 0.34), 0 0 0 2px var(--accent-soft) !important;
}

/* Secondary / reset button */
div[data-testid="stButton"] > button:not([kind="primary"]) {
    background: #181c22 !important;
    border: 1px solid #353c46 !important;
    color: #dfe3e8 !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    font-size: 0.88rem !important;
    padding: 0.5rem 1.4rem !important;
    transition: all 0.2s !important;
}
div[data-testid="stButton"] > button:not([kind="primary"]):hover {
    border-color: var(--accent) !important;
    color: #eaf5ef !important;
}

/* Floating results action button */
.st-key-analyze_new_emails_fixed {
    position: fixed !important;
    right: 1.35rem;
    bottom: 1.1rem;
    z-index: 1000;
    width: min(420px, calc(100vw - 2.2rem));
}
.st-key-analyze_new_emails_fixed > div {
    margin: 0 !important;
}
.st-key-analyze_new_emails_fixed div[data-testid="stButton"] > button {
    width: 100% !important;
    background: rgba(24, 28, 34, 0.94) !important;
    border: 1px solid #3a424d !important;
    box-shadow: 0 10px 28px rgba(0, 0, 0, 0.4), 0 0 0 1px rgba(39, 174, 122, 0.18) !important;
    color: #f2f5f8 !important;
    border-radius: 12px !important;
    padding: 0.66rem 1.1rem !important;
    font-size: 0.9rem !important;
    font-weight: 700 !important;
    backdrop-filter: blur(8px) !important;
}
.st-key-analyze_new_emails_fixed div[data-testid="stButton"] > button:hover {
    border-color: var(--accent) !important;
    box-shadow: 0 14px 30px rgba(0, 0, 0, 0.44), 0 0 0 2px var(--accent-soft) !important;
}
.results-bottom-spacer {
    height: 4.6rem;
}
@media (max-width: 900px) {
    .st-key-analyze_new_emails_fixed {
        left: 1rem;
        right: 1rem;
        width: auto;
        bottom: 0.85rem;
    }
}

/* Sidebar buttons must stay small */
[data-testid="stSidebar"] div[data-testid="stButton"] > button:not([kind="primary"]) {
    all: unset !important;
    cursor: pointer !important;
    font-size: 0.76rem !important;
    color: #9ca3af !important;
    padding: 2px 6px !important;
    border-radius: 5px !important;
    transition: all 0.15s !important;
    line-height: 1 !important;
}
[data-testid="stSidebar"] div[data-testid="stButton"] > button:not([kind="primary"]):hover {
    color: #d9f3e7 !important;
    background: rgba(39, 174, 122, 0.16) !important;
    border: none !important;
}

/* Results */
[data-testid="stMetric"] {
    background: #171a1f !important;
    border: 1px solid var(--line) !important;
    border-radius: 12px !important;
    padding: 0.85rem 1rem !important;
}
[data-testid="stMetricLabel"] {
    color: #a9afb7 !important;
    font-size: 0.68rem !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.07em !important;
}
[data-testid="stMetricValue"] {
    color: #edf3ee !important;
    font-size: 1.4rem !important;
    font-weight: 700 !important;
}

[data-testid="stExpander"] {
    background: #171a1f !important;
    border: 1px solid var(--line) !important;
    border-radius: 13px !important;
    margin-bottom: 0.55rem !important;
    overflow: hidden !important;
}
[data-testid="stExpander"] summary {
    background: #171a1f !important;
    padding: 0.8rem 1.1rem !important;
    color: #e2e6eb !important;
    font-weight: 600 !important;
    font-size: 0.9rem !important;
}
[data-testid="stExpander"] summary:hover { background: #1e232a !important; }
[data-testid="stExpander"] > div > div { padding: 0 1.1rem 0.9rem !important; }

/* Result card pieces */
.rank-hdr { display: flex; align-items: center; gap: 0.55rem; flex-wrap: wrap; margin-bottom: 0.45rem; }
.mbadge { display: inline-block; padding: 2px 9px; border-radius: 20px; font-size: 0.66rem; font-weight: 800; letter-spacing: 0.07em; }
.m-high { background: rgba(39, 174, 122, 0.16); color: #84d5b3; border: 1px solid rgba(39,174,122,0.44); }
.m-med  { background: rgba(243,191,81,0.15); color: #f3cf84; border: 1px solid rgba(243,191,81,0.4); }
.m-low  { background: rgba(239,107,107,0.15); color: #f3a8a8; border: 1px solid rgba(239,107,107,0.38); }
.dpill { display: inline-flex; align-items: center; gap: 4px; padding: 3px 11px; border-radius: 30px; font-weight: 700; font-size: 0.76rem; }
.d-red    { background: rgba(239,107,107,0.12); border: 1px solid #d97777; color: #f1b1b1; }
.d-yellow { background: rgba(243,191,81,0.12); border: 1px solid #e2b454; color: #f0d69a; }
.d-green  { background: rgba(39,174,122,0.12); border: 1px solid #4ab98a; color: #9be0c1; }
.ev-item { display: flex; align-items: flex-start; gap: 8px; padding: 5px 0; border-bottom: 1px solid #242a33; font-size: 0.84rem; color: #b7bec6; }
.ev-icon { color: #73c9a4; flex-shrink: 0; margin-top: 1px; }
.step-row { display: flex; align-items: flex-start; gap: 9px; padding: 7px 11px; margin: 3px 0; background: #12161b; border-radius: 8px; border-left: 3px solid #4ab98a; font-size: 0.83rem; color: #c1c8d0; }
.step-num { background: #2d9f71; color: #ffffff; border-radius: 50%; width: 20px; height: 20px; display: flex; align-items: center; justify-content: center; font-size: 0.66rem; font-weight: 800; flex-shrink: 0; }
.junk-row { display: flex; align-items: center; gap: 8px; padding: 6px 11px; margin: 2px 0; background: #14181d; border-radius: 8px; border-left: 2px solid #2b323b; font-size: 0.78rem; color: #a6adb6; }

hr { border: none !important; border-top: 1px solid var(--line) !important; margin: 1.1rem 0 !important; }

/* Hide Streamlit chrome */
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
header { background: transparent !important; }
.stAppDeployButton { display: none !important; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# BACKEND INTEGRATION
# ─────────────────────────────────────────────
@st.cache_resource(show_spinner=False)
def _get_controller() -> EmailController:
    return EmailController()


def _build_user_profile() -> UserProfile:
    degree = st.session_state.get("degree") or None
    location_pref = st.session_state.get("location_pref") or None
    semester = st.session_state.get("semester")
    experience_level = f"Semester {semester}" if semester else None

    skills = list(st.session_state.get("skills", []))
    experiences = list(st.session_state.get("experiences", []))

    # Combine skills and experience descriptions as interest signals for the scorer
    interests = list(dict.fromkeys(skills + [e.split()[-1] for e in experiences if e.strip()]))

    return UserProfile(
        degree_program=degree,
        semester=semester,
        cgpa=st.session_state.get("cgpa"),
        skills=skills,
        preferred_opportunity_types=list(
            st.session_state.get("preferred_opportunity_types", [])
        ),
        financial_need=st.session_state.get("financial_need") or None,
        experience_level=experience_level,
        education=degree,
        location=location_pref,
        location_preference=location_pref,
        past_experience=experiences,
        interests=interests,
    )


def _compose_eml(subject: str, body: str) -> str:
    safe_subject = " ".join(subject.splitlines()).strip() or "Inbox Email"
    stamp = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")
    return (
        "From: inbox@example.com\n"
        "To: student@example.com\n"
        f"Subject: {safe_subject}\n"
        f"Date: {stamp}\n"
        "MIME-Version: 1.0\n"
        'Content-Type: text/plain; charset="utf-8"\n\n'
        f"{body.strip()}\n"
    )


def _decode_text(raw: bytes) -> str:
    for encoding in ("utf-8", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="ignore")


def _extract_subject_from_text(text: str, fallback: str) -> str:
    for line in text.splitlines()[:40]:
        if line.lower().startswith("subject:"):
            return line.split(":", 1)[1].strip() or fallback
    return fallback


def _split_batch_text_emails(text: str) -> list[str]:
    cleaned = text.strip()
    if not cleaned:
        return []

    # Split on common delimiter bars used in pasted inbox dumps.
    chunks = [
        chunk.strip()
        for chunk in re.split(r"\n(?:-{3,}|={3,}|_{3,})\n", cleaned)
        if chunk.strip()
    ]

    if len(chunks) > 1:
        return chunks

    # Fallback: split on repeated "From:" boundaries.
    lines = cleaned.splitlines()
    grouped: list[str] = []
    current: list[str] = []
    for line in lines:
        if line.strip().lower().startswith("from:") and current:
            grouped.append("\n".join(current).strip())
            current = [line]
        else:
            current.append(line)
    if current:
        grouped.append("\n".join(current).strip())

    return [chunk for chunk in grouped if chunk]


def _prepare_eml_files(
    pasted_text: str,
    uploaded_files: list,
    work_dir: Path,
) -> list[Path]:
    eml_paths: list[Path] = []

    pasted_chunks = _split_batch_text_emails(pasted_text)
    for idx, chunk in enumerate(pasted_chunks, start=1):
        pasted_path = work_dir / f"pasted_{idx}.eml"
        pasted_path.write_text(
            _compose_eml(_extract_subject_from_text(chunk, f"Pasted Email {idx}"), chunk),
            encoding="utf-8",
        )
        eml_paths.append(pasted_path)

    for idx, uploaded in enumerate(uploaded_files, start=1):
        raw = uploaded.getvalue()
        suffix = Path(uploaded.name).suffix.lower()

        if suffix == ".eml":
            target = work_dir / f"uploaded_{idx}.eml"
            target.write_bytes(raw)
            eml_paths.append(target)
        else:
            decoded = _decode_text(raw).strip() or "No readable text found in upload."
            chunks = _split_batch_text_emails(decoded) or [decoded]
            for sub_idx, chunk in enumerate(chunks, start=1):
                target = work_dir / f"uploaded_{idx}_{sub_idx}.eml"
                target.write_text(
                    _compose_eml(
                        _extract_subject_from_text(chunk, f"{uploaded.name} #{sub_idx}"),
                        chunk,
                    ),
                    encoding="utf-8",
                )
                eml_paths.append(target)

    return eml_paths


def _count_candidate_emails(pasted_text: str, uploaded_files: list) -> int:
    count = len(_split_batch_text_emails(pasted_text))
    for uploaded in uploaded_files:
        suffix = Path(uploaded.name).suffix.lower()
        if suffix == ".eml":
            count += 1
            continue

        decoded = _decode_text(uploaded.getvalue())
        chunks = _split_batch_text_emails(decoded)
        count += len(chunks) if chunks else 1

    return count


def _to_aware(dt: datetime) -> datetime:
    """Coerce a naive datetime to UTC-aware (assume UTC if no tzinfo)."""
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def _deadline_for_result(result: PipelineResult) -> datetime | None:
    """
    Return the single most relevant FUTURE actionable deadline for this email.

    Priority ladder (evaluated in order):
      1. application_deadline   — explicit "apply by" field on Job/Admission emails.
                                  This IS an action deadline by definition.
      2. next_steps[].deadline  — LLM-extracted action-item deadlines.
                                  For events this captures the *registration* deadline
                                  (e.g. "Register by Apr 25") rather than event_date.
      3. event_date             — when the event actually occurs; only used as a
                                  fallback when no registration deadline was found.
      4. key_dates              — any other dates mentioned (program starts, email
                                  send date, orientation, etc.); last resort.

    Past dates are ignored at every level — a missed deadline doesn't make an
    email URGENT; the ML urgency score handles that case instead.
    """
    now = datetime.now(timezone.utc)

    def _is_future(dt: datetime) -> bool:
        return _to_aware(dt) > now

    # ── Priority 1: application_deadline only (explicit action deadline) ──
    app_dl = getattr(result.extracted_data, "application_deadline", None)
    if app_dl is not None and _is_future(app_dl):
        return _to_aware(app_dl)

    # ── Priority 2: next_steps action deadlines (covers registration dls) ─
    p2 = [
        _to_aware(step.deadline)
        for step in result.next_steps
        if step.deadline is not None and _is_future(step.deadline)
    ]
    if p2:
        return min(p2)

    # ── Priority 3: event_date (when it happens, not when to act) ─────────
    ev_dt = getattr(result.extracted_data, "event_date", None)
    if ev_dt is not None and _is_future(ev_dt):
        return _to_aware(ev_dt)

    # ── Priority 4: key_dates (last resort, future only) ──────────────────
    p4 = [
        _to_aware(dt)
        for dt in result.extracted_data.key_dates
        if _is_future(dt)
    ]
    if p4:
        return min(p4)

    # No actionable future deadline → caller falls back to ML urgency score
    return None


def _urgency_bucket(deadline: datetime | None, urgency_score: float) -> str:
    """
    Map a deadline + ML urgency score to a colour bucket.

    If a future deadline exists, urgency is deadline-driven:
      🔴 red    → ≤ 3 days left
      🟡 yellow → ≤ 14 days left
      🟢 green  → > 14 days left

    If no future deadline was found, fall back to the ML urgency score:
      🔴 red    → score ≥ 7
      🟡 yellow → score ≥ 4
      🟢 green  → score < 4
    """
    if deadline is not None:
        now = datetime.now(timezone.utc)
        days_left = (_to_aware(deadline) - now).total_seconds() / 86_400
        if days_left <= 3:
            return "red"
        if days_left <= 14:
            return "yellow"
        return "green"

    # No future deadline — use ML score as proxy
    if urgency_score >= 7:
        return "red"
    if urgency_score >= 4:
        return "yellow"
    return "green"


def _match_bucket(fit_score: float) -> str:
    if fit_score >= 7:
        return "High"
    if fit_score >= 4:
        return "Medium"
    return "Low"


def _format_deadline(deadline: datetime | None) -> str:
    if deadline is None:
        return "No deadline"
    if deadline.tzinfo is None:
        return deadline.strftime("%d %b %Y")
    return deadline.astimezone(timezone.utc).strftime("%d %b %Y")


def _reason_lines(result: PipelineResult) -> list[str]:
    reasons = [
        f"Composite score: {result.scores.composite:.1f}/10",
        f"Fit score: {result.scores.fit:.1f}/10",
        f"Urgency score: {result.scores.urgency:.1f}/10",
    ]
    if result.link_trust:
        avg_trust = sum(link.trust_score for link in result.link_trust) / len(result.link_trust)
        reasons.append(f"Average link trust: {avg_trust:.1f}/10")

    admission_reqs = getattr(result.extracted_data, "requirements", [])
    if admission_reqs:
        reasons.append(f"Eligibility requirements: {', '.join(admission_reqs[:3])}")

    required_skills = getattr(result.extracted_data, "required_skills", [])
    if required_skills:
        reasons.append(f"Required skills: {', '.join(required_skills[:4])}")

    required_documents = getattr(result.extracted_data, "required_documents", [])
    if required_documents:
        reasons.append(
            f"Required documents: {', '.join(required_documents[:4])}"
        )

    contact_info = getattr(result.extracted_data, "contact_info", [])
    if contact_info:
        reasons.append(f"Contact / apply via: {', '.join(contact_info[:3])}")

    if result.warnings:
        reasons.append(result.warnings[0])
    return reasons


def _result_to_card(result: PipelineResult) -> dict[str, object]:
    deadline = _deadline_for_result(result)
    location = (
        getattr(result.extracted_data, "location", None)
        or getattr(result.extracted_data, "venue", None)
        or "Unspecified"
    )
    steps = [step.action for step in result.next_steps if step.action.strip()]
    if not steps:
        steps = ["Review the email details and confirm required actions."]

    title = (
        result.extracted_data.subject
        or result.envelope.subject
        or Path(result.source_file).name
    )

    return {
        "title": title,
        "type": result.extracted_data.email_type.value,
        "match": _match_bucket(result.scores.fit),
        "urgency": _urgency_bucket(deadline, result.scores.urgency),
        "deadline": _format_deadline(deadline),
        "location": location,
        "summary": result.extracted_data.summary,
        "reasons": _reason_lines(result),
        "steps": steps,
        "_composite": result.scores.composite,
    }


def _build_frontend_results(
    processed: list[PipelineResult],
    failures: list[dict[str, str]],
) -> dict[str, object]:
    opportunities: list[dict[str, object]] = []
    spam: list[dict[str, str]] = list(failures)

    for result in processed:
        card = _result_to_card(result)
        if card["type"] == "Misc":
            spam.append(
                {
                    "subject": str(card["title"]),
                    "reason": f"Classified as Misc (composite {result.scores.composite:.1f}/10).",
                }
            )
            continue

        opportunities.append(card)

    opportunities.sort(key=lambda item: float(item["_composite"]), reverse=True)
    for item in opportunities:
        item.pop("_composite", None)

    return {
        "total": len(processed) + len(failures),
        "opportunities": opportunities,
        "spam": spam,
    }


def _analyze_with_backend(pasted_text: str, uploaded_files: list) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="emailforest_") as temp_dir:
        eml_paths = _prepare_eml_files(pasted_text, uploaded_files, Path(temp_dir))
        if not eml_paths:
            return {"total": 0, "opportunities": [], "spam": []}

        controller = _get_controller()
        user_profile = _build_user_profile()

        processed: list[PipelineResult] = []
        failures: list[dict[str, str]] = []

        for eml_path in eml_paths:
            try:
                processed.append(controller.process(eml_path, user_profile=user_profile))
            except Exception as exc:
                failures.append(
                    {
                        "subject": eml_path.name,
                        "reason": f"Processing failed: {exc}",
                    }
                )

    return _build_frontend_results(processed, failures)


def _safe(text: object) -> str:
    return escape(str(text))


# ─────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────
_defaults = {
    "analyzed":    False,
    "analyzing":   False,
    "skills":      ["Python", "Machine Learning"],
    "preferred_opportunity_types": ["Scholarship", "Internship", "Competition"],
    "experiences": ["3-month internship at XYZ"],
    "results":     None,
    "analysis_error": None,
    "edit_skill":  None,   # which skill index is being edited
    "edit_exp":    None,   # which experience index is being edited
    "cgpa":        3.20,
}
for _k, _v in _defaults.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v


def _add_skill_from_input() -> None:
    s = st.session_state.get("new_skill_entry", "").strip()
    if s and s not in st.session_state["skills"]:
        st.session_state["skills"].append(s)
    st.session_state["new_skill_entry"] = ""


def _add_experience_from_input() -> None:
    e = st.session_state.get("new_exp_entry", "").strip()
    if e and e not in st.session_state["experiences"]:
        st.session_state["experiences"].append(e)
    st.session_state["new_exp_entry"] = ""


# ═══════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════
with st.sidebar:

    # ══ STUDENT PROFILE ══════════════════════
    st.markdown('<div class="sb-section sb-section-main">Student Profile</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="profile-intro">Set your academic context so ranking becomes more accurate.</div>',
        unsafe_allow_html=True,
    )

    st.selectbox(
        "Degree / Program",
        ["BS Computer Science", "BS Software Engineering", "BS Data Science",
         "BS Electrical Engineering", "BS AI & Data Science",
         "MS Computer Science", "MBA", "Other"],
        key="degree",
    )

    c1, c2 = st.columns([1, 1], gap="small")
    with c1:
        st.number_input("Semester", min_value=1, max_value=12, value=5, step=1, key="semester")
    with c2:
        st.number_input(
            "CGPA",
            min_value=0.0,
            max_value=4.0,
            step=0.01,
            format="%.2f",
            key="cgpa",
        )

    # ══ SKILLS & INTERESTS ═══════════════════
    st.markdown('<div class="sb-section">💡 Skills & Interests</div>', unsafe_allow_html=True)

    skills = st.session_state["skills"]

    for idx, skill in enumerate(skills):
        if st.session_state["edit_skill"] == idx:
            # ── Edit mode: inline text input + save/cancel ──
            new_val = st.text_input(
                f"edit_sk_{idx}",
                value=skill,
                key=f"edit_sk_input_{idx}",
                label_visibility="collapsed",
            )
            ec1, ec2 = st.columns(2)
            with ec1:
                if st.button("✓ Save", key=f"save_sk_{idx}", use_container_width=True):
                    nv = new_val.strip()
                    if nv:
                        st.session_state["skills"][idx] = nv
                    st.session_state["edit_skill"] = None
                    st.rerun()
            with ec2:
                if st.button("✕ Cancel", key=f"cancel_sk_{idx}", use_container_width=True):
                    st.session_state["edit_skill"] = None
                    st.rerun()
        else:
            # ── Display mode: tag + edit icon + delete icon ──
            c_tag, c_edit, c_del = st.columns([6, 1, 1])
            with c_tag:
                st.markdown(
                    f'<div class="skill-row"><span class="skill-name">✦ {skill}</span></div>',
                    unsafe_allow_html=True,
                )
            with c_edit:
                if st.button("✎", key=f"edit_btn_sk_{idx}"):
                    st.session_state["edit_skill"] = idx
                    st.rerun()
            with c_del:
                if st.button("✕", key=f"del_sk_{idx}"):
                    st.session_state["skills"].pop(idx)
                    if st.session_state["edit_skill"] == idx:
                        st.session_state["edit_skill"] = None
                    st.rerun()

    # ── Add new skill ──
    st.text_input(
        "Add skill",
        placeholder="Type a skill",
        key="new_skill_entry",
        label_visibility="collapsed",
    )
    st.button("＋ Add", key="add_skill_btn", use_container_width=True, on_click=_add_skill_from_input)

    # ══ PREFERENCES ══════════════════════════
    st.markdown('<div class="sb-section">📍 Preferences</div>', unsafe_allow_html=True)

    st.selectbox(
        "Financial Need",
        ["None", "Partial (stipend preferred)", "Full (funded only)", "Critical"],
        key="financial_need",
    )
    st.multiselect(
        "Preferred Opportunity Types",
        ["Scholarship", "Internship", "Competition", "Admission", "Fellowship", "Job", "Event"],
        key="preferred_opportunity_types",
    )
    st.text_input(
        "Location Preference",
        placeholder="e.g. Remote, Lahore, USA…",
        key="location_pref",
    )

    # ══ EXPERIENCE ═══════════════════════════
    st.markdown('<div class="sb-section">🕰️ Past Experience</div>', unsafe_allow_html=True)
    
    exps = st.session_state["experiences"]

    for idx, exp in enumerate(exps):
        if st.session_state["edit_exp"] == idx:
            # ── Edit mode: inline text input + save/cancel ──
            new_val = st.text_input(
                f"edit_ex_{idx}",
                value=exp,
                key=f"edit_ex_input_{idx}",
                label_visibility="collapsed",
            )
            ec1, ec2 = st.columns(2)
            with ec1:
                if st.button("✓ Save", key=f"save_ex_{idx}", use_container_width=True):
                    nv = new_val.strip()
                    if nv:
                        st.session_state["experiences"][idx] = nv
                    st.session_state["edit_exp"] = None
                    st.rerun()
            with ec2:
                if st.button("✕ Cancel", key=f"cancel_ex_{idx}", use_container_width=True):
                    st.session_state["edit_exp"] = None
                    st.rerun()
        else:
            # ── Display mode: tag + edit icon + delete icon ──
            c_tag, c_edit, c_del = st.columns([6, 1, 1])
            with c_tag:
                st.markdown(
                    f'<div class="skill-row skill-row--experience"><span class="skill-name">▸ {exp}</span></div>',
                    unsafe_allow_html=True,
                )
            with c_edit:
                if st.button("✎", key=f"edit_btn_ex_{idx}"):
                    st.session_state["edit_exp"] = idx
                    st.rerun()
            with c_del:
                if st.button("✕", key=f"del_ex_{idx}"):
                    st.session_state["experiences"].pop(idx)
                    if st.session_state["edit_exp"] == idx:
                        st.session_state["edit_exp"] = None
                    st.rerun()

    # ── Add new experience ──
    st.text_input(
        "Add experience",
        placeholder="e.g. 3-month internship at XYZ",
        key="new_exp_entry",
        label_visibility="collapsed",
    )
    st.button("＋ Add", key="add_exp_btn", use_container_width=True, on_click=_add_experience_from_input)


# ═══════════════════════════════════════════════════════════
# MAIN — State A: Landing
# ═══════════════════════════════════════════════════════════
if not st.session_state["analyzed"] and not st.session_state["analyzing"]:

    if st.session_state.get("analysis_error"):
        st.error(f"Analysis failed: {st.session_state['analysis_error']}")

    st.markdown(f"""
    <div class="hero-wrap">
        <div style="display:inline-flex;align-items:center;gap:11px;">
            {LOGO_IMG}
            <span class="hero-title">EmailForest</span>
        </div>
        <p class="hero-sub">Drop your emails in &middot; let AI rank what matters <em>for&nbsp;you</em></p>
    </div>
    """, unsafe_allow_html=True)

    _, col, _ = st.columns([0.6, 4, 0.6])
    with col:
        tab_paste, tab_upload = st.tabs(["📋  Paste Emails", "📁  Upload Files"])

        with tab_paste:
            pasted = st.text_area(
                label="emails",
                placeholder=(
                    "Paste 5–15 opportunity emails here…\n\n"
                    "Raw text, .eml content, or anything copied from your inbox."
                ),
                height=200,
                key="pasted_input",
            )

        with tab_upload:
            uploaded_files = st.file_uploader(
                "Drop email files",
                type=["txt", "eml"],
                accept_multiple_files=True,
                label_visibility="collapsed",
                key="uploaded_files",
            )
            if uploaded_files:
                st.markdown(
                    f"<div style='color:#9be0c1;font-size:0.8rem;margin-top:6px;'>"
                    f"✓ {len(uploaded_files)} file(s) ready</div>",
                    unsafe_allow_html=True,
                )

        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

        if st.button("🚀  Analyze Opportunities", use_container_width=True, type="primary"):
            has_pasted = bool(st.session_state.get("pasted_input", "").strip())
            uploads = st.session_state.get("uploaded_files") or []
            has_uploads = bool(uploads)
            if not has_pasted and not has_uploads:
                st.warning("Paste email text or upload at least one .eml/.txt file before analyzing.")
            else:
                total_emails = _count_candidate_emails(
                    st.session_state.get("pasted_input", ""),
                    uploads,
                )
                if total_emails < 1:
                    st.warning("No emails detected. Paste email text or upload at least one file.")
                elif total_emails > 15:
                    st.warning(
                        f"Too many emails detected ({total_emails}). Please provide at most 15 emails/notices."
                    )
                else:
                    if total_emails < 5:
                        st.toast(
                            f"⚠️ {total_emails} email(s) detected — the demo works best with 5–15.",
                            icon="⚠️",
                        )
                    st.session_state["analysis_error"] = None
                    st.session_state["analyzing"] = True
                    st.rerun()


# ═══════════════════════════════════════════════════════════
# MAIN — State B: Loader
# ═══════════════════════════════════════════════════════════
elif st.session_state["analyzing"]:

    st.markdown("""
    <div style="text-align:center;padding:5rem 0 2rem;">
        <div style="font-size:2.6rem;display:inline-block;
             animation:spin 1.5s linear infinite;">🌲</div>
        <p style="color:#aeb4bc;margin-top:1.2rem;font-size:0.9rem;letter-spacing:0.03em;">
            Scanning emails &nbsp;·&nbsp; Extracting opportunities &nbsp;·&nbsp; Ranking for you…
        </p>
    </div>
    <style>@keyframes spin{from{transform:rotate(0deg)}to{transform:rotate(360deg)}}</style>
    """, unsafe_allow_html=True)

    with st.spinner(""):
        try:
            pasted_text = st.session_state.get("pasted_input", "")
            uploaded_files = st.session_state.get("uploaded_files") or []
            st.session_state["results"] = _analyze_with_backend(pasted_text, uploaded_files)
            st.session_state["analyzed"] = True
            st.session_state["analysis_error"] = None
        except Exception as exc:
            st.session_state["results"] = None
            st.session_state["analyzed"] = False
            st.session_state["analysis_error"] = str(exc)
        finally:
            st.session_state["analyzing"] = False

    st.rerun()


# ═══════════════════════════════════════════════════════════
# MAIN — State C: Results
# ═══════════════════════════════════════════════════════════
else:
    results       = st.session_state["results"]
    opportunities = results["opportunities"]
    spam          = results["spam"]

    # Metrics
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("📧 Emails Scanned",    results["total"])
    m2.metric("✅ Opportunities",      len(opportunities))
    m3.metric("🗑️ Ignored / Spam",    len(spam))
    m4.metric("⚡ Urgent (≤3 days)",   sum(1 for o in opportunities if o["urgency"] == "red"))

    st.markdown("---")

    st.markdown(
        "<h2 style='font-size:1.1rem;font-weight:800;color:#e8ecef;"
        "margin:0 0 0.9rem;letter-spacing:0.01em;'>🏆 Priority Dashboard</h2>",
        unsafe_allow_html=True,
    )

    rank_icons = ["🥇", "🥈", "🥉"] + ["🔹"] * 20
    match_cls  = {"High": "m-high", "Medium": "m-med", "Low": "m-low"}
    urg_map    = {
        "red":    ("d-red",    "🔴 URGENT"),
        "yellow": ("d-yellow", "🟡 SOON"),
        "green":  ("d-green",  "🟢 OPEN"),
    }

    if not opportunities:
        st.info("No opportunity emails were detected. Check ignored/spam below.")

    for i, opp in enumerate(opportunities):
        title = str(opp.get("title", "Untitled"))
        match_label = str(opp.get("match", "Low"))
        urgency_label = str(opp.get("urgency", "green"))
        u_cls, u_lbl = urg_map.get(urgency_label, urg_map["green"])
        m_cls = match_cls.get(match_label, "m-low")
        deadline_text = _safe(opp.get("deadline", "No deadline"))
        type_text = _safe(opp.get("type", "Unknown"))
        location_text = _safe(opp.get("location", "Unspecified"))
        summary_text = _safe(opp.get("summary", "No summary available."))

        with st.expander(
            f"{rank_icons[i]}  #{i+1}: {title}   ·   {match_label} Match",
            expanded=(i == 0),
        ):
            st.markdown(f"""
            <div class="rank-hdr">
                <span class="mbadge {m_cls}">{_safe(match_label.upper())} MATCH</span>
                <span class="dpill {u_cls}">{u_lbl} &nbsp; {deadline_text}</span>
                <span style="color:#aab1b8;font-size:0.76rem;">
                    📌 {location_text} &nbsp;|&nbsp {type_text} 
                </span>
            </div>
            <p style="color:#b7bec6;font-size:0.84rem;margin:0.35rem 0 0.75rem;">
                {summary_text}
            </p>
            """, unsafe_allow_html=True)

            st.markdown(
                "<div style='font-size:0.68rem;font-weight:800;text-transform:uppercase;"
                "letter-spacing:0.1em;color:#aab1b8;margin-bottom:4px;'>📋 Why This Ranks Here</div>",
                unsafe_allow_html=True,
            )
            for reason in opp.get("reasons", []):
                st.markdown(
                    f'<div class="ev-item"><span class="ev-icon">›</span><span>{_safe(reason)}</span></div>',
                    unsafe_allow_html=True,
                )

            st.markdown("<div style='height:7px'></div>", unsafe_allow_html=True)

            with st.expander("✅  Action Checklist", expanded=False):
                for j, step in enumerate(opp.get("steps", []), 1):
                    st.markdown(
                        f'<div class="step-row"><div class="step-num">{j}</div>'
                        f'<span>{_safe(step)}</span></div>',
                        unsafe_allow_html=True,
                    )

    # Junk drawer
    st.markdown("---")
    st.markdown(
        "<div style='font-size:0.65rem;font-weight:800;text-transform:uppercase;"
        "letter-spacing:0.12em;color:#9ea5ae;margin-bottom:0.35rem;'>🗑️ Ignored / Spam</div>",
        unsafe_allow_html=True,
    )
    if not spam:
        st.markdown(
            '<div class="junk-row"><span>✓</span><span>No ignored emails in this run.</span></div>',
            unsafe_allow_html=True,
        )
    else:
        for s in spam:
            subject_text = _safe(s.get("subject", "Untitled"))
            reason_text = _safe(s.get("reason", "No reason provided."))
            st.markdown(
                f'<div class="junk-row"><span>✗</span>'
                f'<span><b style="color:#d6dbe2;">{subject_text}</b>'
                f' &nbsp;—&nbsp; {reason_text}</span></div>',
                unsafe_allow_html=True,
            )

    st.markdown('<div class="results-bottom-spacer"></div>', unsafe_allow_html=True)
    if st.button("🔄  Analyze New Emails", key="analyze_new_emails_fixed", use_container_width=True):
        st.session_state.update({
            "analyzed": False,
            "analyzing": False,
            "results": None,
            "analysis_error": None,
        })
        st.rerun()
