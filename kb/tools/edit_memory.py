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

            # S2: Composite patterns table — multi-step named techniques (e.g., reverse_into_drop)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS composite_patterns (
                    name TEXT PRIMARY KEY,
                    content_type TEXT,
                    triggers TEXT,
                    steps_json TEXT,
                    constraints_json TEXT,
                    confidence TEXT DEFAULT 'unverified',
                    success_count INTEGER DEFAULT 0,
                    fail_count INTEGER DEFAULT 0,
                    last_used TEXT,
                    created TEXT
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_composite_content_type ON composite_patterns(content_type)")
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
            cursor = conn.execute("SELECT COUNT(*) FROM composite_patterns")
            composite_total = cursor.fetchone()[0]
        return {"total_patterns": total, "by_content_type": by_type,
                "composite_patterns": composite_total}

    # ── S2: Composite pattern methods ──

    def add_composite_pattern(self, name: str, content_type: str, triggers: list[str],
                              steps: list[dict], constraints: dict,
                              confidence: str = "unverified") -> None:
        """Add or update a composite (multi-step) editing pattern."""
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO composite_patterns
                (name, content_type, triggers, steps_json, constraints_json, confidence, created)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (name, content_type, json.dumps(triggers), json.dumps(steps),
                  json.dumps(constraints), confidence, now))
            conn.commit()

    def query_composite_patterns(self, content_type: str,
                                  triggers: t.Optional[list[str]] = None,
                                  confidence_min: str = "unverified") -> list[dict]:
        """Find composite patterns matching content_type and optionally triggers."""
        confidence_order = {"unverified": 0, "testing": 1, "verified": 2}
        min_conf = confidence_order.get(confidence_min, 0)
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM composite_patterns WHERE content_type=? OR content_type='*'",
                (content_type,))
            rows = cursor.fetchall()

        results = []
        for r in rows:
            conf = r["confidence"] or "unverified"
            if confidence_order.get(conf, 0) < min_conf:
                continue
            pattern_triggers = json.loads(r["triggers"] or "[]")
            if triggers and not any(t in pattern_triggers for t in triggers):
                continue
            results.append({
                "name": r["name"],
                "content_type": r["content_type"],
                "triggers": pattern_triggers,
                "steps": json.loads(r["steps_json"] or "[]"),
                "constraints": json.loads(r["constraints_json"] or "{}"),
                "confidence": conf,
                "success_count": r["success_count"],
                "fail_count": r["fail_count"],
            })
        return results

    def record_composite_outcome(self, name: str, success: bool) -> None:
        """Record success/failure of a composite pattern. Promotes confidence after N successes."""
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        with sqlite3.connect(self.db_path) as conn:
            if success:
                conn.execute("""
                    UPDATE composite_patterns SET success_count=success_count+1, last_used=?
                    WHERE name=?
                """, (now, name))
            else:
                conn.execute("""
                    UPDATE composite_patterns SET fail_count=fail_count+1, last_used=?
                    WHERE name=?
                """, (now, name))
            # Promote confidence after 3+ successes with >70% rate
            cursor = conn.execute(
                "SELECT success_count, fail_count FROM composite_patterns WHERE name=?", (name,))
            row = cursor.fetchone()
            if row:
                sc, fc = row
                total = sc + fc
                if total >= 3 and sc / total >= 0.7 and sc >= 3:
                    conn.execute("UPDATE composite_patterns SET confidence='verified' WHERE name=?", (name,))
            conn.commit()

    def seed_builtin_patterns(self) -> None:
        """Seed built-in composite patterns (the 'signature move' library)."""
        builtin = [
            {
                "name": "reverse_into_drop",
                "content_type": "*",
                "triggers": ["beat_drop_detected", "has_forward_action_clip"],
                "steps": [
                    {"operation": "reverse", "tool": "edit.reverse", "params": {"duration": "0.6-1.2s pre-drop"}},
                    {"operation": "hold_frame", "tool": "edit.trim", "params": {"duration": "0.1-0.2s at drop onset"}},
                    {"operation": "resume_forward", "tool": "edit.speed", "params": {"factor": 1.0, "start": "drop_timestamp"}},
                    {"operation": "music_gate", "tool": "edit.add_audio", "params": {"mode": "duck_until_drop"}},
                ],
                "constraints": {
                    "drop_timestamp": "from music_sync.detect_structure() downbeat/onset spike",
                    "source_clip": "must have detectable forward motion (probe_visual motion_energy > 0.3)",
                },
                "confidence": "unverified",
            },
            {
                "name": "whip_pan_cut",
                "content_type": "*",
                "triggers": ["high_motion_peak", "scene_boundary"],
                "steps": [
                    {"operation": "speed_ramp_up", "tool": "edit.speed", "params": {"factor": 3.0, "duration": "0.15s"}},
                    {"operation": "cut", "tool": "edit.trim", "params": {"accurate": True}},
                    {"operation": "speed_ramp_down", "tool": "edit.speed", "params": {"factor": 0.5, "duration": "0.1s"}},
                ],
                "constraints": {
                    "motion_peak": "sigma >= 2.5 at cut point",
                    "scene_boundary": "cut must align with detected scene boundary",
                },
                "confidence": "unverified",
            },
            {
                "name": "zoom_punch",
                "content_type": "*",
                "triggers": ["hero_moment", "semantic_salience_peak"],
                "steps": [
                    {"operation": "crop_zoom", "tool": "edit.crop", "params": {"zoom": "1.3x centered on face/subject"}},
                    {"operation": "hold", "tool": "edit.trim", "params": {"duration": "0.3-0.5s"}},
                    {"operation": "zoom_out", "tool": "edit.crop", "params": {"zoom": "1.0x (return to full frame)"}},
                ],
                "constraints": {
                    "hero_moment": "level >= 2 from hero_detector",
                    "duration": "total zoom_punch <= 0.8s",
                },
                "confidence": "unverified",
            },
        ]
        for p in builtin:
            self.add_composite_pattern(
                p["name"], p["content_type"], p["triggers"],
                p["steps"], p["constraints"], p["confidence"]
            )
