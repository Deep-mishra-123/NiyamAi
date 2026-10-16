"""
NiyamAI - Pytest Fixtures and Mock Data
Provides realistic Indian public tender and scheme fixtures for unit testing.
"""

import pytest
from models import BusinessProfile

SAMPLE_SEARCH_RESPONSE_JSON = {
    "query": "solar micro enterprise tender gem.gov.in",
    "total_results": 2,
    "page": 0,
    "results": [
        {
            "position": 1,
            "site_name": "gem.gov.in",
            "title": "Supply and Installation of 50kW Rooftop Solar PV Systems",
            "snippet": "Tender No: GEM/2026/B/98712. Ministry of New and Renewable Energy. Last date for submission: 15/11/2026. MSME exemptions apply.",
            "url": "https://gem.gov.in/tenders/solar-pv-98712",
            "date": "2026-10-01",
        },
        {
            "position": 2,
            "site_name": "eprocure.gov.in",
            "title": "Procurement of Agricultural Drones for Crop Surveillance",
            "snippet": "Notice Inviting Tender for Drone manufacturers registered with DPIIT. Submission deadline: 30/11/2026.",
            "url": "https://eprocure.gov.in/cppp/notice-drone-44",
            "date": "2026-10-05",
        },
    ],
}

SAMPLE_FETCH_SUCCESS_JSON = {
    "results": [
        {
            "url": "https://gem.gov.in/tenders/solar-pv-98712",
            "final_url": "https://gem.gov.in/tenders/solar-pv-98712",
            "title": "Supply and Installation of 50kW Rooftop Solar PV Systems",
            "description": "GeM Bid Notice for MNRE rooftop solar project.",
            "language": "en",
            "text": """# Government of India - Government e-Marketplace (GeM)
## Bid Document: Supply and Installation of 50kW Rooftop Solar PV Systems
**Tender ID**: GEM/2026/B/98712
**Issuing Authority**: Ministry of New and Renewable Energy, Government of India.
**Geographic Scope**: Maharashtra.
**Bid Submission Date**: 15/11/2026 15:00:00

### 1. Eligibility Criteria
- Eligible bidders must have experience in Solar Rooftop installation.
- Must hold valid Udyam / MSME Registration and GSTIN.
- DPIIT recognized startups and MSEs are exempted from Earnest Money Deposit (EMD).
- EMD Amount: ₹ 50,000 (Exempted for registered Micro and Small Enterprises).

### 2. Mandatory Documents to be Submitted:
1. Valid GST Registration Certificate
2. Udyam MSME Certificate
3. PAN Card copy
4. CA Certified Turnover Certificate (Average turnover of Rs. 25 Lakhs)
5. Audited Balance Sheets (Last 3 Years)
6. Non-blacklisting affidavit
""",
            "format": "markdown",
        }
    ],
    "errors": [],
}

SAMPLE_FETCH_FAILURE_JSON = {
    "results": [],
    "errors": [
        {
            "url": "https://gem.gov.in/broken-notice",
            "error": "page_not_found",
            "status": 404,
        }
    ],
}


@pytest.fixture
def sample_solar_profile():
    return BusinessProfile(
        name="SuryaShakti Renewable Solutions Pvt Ltd",
        industry="Solar",
        state="Maharashtra",
        business_size="Micro (Investment < ₹1 Cr, Turnover < ₹5 Cr)",
        categories_of_interest=["Tender", "Subsidy"],
        existing_registrations=["Udyam / MSME Registration", "GSTIN / GST Registration", "PAN Card"],
        annual_turnover_inr=45.0,
        description="Rooftop solar developer and EPC contractor in Pune.",
    )


@pytest.fixture
def incomplete_profile():
    return BusinessProfile(
        name="Namaste Enterprises",
        industry="General Services",
        state="Karnataka",
        business_size="Micro",
        categories_of_interest=[],
        existing_registrations=[],
    )
