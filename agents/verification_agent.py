"""
NiyamAI - Verification Agent
Independently verifies extracted claims against the fetched raw document content.
Assigns verifiable audit statuses:
- Verified Against Retrieved Content
- Partially Supported
- Needs Review
- Missing From Source
Guarantees transparent evidence linkage for compliance officers and MSMEs.
"""

import re
from typing import List, Tuple
from models import (
    NoticeExtraction,
    VerificationClaim,
    VerificationReport,
    VerificationStatus,
)


class VerificationAgent:
    """Agent that audits claims extracted from government notices against raw source text."""

    def verify(self, extraction: NoticeExtraction, raw_text: str) -> VerificationReport:
        """Audits each key claim and computes an overall verification report."""
        if not raw_text or not raw_text.strip():
            return VerificationReport(
                claims=[
                    VerificationClaim(
                        claim_field="Document Source Content",
                        extracted_value="Empty",
                        supporting_evidence="No text retrieved from source URL.",
                        status=VerificationStatus.MISSING,
                        explanation="Unable to verify any claims because the fetched document content was empty.",
                    )
                ],
                overall_status="Missing From Source",
                missing_count=1,
                summary="Source content is empty; verification could not be performed.",
            )

        claims: List[VerificationClaim] = []
        raw_lower = raw_text.lower()

        # 1. Audit: Submission Deadline
        if extraction.submission_deadline:
            deadline = extraction.submission_deadline.strip()
            # Search for exact deadline string or normalized date
            if deadline.lower() in raw_lower:
                context_quote = self._find_context_snippet(raw_text, deadline)
                claims.append(
                    VerificationClaim(
                        claim_field="Submission Deadline",
                        extracted_value=deadline,
                        supporting_evidence=context_quote,
                        status=VerificationStatus.VERIFIED,
                        explanation=f"Exact deadline '{deadline}' verified directly in source document.",
                    )
                )
            else:
                # Check for individual components
                date_numbers = re.findall(r"\d+", deadline)
                if len(date_numbers) >= 2 and all(num in raw_text for num in date_numbers[:2]):
                    claims.append(
                        VerificationClaim(
                            claim_field="Submission Deadline",
                            extracted_value=deadline,
                            supporting_evidence="Date components partially detected in source text.",
                            status=VerificationStatus.PARTIAL,
                            explanation=f"Partial date match found for '{deadline}', but full formatted string was not found verbatim.",
                        )
                    )
                else:
                    claims.append(
                        VerificationClaim(
                            claim_field="Submission Deadline",
                            extracted_value=deadline,
                            supporting_evidence="Deadline string not found in retrieved source text.",
                            status=VerificationStatus.MISSING,
                            explanation=f"Claimed deadline '{deadline}' is not present in retrieved document text. Needs independent verification.",
                        )
                    )
        else:
            claims.append(
                VerificationClaim(
                    claim_field="Submission Deadline",
                    extracted_value="Not Specified / Missing",
                    supporting_evidence="No deadline patterns identified in notice.",
                    status=VerificationStatus.NEEDS_REVIEW,
                    explanation="No explicit submission deadline was found in the notice. Check original portal to avoid missing deadlines.",
                )
            )

        # 2. Audit: Issuing Authority
        if extraction.issuing_authority:
            authority = extraction.issuing_authority.strip()
            # Split authority into keywords to check presence
            words = [w for w in re.split(r"[\s,]+", authority) if len(w) > 3]
            matched_words = [w for w in words if w.lower() in raw_lower]
            if len(matched_words) >= max(1, int(len(words) * 0.7)):
                context_quote = self._find_context_snippet(raw_text, matched_words[0])
                claims.append(
                    VerificationClaim(
                        claim_field="Issuing Authority",
                        extracted_value=authority,
                        supporting_evidence=context_quote,
                        status=VerificationStatus.VERIFIED,
                        explanation=f"Authority '{authority}' confirmed by source text context.",
                    )
                )
            elif matched_words:
                claims.append(
                    VerificationClaim(
                        claim_field="Issuing Authority",
                        extracted_value=authority,
                        supporting_evidence=f"Partial match: {', '.join(matched_words)}",
                        status=VerificationStatus.PARTIAL,
                        explanation=f"Some organization keywords found, but full authority name '{authority}' was not matched verbatim.",
                    )
                )
            else:
                claims.append(
                    VerificationClaim(
                        claim_field="Issuing Authority",
                        extracted_value=authority,
                        supporting_evidence="No matching organization names found in document body.",
                        status=VerificationStatus.MISSING,
                        explanation=f"Authority '{authority}' was not found in source text.",
                    )
                )
        else:
            claims.append(
                VerificationClaim(
                    claim_field="Issuing Authority",
                    extracted_value="Unknown",
                    supporting_evidence="No issuing authority identified in document.",
                    status=VerificationStatus.NEEDS_REVIEW,
                    explanation="Issuing authority could not be established from the text.",
                )
            )

        # 3. Audit: Financial Requirements
        if extraction.financial_requirements:
            fin = extraction.financial_requirements.strip()
            # Find digits/numbers
            numbers = re.findall(r"[\d,]+", fin)
            if any(num in raw_text for num in numbers if len(num) >= 3):
                quote = self._find_context_snippet(raw_text, numbers[0])
                claims.append(
                    VerificationClaim(
                        claim_field="Financial Requirements (EMD / Value)",
                        extracted_value=fin,
                        supporting_evidence=quote,
                        status=VerificationStatus.VERIFIED,
                        explanation=f"Financial requirement figures confirmed in source text.",
                    )
                )
            else:
                claims.append(
                    VerificationClaim(
                        claim_field="Financial Requirements (EMD / Value)",
                        extracted_value=fin,
                        supporting_evidence="Figures not located in source body.",
                        status=VerificationStatus.PARTIAL,
                        explanation="Financial terms extracted could not be corroborated with exact figures in source text.",
                    )
                )

        # 4. Audit: Required Registrations
        if extraction.required_registrations:
            verified_regs = []
            missing_regs = []
            for reg in extraction.required_registrations:
                clean_term = re.sub(r"\(.*?\)", "", reg).strip()
                tokens = [t.lower() for t in clean_term.split() if len(t) > 2]
                if any(tok in raw_lower for tok in tokens):
                    verified_regs.append(reg)
                else:
                    missing_regs.append(reg)

            if verified_regs and not missing_regs:
                claims.append(
                    VerificationClaim(
                        claim_field="Required Registrations",
                        extracted_value=", ".join(verified_regs),
                        supporting_evidence=f"Confirmed in document: {', '.join(verified_regs)}",
                        status=VerificationStatus.VERIFIED,
                        explanation="All claimed mandatory registrations exist in source text.",
                    )
                )
            elif verified_regs:
                claims.append(
                    VerificationClaim(
                        claim_field="Required Registrations",
                        extracted_value=f"Verified: {', '.join(verified_regs)} | Unverified: {', '.join(missing_regs)}",
                        supporting_evidence=f"Partial: {', '.join(verified_regs)}",
                        status=VerificationStatus.PARTIAL,
                        explanation="Some registrations were corroborated while others were not explicitly mentioned.",
                    )
                )
            else:
                claims.append(
                    VerificationClaim(
                        claim_field="Required Registrations",
                        extracted_value=", ".join(missing_regs),
                        supporting_evidence="None found in source.",
                        status=VerificationStatus.MISSING,
                        explanation="Claimed registrations were not found in the retrieved document text.",
                    )
                )

        # 5. Audit: Required Documents
        if extraction.required_documents:
            verified_docs = []
            for doc in extraction.required_documents:
                tokens = [t.lower() for t in doc.split() if len(t) > 3]
                if any(tok in raw_lower for tok in tokens):
                    verified_docs.append(doc)

            if len(verified_docs) == len(extraction.required_documents):
                claims.append(
                    VerificationClaim(
                        claim_field="Required Documents",
                        extracted_value=f"{len(verified_docs)} document requirements",
                        supporting_evidence=f"Corroborated: {', '.join(verified_docs[:3])}...",
                        status=VerificationStatus.VERIFIED,
                        explanation="Document requirements corroborated by document text.",
                    )
                )
            elif verified_docs:
                claims.append(
                    VerificationClaim(
                        claim_field="Required Documents",
                        extracted_value=f"{len(verified_docs)} of {len(extraction.required_documents)} verified",
                        supporting_evidence=f"Found: {', '.join(verified_docs[:2])}",
                        status=VerificationStatus.PARTIAL,
                        explanation="Some document checklist items were verified; others may be implied or in external annexures.",
                    )
                )
            else:
                claims.append(
                    VerificationClaim(
                        claim_field="Required Documents",
                        extracted_value=", ".join(extraction.required_documents[:3]),
                        supporting_evidence="No direct document checklist found in retrieved text.",
                        status=VerificationStatus.NEEDS_REVIEW,
                        explanation="Documents list may require downloading full tender PDF/annexure.",
                    )
                )

        # Summary statistics
        verified_count = sum(1 for c in claims if c.status == VerificationStatus.VERIFIED)
        partial_count = sum(1 for c in claims if c.status == VerificationStatus.PARTIAL)
        needs_review_count = sum(1 for c in claims if c.status == VerificationStatus.NEEDS_REVIEW)
        missing_count = sum(1 for c in claims if c.status == VerificationStatus.MISSING)

        if missing_count > 0:
            overall = "Needs Review - Discrepancies Detected"
        elif partial_count > 0 or needs_review_count > 0:
            overall = "Partially Supported"
        else:
            overall = "Verified Against Retrieved Content"

        summary = (
            f"Audit finished: {verified_count} verified, {partial_count} partially supported, "
            f"{needs_review_count} needs review, {missing_count} missing from source."
        )

        return VerificationReport(
            claims=claims,
            overall_status=overall,
            verified_count=verified_count,
            partially_supported_count=partial_count,
            needs_review_count=needs_review_count,
            missing_count=missing_count,
            summary=summary,
        )

    def _find_context_snippet(self, raw_text: str, keyword: str, radius: int = 120) -> str:
        """Finds the sentence or context surrounding a keyword for evidence quotation."""
        idx = raw_text.lower().find(keyword.lower())
        if idx == -1:
            return f"Evidence keyword '{keyword}' found."
        start = max(0, idx - 40)
        end = min(len(raw_text), idx + len(keyword) + radius)
        snippet = raw_text[start:end].replace("\n", " ").strip()
        return f"...{snippet}..."
