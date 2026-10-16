"""
Unit tests for ExtractionAgent validating structured parsing,
deadline detection, registration identification, and zero-hallucination behavior.
"""

from agents.extraction_agent import ExtractionAgent
from tests.conftest import SAMPLE_FETCH_SUCCESS_JSON


def test_extract_complete_tender():
    """Extracts all standard tender fields from real-world markdown text."""
    raw_text = SAMPLE_FETCH_SUCCESS_JSON["results"][0]["text"]
    url = SAMPLE_FETCH_SUCCESS_JSON["results"][0]["url"]

    agent = ExtractionAgent(gemini_api_key="")  # Uses deterministic extractor
    extraction = agent.extract(raw_text=raw_text, source_url=url)

    assert "Solar" in extraction.title or "Supply and Installation" in extraction.title
    assert extraction.category in ["Tender", "Government Scheme", "Expression of Interest (EOI)"]
    assert "15/11/2026" in extraction.submission_deadline
    assert "Ministry of New and Renewable Energy" in extraction.issuing_authority
    assert extraction.geographic_scope == "Maharashtra"

    # Registrations
    assert any("Udyam" in r for r in extraction.required_registrations)
    assert any("GST" in r for r in extraction.required_registrations)

    # Documents
    assert any("Balance Sheets" in d for d in extraction.required_documents)
    assert any("GST" in d for d in extraction.required_documents)

    # Financial requirements
    assert extraction.financial_requirements is not None
    assert "50,000" in extraction.financial_requirements

    # Evidence presence
    assert len(extraction.supporting_evidence) > 0


def test_extract_missing_deadline():
    """Documents without a deadline do not hallucinate a date."""
    text_without_deadline = """# Regulatory Circular No 44/2026
Ministry of Finance, Government of India.
All MSMEs must comply with updated GST e-invoicing turnover thresholds of Rs. 5 Crores.
Applicable throughout India.
Required Registrations: GSTIN, PAN Card.
"""
    agent = ExtractionAgent(gemini_api_key="")
    extraction = agent.extract(raw_text=text_without_deadline, source_url="https://finmin.gov.in/circ-44")

    assert extraction.submission_deadline is None
    assert "submission_deadline" in extraction.uncertain_or_missing_fields
    assert extraction.category == "Regulatory Notice"


def test_extract_empty_content():
    """Empty source content returns safely without unhandled exceptions."""
    agent = ExtractionAgent(gemini_api_key="")
    extraction = agent.extract(raw_text="", source_url="https://gem.gov.in/empty")

    assert extraction.title is not None
    assert extraction.submission_deadline is None
    assert "submission_deadline" in extraction.uncertain_or_missing_fields
    assert len(extraction.uncertain_or_missing_fields) > 0
