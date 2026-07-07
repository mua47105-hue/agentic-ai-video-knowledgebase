"""
Edit-Pattern Memory DB (Phase 9, M5 module). ★ NOVEL (RESEARCH-3 gap #5) ★

SQLite-backed memory of which (content_type, technique, params) tuples succeed.
The planner queries this DB to bias plans toward historically successful techniques.
After every run, the DB is updated with the outcome.

Public surface:
  - EditPatternDB class (query, record_outcome, get_memory_hints, stats)
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import pathlib
import sqlite3
import time
import typing as t


DEFAULT_DB_PATH = str(pathlib.Path.home() / ".cache" / "video_kb" / "edit_patterns.db")


@dataclasses.dataclass
class EditPattern:
    pattern_key: str
    content_type: str
    technique: str
    params: dict
    success_rate: float
    avg_vmaf: float
    avg_reviewer_score: float
    sample_count: int
    last_used: str

    def as_dict(self) -> dict:
        return dataclasses.asdict(self)


class EditPatternDB:
    """SQLite-backed edit-pattern memory."""

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        pathlib.Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _init_schema(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS edit_patterns (
                    pattern_key TEXT PRIMARY KEY,
                    content_type TEXT,
                    technique TEXT,
                    params_canonical TEXT,
                    success_rate REAL,
                    avg_vmaf REAL,
                    avg_reviewer_score REAL,
                    sample_count INTEGER,
                    last_used TEXT,
                    last_run_id TEXT
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_content_type ON edit_patterns(content_type)")
            conn.commit()

    @staticmethod
    def _make_key(content_type: str, technique: str, params: dict) -> str:
        canonical = json.dumps(params, sort_keys=True, default=str)
        key_str = f"{content_type}|{technique}|{canonical}"
        return hashlib.sha256(key_str.encode()).hexdigest()[:16]

    def query(self, content_type: str, technique: t.Optional[str] = None,
              min_sample_count: int = 3) -> list[EditPattern]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            if technique:
                cursor = conn.execute(
                    "SELECT * FROM edit_patterns WHERE content_type=? AND technique=? AND sample_count>=? ORDER BY success_rate DESC",
                    (content_type, technique, min_sample_count))
            else:
                cursor = conn.execute(
                    "SELECT * FROM edit_patterns WHERE content_type=? AND sample_count>=? ORDER BY success_rate DESC",
                    (content_type, min_sample_count))
            rows = cursor.fetchall()
        return [EditPattern(
            pattern_key=r["pattern_key"], content_type=r["content_type"],
            technique=r["technique"], params=json.loads(r["params_canonical"]),
            success_rate=r["success_rate"], avg_vmaf=r["avg_vmaf"] or 0.0,
            avg_reviewer_score=r["avg_reviewer_score"] or 0.0,
            sample_count=r["sample_count"], last_used=r["last_used"],
        ) for r in rows]

    def record_outcome(self, content_type: str, technique: str, params: dict,
                       success: bool, vmaf: t.Optional[float] = None,
                       reviewer_score: t.Optional[float] = None,
                       run_id: t.Optional[str] = None) -> None:
        key = self._make_key(content_type, technique, params)
        canonical = json.dumps(params, sort_keys=True, default=str)
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT * FROM edit_patterns WHERE pattern_key=?", (key,))
            row = cursor.fetchone()
            if row:
                old_count = row[7]
                old_rate = row[4]
                old_vmaf = row[5] or 0.0
                old_reviewer = row[6] or 0.0
                new_count = old_count + 1
                new_rate = ((old_rate * old_count) + (1.0 if success else 0.0)) / new_count
                new_vmaf = ((old_vmaf * old_count) + (vmaf or 0.0)) / new_count if vmaf else old_vmaf
                new_reviewer = ((old_reviewer * old_count) + (reviewer_score or 0.0)) / new_count if reviewer_score else old_reviewer
                conn.execute("""UPDATE edit_patterns SET success_rate=?, avg_vmaf=?, avg_reviewer_score=?, sample_count=?, last_used=?, last_run_id=? WHERE pattern_key=?""",
                             (new_rate, new_vmaf, new_reviewer, new_count, now, run_id, key))
            else:
                conn.execute("""INSERT INTO edit_patterns (pattern_key, content_type, technique, params_canonical, success_rate, avg_vmaf, avg_reviewer_score, sample_count, last_used, last_run_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                             (key, content_type, technique, canonical,
                              1.0 if success else 0.0, vmaf or 0.0, reviewer_score or 0.0, 1, now, run_id))
            conn.commit()

    def get_memory_hints(self, content_type: str, top_n: int = 5) -> list[dict]:
        patterns = self.query(content_type, min_sample_count=3)
        hints: list[dict] = []
        for p in patterns[:top_n]:
            hints.append({
                "technique": p.technique, "params": p.params,
                "success_rate": round(p.success_rate, 3),
                "sample_count": p.sample_count,
                "avg_vmaf": round(p.avg_vmaf, 1) if p.avg_vmaf else None,
                "avg_reviewer_score": round(p.avg_reviewer_score, 3) if p.avg_reviewer_score else None,
                "recommendation": "use these params — historically successful" if p.success_rate > 0.7
                                 else "avoid these params — historically unsuccessful" if p.success_rate < 0.4
                                 else "neutral — mixed results",
            })
        return hints

    def stats(self) -> dict:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM edit_patterns")
            total = cursor.fetchone()[0]
            cursor = conn.execute("SELECT content_type, COUNT(*) FROM edit_patterns GROUP BY content_type")
            by_type = {r[0]: r[1] for r in cursor.fetchall()}
        return {"total_patterns": total, "by_content_type": by_type}
