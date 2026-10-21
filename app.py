"""
NiyamAI - Autonomous AI Government Opportunity & Compliance Agent
Streamlit Web Application
"""

import os
import json
import time
from datetime import datetime
import streamlit as st

from config import (
    TINYFISH_API_KEY,
    GEMINI_API_KEY,
    DEFAULT_GOV_DOMAINS,
    NIYAMAI_DB_PATH,
)
from models import (
    BusinessProfile,
    BusinessSize,
    SavedNotice,
    VerificationStatus,
)
from tinyfish_client import (
    TinyFishClient,
    TinyFishAuthError,
    TinyFishCreditsError,
    TinyFishRateLimitError,
    TinyFishError,
)
from database.db import Database
from agents.extraction_agent import ExtractionAgent
from agents.verification_agent import VerificationAgent
from agents.matching_agent import MatchingAgent

# Page configuration
st.set_page_config(
    page_title="NiyamAI",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------- LUXURY MINIMAL DESIGN SYSTEM ----------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    :root {
        /* Luxury Minimal Palette */
        --bg-canvas: #090A0C;
        --bg-surface: #1A1D24;
        --bg-surface-elevated: #232730;
        --fg-primary: #F8FAFC;
        --fg-secondary: #94A3B8;
        --fg-muted: #586072;
        --accent-primary: #00B4D8;
        --accent-primary-dim: rgba(0, 180, 216, 0.12);
        --accent-warm: #D4A843;
        --accent-warm-dim: rgba(212, 168, 67, 0.12);
        --accent-critical: #EF4444;
        --accent-critical-dim: rgba(239, 68, 68, 0.12);
        --border-subtle: #2D313D;
        --border-emphasis: #3E4452;
        --radius-sharp: 4px;
        --radius-card: 6px;
        --space-unit: 8px;
        --transition-fast: 80ms ease-out;
        --transition-standard: 120ms ease-out;
    }

    /* Global Reset */
    .stApp {
        background: var(--bg-canvas);
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        color: var(--fg-primary);
    }

    /* Typography System */
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif !important;
    }

    h1, h2, h3, h4, h5, h6 {
        font-weight: 700 !important;
        letter-spacing: -0.02em !important;
        color: var(--fg-primary) !important;
        line-height: 1.15 !important;
    }

    h1 { font-size: clamp(1.75rem, 3vw, 2.25rem) !important; }
    h2 { font-size: clamp(1.25rem, 2.5vw, 1.5rem) !important; }
    h3 { font-size: clamp(1rem, 2vw, 1.125rem) !important; }

    /* Label Style - Small, Bold, All-Caps */
    .label-xs, .stMetricLabel, [data-testid="stMetricLabel"] {
        font-size: 0.625rem !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.08em !important;
        color: var(--fg-muted) !important;
        line-height: 1 !important;
    }

    /* Value Style - Large, Light Weight */
    .value-lg, [data-testid="stMetricValue"] {
        font-size: clamp(1.75rem, 3vw, 2.5rem) !important;
        font-weight: 300 !important;
        letter-spacing: -0.03em !important;
        color: var(--fg-primary) !important;
        line-height: 1.1 !important;
    }

    .value-md {
        font-size: 1.125rem !important;
        font-weight: 400 !important;
        color: var(--fg-secondary) !important;
    }

    /* Sidebar - Left Margin Navigation */
    [data-testid="stSidebar"] {
        background: var(--bg-surface) !important;
        border-right: 1px solid var(--border-subtle) !important;
        padding: calc(var(--space-unit) * 3) calc(var(--space-unit) * 2) !important;
    }

    [data-testid="stSidebar"] h2 {
        font-size: 0.75rem !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.1em !important;
        color: var(--fg-muted) !important;
        margin-bottom: calc(var(--space-unit) * 2) !important;
    }

    [data-testid="stSidebar"] .stRadio > label {
        font-size: 0.8125rem !important;
        font-weight: 500 !important;
        color: var(--fg-secondary) !important;
        padding: calc(var(--space-unit) * 1.5) var(--space-unit) !important;
        margin-bottom: calc(var(--space-unit) * 0.5) !important;
        border-radius: var(--radius-sharp) !important;
        transition: background var(--transition-fast), color var(--transition-fast) !important;
    }

    [data-testid="stSidebar"] .stRadio > label:hover {
        background: var(--bg-surface-elevated) !important;
        color: var(--fg-primary) !important;
    }

    [data-testid="stSidebar"] .stRadio [data-baseweb="radio"] > div:first-child {
        background: var(--bg-surface-elevated) !important;
        border: 1px solid var(--border-emphasis) !important;
    }

    [data-testid="stSidebar"] .stRadio [data-baseweb="radio"] > div:first-child > div {
        background: var(--accent-primary) !important;
    }

    [data-testid="stSidebar"] hr {
        border-color: var(--border-subtle) !important;
        margin: calc(var(--space-unit) * 2) 0 !important;
    }

    /* Surface Cards - Flat, No Shadows, Sharp Corners */
    .surface-card {
        background: var(--bg-surface);
        border: 1px solid var(--border-subtle);
        border-radius: var(--radius-card);
        padding: calc(var(--space-unit) * 3);
        transition: border-color var(--transition-fast), background var(--transition-fast);
    }

    .surface-card:hover {
        border-color: var(--border-emphasis);
        background: var(--bg-surface-elevated);
    }

    .surface-card-elevated {
        background: var(--bg-surface-elevated);
        border: 1px solid var(--border-emphasis);
        border-radius: var(--radius-card);
        padding: calc(var(--space-unit) * 3);
    }

    /* Metric Display Panels */
    .metric-panel {
        display: flex;
        flex-direction: column;
        gap: calc(var(--space-unit) * 0.5);
    }

    .metric-panel .label {
        font-size: 0.625rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: var(--fg-muted);
    }

    .metric-panel .value {
        font-size: clamp(1.5rem, 2.5vw, 2rem);
        font-weight: 300;
        letter-spacing: -0.03em;
        color: var(--fg-primary);
        line-height: 1.1;
    }

    .metric-panel .value.accent {
        color: var(--accent-primary);
        font-weight: 500;
    }

    .metric-panel .value.warn {
        color: var(--accent-warm);
        font-weight: 500;
    }

    .metric-panel .value.critical {
        color: var(--accent-critical);
        font-weight: 500;
    }

    /* Buttons - Minimal, Instant State Changes */
    .stButton > button {
        font-family: 'Inter', sans-serif !important;
        font-size: 0.8125rem !important;
        font-weight: 600 !important;
        letter-spacing: 0.01em !important;
        border-radius: var(--radius-sharp) !important;
        padding: calc(var(--space-unit) * 1.25) calc(var(--space-unit) * 2.5) !important;
        border: 1px solid transparent !important;
        transition: background-color var(--transition-fast), border-color var(--transition-fast), color var(--transition-fast), opacity var(--transition-fast) !important;
    }

    .stButton > button[kind="primary"] {
        background: var(--accent-primary) !important;
        color: var(--bg-canvas) !important;
        border-color: var(--accent-primary) !important;
    }

    .stButton > button[kind="primary"]:hover {
        background: #009BB8 !important;
        border-color: #009BB8 !important;
    }

    .stButton > button[kind="secondary"] {
        background: transparent !important;
        color: var(--fg-secondary) !important;
        border-color: var(--border-emphasis) !important;
    }

    .stButton > button[kind="secondary"]:hover {
        background: var(--bg-surface-elevated) !important;
        color: var(--fg-primary) !important;
        border-color: var(--accent-primary) !important;
    }

    .stButton > button:disabled {
        opacity: 0.35 !important;
        cursor: not-allowed !important;
    }

    /* Input Fields */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stSelectbox > div > div > div {
        background: var(--bg-surface-elevated) !important;
        border: 1px solid var(--border-subtle) !important;
        border-radius: var(--radius-sharp) !important;
        color: var(--fg-primary) !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 0.875rem !important;
        transition: border-color var(--transition-fast), box-shadow var(--transition-fast) !important;
    }

    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus,
    .stSelectbox > div > div > div:focus-within {
        border-color: var(--accent-primary) !important;
        box-shadow: 0 0 0 2px var(--accent-primary-dim) !important;
    }

    /* Tabs - Minimal Underline Style */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0 !important;
        border-bottom: 1px solid var(--border-subtle) !important;
        padding-bottom: 0 !important;
    }

    .stTabs [data-baseweb="tab"] {
        font-family: 'Inter', sans-serif !important;
        font-size: 0.75rem !important;
        font-weight: 600 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.06em !important;
        color: var(--fg-muted) !important;
        background: transparent !important;
        border: none !important;
        border-bottom: 2px solid transparent !important;
        padding: calc(var(--space-unit) * 1.5) calc(var(--space-unit) * 2) !important;
        margin-right: calc(var(--space-unit) * 1.5) !important;
        transition: color var(--transition-fast), border-color var(--transition-fast) !important;
    }

    .stTabs [data-baseweb="tab"]:hover {
        color: var(--fg-secondary) !important;
    }

    .stTabs [aria-selected="true"] {
        color: var(--accent-primary) !important;
        border-bottom-color: var(--accent-primary) !important;
    }

    /* Dataframes / Tables */
    .stDataFrame {
        border: 1px solid var(--border-subtle) !important;
        border-radius: var(--radius-card) !important;
        overflow: hidden !important;
    }

    .stDataFrame [data-testid="stTable"] {
        font-family: 'Inter', sans-serif !important;
        font-size: 0.8125rem !important;
    }

    .stDataFrame th {
        background: var(--bg-surface-elevated) !important;
        color: var(--fg-muted) !important;
        font-weight: 600 !important;
        font-size: 0.625rem !important;
        text-transform: uppercase !important;
        letter-spacing: 0.08em !important;
        padding: calc(var(--space-unit) * 1.5) var(--space-unit) !important;
        border-bottom: 1px solid var(--border-subtle) !important;
    }

    .stDataFrame td {
        color: var(--fg-secondary) !important;
        padding: calc(var(--space-unit) * 1.5) var(--space-unit) !important;
        border-bottom: 1px solid var(--border-subtle) !important;
    }

    .stDataFrame tr:last-child td {
        border-bottom: none !important;
    }

    .stDataFrame tr:hover td {
        background: var(--bg-surface-elevated) !important;
    }

    /* Status Badges - Flat, Sharp */
    .status-badge {
        display: inline-flex;
        align-items: center;
        gap: calc(var(--space-unit) * 0.5);
        font-size: 0.625rem !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.06em !important;
        padding: calc(var(--space-unit) * 0.5) calc(var(--space-unit) * 1.25) !important;
        border-radius: var(--radius-sharp) !important;
    }

    .status-badge--verified {
        background: var(--accent-primary-dim) !important;
        color: var(--accent-primary) !important;
        border: 1px solid var(--accent-primary) !important;
    }

    .status-badge--review {
        background: var(--accent-warm-dim) !important;
        color: var(--accent-warm) !important;
        border: 1px solid var(--accent-warm) !important;
    }

    .status-badge--missing {
        background: var(--accent-critical-dim) !important;
        color: var(--accent-critical) !important;
        border: 1px solid var(--accent-critical) !important;
    }

    .status-badge--neutral {
        background: var(--bg-surface-elevated) !important;
        color: var(--fg-muted) !important;
        border: 1px solid var(--border-subtle) !important;
    }

    /* Code Blocks */
    .stCodeBlock, code, pre {
        font-family: 'JetBrains Mono', 'Fira Code', monospace !important;
        font-size: 0.75rem !important;
        background: var(--bg-surface-elevated) !important;
        border: 1px solid var(--border-subtle) !important;
        border-radius: var(--radius-sharp) !important;
    }

    /* Dividers */
    hr, .stDivider {
        border-color: var(--border-subtle) !important;
        margin: calc(var(--space-unit) * 3) 0 !important;
    }

    /* Scrollbars */
    ::-webkit-scrollbar {
        width: 6px;
        height: 6px;
    }
    ::-webkit-scrollbar-track {
        background: var(--bg-canvas);
    }
    ::-webkit-scrollbar-thumb {
        background: var(--border-emphasis);
        border-radius: 3px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: var(--fg-muted);
    }

    /* Hide Streamlit Branding */
    #MainMenu, footer, header { visibility: hidden; }

    /* Expander */
    .streamlit-expanderHeader {
        font-family: 'Inter', sans-serif !important;
        font-size: 0.8125rem !important;
        font-weight: 600 !important;
        color: var(--fg-primary) !important;
        background: var(--bg-surface) !important;
        border: 1px solid var(--border-subtle) !important;
        border-radius: var(--radius-sharp) !important;
    }

    .streamlit-expanderContent {
        background: var(--bg-surface-elevated) !important;
        border: 1px solid var(--border-subtle) !important;
        border-top: none !important;
        border-radius: 0 0 var(--radius-sharp) var(--radius-sharp) !important;
    }

    /* Tooltips */
    .stTooltipIcon {
        color: var(--fg-muted) !important;
    }

    /* Progress Bar */
    .stProgress > div > div > div {
        background: var(--accent-primary) !important;
        border-radius: var(--radius-sharp) !important;
    }

    .stProgress > div > div {
        background: var(--bg-surface-elevated) !important;
        border-radius: var(--radius-sharp) !important;
    }
</style>
""", unsafe_allow_html=True)

# ---------------- Initialize State & Database ----------------
if "db" not in st.session_state:
    st.session_state.db = Database()

if "current_profile" not in st.session_state:
    # Default initial profile for immediate user experimentation
    default_p = BusinessProfile(
        name="SuryaShakti Renewable Solutions Pvt Ltd",
        industry="Solar",
        state="Maharashtra",
        business_size="Micro (Investment < ₹1 Cr, Turnover < ₹5 Cr)",
        categories_of_interest=["Tender", "Subsidy", "Grant"],
        existing_registrations=["Udyam / MSME Registration", "GSTIN / GST Registration", "PAN Card"],
        annual_turnover_inr=45.0,
        description="EPC contractor for rooftop solar panels and rural microgrids.",
    )
    st.session_state.db.save_profile(default_p)
    st.session_state.current_profile = default_p

if "search_results" not in st.session_state:
    st.session_state.search_results = []

if "active_notice_url" not in st.session_state:
    st.session_state.active_notice_url = None

if "fetched_notice" not in st.session_state:
    st.session_state.fetched_notice = None

if "notice_extraction" not in st.session_state:
    st.session_state.notice_extraction = None

if "notice_verification" not in st.session_state:
    st.session_state.notice_verification = None

if "notice_matching" not in st.session_state:
    st.session_state.notice_matching = None

# Custom user API key overrides
if "user_tf_api_key" not in st.session_state:
    st.session_state.user_tf_api_key = TINYFISH_API_KEY or ""

if "user_gemini_api_key" not in st.session_state:
    st.session_state.user_gemini_api_key = GEMINI_API_KEY or ""


def get_tinyfish_client() -> TinyFishClient:
    return TinyFishClient(api_key=st.session_state.user_tf_api_key)


def get_extraction_agent() -> ExtractionAgent:
    return ExtractionAgent(gemini_api_key=st.session_state.user_gemini_api_key)


def get_verification_agent() -> VerificationAgent:
    return VerificationAgent()


def get_matching_agent() -> MatchingAgent:
    return MatchingAgent()


# ---------------- Sidebar Navigation & Status ----------------
with st.sidebar:
    st.markdown("""
    <div style="margin-bottom: 24px;">
        <div style="font-size: 0.625rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; color: var(--fg-muted); margin-bottom: 4px;">NIYAMAI</div>
        <div style="font-size: 1.125rem; font-weight: 700; letter-spacing: -0.02em; color: var(--fg-primary);">Autonomous Compliance Agent</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<hr>", unsafe_allow_html=True)

    # Navigation menu
    menu = st.radio(
        "NAVIGATION",
        [
            "DASHBOARD",
            "BUSINESS PROFILE",
            "LIVE SCAN",
            "NOTICE AUDIT",
            "SAVED NOTICES",
            "SCAN HISTORY",
            "API SETTINGS",
        ],
        index=0,
        label_visibility="collapsed",
    )

    st.markdown("<hr>", unsafe_allow_html=True)

    # Active profile indicator - minimal
    st.markdown("""
    <div class="label-xs" style="margin-bottom: 8px;">ACTIVE PROFILE</div>
    """, unsafe_allow_html=True)

    profile = st.session_state.current_profile
    st.markdown(f"""
    <div class="surface-card" style="margin-bottom: 16px;">
        <div class="value-md" style="margin-bottom: 4px;">{profile.name}</div>
        <div class="label-xs" style="color: var(--fg-secondary);">{profile.industry} · {profile.state}</div>
        <div class="label-xs" style="color: var(--fg-muted); margin-top: 8px;">{profile.business_size}</div>
    </div>
    """, unsafe_allow_html=True)

    # API Configuration Status
    client = get_tinyfish_client()
    tf_configured = client.is_configured()
    gemini_enabled = bool(st.session_state.user_gemini_api_key)

    st.markdown("""
    <div class="label-xs" style="margin-bottom: 12px;">API STATUS</div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="surface-card">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
            <span class="value-md">TINYFISH SEARCH</span>
            <span class="status-badge {'status-badge--verified' if tf_configured else 'status-badge--missing'}">{'CONNECTED' if tf_configured else 'KEY REQUIRED'}</span>
        </div>
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <span class="value-md">GEMINI EXTRACTION</span>
            <span class="status-badge {'status-badge--verified' if gemini_enabled else 'status-badge--neutral'}">{'ENABLED' if gemini_enabled else 'FALLBACK MODE'}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if not tf_configured:
        st.markdown("""
        <div style="margin-top: 12px; padding: 12px; background: var(--accent-warm-dim); border: 1px solid var(--accent-warm); border-radius: var(--radius-sharp); font-size: 0.75rem; color: var(--accent-warm);">
            Configure TINYFISH_API_KEY in API SETTINGS to enable live scanning
        </div>
        """, unsafe_allow_html=True)


# ==============================================================================
# PAGE 1: DASHBOARD OVERVIEW
# ==============================================================================
if menu == "DASHBOARD":
    st.markdown("""
    <div style="margin-bottom: 32px;">
        <div class="label-xs" style="margin-bottom: 8px; color: var(--accent-primary);">NIYAMAI / DASHBOARD</div>
        <h1>Compliance & Opportunity Hub</h1>
        <div class="value-md" style="margin-top: 8px; max-width: 60ch;">Autonomous AI compliance assistant for Indian startups and MSMEs. Monitors official procurement portals — GeM, CPPP, MSME, Startup India — extracts structured notices, verifies claims against source evidence, and tracks critical deadlines.</div>
    </div>
    """, unsafe_allow_html=True)

    saved_notices = st.session_state.db.get_saved_notices()
    scan_history = st.session_state.db.get_scan_history(limit=50)

    # Hero metrics - asymmetric layout: left dense metrics, right contextual
    col_metrics, col_context = st.columns([0.45, 0.55], gap="large")

    with col_metrics:
        st.markdown("""
        <div class="label-xs" style="margin-bottom: 16px;">KEY METRICS</div>
        """, unsafe_allow_html=True)

        m1, m2 = st.columns(2, gap="medium")
        with m1:
            st.markdown(f"""
            <div class="surface-card metric-panel">
                <div class="label">SAVED OPPORTUNITIES</div>
                <div class="value accent">{len(saved_notices)}</div>
            </div>
            """, unsafe_allow_html=True)
        with m2:
            deadlines_count = sum(1 for n in saved_notices if n.deadline)
            st.markdown(f"""
            <div class="surface-card metric-panel">
                <div class="label">TRACKED DEADLINES</div>
                <div class="value warn">{deadlines_count}</div>
            </div>
            """, unsafe_allow_html=True)

        m3, m4 = st.columns(2, gap="medium")
        with m3:
            avg_score = int(sum(n.relevance_score for n in saved_notices) / len(saved_notices)) if saved_notices else 0
            st.markdown(f"""
            <div class="surface-card metric-panel">
                <div class="label">AVG MATCH SCORE</div>
                <div class="value accent">{avg_score}%</div>
            </div>
            """, unsafe_allow_html=True)
        with m4:
            st.markdown(f"""
            <div class="surface-card metric-panel">
                <div class="label">LIVE SCANS RUN</div>
                <div class="value">{len(scan_history)}</div>
            </div>
            """, unsafe_allow_html=True)

    with col_context:
        st.markdown("""
        <div class="label-xs" style="margin-bottom: 16px;">QUICK ACTION</div>
        """, unsafe_allow_html=True)

        profile = st.session_state.current_profile
        suggested_q = f"{profile.industry} tender {profile.state} msme"

        st.markdown(f"""
        <div class="surface-card">
            <div class="value-md" style="margin-bottom: 4px;">Suggested Query</div>
            <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; color: var(--fg-secondary); background: var(--bg-canvas); padding: 12px; border-radius: var(--radius-sharp); border: 1px solid var(--border-subtle); margin-bottom: 16px;">{suggested_q}</div>
        </div>
        """, unsafe_allow_html=True)

        if st.button("EXECUTE LIVE SCAN", type="primary", use_container_width=True):
            st.session_state.custom_query_override = suggested_q
            st.toast("Navigate to LIVE SCAN to execute", icon="⚡")

        st.markdown("""
        <div class="label-xs" style="margin-top: 24px; margin-bottom: 16px;">UPCOMING DEADLINES</div>
        """, unsafe_allow_html=True)

        if not saved_notices:
            st.markdown("""
            <div class="surface-card" style="padding: 32px; text-align: center;">
                <div class="value-md" style="color: var(--fg-muted);">No notices saved</div>
                <div class="label-xs" style="margin-top: 8px;">Execute a live scan to discover opportunities</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            for sn in saved_notices[:3]:
                st.markdown(f"""
                <div class="niyam-card">
                    <h4>{sn.title}</h4>
                    <p style="margin-bottom: 6px;"><strong>Issuing Portal:</strong> <span class="niyam-badge-teal">{sn.site_name}</span> | <strong>Relevance:</strong> {sn.relevance_score}/100</p>
                    <p style="color: #DC2626; font-weight: 600;">⏰ Submission Deadline: {sn.deadline or 'Check Portal'}</p>
                    <a href="{sn.url}" target="_blank">🔗 Open Official Source Notice</a>
                </div>
                """, unsafe_allow_html=True)

    with col_right:
        st.subheader("🏢 Active Company Snapshot")
        cp = st.session_state.current_profile
        st.markdown(f"""
        <div class="niyam-card">
            <h3>{cp.name}</h3>
            <p><strong>Primary Industry:</strong> {cp.industry}</p>
            <p><strong>Operating State:</strong> {cp.state}</p>
            <p><strong>Scale:</strong> {cp.business_size}</p>
            <p><strong>Annual Turnover:</strong> ₹{cp.annual_turnover_inr or 'N/A'} Lakhs</p>
            <p><strong>Existing Registrations:</strong></p>
            <ul>
                {''.join(f'<li>{r}</li>' for r in cp.existing_registrations)}
            </ul>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("""
    <div class="legal-disclaimer">
        <strong>Compliance Notice:</strong> NiyamAI is an autonomous discovery and analysis tool. Final bidding requirements, qualification criteria, and document formats must always be independently confirmed with the respective government issuing authority.
    </div>
    """, unsafe_allow_html=True)


# ==============================================================================
# PAGE 2: BUSINESS PROFILE
# ==============================================================================
elif menu == "BUSINESS PROFILE":
    st.markdown("""
    <div style="margin-bottom: 32px;">
        <div class="label-xs" style="margin-bottom: 8px; color: var(--accent-primary);">NIYAMAI / BUSINESS PROFILE</div>
        <h1>Eligibility Attributes</h1>
        <div class="value-md" style="margin-top: 8px; max-width: 60ch;">NiyamAI uses your company profile to score opportunities, identify eligibility gaps, and produce tailored document checklists.</div>
    </div>
    """, unsafe_allow_html=True)

    # Preset templates
    st.markdown("""
    <div class="label-xs" style="margin-bottom: 16px;">DEMO PRESETS</div>
    """, unsafe_allow_html=True)

    preset_cols = st.columns(3)
    presets = [
        ("SOLAR EPC MSME", "SuryaShakti Renewable Solutions Pvt Ltd", "Solar", "Maharashtra", "Micro (Investment < ₹1 Cr, Turnover < ₹5 Cr)", ["Tender", "Subsidy"], ["Udyam / MSME Registration", "GSTIN / GST Registration", "PAN Card"], 45.0, "Rooftop solar and EPC installation contractor."),
        ("DRONE ROBOTICS STARTUP", "AeroKisan Agri-Drones Pvt Ltd", "Drones & Robotics", "Karnataka", "DPIIT Recognised Startup", ["Tender", "Grant"], ["DPIIT Startup Recognition", "GSTIN / GST Registration", "PAN Card", "ISO Certification"], 95.0, "Agricultural surveillance and crop spraying drones."),
        ("PRECISION ENGINEERING", "Vidyut Precision Valves & Pumps", "Manufacturing", "Gujarat", "Small (Investment < ₹10 Cr, Turnover < ₹50 Cr)", ["Tender", "Government Scheme"], ["Udyam / MSME Registration", "GSTIN / GST Registration", "PAN Card", "Class 3 Digital Signature (DSC)"], 320.0, "Industrial valves manufacturer supplying water and gas projects."),
    ]

    for i, (label, name, industry, state, size, cats, regs, turnover, desc) in enumerate(presets):
        with preset_cols[i]:
            if st.button(label, use_container_width=True):
                p = BusinessProfile(name=name, industry=industry, state=state, business_size=size, categories_of_interest=cats, existing_registrations=regs, annual_turnover_inr=turnover, description=desc)
                st.session_state.db.save_profile(p)
                st.session_state.current_profile = p
                st.toast(f"Loaded {name}", icon="✓")
                st.rerun()

    st.markdown("<hr>", unsafe_allow_html=True)

    # Profile Form
    with st.form("profile_form"):
        curr = st.session_state.current_profile

        st.markdown("""
        <div class="label-xs" style="margin-bottom: 16px;">CORE IDENTITY</div>
        """, unsafe_allow_html=True)

        name = st.text_input("BUSINESS NAME", value=curr.name)

        col_a, col_b = st.columns(2)
        with col_a:
            industry = st.text_input("PRIMARY INDUSTRY / SECTOR", value=curr.industry, help="e.g. Solar, Software, Defense, Drone, Textile")
            state = st.text_input("REGISTERED STATE / UT", value=curr.state, help="e.g. Maharashtra, Karnataka, Gujarat, Delhi")
            turnover = st.number_input("ANNUAL TURNOVER (₹ IN LAKHS)", min_value=0.0, value=float(curr.annual_turnover_inr or 25.0))

        with col_b:
            size_options = [
                "Micro (Investment < ₹1 Cr, Turnover < ₹5 Cr)",
                "Small (Investment < ₹10 Cr, Turnover < ₹50 Cr)",
                "Medium (Investment < ₹50 Cr, Turnover < ₹250 Cr)",
                "DPIIT Recognised Startup",
                "Large Enterprise",
            ]
            current_size_idx = next((i for i, opt in enumerate(size_options) if curr.business_size in opt), 0)
            business_size = st.selectbox("BUSINESS SIZE TIER", size_options, index=current_size_idx)

            categories = st.multiselect(
                "NOTICE CATEGORIES OF INTEREST",
                ["Tender", "Grant", "Subsidy", "Government Scheme", "Regulatory Notice", "Expression of Interest (EOI)"],
                default=curr.categories_of_interest or ["Tender", "Subsidy"],
            )

        st.markdown("""
        <div class="label-xs" style="margin-top: 20px; margin-bottom: 12px;">ACTIVE REGISTRATIONS</div>
        """, unsafe_allow_html=True)

        registrations = st.multiselect(
            "EXISTING REGISTRATIONS / CERTIFICATIONS",
            [
                "Udyam / MSME Registration",
                "GSTIN / GST Registration",
                "DPIIT Startup Recognition",
                "PAN Card",
                "ISO Certification",
                "Class 3 Digital Signature (DSC)",
                "EPFO / ESIC Registration",
                "Import Export Code (IEC)",
            ],
            default=[r for r in curr.existing_registrations if r in [
                "Udyam / MSME Registration", "GSTIN / GST Registration", "DPIIT Startup Recognition",
                "PAN Card", "ISO Certification", "Class 3 Digital Signature (DSC)", "EPFO / ESIC Registration", "Import Export Code (IEC)"
            ]],
        )

        st.markdown("""
        <div class="label-xs" style="margin-top: 20px; margin-bottom: 12px;">CAPABILITIES</div>
        """, unsafe_allow_html=True)

        description = st.text_area("PRODUCTS / CAPABILITIES OVERVIEW", value=curr.description or "")

        submitted = st.form_submit_button("SAVE PROFILE", type="primary", use_container_width=True)
        if submitted:
            updated_profile = BusinessProfile(
                name=name, industry=industry, state=state, business_size=business_size,
                categories_of_interest=categories, existing_registrations=registrations,
                annual_turnover_inr=turnover, description=description,
            )
            st.session_state.db.save_profile(updated_profile)
            st.session_state.current_profile = updated_profile
            st.toast(f"Profile '{name}' saved", icon="✓")
            st.rerun()


# ==============================================================================
# PAGE 3: LIVE SCAN
# ==============================================================================
elif menu == "LIVE SCAN":
    st.markdown("""
    <div style="margin-bottom: 32px;">
        <div class="label-xs" style="margin-bottom: 8px; color: var(--accent-primary);">NIYAMAI / LIVE SCAN</div>
        <h1>Government Portal Discovery</h1>
        <div class="value-md" style="margin-top: 8px; max-width: 60ch;">Search live web portals in real-time using the TinyFish Search API. Filter for official Indian procurement, tender, and MSME scheme sources.</div>
    </div>
    """, unsafe_allow_html=True)

    client = get_tinyfish_client()
    if not client.is_configured():
        st.warning("⚠️ **TinyFish API Key is not configured yet.**")
        with st.expander("🔑 Enter Your TinyFish API Key Here (or in sidebar 'API Settings')", expanded=True):
            st.markdown(
                "You can get a free key (12,000 free searches/day) at: "
                "[https://agent.tinyfish.ai/api-keys](https://agent.tinyfish.ai/api-keys)"
            )
            c_key, c_btn = st.columns([3, 1])
            with c_key:
                new_key = st.text_input("TinyFish API Key", type="password", key="inline_key_input", placeholder="Paste your API key here...")
            with c_btn:
                st.write("")
                st.write("")
                if st.button("Save Key", type="primary"):
                    if new_key.strip():
                        st.session_state.user_tf_api_key = new_key.strip()
                        st.success("API key saved! Enabling live scan...")
                        st.rerun()

    # Search query generator
    cp = st.session_state.current_profile
    default_gen_query = f"{cp.industry} tender {cp.state} msme"
    if "custom_query_override" in st.session_state:
        default_gen_query = st.session_state.custom_query_override

    with st.expander("🛠️ Search Parameters & Portal Filter", expanded=True):
        col1, col2 = st.columns([3, 1])
        with col1:
            query = st.text_input("Search Query", value=default_gen_query, help="Enter keywords, tender numbers, or scheme names")
        with col2:
            location = st.selectbox("Search Geo-Location", ["IN", "US", "GB"], index=0, help="IN = India geo-targeted search")

        st.markdown("**Restrict to Official Government Domains:**")
        selected_domains = st.multiselect(
            "Target Domains",
            DEFAULT_GOV_DOMAINS,
            default=["gem.gov.in", "eprocure.gov.in", "msme.gov.in", "startupindia.gov.in"],
        )

    scan_col1, scan_col2 = st.columns([1, 1])
    with scan_col1:
        scan_button = st.button("🚀 Run Live Scan with TinyFish", type="primary", disabled=not client.is_configured())

    st.markdown("<hr>", unsafe_allow_html=True)

    if scan_button and query:
        with st.spinner("Calling TinyFish Search API..."):
            try:
                purpose_stmt = f"Discovering public tenders, grants, and regulatory notices for {cp.name} in {cp.industry}"
                search_response = client.search(
                    query=query,
                    purpose=purpose_stmt,
                    location=location,
                    include_domains=selected_domains,
                )

                st.session_state.search_results = search_response.results
                st.session_state.last_search_query = query
                st.session_state.db.save_scan(query=query, profile_name=cp.name, results=search_response.results)
                st.toast(f"Found {search_response.total_results} opportunities", icon="✓")
            except TinyFishAuthError as e:
                st.error(f"Authentication Failed: {e}")
            except TinyFishCreditsError as e:
                st.error(f"Credits Exhausted: {e}")
            except TinyFishRateLimitError as e:
                st.warning(f"Rate Limited: {e}")
            except Exception as e:
                st.error(f"Search failed: {e}")

    if not client.is_configured() and not st.session_state.search_results:
        if st.button("LOAD DEMO DATA", use_container_width=True):
            from tests.conftest import SAMPLE_SEARCH_RESPONSE_JSON
            from models import SearchResultItem
            results = [
                SearchResultItem(
                    position=r["position"], site_name=r["site_name"],
                    title=r["title"], snippet=r["snippet"], url=r["url"], date=r.get("date"),
                )
                for r in SAMPLE_SEARCH_RESPONSE_JSON["results"]
            ]
            st.session_state.search_results = results
            st.session_state.last_search_query = query + " (Demo)"
            st.toast("Loaded demo tenders", icon="✓")
            st.rerun()

    # Display Search Results
    if st.session_state.search_results:
        st.markdown(f"""
        <div class="label-xs" style="margin-bottom: 16px;">SEARCH RESULTS — {len(st.session_state.search_results)} ITEMS</div>
        """, unsafe_allow_html=True)

        for res in st.session_state.search_results:
            st.markdown(f"""
            <div class="surface-card" style="margin-bottom: 12px;">
                <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; margin-bottom: 8px;">
                    <div style="flex: 1;">
                        <span class="status-badge status-badge--neutral">{res.site_name or 'WEB SOURCE'}</span>
                        <div class="value-md" style="margin-top: 8px;">{res.title}</div>
                    </div>
                    <div style="flex-shrink: 0; width: 140px; text-align: right;">
                        <div class="label-xs" style="margin-bottom: 4px;">POSITION</div>
                        <div class="value-md" style="font-size: 1.5rem;">#{res.position}</div>
                    </div>
                </div>
                <div style="color: var(--fg-secondary); font-size: 0.8125rem; line-height: 1.5; margin-bottom: 8px;">{res.snippet}</div>
                <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; color: var(--fg-muted);">URL: {res.url}</div>
            </div>
            """, unsafe_allow_html=True)

            if st.button("FETCH & ANALYZE", key=f"fetch_{res.url}", use_container_width=True):
                st.session_state.active_notice_url = res.url
                st.session_state.active_notice_title_hint = res.title
                st.session_state.fetched_notice = None
                st.session_state.notice_extraction = None
                st.session_state.notice_verification = None
                st.session_state.notice_matching = None
                st.toast("Navigate to NOTICE AUDIT", icon="⚡")
    elif client.is_configured():
        st.markdown("""
        <div class="surface-card" style="padding: 32px; text-align: center;">
            <div class="value-md" style="color: var(--fg-muted);">No results</div>
            <div class="label-xs" style="margin-top: 8px;">Enter a query and execute scan</div>
        </div>
        """, unsafe_allow_html=True)


# ==============================================================================
# PAGE 4: NOTICE DEEP DIVE (FETCH, EXTRACT, VERIFY, MATCH)
# ==============================================================================
elif menu == "NOTICE AUDIT":
    st.markdown("""
    <div style="margin-bottom: 32px;">
        <div class="label-xs" style="margin-bottom: 8px; color: var(--accent-primary);">NIYAMAI / NOTICE AUDIT</div>
        <h1>Fetch, Extract, Verify, Match</h1>
        <div class="value-md" style="margin-top: 8px; max-width: 60ch;">Fetch official notice content with TinyFish Fetch API, extract structured compliance fields, independently verify claims against raw text evidence, and compute business profile compatibility.</div>
    </div>
    """, unsafe_allow_html=True)

    client = get_tinyfish_client()
    default_url = st.session_state.active_notice_url or "https://gem.gov.in/tenders/solar-pv-98712"
    title_hint = getattr(st.session_state, "active_notice_title_hint", None)

    # URL Input Section
    st.markdown("""
    <div class="label-xs" style="margin-bottom: 12px;">TARGET URL</div>
    """, unsafe_allow_html=True)

    input_url = st.text_input("NOTICE URL", value=default_url, label_visibility="collapsed", placeholder="https://gem.gov.in/tenders/...")

    fetch_col, sample_col = st.columns([1, 1])
    with fetch_col:
        fetch_clicked = st.button("FETCH LIVE NOTICE", type="primary", use_container_width=True, disabled=not client.is_configured())

    with sample_col:
        if not client.is_configured():
            if st.button("LOAD DEMO NOTICE", use_container_width=True):
                from tests.conftest import SAMPLE_FETCH_SUCCESS_JSON
                from models import FetchResponseItem
                raw_sample = SAMPLE_FETCH_SUCCESS_JSON["results"][0]
                st.session_state.fetched_notice = FetchResponseItem(
                    url=raw_sample["url"], final_url=raw_sample["final_url"],
                    title=raw_sample["title"], description=raw_sample["description"],
                    language=raw_sample["language"], text=raw_sample["text"],
                    format=raw_sample["format"],
                )
                st.session_state.active_notice_url = raw_sample["url"]
                st.session_state.notice_extraction = None
                st.session_state.notice_verification = None
                st.session_state.notice_matching = None
                st.toast("Loaded MNRE Solar Rooftop demo notice", icon="✓")
                st.rerun()

    if fetch_clicked and input_url:
        with st.spinner("Fetching with TinyFish Fetch API..."):
            try:
                fetch_res = client.fetch(
                    urls=[input_url],
                    purpose="Extract procurement requirements, deadlines, and eligibility criteria for MSME compliance audit",
                    format="markdown",
                )
                if fetch_res.results:
                    st.session_state.fetched_notice = fetch_res.results[0]
                    st.session_state.active_notice_url = input_url
                    st.toast(f"Fetched {len(st.session_state.fetched_notice.text or '')} chars", icon="✓")
                elif fetch_res.errors:
                    err = fetch_res.errors[0]
                    st.error(f"Fetch Error: {err.error} (Status: {err.status})")
            except Exception as e:
                st.error(f"Fetch failed: {e}")

    # If document fetched, offer Analysis Pipeline
    if st.session_state.fetched_notice:
        fn = st.session_state.fetched_notice

        # Automatically execute Extraction, Verification, Matching if not yet done
        if not st.session_state.notice_extraction:
            with st.spinner("Running Multi-Agent Pipeline..."):
                ext_agent = get_extraction_agent()
                ver_agent = get_verification_agent()
                mat_agent = get_matching_agent()

                extraction = ext_agent.extract(raw_text=fn.text or "", source_url=fn.url, title_hint=title_hint or fn.title)
                st.session_state.notice_extraction = extraction

                verification = ver_agent.verify(extraction=extraction, raw_text=fn.text or "")
                st.session_state.notice_verification = verification

                matching = mat_agent.match(profile=st.session_state.current_profile, extraction=extraction)
                st.session_state.notice_matching = matching

        ext = st.session_state.notice_extraction
        ver = st.session_state.notice_verification
        mat = st.session_state.notice_matching

        # Pipeline tabs
        tab1, tab2, tab3, tab4 = st.tabs([
            "SOURCE", "EXTRACTION", "VERIFICATION", "MATCH & CHECKLIST"
        ])

        # TAB 1: RETRIEVED SOURCE
        with tab1:
            st.markdown("""
            <div class="label-xs" style="margin-bottom: 16px;">DOCUMENT METADATA</div>
            """, unsafe_allow_html=True)

            meta_cols = st.columns(4)
            with meta_cols[0]:
                st.markdown(f"""
                <div class="surface-card metric-panel">
                    <div class="label">TARGET URL</div>
                    <div class="value" style="font-size: 0.875rem; font-family: 'JetBrains Mono', monospace;">{fn.url}</div>
                </div>
                """, unsafe_allow_html=True)
            with meta_cols[1]:
                st.markdown(f"""
                <div class="surface-card metric-panel">
                    <div class="label">FINAL URL</div>
                    <div class="value" style="font-size: 0.875rem; font-family: 'JetBrains Mono', monospace;">{fn.final_url or fn.url}</div>
                </div>
                """, unsafe_allow_html=True)
            with meta_cols[2]:
                st.markdown(f"""
                <div class="surface-card metric-panel">
                    <div class="label">DETECTED TITLE</div>
                    <div class="value" style="font-size: 0.875rem;">{fn.title or 'N/A'}</div>
                </div>
                """, unsafe_allow_html=True)
            with meta_cols[3]:
                st.markdown(f"""
                <div class="surface-card metric-panel">
                    <div class="label">LATENCY</div>
                    <div class="value accent">{fn.latency_ms or 'N/A'} ms</div>
                </div>
                """, unsafe_allow_html=True)

            st.markdown("""
            <div class="label-xs" style="margin-top: 24px; margin-bottom: 12px;">RAW MARKDOWN</div>
            """, unsafe_allow_html=True)

            with st.expander("VIEW FULL FETCHED MARKDOWN", expanded=True):
                st.markdown(f"""
                <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; line-height: 1.6; background: var(--bg-canvas); border: 1px solid var(--border-subtle); border-radius: var(--radius-sharp); padding: 16px; max-height: 600px; overflow-y: auto;">
                {fn.text[:12000] if fn.text else '*Empty content*'}
                </div>
                """, unsafe_allow_html=True)
                if fn.text and len(fn.text) > 12000:
                    st.caption(f"Showing first 12,000 of {len(fn.text)} characters")

        # TAB 2: EXTRACTION
        with tab2:
            st.markdown("""
            <div class="label-xs" style="margin-bottom: 16px;">STRUCTURED FIELDS (PYDANTIC VALIDATED)</div>
            """, unsafe_allow_html=True)

            ec1, ec2 = st.columns(2)
            with ec1:
                fields = [
                    ("NOTICE TITLE", ext.title),
                    ("ISSUING AUTHORITY", ext.issuing_authority or "Unknown"),
                    ("CATEGORY", ext.category),
                    ("GEOGRAPHIC SCOPE", ext.geographic_scope or "All India"),
                ]
                for label, value in fields:
                    st.markdown(f"""
                    <div class="surface-card" style="margin-bottom: 12px;">
                        <div class="label">{label}</div>
                        <div class="value-md">{value}</div>
                    </div>
                    """, unsafe_allow_html=True)

            with ec2:
                deadline_status = "DEADLINE FOUND" if ext.submission_deadline else "NOT SPECIFIED"
                deadline_class = "accent" if ext.submission_deadline else "warn"
                st.markdown(f"""
                <div class="surface-card" style="margin-bottom: 12px;">
                    <div class="label">SUBMISSION DEADLINE</div>
                    <div class="value {deadline_class}" style="font-size: 1.25rem;">{ext.submission_deadline or deadline_status}</div>
                </div>
                """, unsafe_allow_html=True)

                st.markdown(f"""
                <div class="surface-card" style="margin-bottom: 12px;">
                    <div class="label">FINANCIALS (EMD / COST)</div>
                    <div class="value-md">{ext.financial_requirements or 'None stated'}</div>
                </div>
                """, unsafe_allow_html=True)

                st.markdown(f"""
                <div class="surface-card" style="margin-bottom: 12px;">
                    <div class="label">REFERENCE / ID</div>
                    <div class="value-md">{ext.scheme_or_tender_name or 'N/A'}</div>
                </div>
                """, unsafe_allow_html=True)

            if ext.required_registrations:
                st.markdown("""
                <div class="label-xs" style="margin-top: 20px; margin-bottom: 12px;">MANDATORY REGISTRATIONS</div>
                """, unsafe_allow_html=True)
                for r in ext.required_registrations:
                    st.markdown(f"""
                    <div class="surface-card" style="margin-bottom: 8px; display: flex; align-items: center; gap: 12px;">
                        <div class="status-badge status-badge--verified">REQUIRED</div>
                        <div class="value-md">{r}</div>
                    </div>
                    """, unsafe_allow_html=True)

            if ext.required_documents:
                st.markdown("""
                <div class="label-xs" style="margin-top: 20px; margin-bottom: 12px;">REQUIRED APPLICATION DOCUMENTS</div>
                """, unsafe_allow_html=True)
                for d in ext.required_documents:
                    st.markdown(f"""
                    <div class="surface-card" style="margin-bottom: 8px; display: flex; align-items: center; gap: 12px;">
                        <div class="status-badge status-badge--neutral">DOCUMENT</div>
                        <div class="value-md">{d}</div>
                    </div>
                    """, unsafe_allow_html=True)

            if ext.uncertain_or_missing_fields:
                st.markdown(f"""
                <div style="margin-top: 20px; padding: 16px; background: var(--accent-warm-dim); border: 1px solid var(--accent-warm); border-radius: var(--radius-sharp);">
                    <div class="label-xs" style="color: var(--accent-warm); margin-bottom: 8px;">UNCERTAIN OR MISSING FIELDS</div>
                    <div class="value-md" style="color: var(--accent-warm);">{', '.join(ext.uncertain_or_missing_fields)}</div>
                </div>
                """, unsafe_allow_html=True)

        # TAB 3: VERIFICATION
        with tab3:
            st.markdown("""
            <div class="label-xs" style="margin-bottom: 16px;">SOURCE EVIDENCE & CLAIM VERIFICATION</div>
            """, unsafe_allow_html=True)

            status_map = {
                VerificationStatus.VERIFIED: ("VERIFIED", "status-badge--verified"),
                VerificationStatus.PARTIAL: ("PARTIAL", "status-badge--neutral"),
                VerificationStatus.NEEDS_REVIEW: ("NEEDS REVIEW", "status-badge--review"),
                VerificationStatus.MISSING: ("MISSING FROM SOURCE", "status-badge--missing"),
            }

            st.markdown(f"""
            <div class="surface-card" style="margin-bottom: 20px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <div class="label">OVERALL AUDIT STATUS</div>
                        <div class="value-md">{ver.overall_status}</div>
                    </div>
                    <span class="status-badge {status_map.get(ver.overall_status, ('', 'status-badge--neutral'))[1]}">{status_map.get(ver.overall_status, ('', ''))[0]}</span>
                </div>
                <div class="value-md" style="margin-top: 8px; color: var(--fg-secondary);">{ver.summary}</div>
            </div>
            """, unsafe_allow_html=True)

            for claim in ver.claims:
                status_label, status_class = status_map.get(claim.status, ("UNKNOWN", "status-badge--neutral"))
                evidence = claim.supporting_evidence or "— No supporting text found —"

                st.markdown(f"""
                <div class="surface-card" style="margin-bottom: 12px;">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; margin-bottom: 12px;">
                        <div>
                            <div class="label">CLAIM FIELD</div>
                            <div class="value-md">{claim.claim_field}</div>
                        </div>
                        <span class="status-badge {status_class}" style="flex-shrink: 0;">{status_label}</span>
                    </div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; font-size: 0.8125rem;">
                        <div>
                            <div class="label" style="margin-bottom: 4px;">EXTRACTED VALUE</div>
                            <div style="font-family: 'JetBrains Mono', monospace; color: var(--fg-primary); background: var(--bg-canvas); padding: 8px; border-radius: var(--radius-sharp); border: 1px solid var(--border-subtle);">{claim.extracted_value}</div>
                        </div>
                        <div>
                            <div class="label" style="margin-bottom: 4px;">SOURCE EVIDENCE</div>
                            <div style="color: var(--fg-secondary); background: var(--bg-canvas); padding: 8px; border-radius: var(--radius-sharp); border: 1px solid var(--border-subtle); font-style: italic;">{evidence}</div>
                        </div>
                    </div>
                    <div class="label" style="margin-top: 12px;">AUDIT RATIONALE</div>
                    <div class="value-md" style="color: var(--fg-secondary);">{claim.explanation}</div>
                </div>
                """, unsafe_allow_html=True)

        # TAB 4: MATCHING & CHECKLIST
        with tab4:
            st.markdown(f"""
            <div class="label-xs" style="margin-bottom: 16px;">COMPATIBILITY — {st.session_state.current_profile.name.upper()}</div>
            """, unsafe_allow_html=True)

            mcol1, mcol2 = st.columns([0.35, 0.65], gap="large")

            with mcol1:
                score_class = "accent" if mat.relevance_score >= 80 else "warn" if mat.relevance_score >= 50 else "critical"
                st.markdown(f"""
                <div class="surface-card metric-panel" style="text-align: center; padding: 32px;">
                    <div class="label">RELEVANCE SCORE</div>
                    <div class="value {score_class}" style="font-size: 4rem; line-height: 1;">{mat.relevance_score}</div>
                    <div style="margin-top: 16px; height: 4px; background: var(--bg-canvas); border-radius: 2px; overflow: hidden;">
                        <div style="width: {mat.relevance_score}%; height: 100%; background: var(--accent-primary);"></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                st.markdown("""
                <div class="label-xs" style="margin-top: 24px; margin-bottom: 12px;">SCORE BREAKDOWN</div>
                """, unsafe_allow_html=True)

                for k, v in mat.score_breakdown.items():
                    st.markdown(f"""
                    <div class="surface-card" style="margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center;">
                        <div class="value-md">{k}</div>
                        <div class="value accent" style="font-size: 1.25rem;">{v} pts</div>
                    </div>
                    """, unsafe_allow_html=True)

            with mcol2:
                st.markdown(f"""
                <div class="surface-card" style="margin-bottom: 20px;">
                    <div class="label">ANALYSIS SUMMARY</div>
                    <div class="value-md">{mat.relevance_explanation}</div>
                </div>
                """, unsafe_allow_html=True)

                if mat.satisfied_criteria:
                    st.markdown("""
                    <div class="label-xs" style="margin-bottom: 12px;">SATISFIED REQUIREMENTS</div>
                    """, unsafe_allow_html=True)
                    for s in mat.satisfied_criteria:
                        st.markdown(f"""
                        <div class="surface-card" style="margin-bottom: 8px; display: flex; align-items: center; gap: 12px;">
                            <div class="status-badge status-badge--verified">MET</div>
                            <div class="value-md">{s}</div>
                        </div>
                        """, unsafe_allow_html=True)

                if mat.unsatisfied_criteria:
                    st.markdown("""
                    <div class="label-xs" style="margin-top: 20px; margin-bottom: 12px;">GAPS & INELIGIBILITY RISKS</div>
                    """, unsafe_allow_html=True)
                    for u in mat.unsatisfied_criteria:
                        st.markdown(f"""
                        <div class="surface-card" style="margin-bottom: 8px; display: flex; align-items: center; gap: 12px;">
                            <div class="status-badge status-badge--missing">GAP</div>
                            <div class="value-md">{u}</div>
                        </div>
                        """, unsafe_allow_html=True)

                if mat.information_needed:
                    st.markdown("""
                    <div class="label-xs" style="margin-top: 20px; margin-bottom: 12px;">INFORMATION NEEDED FROM YOU</div>
                    """, unsafe_allow_html=True)
                    for q in mat.information_needed:
                        st.markdown(f"""
                        <div class="surface-card" style="margin-bottom: 8px; display: flex; align-items: center; gap: 12px;">
                            <div class="status-badge status-badge--review">PENDING</div>
                            <div class="value-md">{q}</div>
                        </div>
                        """, unsafe_allow_html=True)

                st.markdown("""
                <div class="label-xs" style="margin-top: 24px; margin-bottom: 12px;">APPLICATION DOCUMENT CHECKLIST</div>
                """, unsafe_allow_html=True)

                for idx, item in enumerate(mat.checklist):
                    is_present = item.is_present_in_profile
                    badge_class = "status-badge--verified" if is_present else "status-badge--missing"
                    badge_label = "PRESENT" if is_present else "MISSING"
                    st.markdown(f"""
                    <div class="surface-card" style="margin-bottom: 8px; display: flex; align-items: center; gap: 12px;">
                        <span class="status-badge {badge_class}">{badge_label}</span>
                        <div style="flex: 1;">
                            <div class="value-md" style="margin-bottom: 2px;">{item.document_name}</div>
                            <div class="label-xs" style="color: var(--fg-secondary);">{item.status_note}</div>
                        </div>
                        <input type="checkbox" {"checked" if is_present else ""} disabled style="width: 18px; height: 18px; accent-color: var(--accent-primary);">
                    </div>
                    """, unsafe_allow_html=True)

                st.markdown("""
                <div class="label-xs" style="margin-top: 24px; margin-bottom: 12px;">RECOMMENDED NEXT STEPS</div>
                """, unsafe_allow_html=True)

                for step in mat.recommended_next_steps:
                    st.markdown(f"""
                    <div class="surface-card" style="margin-bottom: 8px; display: flex; align-items: flex-start; gap: 12px;">
                        <div class="label-xs" style="color: var(--accent-primary); margin-top: 2px;">→</div>
                        <div class="value-md">{step}</div>
                    </div>
                    """, unsafe_allow_html=True)

        # Save button
        st.markdown("<hr>", unsafe_allow_html=True)
        if st.button("SAVE NOTICE TO DATABASE", type="primary", use_container_width=True):
            saved_obj = SavedNotice(
                url=fn.url, title=ext.title,
                site_name=fn.url.split("/")[2] if "/" in fn.url else "Government Portal",
                category=ext.category, deadline=ext.submission_deadline,
                relevance_score=mat.relevance_score, raw_content=fn.text or "",
                extraction=ext, verification=ver, matching=mat,
            )
            nid, is_dup = st.session_state.db.save_notice(saved_obj)
            if is_dup:
                st.toast(f"Notice updated (ID: {nid})", icon="↻")
            else:
                st.toast(f"Notice saved (ID: {nid})", icon="✓")


# ==============================================================================
# PAGE 5: SAVED NOTICES
# ==============================================================================
elif menu == "SAVED NOTICES":
    st.markdown("""
    <div style="margin-bottom: 32px;">
        <div class="label-xs" style="margin-bottom: 8px; color: var(--accent-primary);">NIYAMAI / SAVED NOTICES</div>
        <h1>Persisted Opportunities</h1>
        <div class="value-md" style="margin-top: 8px; max-width: 60ch;">SQLite database records with deduplication and complete agent audit trails.</div>
    </div>
    """, unsafe_allow_html=True)

    saved_notices = st.session_state.db.get_saved_notices()

    if not saved_notices:
        st.markdown("""
        <div class="surface-card" style="padding: 48px; text-align: center;">
            <div class="value-md" style="color: var(--fg-muted);">No saved notices</div>
            <div class="label-xs" style="margin-top: 8px;">Execute a live scan and save notices to populate this view</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="label-xs" style="margin-bottom: 16px;">TOTAL RECORDS — {len(saved_notices)}</div>
        """, unsafe_allow_html=True)

        for sn in saved_notices:
            score_class = "accent" if sn.relevance_score >= 80 else "warn" if sn.relevance_score >= 50 else "critical"
            deadline_display = sn.deadline or "Check Portal"

            st.markdown(f"""
            <div class="surface-card" style="margin-bottom: 12px;">
                <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; margin-bottom: 12px;">
                    <div style="flex: 1;">
                        <span class="status-badge status-badge--neutral">{sn.site_name}</span>
                        <div class="value-md" style="margin-top: 8px;">{sn.title}</div>
                    </div>
                    <div style="display: flex; flex-direction: column; align-items: flex-end; gap: 4px; flex-shrink: 0;">
                        <span class="status-badge {'status-badge--verified' if score_class == 'accent' else 'status-badge--review' if score_class == 'warn' else 'status-badge--missing'}">SCORE {sn.relevance_score}/100</span>
                        <div class="label-xs" style="text-align: right;">SAVED: {sn.saved_at}</div>
                    </div>
                </div>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; font-size: 0.8125rem;">
                    <div><div class="label">CATEGORY</div><div class="value-md">{sn.category}</div></div>
                    <div><div class="label">DEADLINE</div><div class="value warn">{deadline_display}</div></div>
                </div>
                <div style="margin-top: 12px; padding-top: 12px; border-top: 1px solid var(--border-subtle); display: flex; justify-content: space-between; align-items: center;">
                    <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; color: var(--fg-muted);">{sn.url}</div>
                    <div style="display: flex; gap: 8px;">
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            col_a, col_b = st.columns([1, 5])
            with col_a:
                if st.button("DELETE", key=f"del_{sn.id}", use_container_width=True):
                    st.session_state.db.delete_saved_notice(sn.id)
                    st.toast("Notice deleted", icon="🗑️")
                    st.rerun()
            with col_b:
                if st.button("OPEN AUDIT", key=f"open_{sn.id}", use_container_width=True):
                    st.session_state.active_notice_url = sn.url
                    st.session_state.notice_extraction = sn.extraction
                    st.session_state.notice_verification = sn.verification
                    st.session_state.notice_matching = sn.matching
                    st.toast("Navigate to NOTICE AUDIT", icon="⚡")


# ==============================================================================
# PAGE 6: SCAN HISTORY
# ==============================================================================
elif menu == "SCAN HISTORY":
    st.markdown("""
    <div style="margin-bottom: 32px;">
        <div class="label-xs" style="margin-bottom: 8px; color: var(--accent-primary);">NIYAMAI / SCAN HISTORY</div>
        <h1>Audit Log</h1>
        <div class="value-md" style="margin-top: 8px; max-width: 60ch;">Audit log of all queries executed against TinyFish Search API.</div>
    </div>
    """, unsafe_allow_html=True)

    history = st.session_state.db.get_scan_history(limit=50)
    if not history:
        st.markdown("""
        <div class="surface-card" style="padding: 48px; text-align: center;">
            <div class="value-md" style="color: var(--fg-muted);">No scan history recorded</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        for item in history:
            with st.expander(f"QUERY: {item['query']} — {item['result_count']} RESULTS ({item['scanned_at']})", expanded=False):
                st.markdown(f"""
                <div class="surface-card">
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 16px;">
                        <div><div class="label">PROFILE</div><div class="value-md">{item['profile_name']}</div></div>
                        <div><div class="label">TIMESTAMP</div><div class="value-md">{item['scanned_at']}</div></div>
                        <div><div class="label">RESULTS</div><div class="value accent">{item['result_count']}</div></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                for r in item["results"]:
                    st.markdown(f"""
                    <div class="surface-card" style="margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <div class="value-md">{r.get('title')}</div>
                            <div class="label-xs">{r.get('site_name')}</div>
                        </div>
                        <a href="{r.get('url')}" target="_blank" class="status-badge status-badge--neutral" style="text-decoration: none;">OPEN SOURCE</a>
                    </div>
                    """, unsafe_allow_html=True)


# ==============================================================================
# PAGE 7: API SETTINGS
# ==============================================================================
elif menu == "API SETTINGS":
    st.markdown("""
    <div style="margin-bottom: 32px;">
        <div class="label-xs" style="margin-bottom: 8px; color: var(--accent-primary);">NIYAMAI / API SETTINGS</div>
        <h1>Configuration & Diagnostics</h1>
        <div class="value-md" style="margin-top: 8px; max-width: 60ch;">Configure credentials and verify system connectivity.</div>
    </div>
    """, unsafe_allow_html=True)

    with st.form("api_keys_form"):
        st.markdown("""
        <div class="label-xs" style="margin-bottom: 16px;">API CREDENTIALS</div>
        """, unsafe_allow_html=True)

        tf_key = st.text_input(
            "TINYFISH API KEY",
            value=st.session_state.user_tf_api_key,
            type="password",
            help="Required for Search & Fetch. Get at: https://agent.tinyfish.ai/api-keys",
        )
        gemini_key = st.text_input(
            "GOOGLE GEMINI API KEY",
            value=st.session_state.user_gemini_api_key,
            type="password",
            help="Optional for LLM extraction. Get at: https://aistudio.google.com/. Empty = deterministic fallback.",
        )

        save_keys = st.form_submit_button("SAVE CREDENTIALS", type="primary", use_container_width=True)
        if save_keys:
            st.session_state.user_tf_api_key = tf_key.strip()
            st.session_state.user_gemini_api_key = gemini_key.strip()
            st.toast("API keys updated", icon="✓")
            st.rerun()

    st.markdown("<hr>", unsafe_allow_html=True)

    st.markdown("""
    <div class="label-xs" style="margin-bottom: 16px;">DIAGNOSTICS</div>
    """, unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"""
        <div class="surface-card">
            <div class="label">DATABASE PATH</div>
            <div class="value-md" style="font-family: 'JetBrains Mono', monospace; font-size: 0.75rem;">{NIYAMAI_DB_PATH}</div>
            <div class="label" style="margin-top: 16px;">TINYFISH CLIENT</div>
            <div class="value-md">{'CONFIGURED' if get_tinyfish_client().is_configured() else 'NOT CONFIGURED'}</div>
            <div class="label" style="margin-top: 16px;">LLM EXTRACTION</div>
            <div class="value-md">{'ENABLED' if bool(st.session_state.user_gemini_api_key) else 'FALLBACK MODE'}</div>
        </div>
        """, unsafe_allow_html=True)

    with c2:
        if st.button("TEST TINYFISH CONNECTION", use_container_width=True):
            client = get_tinyfish_client()
            if not client.is_configured():
                st.error("Cannot test: TINYFISH_API_KEY is not set.")
            else:
                with st.spinner("Pinging TinyFish Search API..."):
                    try:
                        res = client.search(query="test", page=0)
                        st.toast(f"TinyFish responded: {len(res.results)} results", icon="✓")
                    except Exception as e:
                        st.error(f"Connection test failed: {e}")
