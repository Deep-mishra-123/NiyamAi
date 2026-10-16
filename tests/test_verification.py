"""
Unit tests for VerificationAgent validating claim audit against retrieved text,
detection of unsupported claims, and status classification.
"""

from agents.verification_agent import VerificationAgent
from models import NoticeExtraction, VerificationStatus
from tests.conftest import SAMPLE_FETCH_SUCCESS_JSON


def test_verify_supported_claims():
    """Claims matching retrieved text receive VERIFIED status with quotation evidence."""
    raw_text = SAMPLE_FETCH_SUCCESS_JSON["results"][0]["text"]
    extraction = NoticeExtraction(
        title="Supply and Installation of 50kW Rooftop Solar PV Systems",
        issuing_authority="Ministry of New and Renewable Energy",
        category="Tender",
        submission_deadline="15/11/2026",
        financial_requirements="₹ 50,000",
        required_registrations=["Udyam / MSME Registration", "GST Registration Certificate"],
        required_documents=["Audited Balance Sheets"],
        official_source_url="https://gem.gov.in/tenders/solar-pv-98712",
    )

    verifier = VerificationAgent()
    report = verifier.verify(extraction, raw_text)

    assert report.verified_count >= 3
    assert report.missing_count == 0

    # Deadline claim
    deadline_claim = next(c for c in report.claims if c.claim_field == "Submission Deadline")
    assert deadline_claim.status == VerificationStatus.VERIFIED
    assert "15/11/2026" in deadline_claim.supporting_evidence


def test_verify_unsupported_claim():
    """Extracted claims absent from the source document are flagged as MISSING."""
    raw_text = SAMPLE_FETCH_SUCCESS_JSON["results"][0]["text"]
    extraction = NoticeExtraction(
        title="Supply and Installation of 50kW Rooftop Solar PV Systems",
        issuing_authority="Department of Space ISRO",  # Fabricated authority
        category="Tender",
        submission_deadline="31/12/2099",  # Fabricated deadline
        financial_requirements="₹ 999 Crores",  # Fabricated figure
        required_registrations=["Aviation Security Clearance"],  # Fabricated
        official_source_url="https://gem.gov.in/tenders/solar-pv-98712",
    )

    verifier = VerificationAgent()
    report = verifier.verify(extraction, raw_text)

    assert report.missing_count >= 2
    assert "Needs Review" in report.overall_status

    # Unsupported deadline
    deadline_claim = next(c for c in report.claims if c.claim_field == "Submission Deadline")
    assert deadline_claim.status == VerificationStatus.MISSING
    assert "not present in retrieved document" in deadline_claim.explanation


def test_verify_empty_raw_text():
    """Empty source text produces a clear audit failure report."""
    extraction = NoticeExtraction(
        title="Tender Notice",
        official_source_url="https://example.com/empty",
    )
    verifier = VerificationAgent()
    report = verifier.verify(extraction, "")

    assert report.missing_count == 1
    assert "Empty" in report.claims[0].extracted_value
