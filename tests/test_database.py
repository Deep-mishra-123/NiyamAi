"""
Unit tests for Database persistence layer verifying profile CRUD,
scan history recording, notice storage, and duplicate detection.
"""

import tempfile
import os
from pathlib import Path
import pytest

from database.db import Database
from models import BusinessProfile, SavedNotice, NoticeExtraction


@pytest.fixture
def temp_db():
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_file = os.path.join(tmp_dir, "test_niyamai.db")
        db = Database(db_path=db_file)
        yield db


def test_save_and_get_profile(temp_db, sample_solar_profile):
    """Business profiles are saved and retrieved accurately."""
    temp_db.save_profile(sample_solar_profile)
    retrieved = temp_db.get_profile(sample_solar_profile.name)

    assert retrieved is not None
    assert retrieved.name == sample_solar_profile.name
    assert retrieved.industry == "Solar"
    assert "Udyam / MSME Registration" in retrieved.existing_registrations


def test_notice_deduplication(temp_db):
    """Inserting notice with existing URL updates record and flags is_duplicate as True."""
    notice1 = SavedNotice(
        url="https://gem.gov.in/tenders/notice-123",
        title="Notice Version 1",
        site_name="gem.gov.in",
        category="Tender",
        relevance_score=75,
        raw_content="Content 1",
    )
    notice_id1, is_dup1 = temp_db.save_notice(notice1)
    assert is_dup1 is False
    assert notice_id1 > 0

    # Save second notice with same URL
    notice2 = SavedNotice(
        url="https://gem.gov.in/tenders/notice-123",
        title="Notice Version 2 (Updated)",
        site_name="gem.gov.in",
        category="Tender",
        relevance_score=85,
        raw_content="Content 2 Updated",
    )
    notice_id2, is_dup2 = temp_db.save_notice(notice2)
    assert is_dup2 is True

    # Check that database has only 1 record with updated title
    saved = temp_db.get_saved_notices()
    assert len(saved) == 1
    assert saved[0].title == "Notice Version 2 (Updated)"
    assert saved[0].relevance_score == 85


def test_scan_history_persistence(temp_db):
    """Scan queries and result counts are recorded in scan history."""
    temp_db.save_scan(
        query="msme solar tender",
        profile_name="SuryaShakti",
        results=[],
    )
    history = temp_db.get_scan_history(limit=5)
    assert len(history) == 1
    assert history[0]["query"] == "msme solar tender"
    assert history[0]["profile_name"] == "SuryaShakti"
