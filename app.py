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
    page_title="NiyamAI - Autonomous Compliance & Tender Agent",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------- Navy & Teal Custom Styling ----------------
st.markdown("""
<style>
    /* Theme color variables */
    :root {
        --bg-navy-dark: #0A192F;
        --bg-navy-card: #112240;
        --accent-teal: #00B4D8;
        --accent-teal-light: #64DFDF;
        --text-light: #F8F9FA;
        --text-muted: #8892B0;
    }
    
    /* Header & typography */
    h1, h2, h3 {
        color: #0A192F !important;
        font-weight: 700;
    }
    
    /* Custom badge styles */
    .niyam-badge-teal {
        background-color: #E0F2FE;
        color: #0369A1;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.82rem;
        font-weight: 600;
        display: inline-block;
        border: 1px solid #BAE6FD;
    }
    .niyam-badge-verified {
        background-color: #DCFCE7;
        color: #15803D;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.82rem;
        font-weight: 600;
        display: inline-block;
        border: 1px solid #BBF7D0;
    }
    .niyam-badge-review {
        background-color: #FEF3C7;
        color: #B45309;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.82rem;
        font-weight: 600;
        display: inline-block;
        border: 1px solid #FDE68A;
    }
    .niyam-badge-missing {
        background-color: #FEE2E2;
        color: #B91C1C;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.82rem;
        font-weight: 600;
        display: inline-block;
        border: 1px solid #FECACA;
    }
    
    /* Card design */
    .niyam-card {
        background: #FFFFFF;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #E2E8F0;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        margin-bottom: 16px;
        transition: transform 0.15s ease-in-out, box-shadow 0.15s ease-in-out;
    }
    .niyam-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.08);
    }
    
    /* Metric hero card */
    .metric-box {
        background: linear-gradient(135deg, #0A192F 0%, #1E3A8A 100%);
        color: #FFFFFF !important;
        padding: 18px;
        border-radius: 10px;
        text-align: center;
        box-shadow: 0 4px 12px rgba(10, 25, 47, 0.15);
    }
    .metric-value {
        font-size: 2rem;
        font-weight: 800;
        color: #64DFDF;
    }
    .metric-label {
        font-size: 0.85rem;
        color: #E2E8F0;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    /* Disclaimer */
    .legal-disclaimer {
        font-size: 0.78rem;
        color: #64748B;
        border-left: 3px solid #00B4D8;
        padding-left: 10px;
        margin-top: 20px;
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
    st.markdown("## ⚖️ **NiyamAI**")
    st.caption("Never Miss a Government Opportunity or Compliance Deadline.")
    st.divider()

    # Navigation menu
    menu = st.radio(
        "Navigation",
        [
            "📊 Dashboard Overview",
            "🏢 Business Profile",
            "🔍 Live Scan & Search",
            "📑 Notice Deep Dive & Audit",
            "💾 Saved Notices & Deadlines",
            "📜 Scan History",
            "⚙️ API Settings & Diagnostics",
        ],
        index=0,
    )

    st.divider()

    # Active profile indicator
    st.markdown(f"**Active Profile:**")
    st.info(f"🏢 **{st.session_state.current_profile.name}**\n\n📌 Sector: {st.session_state.current_profile.industry} | {st.session_state.current_profile.state}")

    st.divider()

    # API Configuration Status
    client = get_tinyfish_client()
    tf_status = "🟢 Connected" if client.is_configured() else "🔴 Key Missing"
    gemini_status = "🟢 Enabled" if bool(st.session_state.user_gemini_api_key) else "⚪ Fallback Active"

    st.markdown("### 🔌 API Status")
    st.write(f"**TinyFish API:** {tf_status}")
    st.write(f"**Gemini AI:** {gemini_status}")

    if not client.is_configured():
        st.warning("⚠️ Enter your `TINYFISH_API_KEY` in 'API Settings' to enable live scanning.")


# ==============================================================================
# PAGE 1: DASHBOARD OVERVIEW
# ==============================================================================
if menu == "📊 Dashboard Overview":
    st.title("🛡️ NiyamAI Compliance & Opportunity Hub")
    st.markdown(
        "Autonomous AI compliance assistant for Indian startups and MSMEs. "
        "Monitors official procurement portals (GeM, CPPP, MSME, Startup India), "
        "extracts structured notices, verifies claims against source evidence, and tracks critical deadlines."
    )

    saved_notices = st.session_state.db.get_saved_notices()
    scan_history = st.session_state.db.get_scan_history(limit=50)

    # Hero metrics
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown("""
        <div class="metric-box">
            <div class="metric-value">""" + str(len(saved_notices)) + """</div>
            <div class="metric-label">Saved Opportunities</div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        deadlines_count = sum(1 for n in saved_notices if n.deadline)
        st.markdown("""
        <div class="metric-box">
            <div class="metric-value">""" + str(deadlines_count) + """</div>
            <div class="metric-label">Tracked Deadlines</div>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        avg_score = int(sum(n.relevance_score for n in saved_notices) / len(saved_notices)) if saved_notices else 0
        st.markdown("""
        <div class="metric-box">
            <div class="metric-value">""" + str(avg_score) + """%</div>
            <div class="metric-label">Avg Match Score</div>
        </div>
        """, unsafe_allow_html=True)
    with c4:
        st.markdown("""
        <div class="metric-box">
            <div class="metric-value">""" + str(len(scan_history)) + """</div>
            <div class="metric-label">Live Scans Run</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    col_left, col_right = st.columns([3, 2])

    with col_left:
        st.subheader("⚡ Quick Action: One-Click Discovery")
        st.markdown(f"Execute a live scan tailored for **{st.session_state.current_profile.name}**:")

        suggested_q = f"{st.session_state.current_profile.industry} tender {st.session_state.current_profile.state} msme"
        st.code(suggested_q, language="text")

        if st.button("🚀 Run Live Scan Now", type="primary"):
            st.session_state.custom_query_override = suggested_q
            st.info("Navigating to Live Scan page... Please click '🔍 Live Scan & Search' on the sidebar.")

        st.subheader("📋 Upcoming Tracked Deadlines")
        if not saved_notices:
            st.info("No notices saved yet. Run a scan to discover public tenders and government schemes.")
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
elif menu == "🏢 Business Profile":
    st.title("🏢 Business Profile & Eligibility Attributes")
    st.markdown(
        "NiyamAI uses your company profile to score opportunities, identify eligibility gaps, "
        "and produce tailored document checklists."
    )

    # Preset templates
    st.subheader("Load Quick Demo Profiles")
    preset_cols = st.columns(3)
    with preset_cols[0]:
        if st.button("☀️ Solar EPC MSME (Pune)"):
            p = BusinessProfile(
                name="SuryaShakti Renewable Solutions Pvt Ltd",
                industry="Solar",
                state="Maharashtra",
                business_size="Micro (Investment < ₹1 Cr, Turnover < ₹5 Cr)",
                categories_of_interest=["Tender", "Subsidy"],
                existing_registrations=["Udyam / MSME Registration", "GSTIN / GST Registration", "PAN Card"],
                annual_turnover_inr=45.0,
                description="Rooftop solar and EPC installation contractor.",
            )
            st.session_state.db.save_profile(p)
            st.session_state.current_profile = p
            st.success("Loaded SuryaShakti profile!")
            st.rerun()

    with preset_cols[1]:
        if st.button("🚁 Drone Robotics Startup (Bengaluru)"):
            p = BusinessProfile(
                name="AeroKisan Agri-Drones Pvt Ltd",
                industry="Drones & Robotics",
                state="Karnataka",
                business_size="DPIIT Recognised Startup",
                categories_of_interest=["Tender", "Grant"],
                existing_registrations=["DPIIT Startup Recognition", "GSTIN / GST Registration", "PAN Card", "ISO Certification"],
                annual_turnover_inr=95.0,
                description="Agricultural surveillance and crop spraying drones.",
            )
            st.session_state.db.save_profile(p)
            st.session_state.current_profile = p
            st.success("Loaded AeroKisan profile!")
            st.rerun()

    with preset_cols[2]:
        if st.button("⚙️ Precision Engineering (Gujarat)"):
            p = BusinessProfile(
                name="Vidyut Precision Valves & Pumps",
                industry="Manufacturing",
                state="Gujarat",
                business_size="Small (Investment < ₹10 Cr, Turnover < ₹50 Cr)",
                categories_of_interest=["Tender", "Government Scheme"],
                existing_registrations=["Udyam / MSME Registration", "GSTIN / GST Registration", "PAN Card", "Class 3 Digital Signature (DSC)"],
                annual_turnover_inr=320.0,
                description="Industrial valves manufacturer supplying water and gas projects.",
            )
            st.session_state.db.save_profile(p)
            st.session_state.current_profile = p
            st.success("Loaded Vidyut Engineering profile!")
            st.rerun()

    st.markdown("---")

    # Profile Form
    with st.form("profile_form"):
        curr = st.session_state.current_profile
        name = st.text_input("Business Name", value=curr.name)
        col_a, col_b = st.columns(2)
        with col_a:
            industry = st.text_input("Primary Industry / Sector", value=curr.industry, help="e.g. Solar, Software, Defense, Drone, Textile")
            state = st.text_input("Registered State / UT", value=curr.state, help="e.g. Maharashtra, Karnataka, Gujarat, Delhi")
            turnover = st.number_input("Annual Turnover (₹ in Lakhs)", min_value=0.0, value=float(curr.annual_turnover_inr or 25.0))
        with col_b:
            size_options = [
                "Micro (Investment < ₹1 Cr, Turnover < ₹5 Cr)",
                "Small (Investment < ₹10 Cr, Turnover < ₹50 Cr)",
                "Medium (Investment < ₹50 Cr, Turnover < ₹250 Cr)",
                "DPIIT Recognised Startup",
                "Large Enterprise",
            ]
            current_size_idx = 0
            for i, opt in enumerate(size_options):
                if curr.business_size in opt:
                    current_size_idx = i
                    break
            business_size = st.selectbox("Business Size Tier", size_options, index=current_size_idx)

            categories = st.multiselect(
                "Notice Categories of Interest",
                ["Tender", "Grant", "Subsidy", "Government Scheme", "Regulatory Notice", "Expression of Interest (EOI)"],
                default=curr.categories_of_interest or ["Tender", "Subsidy"],
            )

        registrations = st.multiselect(
            "Existing Active Registrations / Certifications",
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

        description = st.text_area("Products / Capabilities Overview", value=curr.description or "")

        submitted = st.form_submit_button("💾 Save Profile", type="primary")
        if submitted:
            updated_profile = BusinessProfile(
                name=name,
                industry=industry,
                state=state,
                business_size=business_size,
                categories_of_interest=categories,
                existing_registrations=registrations,
                annual_turnover_inr=turnover,
                description=description,
            )
            st.session_state.db.save_profile(updated_profile)
            st.session_state.current_profile = updated_profile
            st.success(f"Business profile '{name}' successfully updated and saved!")
            st.rerun()


# ==============================================================================
# PAGE 3: LIVE SCAN & SEARCH
# ==============================================================================
elif menu == "🔍 Live Scan & Search":
    st.title("🔍 Live Government Portal Discovery (Powered by TinyFish)")
    st.markdown(
        "Search live web portals in real-time using the **TinyFish Search API** (`api.search.tinyfish.ai`). "
        "Filter for official Indian procurement, tender, and MSME scheme sources."
    )

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

    with scan_col2:
        if not client.is_configured():
            demo_search_clicked = st.button("🧪 Preview Sample Live Indian Tenders (Demo Mode)")
            if demo_search_clicked:
                from tests.conftest import SAMPLE_SEARCH_RESPONSE_JSON
                from models import SearchResultItem
                results = [
                    SearchResultItem(
                        position=r["position"],
                        site_name=r["site_name"],
                        title=r["title"],
                        snippet=r["snippet"],
                        url=r["url"],
                        date=r.get("date"),
                    )
                    for r in SAMPLE_SEARCH_RESPONSE_JSON["results"]
                ]
                st.session_state.search_results = results
                st.session_state.last_search_query = query + " (Demo Inspection Data)"
                st.info("Loaded pre-recorded sample government tenders (MNRE & CPPP) for inspection!")
                st.rerun()

    if scan_button and query:
        with st.spinner("Calling TinyFish Search API (api.search.tinyfish.ai)..."):
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

                # Persist to database
                st.session_state.db.save_scan(
                    query=query,
                    profile_name=cp.name,
                    results=search_response.results,
                )

                st.success(f"Found {search_response.total_results} live opportunities!")
            except TinyFishAuthError as e:
                st.error(f"Authentication Failed: {e}")
            except TinyFishCreditsError as e:
                st.error(f"Credits Exhausted: {e}")
            except TinyFishRateLimitError as e:
                st.warning(f"Rate Limited: {e}. Please wait a moment before querying again.")
            except Exception as e:
                st.error(f"Search failed: {e}")

    # Display Search Results
    if st.session_state.search_results:
        st.subheader(f"Results for '{st.session_state.get('last_search_query', query)}'")
        st.caption("Click '⚡ Fetch & Analyze with NiyamAI' on any notice to pull content and run the agent audit.")

        for res in st.session_state.search_results:
            with st.container():
                st.markdown(f"""
                <div class="niyam-card">
                    <span class="niyam-badge-teal">{res.site_name or 'Web Source'}</span>
                    <h3 style="margin-top: 8px; margin-bottom: 6px;">{res.title}</h3>
                    <p style="color: #475569; font-size: 0.92rem;">{res.snippet}</p>
                    <p style="font-size: 0.8rem; color: #94A3B8;">URL: <a href="{res.url}" target="_blank">{res.url}</a></p>
                </div>
                """, unsafe_allow_html=True)

                col_btn, _ = st.columns([2, 5])
                with col_btn:
                    if st.button(f"⚡ Fetch & Analyze", key=f"fetch_btn_{res.url}"):
                        st.session_state.active_notice_url = res.url
                        st.session_state.active_notice_title_hint = res.title
                        st.session_state.fetched_notice = None
                        st.session_state.notice_extraction = None
                        st.session_state.notice_verification = None
                        st.session_state.notice_matching = None
                        st.info("Notice selected! Please switch to '📑 Notice Deep Dive & Audit' on the sidebar.")
    elif client.is_configured():
        st.info("Enter a query and click 'Run Live Scan' to discover government tenders, grants, and notices.")


# ==============================================================================
# PAGE 4: NOTICE DEEP DIVE (FETCH, EXTRACT, VERIFY, MATCH)
# ==============================================================================
elif menu == "📑 Notice Deep Dive & Audit":
    st.title("📑 Notice Deep Dive & Autonomous Audit")
    st.markdown(
        "Fetches official notice content with **TinyFish Fetch API**, extracts structured compliance fields, "
        "independently verifies claims against raw text evidence, and computes business profile compatibility."
    )

    client = get_tinyfish_client()
    default_url = st.session_state.active_notice_url or "https://gem.gov.in/tenders/solar-pv-98712"
    title_hint = getattr(st.session_state, "active_notice_title_hint", None)

    input_url = st.text_input("Notice URL to Fetch & Inspect", value=default_url)

    fetch_col, sample_col = st.columns([1, 1])
    with fetch_col:
        fetch_clicked = st.button("📥 1. Fetch Live Notice with TinyFish", type="primary", disabled=not client.is_configured())

    with sample_col:
        if not client.is_configured():
            if st.button("🧪 Inspect Sample Notice (MNRE Solar Rooftop)"):
                from tests.conftest import SAMPLE_FETCH_SUCCESS_JSON
                from models import FetchResponseItem
                raw_sample = SAMPLE_FETCH_SUCCESS_JSON["results"][0]
                st.session_state.fetched_notice = FetchResponseItem(
                    url=raw_sample["url"],
                    final_url=raw_sample["final_url"],
                    title=raw_sample["title"],
                    description=raw_sample["description"],
                    language=raw_sample["language"],
                    text=raw_sample["text"],
                    format=raw_sample["format"],
                )
                st.session_state.active_notice_url = raw_sample["url"]
                st.session_state.notice_extraction = None
                st.session_state.notice_verification = None
                st.session_state.notice_matching = None
                st.info("Loaded sample MNRE Rooftop Solar tender notice for agent audit!")
                st.rerun()

    if fetch_clicked and input_url:
        with st.spinner("Fetching page with TinyFish Fetch API (api.fetch.tinyfish.ai)..."):
            try:
                fetch_res = client.fetch(
                    urls=[input_url],
                    purpose="Extract procurement requirements, deadlines, and eligibility criteria for MSME compliance audit",
                    format="markdown",
                )
                if fetch_res.results:
                    st.session_state.fetched_notice = fetch_res.results[0]
                    st.session_state.active_notice_url = input_url
                    st.success(f"Successfully fetched document ({len(st.session_state.fetched_notice.text or '')} characters)!")
                elif fetch_res.errors:
                    err = fetch_res.errors[0]
                    st.error(f"TinyFish Fetch Error: {err.error} (Status: {err.status})")
            except Exception as e:
                st.error(f"Fetch request failed: {e}")

    # If document fetched, offer Analysis Pipeline
    if st.session_state.fetched_notice:
        fn = st.session_state.fetched_notice

        # Pipeline tabs
        tab1, tab2, tab3, tab4 = st.tabs([
            "📄 Retrieved Source Content",
            "🤖 Structured Extraction",
            "🛡️ Evidence Verification Audit",
            "🎯 Business Matching & Checklist",
        ])

        # TAB 1: RETRIEVED SOURCE
        with tab1:
            st.subheader("Source Document Metadata")
            st.write(f"**Target URL:** {fn.url}")
            st.write(f"**Final Redirect URL:** {fn.final_url or fn.url}")
            st.write(f"**Detected Title:** {fn.title or 'N/A'}")
            st.write(f"**Latency:** {fn.latency_ms or 'N/A'} ms")

            st.markdown("---")
            st.subheader("Raw Markdown Text (Retrieved Content)")
            with st.expander("View Full Fetched Markdown", expanded=True):
                st.markdown(fn.text[:8000] if fn.text else "*Empty content*")
                if fn.text and len(fn.text) > 8000:
                    st.caption("*(Showing first 8,000 characters for performance)*")

        # Automatically execute Extraction, Verification, Matching if not yet done
        if not st.session_state.notice_extraction:
            with st.spinner("Running NiyamAI Multi-Agent Pipeline (Extracting, Verifying, Matching)..."):
                ext_agent = get_extraction_agent()
                ver_agent = get_verification_agent()
                mat_agent = get_matching_agent()

                # 1. Extraction
                extraction = ext_agent.extract(
                    raw_text=fn.text or "",
                    source_url=fn.url,
                    title_hint=title_hint or fn.title,
                )
                st.session_state.notice_extraction = extraction

                # 2. Verification
                verification = ver_agent.verify(
                    extraction=extraction,
                    raw_text=fn.text or "",
                )
                st.session_state.notice_verification = verification

                # 3. Matching
                matching = mat_agent.match(
                    profile=st.session_state.current_profile,
                    extraction=extraction,
                )
                st.session_state.notice_matching = matching

        ext = st.session_state.notice_extraction
        ver = st.session_state.notice_verification
        mat = st.session_state.notice_matching

        # TAB 2: EXTRACTION
        with tab2:
            st.subheader("Structured Notice Fields (Validated with Pydantic)")

            ec1, ec2 = st.columns(2)
            with ec1:
                st.markdown(f"**Notice Title:** {ext.title}")
                st.markdown(f"**Issuing Authority:** {ext.issuing_authority or 'Unknown'}")
                st.markdown(f"**Category:** <span class='niyam-badge-teal'>{ext.category}</span>", unsafe_allow_html=True)
                st.markdown(f"**Geographic Scope:** {ext.geographic_scope or 'All India'}")
            with ec2:
                if ext.submission_deadline:
                    st.markdown(f"**Submission Deadline:** <span style='color: #DC2626; font-size: 1.1rem; font-weight: bold;'>⏰ {ext.submission_deadline}</span>", unsafe_allow_html=True)
                else:
                    st.markdown("**Submission Deadline:** <span class='niyam-badge-review'>Not Specified in Document</span>", unsafe_allow_html=True)

                st.markdown(f"**Financials (EMD / Cost):** {ext.financial_requirements or 'None stated'}")
                st.markdown(f"**Reference / ID:** {ext.scheme_or_tender_name or 'N/A'}")

            st.markdown("---")
            st.markdown("#### Mandatory Registrations")
            if ext.required_registrations:
                for r in ext.required_registrations:
                    st.markdown(f"- 📋 **{r}**")
            else:
                st.write("No specialized registrations identified in initial document.")

            st.markdown("#### Required Application Documents")
            if ext.required_documents:
                for d in ext.required_documents:
                    st.markdown(f"- 📁 {d}")
            else:
                st.write("No document list explicitly extracted.")

            if ext.uncertain_or_missing_fields:
                st.markdown("---")
                st.warning(f"⚠️ **Uncertain or Missing Fields from Source:** {', '.join(ext.uncertain_or_missing_fields)}")

        # TAB 3: VERIFICATION
        with tab3:
            st.subheader("🛡️ Source Evidence & Claim Verification")
            st.markdown(
                "NiyamAI's Verification Agent compares each extracted field against the retrieved raw content. "
                "Claims are strictly categorized to prevent AI hallucinations."
            )

            st.markdown(f"**Overall Audit Status:** `{ver.overall_status}`")
            st.caption(ver.summary)

            for claim in ver.claims:
                if claim.status == VerificationStatus.VERIFIED:
                    badge = "<span class='niyam-badge-verified'>✅ Verified</span>"
                elif claim.status == VerificationStatus.PARTIAL:
                    badge = "<span class='niyam-badge-teal'>ℹ️ Partially Supported</span>"
                elif claim.status == VerificationStatus.NEEDS_REVIEW:
                    badge = "<span class='niyam-badge-review'>⚠️ Needs Review</span>"
                else:
                    badge = "<span class='niyam-badge-missing'>❌ Missing From Source</span>"

                st.markdown(f"""
                <div class="niyam-card">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <h4 style="margin: 0;">Claim: {claim.claim_field}</h4>
                        {badge}
                    </div>
                    <p style="margin: 8px 0 4px 0;"><strong>Extracted Value:</strong> <code>{claim.extracted_value}</code></p>
                    <p style="margin: 0 0 4px 0; color: #475569; font-size: 0.88rem;"><strong>Source Evidence:</strong> <em>"{claim.supporting_evidence}"</em></p>
                    <p style="margin: 0; color: #64748B; font-size: 0.82rem;"><strong>Audit Rationale:</strong> {claim.explanation}</p>
                </div>
                """, unsafe_allow_html=True)

        # TAB 4: MATCHING & CHECKLIST
        with tab4:
            st.subheader(f"🎯 Compatibility with {st.session_state.current_profile.name}")

            mcol1, mcol2 = st.columns([1, 2])
            with mcol1:
                st.markdown(f"""
                <div class="metric-box">
                    <div class="metric-value">{mat.relevance_score}/100</div>
                    <div class="metric-label">Relevance Score</div>
                </div>
                """, unsafe_allow_html=True)

                st.markdown("#### Score Rubric Breakdown")
                for k, v in mat.score_breakdown.items():
                    st.write(f"- **{k}:** {v} pts")

            with mcol2:
                st.markdown(f"**Analysis Summary:** {mat.relevance_explanation}")

                if mat.satisfied_criteria:
                    st.success("**Satisfied Requirements:**\n\n" + "\n".join(f"- ✅ {s}" for s in mat.satisfied_criteria))

                if mat.unsatisfied_criteria:
                    st.error("**Gaps & Ineligibility Risks:**\n\n" + "\n".join(f"- ❌ {u}" for u in mat.unsatisfied_criteria))

                if mat.information_needed:
                    st.warning("**Information Still Needed from You:**\n\n" + "\n".join(f"- ❓ {q}" for q in mat.information_needed))

            st.markdown("---")
            st.subheader("📋 Interactive Application Document Checklist")
            st.caption("Check off items as you assemble your bidding packet:")

            for idx, item in enumerate(mat.checklist):
                status_icon = "✅" if item.is_present_in_profile else "⚠️"
                st.checkbox(
                    f"{status_icon} **{item.document_name}** — *{item.status_note}*",
                    value=item.is_present_in_profile,
                    key=f"chk_{idx}_{item.document_name}",
                )

            st.markdown("---")
            st.subheader("🚀 Actionable Next Steps")
            for step in mat.recommended_next_steps:
                st.markdown(f"- {step}")

            st.markdown("---")
            # Save button
            if st.button("💾 Save Notice to Local Database", type="primary"):
                saved_obj = SavedNotice(
                    url=fn.url,
                    title=ext.title,
                    site_name=fn.url.split("/")[2] if "/" in fn.url else "Government Portal",
                    category=ext.category,
                    deadline=ext.submission_deadline,
                    relevance_score=mat.relevance_score,
                    raw_content=fn.text or "",
                    extraction=ext,
                    verification=ver,
                    matching=mat,
                )
                nid, is_dup = st.session_state.db.save_notice(saved_obj)
                if is_dup:
                    st.info(f"Notice updated in database (ID: {nid}, URL already existed).")
                else:
                    st.success(f"Notice successfully saved to database (ID: {nid})!")


# ==============================================================================
# PAGE 5: SAVED NOTICES & DEADLINES
# ==============================================================================
elif menu == "💾 Saved Notices & Deadlines":
    st.title("💾 Saved Government Opportunities & Compliance Deadlines")
    st.markdown("Persisted records from SQLite database with deduplication and complete agent audit trails.")

    saved_notices = st.session_state.db.get_saved_notices()

    if not saved_notices:
        st.info("No saved notices yet. Discover notices using '🔍 Live Scan & Search' and save them.")
    else:
        st.write(f"Total Saved Notices: **{len(saved_notices)}**")

        for sn in saved_notices:
            with st.container():
                st.markdown(f"""
                <div class="niyam-card">
                    <div style="display: flex; justify-content: space-between;">
                        <span class="niyam-badge-teal">{sn.site_name}</span>
                        <span class="niyam-badge-verified">Score: {sn.relevance_score}/100</span>
                    </div>
                    <h3 style="margin-top: 8px;">{sn.title}</h3>
                    <p><strong>Category:</strong> {sn.category} | <strong>Saved At:</strong> {sn.saved_at}</p>
                    <p style="color: #DC2626; font-weight: bold;">⏰ Deadline: {sn.deadline or 'Check Portal'}</p>
                    <p><a href="{sn.url}" target="_blank">🔗 Official Source: {sn.url}</a></p>
                </div>
                """, unsafe_allow_html=True)

                col_a, col_b = st.columns([1, 5])
                with col_a:
                    if st.button("🗑️ Delete", key=f"del_{sn.id}"):
                        st.session_state.db.delete_saved_notice(sn.id)
                        st.warning("Notice deleted.")
                        st.rerun()
                with col_b:
                    if st.button("🔍 Open Full Audit", key=f"open_{sn.id}"):
                        st.session_state.active_notice_url = sn.url
                        st.session_state.notice_extraction = sn.extraction
                        st.session_state.notice_verification = sn.verification
                        st.session_state.notice_matching = sn.matching
                        st.info("Notice loaded! Switch to '📑 Notice Deep Dive & Audit' to view.")


# ==============================================================================
# PAGE 6: SCAN HISTORY
# ==============================================================================
elif menu == "📜 Scan History":
    st.title("📜 Live Scan Audit History")
    st.markdown("Audit log of all queries executed against TinyFish Search API.")

    history = st.session_state.db.get_scan_history(limit=50)
    if not history:
        st.info("No scan history recorded yet.")
    else:
        for item in history:
            with st.expander(f"🔍 '{item['query']}' — {item['result_count']} results ({item['scanned_at']})"):
                st.write(f"**Profile:** {item['profile_name']}")
                st.write(f"**Timestamp:** {item['scanned_at']}")
                for r in item["results"]:
                    st.markdown(f"- **{r.get('title')}** ({r.get('site_name')}) — [Link]({r.get('url')})")


# ==============================================================================
# PAGE 7: API SETTINGS & DIAGNOSTICS
# ==============================================================================
elif menu == "⚙️ API Settings & Diagnostics":
    st.title("⚙️ API Configuration & System Diagnostics")
    st.markdown("Configure server-side environment variables and verify connectivity.")

    with st.form("api_keys_form"):
        st.subheader("API Credentials")
        tf_key = st.text_input(
            "TinyFish API Key (Required for Search & Fetch)",
            value=st.session_state.user_tf_api_key,
            type="password",
            help="Get your API key at: https://agent.tinyfish.ai/api-keys",
        )
        gemini_key = st.text_input(
            "Google Gemini API Key (Optional for LLM extraction)",
            value=st.session_state.user_gemini_api_key,
            type="password",
            help="Get your key at: https://aistudio.google.com/. If empty, NiyamAI uses high-precision deterministic regex/NLP fallback.",
        )

        save_keys = st.form_submit_button("Save Credentials to Session", type="primary")
        if save_keys:
            st.session_state.user_tf_api_key = tf_key.strip()
            st.session_state.user_gemini_api_key = gemini_key.strip()
            st.success("API keys updated in session state!")
            st.rerun()

    st.markdown("---")
    st.subheader("Diagnostics & Live Health Check")

    c1, c2 = st.columns(2)
    with c1:
        st.write(f"**Database Path:** `{NIYAMAI_DB_PATH}`")
        st.write(f"**TinyFish Client Configured:** `{get_tinyfish_client().is_configured()}`")
        st.write(f"**LLM Extraction Enabled:** `{bool(st.session_state.user_gemini_api_key)}`")

    with c2:
        if st.button("🧪 Test TinyFish Connection"):
            client = get_tinyfish_client()
            if not client.is_configured():
                st.error("Cannot test: TINYFISH_API_KEY is not set.")
            else:
                with st.spinner("Pinging TinyFish Search API with test query..."):
                    try:
                        res = client.search(query="test", page=0)
                        st.success(f"TinyFish Search API responded successfully! ({len(res.results)} results)")
                    except Exception as e:
                        st.error(f"TinyFish Connection Test Failed: {e}")
