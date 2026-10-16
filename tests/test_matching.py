"""
Unit tests for MatchingAgent verifying relevance scoring, gap detection,
handling of incomplete business profiles, and document checklist generation.
"""

from agents.matching_agent import MatchingAgent
from models import NoticeExtraction, BusinessProfile


def test_matching_high_relevance(sample_solar_profile):
    """Profile matching solar industry in Maharashtra with MSME registration scores high."""
    extraction = NoticeExtraction(
        title="Supply and Installation of 50kW Rooftop Solar PV Systems",
        issuing_authority="Ministry of New and Renewable Energy",
        category="Tender",
        submission_deadline="15/11/2026",
        required_registrations=["Udyam / MSME Registration", "GSTIN / GST Registration"],
        geographic_scope="Maharashtra",
        official_source_url="https://gem.gov.in/solar",
    )

    matcher = MatchingAgent()
    report = matcher.match(sample_solar_profile, extraction)

    assert report.relevance_score >= 80
    assert len(report.satisfied_criteria) >= 3
    assert any("Industry alignment" in s for s in report.satisfied_criteria)
    assert any("State eligibility" in s for s in report.satisfied_criteria)
    assert len(report.checklist) > 0
    assert report.is_legally_binding_advice is False


def test_matching_incomplete_profile(incomplete_profile):
    """Incomplete profiles calculate scores without crashing and generate requests for info."""
    extraction = NoticeExtraction(
        title="Procurement of IT Equipment and Software Licenses",
        category="Tender",
        required_registrations=["Udyam MSME", "ISO 27001"],
        geographic_scope="Pan-India",
        official_source_url="https://gem.gov.in/it-procure",
    )

    matcher = MatchingAgent()
    report = matcher.match(incomplete_profile, extraction)

    assert 0 <= report.relevance_score <= 100
    assert len(report.information_needed) > 0
    assert any("missing" in u.lower() or "industry" in u.lower() for u in report.unsatisfied_criteria)


def test_matching_state_mismatch(sample_solar_profile):
    """Notice restricted to another state marks geographic mismatch in unsatisfied criteria."""
    extraction = NoticeExtraction(
        title="Solar Power Plant Installation",
        category="Tender",
        geographic_scope="Kerala",  # Profile is in Maharashtra
        official_source_url="https://gem.gov.in/solar-kerala",
    )

    matcher = MatchingAgent()
    report = matcher.match(sample_solar_profile, extraction)

    assert any("Location restriction" in u for u in report.unsatisfied_criteria)
    assert report.score_breakdown["Geographic Scope (Max 20)"] < 20
