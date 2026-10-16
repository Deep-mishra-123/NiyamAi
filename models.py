"""
NiyamAI - Data Models
Strict Pydantic schemas for business profiles, TinyFish API responses,
agent extraction, verification audits, and business matching.
"""

from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field


class BusinessSize(str, Enum):
    MICRO = "Micro (Investment < ₹1 Cr, Turnover < ₹5 Cr)"
    SMALL = "Small (Investment < ₹10 Cr, Turnover < ₹50 Cr)"
    MEDIUM = "Medium (Investment < ₹50 Cr, Turnover < ₹250 Cr)"
    LARGE = "Large Enterprise"
    STARTUP = "DPIIT Recognised Startup"


class VerificationStatus(str, Enum):
    VERIFIED = "Verified Against Retrieved Content"
    PARTIAL = "Partially Supported"
    NEEDS_REVIEW = "Needs Review"
    MISSING = "Missing From Source"


class BusinessProfile(BaseModel):
    name: str = Field(..., description="Business or Company Name")
    industry: str = Field(..., description="Primary industry sector, e.g., Solar, IT, Manufacturing")
    state: str = Field(..., description="Indian state or Union Territory")
    business_size: str = Field(default="Micro", description="MSME category or size")
    categories_of_interest: List[str] = Field(default_factory=list, description="Schemes, Tenders, Subsidies, Grants")
    existing_registrations: List[str] = Field(default_factory=list, description="Udyam, GSTIN, DPIIT, ISO, PAN, etc.")
    annual_turnover_inr: Optional[float] = Field(default=None, description="Annual turnover in Lakhs or Crores INR")
    description: Optional[str] = Field(default=None, description="Brief description of products/services")


class SearchResultItem(BaseModel):
    position: int = Field(default=1)
    site_name: str = Field(default="")
    title: str = Field(default="")
    snippet: str = Field(default="")
    url: str = Field(...)
    date: Optional[str] = Field(default=None)


class SearchResponse(BaseModel):
    query: str
    results: List[SearchResultItem] = Field(default_factory=list)
    total_results: int = 0
    page: int = 0


class FetchResponseItem(BaseModel):
    url: str
    final_url: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    language: Optional[str] = None
    author: Optional[str] = None
    published_date: Optional[str] = None
    text: Optional[str] = None
    format: str = "markdown"
    latency_ms: Optional[float] = None


class FetchErrorItem(BaseModel):
    url: str
    error: str
    status: Optional[int] = None


class FetchResponse(BaseModel):
    results: List[FetchResponseItem] = Field(default_factory=list)
    errors: List[FetchErrorItem] = Field(default_factory=list)


class NoticeExtraction(BaseModel):
    title: str = Field(..., description="Notice or tender title")
    issuing_authority: Optional[str] = Field(default=None, description="Ministry, PSU, or department")
    category: str = Field(default="Tender", description="Tender, Grant, Scheme, Subsidy, Regulatory Notice, etc.")
    scheme_or_tender_name: Optional[str] = Field(default=None, description="Official scheme or tender identifier")
    publication_date: Optional[str] = Field(default=None, description="Notice publish date")
    submission_deadline: Optional[str] = Field(default=None, description="Application or bid submission deadline")
    eligibility_criteria: List[str] = Field(default_factory=list, description="List of eligibility conditions")
    required_registrations: List[str] = Field(default_factory=list, description="Mandatory registrations (e.g. Udyam, GSTIN)")
    required_documents: List[str] = Field(default_factory=list, description="Documents needed to apply")
    financial_requirements: Optional[str] = Field(default=None, description="EMD, turnover, or fee requirements")
    geographic_scope: Optional[str] = Field(default=None, description="Applicable state, region, or All-India")
    official_source_url: str = Field(..., description="Source URL where notice was found")
    supporting_evidence: List[str] = Field(default_factory=list, description="Direct excerpts from source text")
    uncertain_or_missing_fields: List[str] = Field(default_factory=list, description="Fields not found in source")
    extracted_at: Optional[str] = None


class VerificationClaim(BaseModel):
    claim_field: str = Field(..., description="Field tested, e.g. Deadline, Issuing Authority")
    extracted_value: str = Field(..., description="Extracted claim value")
    supporting_evidence: str = Field(..., description="Source quotation or lack thereof")
    status: VerificationStatus = Field(..., description="Verification status")
    explanation: str = Field(..., description="Detailed audit rationale")


class VerificationReport(BaseModel):
    claims: List[VerificationClaim] = Field(default_factory=list)
    overall_status: str = Field(default="Needs Review")
    verified_count: int = 0
    partially_supported_count: int = 0
    needs_review_count: int = 0
    missing_count: int = 0
    summary: str = Field(default="")


class ChecklistItem(BaseModel):
    document_name: str
    is_present_in_profile: bool = False
    status_note: str = ""


class BusinessMatchReport(BaseModel):
    relevance_score: int = Field(default=0, ge=0, le=100)
    score_breakdown: Dict[str, int] = Field(default_factory=dict)
    relevance_explanation: str = Field(default="")
    satisfied_criteria: List[str] = Field(default_factory=list)
    unsatisfied_criteria: List[str] = Field(default_factory=list)
    information_needed: List[str] = Field(default_factory=list)
    checklist: List[ChecklistItem] = Field(default_factory=list)
    recommended_next_steps: List[str] = Field(default_factory=list)
    deadline_status: str = Field(default="Unknown")
    is_legally_binding_advice: bool = False  # Always False as legal safety disclaimer


class SavedNotice(BaseModel):
    id: Optional[int] = None
    url: str
    title: str
    site_name: str
    category: str
    deadline: Optional[str] = None
    relevance_score: int = 0
    raw_content: str = ""
    extraction: Optional[NoticeExtraction] = None
    verification: Optional[VerificationReport] = None
    matching: Optional[BusinessMatchReport] = None
    saved_at: Optional[str] = None
