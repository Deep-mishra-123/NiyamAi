# ⚖️ NiyamAI — Autonomous AI Government Opportunity & Compliance Agent

> **Tagline:** Never Miss a Government Opportunity or Compliance Deadline.  
> **Built for:** AZINHACK '26

---

## 📌 1. Problem Statement
Indian startups, manufacturers, and MSMEs (Micro, Small, and Medium Enterprises) face significant hurdles tracking and bidding on public tenders, procurement contracts, and government subsidies. Information is fragmented across disparate central and state portals:
- **Government e-Marketplace (GeM)**
- **Central Public Procurement Portal (CPPP / eprocure.gov.in)**
- **Ministry of MSME (msme.gov.in)**
- **Startup India (startupindia.gov.in)**
- **State-specific e-procurement boards (MahaTenders, Karnataka KPPP, Gujarat, etc.)**

Valuable opportunities—especially those with **MSME purchase preferences (25% public procurement policy)** and **EMD (Earnest Money Deposit) exemptions**—are frequently missed due to:
1. Scattered announcements and opaque qualification criteria.
2. Short submission deadlines (often 7–14 days).
3. Complex, multi-page bid documents requiring extensive manual compliance checks.
4. Risk of bid disqualification due to missing statutory registrations or overlooked certificates.

---

## 💡 2. Proposed Solution
**NiyamAI** is an autonomous, agentic opportunity discovery and compliance assistant that:
1. **Discovers Live Tenders & Schemes:** Uses the **TinyFish Search API** (`api.search.tinyfish.ai`) to scan official Indian portals in real-time.
2. **Extracts Unaltered Source Content:** Uses the **TinyFish Fetch API** (`api.fetch.tinyfish.ai`) to retrieve and parse tender documents and circulars into clean markdown.
3. **Pydantic Structured Extraction:** Parses issuing authorities, bid submission cutoffs, financial guarantees (EMD), and required documents into strongly-typed schemas.
4. **Source Evidence Verification:** Compares extracted claims against retrieved document text to guarantee **zero hallucinations** and flag missing information as *"Needs Review"*.
5. **Transparent Business Matching (0–100):** Evaluates notices against the company's profile across 4 weighted dimensions (Industry fit, MSME policy, Geographic scope, Registration readiness).
6. **Actionable Application Checklist:** Generates an interactive document checklist (Udyam, GSTIN, ITR, Solvency) with deadline urgency alerts.
7. **Local Audit Persistence:** Stores profiles, scan history, and saved notices in SQLite with automatic deduplication.

---

## 👥 3. Target Users
- **Indian MSMEs:** Micro and small businesses seeking to leverage MSME reservation policies and tender exemptions.
- **DPIIT Recognized Startups:** Young enterprises eligible for startup innovation tenders and relaxation of prior turnover/experience requirements.
- **Contractors & EPC Developers:** Solar, infrastructure, defense, drone, and IT equipment vendors.
- **Compliance & Bid Managers:** Professionals tasked with assembling error-free bidding packages before cut-off deadlines.

---

## 🏗️ 4. System Architecture

```
+-----------------------------------------------------------------------------------+
|                            NiyamAI Web Dashboard (Streamlit)                      |
|                   (Navy #0A192F & Teal #00B4D8 Professional Theme)                |
+-----------------------------------------------------------------------------------+
                                         |
     +-----------------------------------+-----------------------------------+
     |                                   |                                   |
     v                                   v                                   v
+-----------------------+   +-------------------------+   +-------------------------+
|   Business Profile    |   |     Live Scan Hub       |   | Notice Deep Dive & Audit|
| - Industry & State    |   | - Auto Query Generator  |   | - Source Viewer         |
| - Scale & Turnover    |   | - Gov Domain Filtering  |   | - Structured Extraction |
| - Registrations & DSC |   | - Geo-targeted ('IN')   |   | - Verification Audit    |
+-----------------------+   +-------------------------+   | - Match & Checklist     |
                                         |                +-------------------------+
                                         |                             |
                                         v                             v
                        +---------------------------------+            |
                        |      TinyFish API Client        |            |
                        | - GET https://api.search...     |            |
                        | - POST https://api.fetch...     |            |
                        | - SSRF Defense & Rate Backoff   |            |
                        +---------------------------------+            |
                                         |                             |
                                         v                             v
                        +---------------------------------+   +---------------------+
                        |     Autonomous Agent Pipeline   |   |   SQLite Database   |
                        | 1. ExtractionAgent (LLM/Regex)  |-->| - profiles          |
                        | 2. VerificationAgent (Auditor)  |   | - scan_history      |
                        | 3. MatchingAgent (Scorer 0-100) |   | - saved_notices     |
                        +---------------------------------+   +---------------------+
```

---

## 🐟 5. How TinyFish is Used

TinyFish provides the core real-time discovery and content extraction engine for NiyamAI:

### A. TinyFish Search API
- **Endpoint:** `GET https://api.search.tinyfish.ai`
- **Header:** `X-API-Key: <TINYFISH_API_KEY>`
- **Parameters:**
  - `query`: Dynamic profile-generated query (e.g. `Solar rooftop tender Maharashtra Udyam MSME`)
  - `purpose`: Task context (`Discovering public tenders and regulatory notices for MSME compliance`)
  - `location`: `IN` (Country code targeting Indian results)
  - `language`: `en`
  - `include_domains`: Restricts results strictly to trusted portals:
    - `gem.gov.in` (Government e-Marketplace)
    - `eprocure.gov.in` (CPPP)
    - `msme.gov.in` (Ministry of MSME)
    - `startupindia.gov.in` (DPIIT)
    - `sidbi.in`, `mahatenders.gov.in`, etc.
- **Output:** Structured items including ranking position, snippet, portal name, and direct URL.

### B. TinyFish Fetch API
- **Endpoint:** `POST https://api.fetch.tinyfish.ai`
- **Header:** `X-API-Key: <TINYFISH_API_KEY>`, `Content-Type: application/json`
- **Body:** `{"urls": ["<portal_url>"], "format": "markdown", "purpose": "Extract tender criteria"}`
- **Security & SSRF Defense:** NiyamAI validates all URLs with `is_safe_url()` prior to dispatch, blocking private IP ranges (RFC 1918), localhost, and cloud metadata endpoints (`169.254.169.254`).
- **Error Handling:** Robust handling for per-URL errors (`page_not_found`, `bot_blocked`, `timeout`) and HTTP status codes (`401`, `402`, `429`, `500`).

---

## 🚀 6. Setup & Installation

### Prerequisites
- Python 3.11+ (Python 3.14 compatible)
- Windows, macOS, or Linux
- TinyFish API Key ([Get an API Key](https://agent.tinyfish.ai/api-keys))
- *(Optional)* Google Gemini API Key ([AI Studio](https://aistudio.google.com/))

### Installation Steps

1. **Clone or Navigate to the Workspace:**
   ```bash
   cd C:\Users\Deep\.gemini\antigravity\scratch\niyam-ai
   ```

2. **Create and Activate Virtual Environment:**
   ```bash
   # Windows PowerShell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1

   # macOS / Linux
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment Variables:**
   Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
   Add your keys in `.env`:
   ```ini
   TINYFISH_API_KEY=your_actual_tinyfish_api_key_here
   GEMINI_API_KEY=your_optional_gemini_key_here
   NIYAMAI_DB_PATH=niyamai.db
   ```
   *(Note: You can also enter or update your API keys directly inside the application's "API Settings" UI tab).*

---

## 💻 7. Running the Application

Launch the Streamlit web dashboard:
```bash
streamlit run app.py
```
Open your browser at: **`http://localhost:8501`**

---

## 🧪 8. Running Automated Tests

Run the complete test suite using `pytest`:
```bash
python -m pytest tests -v
```

### Test Suite Coverage:
- `test_tinyfish_client.py`:
  - Successful Search response parsing (`SearchResponse` model)
  - Search API 401 Unauthorized handling (`TinyFishAuthError`)
  - Search API 429 Rate Limit backoff (`TinyFishRateLimitError`)
  - Search API timeout resilience
  - Successful Fetch response parsing (`FetchResponse` model)
  - Per-URL Fetch failure handling (`errors[]`)
  - SSRF protection (rejection of localhost & cloud metadata endpoints)
- `test_extraction.py`:
  - Complete tender parsing (title, category, deadline, EMD, documents)
  - Missing deadline handling (no hallucinations, sets `None`)
  - Empty source document handling
- `test_verification.py`:
  - Verified claims matched with verbatim source context
  - Unsupported/hallucinated claims flagged as `Missing From Source`
- `test_matching.py`:
  - High relevance scoring for compatible sectors and MSME preferences
  - Incomplete business profile handling without crashes
  - State location mismatch detection
- `test_database.py`:
  - Business profile CRUD
  - Notice deduplication by URL
  - Scan audit history recording

---

## 🎬 9. Live Demo Workflow

1. **Open the Dashboard:** View the navy-and-teal hub summarizing saved opportunities, tracked deadlines, and active company details.
2. **Set Business Profile:** Select a preset (e.g. *SuryaShakti Solar EPC MSME* or *AeroKisan Agri-Drones Startup*) or enter your own business name, state, and statutory registrations.
3. **Execute Live Scan:**
   - Go to **Live Scan & Search**.
   - Notice the auto-generated query based on your profile.
   - Click **Run Live Scan with TinyFish**.
   - Review live search results returned with portal tags (`gem.gov.in`, `eprocure.gov.in`).
4. **Fetch & Analyze a Notice:**
   - Click **⚡ Fetch & Analyze** on any search result.
   - Watch the agent fetch the live page via TinyFish Fetch API.
   - Inspect the **4 Agent Audit Tabs**:
     - *Retrieved Source:* Read clean markdown content.
     - *Structured Extraction:* View Pydantic-validated fields (submission deadline, EMD, mandatory documents).
     - *Evidence Verification:* Verify claims against exact quotations from the source text.
     - *Business Matching & Checklist:* Check your 0–100 score, satisfied criteria, gaps, and check off items in the bidding checklist.
5. **Save Opportunity:**
   - Click **Save Notice to Local Database**.
   - Open **Saved Notices & Deadlines** to view persisted records and track upcoming cut-offs.

---

## 🔒 10. Security & Compliance Safeguards

- **SSRF Defense:** Enforces strict URL sanitization preventing requests to `localhost`, `127.0.0.1`, RFC 1918 private IPs, and cloud metadata endpoints (`169.254.169.254`).
- **No Hardcoded Secrets:** Credentials are read strictly from `.env` or session memory. `.env` and SQLite databases are excluded in `.gitignore`.
- **Zero Hallucination Guarantee:** The Extraction Agent explicitly records missing information as `None` or "Unknown" and lists them in `uncertain_or_missing_fields`.
- **Legal Advice Disclaimer:** All agent outputs explicitly remind users that NiyamAI is an exploratory screening assistant, not a substitute for official legal or bid counsel.

---

## 📈 11. Limitations & Future Roadmap

### Current Limitations:
- Relies on HTML/Markdown extraction provided by TinyFish; non-extractable scanned raster image PDFs require upstream OCR.
- Scheduled scans currently run on-demand or during active dashboard sessions.

### Future Roadmap:
- **Autonomous Notification Dispatch:** Integrate WhatsApp and Email alerts for deadlines 72h before tender closing.
- **Multilingual Support:** Support Indian regional languages (Hindi, Marathi, Tamil, Telugu, Gujarati) for vernacular gazette notices.
- **Automated GeM Bid Prep:** Pre-fill GeM participation templates with verified Udyam and GST certificates.

---

## ⚖️ License
Apache-2.0 License. Developed for AZINHACK '26.
