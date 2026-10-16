"""
NiyamAI - Document Extraction Agent
Extracts structured compliance, tender, and scheme data from raw fetched markdown.
Supports:
1. LLM-based extraction (Google Gemini) when GEMINI_API_KEY is configured.
2. Deterministic rule-based extraction fallback when no LLM key is configured.
Strictly grounds extracted fields in source snippets without hallucinating missing data.
"""

import re
import json
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from config import GEMINI_API_KEY
from models import NoticeExtraction

logger = logging.getLogger("niyamai.extraction_agent")

# Well-known Indian states and UTs
INDIAN_STATES = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
    "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka",
    "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram",
    "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu",
    "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal",
    "Delhi", "Jammu and Kashmir", "Ladakh", "Chandigarh", "Puducherry",
]


class ExtractionAgent:
    """Agent responsible for parsing retrieved notice markdown into structured fields."""

    def __init__(self, gemini_api_key: Optional[str] = None):
        self.api_key = (gemini_api_key or GEMINI_API_KEY).strip()
        self.has_llm = bool(self.api_key and len(self.api_key) > 10)

    def extract(self, raw_text: str, source_url: str, title_hint: Optional[str] = None) -> NoticeExtraction:
        """
        Main extraction entry point. Uses Gemini LLM if configured, otherwise falls back
        to deterministic rule-based extractor.
        """
        if not raw_text or not raw_text.strip():
            return NoticeExtraction(
                title=title_hint or "Empty Notice Document",
                official_source_url=source_url,
                uncertain_or_missing_fields=["title", "issuing_authority", "submission_deadline", "eligibility_criteria", "required_documents"],
                extracted_at=datetime.now(timezone.utc).isoformat(),
            )

        if self.has_llm:
            try:
                return self._extract_with_gemini(raw_text, source_url, title_hint)
            except Exception as e:
                logger.warning(f"LLM extraction failed, falling back to deterministic extraction: {e}")
                fallback = self._extract_deterministic(raw_text, source_url, title_hint)
                fallback.uncertain_or_missing_fields.append("llm_extraction_failed (used deterministic fallback)")
                return fallback
        else:
            return self._extract_deterministic(raw_text, source_url, title_hint)

    def _extract_with_gemini(self, raw_text: str, source_url: str, title_hint: Optional[str] = None) -> NoticeExtraction:
        """Invokes Google Gemini with structured JSON output instructions."""
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=self.api_key)

        prompt = f"""You are NiyamAI's Document Extraction Agent specializing in Indian public tenders, MSME schemes, grants, and regulatory notices.
Extract structured information strictly from the provided source document text.

CRITICAL RULES:
1. NEVER hallucinate, guess, or invent deadlines, monetary amounts, or requirements not explicitly present in the text.
2. If a field is not found in the source text, set its value to null (or empty list) and include the field name in uncertain_or_missing_fields.
3. Every important claim (deadline, EMD/financials, registrations) MUST include an exact quotation in supporting_evidence.
4. Distinguish clearly between Tenders, Grants, Subsidies, and Regulatory Notices.

SOURCE URL: {source_url}
TITLE HINT: {title_hint or "N/A"}

DOCUMENT CONTENT:
\"\"\"
{raw_text[:18000]}
\"\"\"
"""

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=NoticeExtraction,
                temperature=0.0,
            ),
        )

        extraction_data = json.loads(response.text)
        extraction_data["official_source_url"] = source_url
        extraction_data["extracted_at"] = datetime.now(timezone.utc).isoformat()
        return NoticeExtraction.model_validate(extraction_data)

    def _extract_deterministic(self, raw_text: str, source_url: str, title_hint: Optional[str] = None) -> NoticeExtraction:
        """
        High-precision deterministic rule-based extractor for Indian government procurement,
        MSME schemes, and tender notices.
        """
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        evidence: List[str] = []
        missing_fields: List[str] = []

        # 1. Title Extraction
        title = title_hint
        if not title:
            # Check headings; skip generic site headers like 'Government of India - GeM'
            generic_headers = ["government of india", "gem", "central public procurement portal", "government e-marketplace"]
            candidates = []
            for line in lines[:15]:
                if line.startswith("#"):
                    cleaned = re.sub(r"^#+\s*", "", line).strip()
                    cleaned = re.sub(r"^(?:Bid Document|Tender Document|Notice Inviting Tender|NIT)[:\s]+", "", cleaned, flags=re.I).strip()
                    candidates.append(cleaned)

            for cand in candidates:
                if not any(cand.lower().startswith(gh) for gh in generic_headers) and len(cand) > 10:
                    title = cand
                    break

            if not title and candidates:
                title = candidates[0]
            elif not title and lines:
                title = lines[0][:150]

        if not title:
            title = "Official Government Notice"
            missing_fields.append("title")

        # 2. Issuing Authority
        issuing_authority = None
        authority_patterns = [
            r"(?:Ministry of\s+[A-Za-z\s&,]+(?:Government of India)?)",
            r"(?:Department of\s+[A-Za-z\s&,]+)",
            r"(?:[A-Z][A-Za-z\s&]+(?:Corporation|Limited|Ltd|Board|Authority|Nigam|Vidyut|Rail|Airport|Port|University))",
            r"(?:Government of\s+[A-Za-z\s]+)",
            r"(?:GeM|Government e-Marketplace|CPPP|Central Public Procurement Portal)",
        ]
        for pattern in authority_patterns:
            match = re.search(pattern, raw_text, re.IGNORECASE)
            if match:
                candidate = match.group(0).strip()
                if len(candidate) > 4 and len(candidate) < 100:
                    issuing_authority = candidate
                    evidence.append(f"Authority matched: '{issuing_authority}'")
                    break

        if not issuing_authority:
            # Check domain name from source_url
            if "gem.gov.in" in source_url:
                issuing_authority = "Government e-Marketplace (GeM)"
            elif "msme.gov.in" in source_url:
                issuing_authority = "Ministry of Micro, Small and Medium Enterprises"
            elif "startupindia.gov.in" in source_url:
                issuing_authority = "Department for Promotion of Industry and Internal Trade (DPIIT)"
            elif "eprocure.gov.in" in source_url:
                issuing_authority = "Central Public Procurement Portal (CPPP)"
            else:
                missing_fields.append("issuing_authority")

        # 3. Category
        category = "Tender"
        lower_text = raw_text.lower()
        if "expression of interest" in lower_text or "eoi" in lower_text:
            category = "Expression of Interest (EOI)"
        elif "request for proposal" in lower_text or "rfp" in lower_text:
            category = "Request for Proposal (RFP)"
        elif "grant" in lower_text or "financial assistance" in lower_text:
            category = "Grant"
        elif "subsidy" in lower_text or "incentive scheme" in lower_text:
            category = "Subsidy / Incentive"
        elif "scheme" in lower_text or "yojna" in lower_text or "yojana" in lower_text:
            category = "Government Scheme"
        elif "compliance" in lower_text or "circular" in lower_text or "gazette" in lower_text:
            category = "Regulatory Notice"

        # 4. Tender/Scheme Reference Number
        scheme_or_tender_name = None
        ref_patterns = [
            r"(?:Tender\s+(?:No|Ref|Notice|ID)[:.\s]+)([A-Za-z0-9/\-_.]+)",
            r"(?:Bid\s+Number[:.\s]+)([A-Za-z0-9/\-_.]+)",
            r"(?:NIT\s+No[:.\s]+)([A-Za-z0-9/\-_.]+)",
            r"(?:Scheme\s+Code[:.\s]+)([A-Za-z0-9/\-_.]+)",
        ]
        for pat in ref_patterns:
            ref_match = re.search(pat, raw_text, re.IGNORECASE)
            if ref_match:
                scheme_or_tender_name = ref_match.group(0).strip()
                evidence.append(f"Identifier: {scheme_or_tender_name}")
                break

        # 5. Submission Deadline
        submission_deadline = None
        deadline_patterns = [
            r"(?:(?:Bid\s+Submission|Submission|Closing|Due|End)\s+(?:Date|Time|Deadline)|Last\s+Date\s+for\s+Submission)[^\n\r:]{0,25}[:.\s]+([0-9]{1,2}[-/.][0-9]{1,2}[-/.][0-9]{2,4}(?:\s+[0-9]{1,2}:[0-9]{2}(?:\s*[AaPp][Mm])?)?)",
            r"(?:(?:Bid\s+Submission|Submission|Closing|Due|Last)\s+Date)[^\n\r:]{0,25}[:.\s]+([0-9]{1,2}\s+[A-Za-z]{3,9}\s+[0-9]{4})",
            r"(?:Before|by|on)\s+([0-9]{1,2}[-/.][0-9]{1,2}[-/.][0-9]{2,4})",
        ]
        for d_pat in deadline_patterns:
            d_match = re.search(d_pat, raw_text, re.IGNORECASE)
            if d_match:
                snippet = d_match.group(0).strip()
                submission_deadline = d_match.group(1).strip()
                evidence.append(f"Deadline found in: '{snippet}'")
                break

        if not submission_deadline:
            missing_fields.append("submission_deadline")

        # 6. Publication Date
        publication_date = None
        pub_patterns = [
            r"(?:(?:Published|Issue|Notice)\s+Date)[^\n\r:]{0,25}[:.\s]+([0-9]{1,2}[-/.][0-9]{1,2}[-/.][0-9]{2,4})",
            r"(?:Dated[:.\s]+)([0-9]{1,2}[-/.][0-9]{1,2}[-/.][0-9]{2,4})",
        ]
        for p_pat in pub_patterns:
            p_match = re.search(p_pat, raw_text, re.IGNORECASE)
            if p_match:
                publication_date = p_match.group(1).strip()
                break

        # 7. Required Registrations
        required_registrations: List[str] = []
        reg_keywords = {
            "Udyam / MSME Registration": [r"\budyam\b", r"\bmsme\b", r"\budyog\s+aadhaar\b"],
            "GSTIN / GST Registration": [r"\bgst\b", r"\bgstin\b", r"\bgst\s+registration\b"],
            "DPIIT Startup Recognition": [r"\bdpiit\b", r"\bstartup\s+india\b"],
            "PAN Card": [r"\bpan\s+card\b", r"\bpan\s+number\b", r"\bvalid\s+pan\b"],
            "ISO Certification": [r"\biso\s+\d{4,5}\b", r"\biso\s+certified\b"],
            "EPFO / ESIC Registration": [r"\bepf\b", r"\bepfo\b", r"\besic\b"],
            "Class 3 Digital Signature (DSC)": [r"\bdsc\b", r"\bdigital\s+signature\b"],
        }
        for name, pats in reg_keywords.items():
            for pat in pats:
                if re.search(pat, raw_text, re.IGNORECASE):
                    required_registrations.append(name)
                    evidence.append(f"Registration required: {name}")
                    break

        # 8. Required Documents
        required_documents: List[str] = []
        doc_patterns = {
            "GST Registration Certificate": [r"gst\s+registration\s+certificate", r"gst\s+certificate", r"copy\s+of\s+gst"],
            "Udyam / MSME Certificate": [r"udyam\s+(?:msme\s+)?certificate", r"msme\s+certificate"],
            "PAN Card Copy": [r"pan\s+card\s+copy", r"copy\s+of\s+pan"],
            "Audited Balance Sheets (Last 3 Years)": [r"balance\s+sheet", r"audited\s+financial", r"financial\s+statements"],
            "Income Tax Returns (ITR)": [r"\bitr\b", r"income\s+tax\s+return"],
            "CA Certified Turnover Certificate": [r"ca\s+certificate", r"turnover\s+certificate", r"chartered\s+accountant"],
            "Earnest Money Deposit (EMD) or Exemption": [r"\bemd\b", r"earnest\s+money"],
            "Past Experience / Work Completion Certificate": [r"past\s+experience", r"completion\s+certificate", r"work\s+order"],
            "Partnership Deed / Incorporation Certificate": [r"certificate\s+of\s+incorporation", r"partnership\s+deed", r"moa\b", r"aoa\b"],
            "Undertaking / Non-Blacklisting Affidavit": [r"blacklisting", r"affidavit", r"non-blacklisting"],
        }
        for doc_name, pats in doc_patterns.items():
            for pat in pats:
                if re.search(pat, raw_text, re.IGNORECASE):
                    required_documents.append(doc_name)
                    break

        if not required_documents:
            missing_fields.append("required_documents")

        # 9. Financial Requirements (EMD, Estimated Tender Value)
        financial_requirements = None
        fin_match = re.search(
            r"(?:(?:EMD|Earnest\s+Money|Estimated\s+Cost|Tender\s+Value|Average\s+Turnover)[^\n\r:]{0,25}[:.\s]+(?:Rs\.?|INR|₹)?\s*[0-9,]+(?:\.[0-9]+)?\s*(?:Lakhs?|Cr|Crores?|Lakh)?|\b(?:Rs\.?|INR|₹)\s*[0-9,]+(?:\.[0-9]+)?\s*(?:Lakhs?|Cr|Crores?|Thousand)?)",
            raw_text,
            re.IGNORECASE,
        )
        if fin_match:
            financial_requirements = fin_match.group(0).strip()
            evidence.append(f"Financial spec: {financial_requirements}")
        else:
            missing_fields.append("financial_requirements")

        # 10. Geographic Scope
        geographic_scope = "Pan-India (All India)"
        found_state = False
        for st in INDIAN_STATES:
            if re.search(rf"\b{re.escape(st)}\b", raw_text, re.IGNORECASE):
                geographic_scope = st
                found_state = True
                evidence.append(f"State scope identified: {st}")
                break

        # 11. Eligibility Criteria
        eligibility_criteria: List[str] = []
        for line in lines:
            if any(term in line.lower() for term in ["eligible", "eligibility", "qualification", "criteria"]):
                if len(line) > 20 and len(line) < 300:
                    eligibility_criteria.append(line)
                    if len(eligibility_criteria) >= 4:
                        break

        if not eligibility_criteria:
            if required_registrations:
                eligibility_criteria.append(f"Must possess valid registrations: {', '.join(required_registrations[:3])}")
            else:
                missing_fields.append("eligibility_criteria")

        return NoticeExtraction(
            title=title,
            issuing_authority=issuing_authority,
            category=category,
            scheme_or_tender_name=scheme_or_tender_name,
            publication_date=publication_date,
            submission_deadline=submission_deadline,
            eligibility_criteria=eligibility_criteria,
            required_registrations=required_registrations,
            required_documents=required_documents,
            financial_requirements=financial_requirements,
            geographic_scope=geographic_scope,
            official_source_url=source_url,
            supporting_evidence=evidence[:10],
            uncertain_or_missing_fields=missing_fields,
            extracted_at=datetime.now(timezone.utc).isoformat(),
        )
