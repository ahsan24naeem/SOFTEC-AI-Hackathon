import streamlit as st
import time
from datetime import datetime, timedelta

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
# MOCK DATA
# ─────────────────────────────────────────────
def _mock_results():
    today = datetime.today()
    return {
        "total": 12,
        "opportunities": [
            {
                "title":   "Google Summer of Code 2026",
                "type":    "Fellowship", "match": "High", "urgency": "red",
                "deadline": (today + timedelta(days=2)).strftime("%d %b %Y"),
                "location": "Remote",
                "summary":  "Open-source fellowship by Google. Stipend $3,000–$6,600. Project proposal required.",
                "reasons": [
                    "Python skill directly matches stated requirement.",
                    "CGPA ≥ 3.0 minimum threshold met.",
                    "Remote — matches your location preference.",
                    "Deadline in 2 days — immediate action needed.",
                ],
                "steps": [
                    "Visit summerofcode.withgoogle.com and browse org list.",
                    "Draft a 2-page project proposal.",
                    "Contact a mentor from your chosen org.",
                    "Submit via the GSoC portal before deadline.",
                ],
            },
            {
                "title":   "LUMS NOP Scholarship",
                "type":    "Scholarship", "match": "High", "urgency": "yellow",
                "deadline": (today + timedelta(days=10)).strftime("%d %b %Y"),
                "location": "Lahore, Pakistan",
                "summary":  "Full need-based scholarship covering tuition + living stipend.",
                "reasons": [
                    "Financial need flag set to 'Partial (stipend preferred)'.",
                    "Location preference 'Lahore' matches programme site.",
                    "Semester 5 within eligible range (Sem 1–6).",
                    "CGPA well above 2.5 cut-off.",
                ],
                "steps": [
                    "Download NOP application form from LUMS portal.",
                    "Gather income certificate & family documents.",
                    "Write 500-word personal statement.",
                    "Submit scanned copies via email.",
                ],
            },
            {
                "title":   "Microsoft Imagine Cup 2026",
                "type":    "Competition", "match": "Medium", "urgency": "green",
                "deadline": (today + timedelta(days=45)).strftime("%d %b %Y"),
                "location": "Remote / Global",
                "summary":  "Global student tech competition. $100,000 grand prize.",
                "reasons": [
                    "Competition listed in preferred opportunity types.",
                    "Python & ML skills relevant to AI track.",
                    "Deadline 45 days away — plenty of time.",
                    "No strict CGPA requirement; team ≤ 3 members.",
                ],
                "steps": [
                    "Form a team of 2–3 students.",
                    "Register at imaginecup.microsoft.com.",
                    "Brainstorm an AI-for-good project idea.",
                    "Build MVP and record a 3-minute pitch video.",
                ],
            },
        ],
        "spam": [
            {"subject": "URGENT — Claim Your $10,000 Award Now!!",       "reason": "Phishing — no legitimate org."},
            {"subject": "Webinar: Top 10 LinkedIn Tips for 2026",         "reason": "Informational only."},
            {"subject": "Unsubscribe from Our Newsletter",                 "reason": "Administrative email."},
            {"subject": "Class Schedule Update — Spring Semester",         "reason": "Internal admin notice."},
            {"subject": "Flash Sale: 50% Off Online Courses",              "reason": "Commercial promotion."},
            {"subject": "Follow us on Instagram!",                         "reason": "Social media marketing."},
            {"subject": "Re: Meeting Notes from Feb Board",                "reason": "Internal memo."},
            {"subject": "📢 Free Webinar: Crypto Investing 101",           "reason": "Unrelated commercial."},
            {"subject": "Your Amazon order has shipped",                   "reason": "E-commerce notification."},
        ],
    }


# ─────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────
_defaults = {
    "analyzed":    False,
    "analyzing":   False,
    "skills":      ["Python", "Machine Learning"],
    "experiences": ["3-month internship at XYZ"],
    "results":     None,
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
                type=["txt", "eml", "docx", "pdf", "msg"],
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
        time.sleep(2)   # ← swap for real AI call

    st.session_state["results"]   = _mock_results()
    st.session_state["analyzing"] = False
    st.session_state["analyzed"]  = True
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

    for i, opp in enumerate(opportunities):
        u_cls, u_lbl = urg_map[opp["urgency"]]
        m_cls        = match_cls[opp["match"]]

        with st.expander(
            f"{rank_icons[i]}  #{i+1}: {opp['title']}   ·   {opp['match']} Match",
            expanded=(i == 0),
        ):
            st.markdown(f"""
            <div class="rank-hdr">
                <span class="mbadge {m_cls}">{opp['match'].upper()} MATCH</span>
                <span class="dpill {u_cls}">{u_lbl} &nbsp; {opp['deadline']}</span>
                <span style="color:#aab1b8;font-size:0.76rem;">
                    📌 {opp['type']} &nbsp;|&nbsp; {opp['location']}
                </span>
            </div>
            <p style="color:#b7bec6;font-size:0.84rem;margin:0.35rem 0 0.75rem;">
                {opp['summary']}
            </p>
            """, unsafe_allow_html=True)

            st.markdown(
                "<div style='font-size:0.68rem;font-weight:800;text-transform:uppercase;"
                "letter-spacing:0.1em;color:#aab1b8;margin-bottom:4px;'>📋 Why This Ranks Here</div>",
                unsafe_allow_html=True,
            )
            for reason in opp["reasons"]:
                st.markdown(
                    f'<div class="ev-item"><span class="ev-icon">›</span><span>{reason}</span></div>',
                    unsafe_allow_html=True,
                )

            st.markdown("<div style='height:7px'></div>", unsafe_allow_html=True)

            with st.expander("✅  Action Checklist", expanded=False):
                for j, step in enumerate(opp["steps"], 1):
                    st.markdown(
                        f'<div class="step-row"><div class="step-num">{j}</div>'
                        f'<span>{step}</span></div>',
                        unsafe_allow_html=True,
                    )

    # Junk drawer
    st.markdown("---")
    st.markdown(
        "<div style='font-size:0.65rem;font-weight:800;text-transform:uppercase;"
        "letter-spacing:0.12em;color:#9ea5ae;margin-bottom:0.35rem;'>🗑️ Ignored / Spam</div>",
        unsafe_allow_html=True,
    )
    for s in spam:
        st.markdown(
            f'<div class="junk-row"><span>✗</span>'
            f'<span><b style="color:#d6dbe2;">{s["subject"]}</b>'
            f' &nbsp;—&nbsp; {s["reason"]}</span></div>',
            unsafe_allow_html=True,
        )

    st.markdown('<div class="results-bottom-spacer"></div>', unsafe_allow_html=True)
    if st.button("🔄  Analyze New Emails", key="analyze_new_emails_fixed", use_container_width=True):
        st.session_state.update({"analyzed": False, "analyzing": False, "results": None})
        st.rerun()
