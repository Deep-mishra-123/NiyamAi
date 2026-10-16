"""
NiyamAI - SQLite Database Storage
Provides persistence for business profiles, scan history, and saved notices with deduplication.
"""

import sqlite3
import json
import logging
from datetime import datetime, timezone
from contextlib import contextmanager
from typing import List, Optional, Tuple, Dict, Any, Generator
from pathlib import Path

from config import NIYAMAI_DB_PATH
from models import (
    BusinessProfile,
    SearchResultItem,
    NoticeExtraction,
    VerificationReport,
    BusinessMatchReport,
    SavedNotice,
)

logger = logging.getLogger("niyamai.database")


class Database:
    """Manages SQLite tables and operations for NiyamAI."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or NIYAMAI_DB_PATH
        # Ensure parent directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    @contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Returns a SQLite connection with dict row access and guaranteed closure."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def init_db(self) -> None:
        """Initializes database tables if they do not exist."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Business Profiles table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    industry TEXT NOT NULL,
                    state TEXT NOT NULL,
                    business_size TEXT NOT NULL,
                    categories_json TEXT,
                    registrations_json TEXT,
                    annual_turnover_inr REAL,
                    description TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Scan History table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scan_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query TEXT NOT NULL,
                    profile_name TEXT,
                    result_count INTEGER DEFAULT 0,
                    results_json TEXT,
                    scanned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Saved Notices table with unique URL constraint for deduplication
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS saved_notices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    site_name TEXT,
                    category TEXT,
                    deadline TEXT,
                    relevance_score INTEGER DEFAULT 0,
                    raw_content TEXT,
                    extraction_json TEXT,
                    verification_json TEXT,
                    matching_json TEXT,
                    saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    # ---------------- Profile Operations ----------------

    def save_profile(self, profile: BusinessProfile) -> int:
        """Saves or updates a business profile."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            categories_str = json.dumps(profile.categories_of_interest)
            registrations_str = json.dumps(profile.existing_registrations)
            now = datetime.now(timezone.utc).isoformat()

            cursor.execute("""
                INSERT INTO profiles (
                    name, industry, state, business_size, categories_json,
                    registrations_json, annual_turnover_inr, description, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    industry=excluded.industry,
                    state=excluded.state,
                    business_size=excluded.business_size,
                    categories_json=excluded.categories_json,
                    registrations_json=excluded.registrations_json,
                    annual_turnover_inr=excluded.annual_turnover_inr,
                    description=excluded.description,
                    updated_at=excluded.updated_at
            """, (
                profile.name,
                profile.industry,
                profile.state,
                profile.business_size,
                categories_str,
                registrations_str,
                profile.annual_turnover_inr,
                profile.description,
                now,
            ))
            conn.commit()
            return cursor.lastrowid or 1

    def get_profile(self, name: str) -> Optional[BusinessProfile]:
        """Fetches a profile by business name."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM profiles WHERE name = ?", (name,))
            row = cursor.fetchone()
            if not row:
                return None
            return BusinessProfile(
                name=row["name"],
                industry=row["industry"],
                state=row["state"],
                business_size=row["business_size"],
                categories_of_interest=json.loads(row["categories_json"] or "[]"),
                existing_registrations=json.loads(row["registrations_json"] or "[]"),
                annual_turnover_inr=row["annual_turnover_inr"],
                description=row["description"],
            )

    def list_profiles(self) -> List[BusinessProfile]:
        """Lists all stored business profiles."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM profiles ORDER BY updated_at DESC")
            profiles = []
            for row in cursor.fetchall():
                profiles.append(
                    BusinessProfile(
                        name=row["name"],
                        industry=row["industry"],
                        state=row["state"],
                        business_size=row["business_size"],
                        categories_of_interest=json.loads(row["categories_json"] or "[]"),
                        existing_registrations=json.loads(row["registrations_json"] or "[]"),
                        annual_turnover_inr=row["annual_turnover_inr"],
                        description=row["description"],
                    )
                )
            return profiles

    # ---------------- Scan History Operations ----------------

    def save_scan(self, query: str, profile_name: str, results: List[SearchResultItem]) -> int:
        """Stores search query and results for audit and history."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            results_dict = [r.model_dump() for r in results]
            cursor.execute("""
                INSERT INTO scan_history (query, profile_name, result_count, results_json, scanned_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                query,
                profile_name,
                len(results),
                json.dumps(results_dict),
                datetime.now(timezone.utc).isoformat(),
            ))
            conn.commit()
            return cursor.lastrowid or 0

    def get_scan_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Retrieves past scan records."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, query, profile_name, result_count, results_json, scanned_at
                FROM scan_history ORDER BY id DESC LIMIT ?
            """, (limit,))
            history = []
            for row in cursor.fetchall():
                history.append({
                    "id": row["id"],
                    "query": row["query"],
                    "profile_name": row["profile_name"],
                    "result_count": row["result_count"],
                    "results": json.loads(row["results_json"] or "[]"),
                    "scanned_at": row["scanned_at"],
                })
            return history

    # ---------------- Saved Notice Operations (Deduplication) ----------------

    def save_notice(self, notice: SavedNotice) -> Tuple[int, bool]:
        """
        Saves or updates a notice in the database.
        Returns a tuple: (notice_id, is_duplicate).
        If URL already exists, updates the record and flags is_duplicate = True.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM saved_notices WHERE url = ?", (notice.url,))
            existing = cursor.fetchone()
            is_duplicate = existing is not None

            ext_json = notice.extraction.model_dump_json() if notice.extraction else None
            ver_json = notice.verification.model_dump_json() if notice.verification else None
            match_json = notice.matching.model_dump_json() if notice.matching else None
            now = datetime.now(timezone.utc).isoformat()

            if is_duplicate:
                notice_id = existing["id"]
                cursor.execute("""
                    UPDATE saved_notices SET
                        title = ?,
                        site_name = ?,
                        category = ?,
                        deadline = ?,
                        relevance_score = ?,
                        raw_content = ?,
                        extraction_json = ?,
                        verification_json = ?,
                        matching_json = ?,
                        saved_at = ?
                    WHERE id = ?
                """, (
                    notice.title,
                    notice.site_name,
                    notice.category,
                    notice.deadline,
                    notice.relevance_score,
                    notice.raw_content,
                    ext_json,
                    ver_json,
                    match_json,
                    now,
                    notice_id,
                ))
            else:
                cursor.execute("""
                    INSERT INTO saved_notices (
                        url, title, site_name, category, deadline, relevance_score,
                        raw_content, extraction_json, verification_json, matching_json, saved_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    notice.url,
                    notice.title,
                    notice.site_name,
                    notice.category,
                    notice.deadline,
                    notice.relevance_score,
                    notice.raw_content,
                    ext_json,
                    ver_json,
                    match_json,
                    now,
                ))
                notice_id = cursor.lastrowid or 0

            conn.commit()
            return (notice_id, is_duplicate)

    def get_saved_notices(self) -> List[SavedNotice]:
        """Returns all saved notices."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM saved_notices ORDER BY saved_at DESC")
            notices = []
            for row in cursor.fetchall():
                ext = NoticeExtraction.model_validate_json(row["extraction_json"]) if row["extraction_json"] else None
                ver = VerificationReport.model_validate_json(row["verification_json"]) if row["verification_json"] else None
                mat = BusinessMatchReport.model_validate_json(row["matching_json"]) if row["matching_json"] else None

                notices.append(
                    SavedNotice(
                        id=row["id"],
                        url=row["url"],
                        title=row["title"],
                        site_name=row["site_name"] or "",
                        category=row["category"] or "Tender",
                        deadline=row["deadline"],
                        relevance_score=row["relevance_score"] or 0,
                        raw_content=row["raw_content"] or "",
                        extraction=ext,
                        verification=ver,
                        matching=mat,
                        saved_at=row["saved_at"],
                    )
                )
            return notices

    def get_saved_notice_by_url(self, url: str) -> Optional[SavedNotice]:
        """Finds a notice by source URL."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM saved_notices WHERE url = ?", (url,))
            row = cursor.fetchone()
            if not row:
                return None
            ext = NoticeExtraction.model_validate_json(row["extraction_json"]) if row["extraction_json"] else None
            ver = VerificationReport.model_validate_json(row["verification_json"]) if row["verification_json"] else None
            mat = BusinessMatchReport.model_validate_json(row["matching_json"]) if row["matching_json"] else None

            return SavedNotice(
                id=row["id"],
                url=row["url"],
                title=row["title"],
                site_name=row["site_name"] or "",
                category=row["category"] or "Tender",
                deadline=row["deadline"],
                relevance_score=row["relevance_score"] or 0,
                raw_content=row["raw_content"] or "",
                extraction=ext,
                verification=ver,
                matching=mat,
                saved_at=row["saved_at"],
            )

    def delete_saved_notice(self, notice_id: int) -> bool:
        """Deletes a notice by ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM saved_notices WHERE id = ?", (notice_id,))
            conn.commit()
            return cursor.rowcount > 0
