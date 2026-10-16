"""
NiyamAI - Business Matching Agent
Compares extracted notice data against a company's profile.
Computes a transparent 0-100 relevance score with weighted breakdown:
- Industry/Domain Fit: 30%
- Business Scale & MSME Policy: 25%
- Geographic Scope: 20%
- Registration & Compliance Readiness: 25%
Generates gap analysis, required documents checklist, and actionable next steps.
"""

import re
from datetime import datetime
from typing import List, Dict, Any, Optional

from models import (
    BusinessProfile,
    NoticeExtraction,
    BusinessMatchReport,
    ChecklistItem,
)


class MatchingAgent:
    """Agent that performs multi-criteria scoring and gap analysis."""

    def match(self, profile: BusinessProfile, extraction: NoticeExtraction) -> BusinessMatchReport:
        """Evaluates notice against business profile and produces audit report."""
        satisfied: List[str] = []
        unsatisfied: List[str] = []
        info_needed: List[str] = []
        breakdown: Dict[str, int] = {}

        # ---------------- 1. Industry / Sector Fit (Max 30) ----------------
        industry_score = 0
        profile_ind = profile.industry.lower().strip()
        notice_text_repr = f"{extraction.title} {extraction.category} {' '.join(extraction.eligibility_criteria)}".lower()

        if profile_ind in notice_text_repr:
            industry_score = 30
            satisfied.append(f"Industry alignment: Notice directly matches your primary sector '{profile.industry}'.")
        else:
            # Check interest categories
            matched_cats = [c for c in profile.categories_of_interest if c.lower() in notice_text_repr]
            if matched_cats:
                industry_score = 25
                satisfied.append(f"Category match: Aligns with your specified interests ({', '.join(matched_cats)}).")
            else:
                # Check broad keywords
                industry_words = [w for w in profile_ind.split() if len(w) > 3]
                if any(w in notice_text_repr for w in industry_words):
                    industry_score = 15
                    satisfied.append(f"Broad sector correlation with '{profile.industry}'.")
                else:
                    industry_score = 5
                    unsatisfied.append(f"Industry gap: Notice does not explicitly mention '{profile.industry}'. Verify work scope.")

        breakdown["Industry Fit (Max 30)"] = industry_score

        # ---------------- 2. Business Scale & MSME Preference (Max 25) ----------------
        scale_score = 10
        profile_size_lower = profile.business_size.lower()
        is_msme = any(tier in profile_size_lower for tier in ["micro", "small", "medium"])
        is_startup = "startup" in profile_size_lower

        notice_has_msme = any(
            "msme" in reg.lower() or "udyam" in reg.lower()
            for reg in extraction.required_registrations
        ) or any("msme" in crit.lower() for crit in extraction.eligibility_criteria)

        if is_msme and notice_has_msme:
            scale_score = 25
            satisfied.append("MSME Policy advantage: Government procurement offers reservation or EMD waiver for your tier.")
        elif is_msme:
            scale_score = 20
            satisfied.append("Scale compatibility: Open to MSMEs under general qualification guidelines.")
        elif is_startup:
            scale_score = 20
            satisfied.append("Startup eligibility: Eligible under DPIIT Innovation or General Procurement norms.")
        else:
            scale_score = 15

        breakdown["Scale & MSME Fit (Max 25)"] = scale_score

        # ---------------- 3. Geographic Scope (Max 20) ----------------
        geo_score = 0
        notice_geo = (extraction.geographic_scope or "Pan-India").lower()
        profile_state = profile.state.lower().strip()

        if "pan-india" in notice_geo or "all india" in notice_geo or "central" in notice_geo:
            geo_score = 20
            satisfied.append("Geographic eligibility: Pan-India notice open to businesses registered in any state.")
        elif profile_state in notice_geo:
            geo_score = 20
            satisfied.append(f"State eligibility: Perfect location match with {profile.state}.")
        else:
            # Another specific state is required
            geo_score = 5
            unsatisfied.append(f"Location restriction: Notice specifies '{extraction.geographic_scope}', while your business is in '{profile.state}'. Check if out-of-state entities can bid.")

        breakdown["Geographic Scope (Max 20)"] = geo_score

        # ---------------- 4. Registrations & Compliance Readiness (Max 25) ----------------
        reg_score = 0
        existing_norm = [r.lower() for r in profile.existing_registrations]

        if not extraction.required_registrations:
            reg_score = 20
            satisfied.append("No specialized statutory registrations mandated in initial notice.")
        else:
            matched_regs = []
            missing_regs = []
            for req in extraction.required_registrations:
                clean_req = re.sub(r"\(.*?\)", "", req).strip().lower()
                req_tokens = clean_req.split()
                if any(any(tok in ex for tok in req_tokens if len(tok) > 2) for ex in existing_norm):
                    matched_regs.append(req)
                else:
                    missing_regs.append(req)

            if matched_regs:
                satisfied.append(f"Satisfied registrations: {', '.join(matched_regs)}")
            if missing_regs:
                unsatisfied.append(f"Missing required registrations: {', '.join(missing_regs)}")
                info_needed.append(f"Do you possess valid {', '.join(missing_regs)}?")

            total_reqs = len(extraction.required_registrations)
            match_ratio = len(matched_regs) / total_reqs if total_reqs > 0 else 1.0
            reg_score = int(round(match_ratio * 25))

        breakdown["Registration Readiness (Max 25)"] = reg_score

        # ---------------- Calculate Total Score ----------------
        total_score = sum(breakdown.values())
        total_score = min(max(total_score, 0), 100)

        # ---------------- Build Document Checklist ----------------
        checklist: List[ChecklistItem] = []
        # Standard docs + notice-specific docs
        standard_docs = extraction.required_documents or [
            "GST Registration Certificate",
            "Udyam MSME Certificate",
            "PAN Card",
            "Last 3 Years Income Tax Returns (ITR)",
            "Bank Solvency Certificate / Cancelled Cheque",
        ]

        for doc in standard_docs:
            is_present = any(reg.lower() in doc.lower() for reg in profile.existing_registrations)
            status_note = "Present in your registered profile" if is_present else "Required for formal application submission"
            checklist.append(
                ChecklistItem(
                    document_name=doc,
                    is_present_in_profile=is_present,
                    status_note=status_note,
                )
            )

        # ---------------- Next Steps ----------------
        next_steps = [
            f"1. Download complete tender document/gazette from: {extraction.official_source_url}",
            "2. Verify whether EMD exemption applies under your MSME/Udyam status.",
            "3. Compile all checklist documents and ensure Digital Signature (Class 3 DSC) is active.",
        ]
        if extraction.submission_deadline:
            next_steps.append(f"4. Calendar deadline alert: Complete submission before {extraction.submission_deadline}.")
        else:
            next_steps.append("4. Contact the issuing procurement officer to confirm the final bid submission cut-off date.")

        # ---------------- Deadline Status ----------------
        deadline_status = "No Deadline Specified"
        if extraction.submission_deadline:
            deadline_status = f"Deadline: {extraction.submission_deadline}"

        # ---------------- Relevance Explanation ----------------
        explanation = (
            f"Notice scored {total_score}/100. "
            f"Industry fit contributed {industry_score}/30, business scale contributed {scale_score}/25, "
            f"geographic compatibility contributed {geo_score}/20, and registration readiness contributed {reg_score}/25."
        )

        return BusinessMatchReport(
            relevance_score=total_score,
            score_breakdown=breakdown,
            relevance_explanation=explanation,
            satisfied_criteria=satisfied,
            unsatisfied_criteria=unsatisfied,
            information_needed=info_needed,
            checklist=checklist,
            recommended_next_steps=next_steps,
            deadline_status=deadline_status,
            is_legally_binding_advice=False,
        )
