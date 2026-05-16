"""
Coding-room HTTP routes for the monolith.

Path prefix: /api/v1/coding/*

Endpoints:
  GET    /problems
  GET    /problems/{id}
  POST   /run
  POST   /submit
  GET    /submissions/{id}

Admin endpoints:
  POST   /admin/problems              create problem + test cases
  PUT    /admin/problems/{id}         update problem (and replace test cases if provided)
  DELETE /admin/problems/{id}         soft-delete problem
  GET    /admin/problems/{id}         full problem incl. hidden test cases
  GET    /admin/submissions           list submissions for review
  GET    /admin/submissions/{id}      full submission detail
  POST   /admin/submissions/{id}/review  override score / leave feedback
"""

from __future__ import annotations

import json
import logging

from flask import Blueprint, jsonify, request

from backend.coding.sandbox import run_code
from backend.db.engine import get_connection
from backend.utils.auth import token_required

logger = logging.getLogger(__name__)

coding_bp = Blueprint("coding", __name__, url_prefix="/api/v1/coding")


def _row_to_dict(row):
    if row is None:
        return None
    if isinstance(row, dict):
        return row
    try:
        return dict(row)
    except Exception:  # noqa: BLE001
        return row


# ------------------------------------------------------------------ #
# GET /problems  — list all active problems
# ------------------------------------------------------------------ #
@coding_bp.route("/problems", methods=["GET"])
@token_required
def list_problems(user_id, user_role):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, title, difficulty, tags FROM coding_problems "
            "WHERE is_active = TRUE ORDER BY id"
        )
        rows = cur.fetchall()
        problems = []
        for r in rows:
            d = _row_to_dict(r)
            problems.append(
                {
                    "id": d["id"],
                    "title": d["title"],
                    "difficulty": d["difficulty"],
                    "tags": json.loads(d.get("tags") or "[]"),
                }
            )
        return jsonify(problems), 200
    finally:
        conn.close()


# ------------------------------------------------------------------ #
# GET /problems/{id}  — full problem + sample test cases
# ------------------------------------------------------------------ #
@coding_bp.route("/problems/<int:problem_id>", methods=["GET"])
@token_required
def get_problem(user_id, user_role, problem_id):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, title, description, difficulty, starter_code, constraints, tags, "
            "time_limit_ms, memory_limit_kb FROM coding_problems WHERE id = ?",
            (problem_id,),
        )
        row = cur.fetchone()
        if not row:
            return jsonify({"message": "Problem not found"}), 404
        p = _row_to_dict(row)

        cur.execute(
            "SELECT input_data, expected_output FROM coding_testcases "
            "WHERE problem_id = ? AND is_sample = TRUE ORDER BY order_index",
            (problem_id,),
        )
        samples = [_row_to_dict(r) for r in cur.fetchall()]

        return (
            jsonify(
                {
                    "id": p["id"],
                    "title": p["title"],
                    "description": p["description"],
                    "difficulty": p["difficulty"],
                    "starter_code": json.loads(p.get("starter_code") or "{}"),
                    "constraints": p.get("constraints") or "",
                    "tags": json.loads(p.get("tags") or "[]"),
                    "time_limit_ms": p["time_limit_ms"],
                    "memory_limit_kb": p["memory_limit_kb"],
                    "sample_cases": [
                        {
                            "input": s["input_data"],
                            "expected_output": s["expected_output"],
                        }
                        for s in samples
                    ],
                }
            ),
            200,
        )
    finally:
        conn.close()


# ------------------------------------------------------------------ #
# POST /run  — run code (no grading, sample/custom input)
# ------------------------------------------------------------------ #
@coding_bp.route("/run", methods=["POST"])
@token_required
def run_endpoint(user_id, user_role):
    data = request.get_json(silent=True) or {}
    problem_id = data.get("problem_id")
    language = (data.get("language") or "python").lower()
    source_code = data.get("source_code") or ""
    custom_input = data.get("custom_input")

    if not source_code.strip():
        return jsonify({"message": "source_code is required"}), 400

    stdin = custom_input
    time_limit = 5.0
    if not custom_input and problem_id:
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT time_limit_ms FROM coding_problems WHERE id = ?",
                (problem_id,),
            )
            row = _row_to_dict(cur.fetchone())
            if row:
                time_limit = max(1.0, (row["time_limit_ms"] or 2000) / 1000.0)

            cur.execute(
                "SELECT input_data FROM coding_testcases "
                "WHERE problem_id = ? AND is_sample = TRUE "
                "ORDER BY order_index LIMIT 1",
                (problem_id,),
            )
            sample = _row_to_dict(cur.fetchone())
            if sample:
                stdin = sample["input_data"]
        finally:
            conn.close()

    result = run_code(
        source_code=source_code,
        language=language,
        stdin=stdin or "",
        expected_output="",
        time_limit=time_limit,
    )
    return (
        jsonify(
            {
                "status": result.status,
                "stdout": result.stdout,
                "stderr": result.stderr or result.compile_output,
                "execution_time_ms": result.time_ms,
                "memory_used_kb": result.memory_kb,
            }
        ),
        200,
    )


# ------------------------------------------------------------------ #
# POST /submit  — grade against all test cases
# ------------------------------------------------------------------ #
@coding_bp.route("/submit", methods=["POST"])
@token_required
def submit_endpoint(user_id, user_role):
    data = request.get_json(silent=True) or {}
    problem_id = data.get("problem_id")
    language = (data.get("language") or "python").lower()
    source_code = data.get("source_code") or ""
    paste_count = int(data.get("paste_count") or 0)
    typing_speed = data.get("typing_speed_wpm")

    if not problem_id or not source_code.strip():
        return jsonify({"message": "problem_id and source_code are required"}), 400

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, time_limit_ms FROM coding_problems WHERE id = ?",
            (problem_id,),
        )
        problem = _row_to_dict(cur.fetchone())
        if not problem:
            return jsonify({"message": "Problem not found"}), 404

        cur.execute(
            "SELECT input_data, expected_output, weight FROM coding_testcases "
            "WHERE problem_id = ? ORDER BY order_index",
            (problem_id,),
        )
        cases = [_row_to_dict(r) for r in cur.fetchall()]
        if not cases:
            return jsonify({"message": "No test cases configured"}), 400

        time_limit = max(1.0, (problem["time_limit_ms"] or 2000) / 1000.0)

        # Insert pending submission
        cur.execute(
            "INSERT INTO coding_submissions "
            "(problem_id, user_id, language, source_code, status, tests_total, "
            "paste_count, typing_speed_wpm) "
            "VALUES (?, ?, ?, ?, 'running', ?, ?, ?)",
            (
                problem_id,
                user_id,
                language,
                source_code,
                len(cases),
                paste_count,
                typing_speed,
            ),
        )
        conn.commit()
        submission_id = getattr(cur, "lastrowid", None)
        if submission_id is None:
            cur.execute("SELECT MAX(id) AS id FROM coding_submissions WHERE user_id = ?", (user_id,))
            submission_id = _row_to_dict(cur.fetchone())["id"]

        passed = 0
        total_weight = sum(c.get("weight") or 1.0 for c in cases)
        weighted = 0.0
        first_fail = {"stdout": "", "stderr": "", "compile_output": ""}
        last_time_ms = 0

        for case in cases:
            res = run_code(
                source_code=source_code,
                language=language,
                stdin=case["input_data"],
                expected_output=case["expected_output"],
                time_limit=time_limit,
            )
            last_time_ms = res.time_ms or last_time_ms
            if res.status == "Accepted":
                passed += 1
                weighted += case.get("weight") or 1.0
            elif not first_fail["stderr"] and not first_fail["compile_output"]:
                first_fail = {
                    "stdout": res.stdout,
                    "stderr": res.stderr,
                    "compile_output": res.compile_output,
                }

        score_pct = (weighted / total_weight * 100.0) if total_weight else 0.0
        final_status = "accepted" if passed == len(cases) else "wrong_answer"

        # AI rubric scoring (best-effort, never raises)
        ai_rubric = None
        ai_score_val = None
        try:
            cur.execute("SELECT description FROM coding_problems WHERE id = ?", (problem_id,))
            desc_row = _row_to_dict(cur.fetchone())
            problem_desc = desc_row.get("description", "") if desc_row else ""
            from backend.coding.ai_scorer import score_code

            ai_rubric = score_code(
                problem_description=problem_desc,
                source_code=source_code,
                language=language,
                tests_passed=passed,
                tests_total=len(cases),
                execution_time_ms=last_time_ms,
            )
            ai_score_val = float(ai_rubric.get("total_score", 0)) if ai_rubric else None
        except Exception as e:
            logger.warning(f"AI scoring step failed (non-fatal): {e}")

        cur.execute(
            "UPDATE coding_submissions "
            "SET status = ?, tests_passed = ?, score = ?, "
            "stdout = ?, stderr = ?, execution_time_ms = ?, "
            "ai_rubric = ?, ai_score = ?, judged_at = NOW() "
            "WHERE id = ?",
            (
                final_status,
                passed,
                round(score_pct, 2),
                first_fail["stdout"],
                first_fail["stderr"] or first_fail["compile_output"],
                last_time_ms,
                json.dumps(ai_rubric) if ai_rubric else None,
                ai_score_val,
                submission_id,
            ),
        )
        conn.commit()

        return (
            jsonify(
                {
                    "submission_id": submission_id,
                    "status": final_status,
                    "tests_passed": passed,
                    "tests_total": len(cases),
                    "score": round(score_pct, 2),
                    "execution_time_ms": last_time_ms,
                    "stdout": first_fail["stdout"],
                    "stderr": first_fail["stderr"] or first_fail["compile_output"],
                    "ai_rubric": ai_rubric,
                    "ai_score": ai_score_val,
                    "message": f"Passed {passed}/{len(cases)} tests ({score_pct:.1f}%)",
                }
            ),
            200,
        )
    except Exception as e:
        logger.exception("submit failed")
        try:
            conn.rollback()
        except Exception:
            pass
        return jsonify({"message": str(e)}), 500
    finally:
        conn.close()


# ------------------------------------------------------------------ #
# GET /submissions/{id}
# ------------------------------------------------------------------ #
@coding_bp.route("/submissions/<int:submission_id>", methods=["GET"])
@token_required
def get_submission(user_id, user_role, submission_id):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, user_id, status, tests_passed, tests_total, score, "
            "stdout, stderr, execution_time_ms, ai_rubric, ai_score "
            "FROM coding_submissions WHERE id = ?",
            (submission_id,),
        )
        row = _row_to_dict(cur.fetchone())
        if not row:
            return jsonify({"message": "Submission not found"}), 404
        if user_role == "student" and row["user_id"] != user_id:
            return jsonify({"message": "Access denied"}), 403

        return (
            jsonify(
                {
                    "submission_id": row["id"],
                    "status": row["status"],
                    "tests_passed": row["tests_passed"],
                    "tests_total": row["tests_total"],
                    "score": row["score"],
                    "stdout": row.get("stdout"),
                    "stderr": row.get("stderr"),
                    "execution_time_ms": row.get("execution_time_ms"),
                    "ai_rubric": (
                        json.loads(row["ai_rubric"]) if row.get("ai_rubric") else None
                    ),
                    "ai_score": row.get("ai_score"),
                }
            ),
            200,
        )
    finally:
        conn.close()


# ================================================================== #
# ADMIN ENDPOINTS
# ================================================================== #


def _require_admin(user_role):
    return user_role in ("admin", "teacher")


# ------------------------------------------------------------------ #
# POST /admin/problems
# ------------------------------------------------------------------ #
@coding_bp.route("/admin/problems", methods=["POST"])
@token_required
def admin_create_problem(user_id, user_role):
    if not _require_admin(user_role):
        return jsonify({"message": "Admin/teacher access required"}), 403

    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    description = (data.get("description") or "").strip()
    if not title or not description:
        return jsonify({"message": "title and description are required"}), 400

    difficulty = data.get("difficulty") or "medium"
    starter_code = data.get("starter_code") or {}
    constraints = data.get("constraints") or ""
    tags = data.get("tags") or []
    time_limit_ms = int(data.get("time_limit_ms") or 2000)
    memory_limit_kb = int(data.get("memory_limit_kb") or 256000)
    test_cases = data.get("test_cases") or []

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO coding_problems "
            "(title, description, difficulty, starter_code, constraints, tags, "
            "time_limit_ms, memory_limit_kb, created_by, is_active) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, TRUE)",
            (
                title,
                description,
                difficulty,
                json.dumps(starter_code) if not isinstance(starter_code, str) else starter_code,
                constraints,
                json.dumps(tags) if not isinstance(tags, str) else tags,
                time_limit_ms,
                memory_limit_kb,
                user_id,
            ),
        )
        conn.commit()
        problem_id = getattr(cur, "lastrowid", None)
        if problem_id is None:
            cur.execute(
                "SELECT MAX(id) AS id FROM coding_problems WHERE created_by = ?",
                (user_id,),
            )
            problem_id = _row_to_dict(cur.fetchone())["id"]

        for i, tc in enumerate(test_cases):
            cur.execute(
                "INSERT INTO coding_testcases "
                "(problem_id, input_data, expected_output, is_sample, weight, order_index) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    problem_id,
                    tc.get("input", ""),
                    tc.get("expected", ""),
                    bool(tc.get("is_sample", False)),
                    float(tc.get("weight", 1.0)),
                    i,
                ),
            )
        conn.commit()

        return (
            jsonify(
                {
                    "problem_id": problem_id,
                    "test_cases": len(test_cases),
                    "message": "Problem created",
                }
            ),
            201,
        )
    except Exception as e:
        logger.exception("admin_create_problem failed")
        try:
            conn.rollback()
        except Exception:
            pass
        return jsonify({"message": str(e)}), 500
    finally:
        conn.close()


# ------------------------------------------------------------------ #
# GET /admin/problems/{id}  — full problem incl. hidden test cases
# ------------------------------------------------------------------ #
@coding_bp.route("/admin/problems/<int:problem_id>", methods=["GET"])
@token_required
def admin_get_problem(user_id, user_role, problem_id):
    if not _require_admin(user_role):
        return jsonify({"message": "Admin/teacher access required"}), 403

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, title, description, difficulty, starter_code, constraints, tags, "
            "time_limit_ms, memory_limit_kb, is_active FROM coding_problems WHERE id = ?",
            (problem_id,),
        )
        row = _row_to_dict(cur.fetchone())
        if not row:
            return jsonify({"message": "Problem not found"}), 404

        cur.execute(
            "SELECT id, input_data, expected_output, is_sample, weight, order_index "
            "FROM coding_testcases WHERE problem_id = ? ORDER BY order_index",
            (problem_id,),
        )
        cases = [_row_to_dict(r) for r in cur.fetchall()]

        return (
            jsonify(
                {
                    "id": row["id"],
                    "title": row["title"],
                    "description": row["description"],
                    "difficulty": row["difficulty"],
                    "starter_code": json.loads(row.get("starter_code") or "{}"),
                    "constraints": row.get("constraints") or "",
                    "tags": json.loads(row.get("tags") or "[]"),
                    "time_limit_ms": row["time_limit_ms"],
                    "memory_limit_kb": row["memory_limit_kb"],
                    "is_active": row.get("is_active", True),
                    "test_cases": [
                        {
                            "id": c["id"],
                            "input": c["input_data"],
                            "expected": c["expected_output"],
                            "is_sample": bool(c["is_sample"]),
                            "weight": c.get("weight") or 1.0,
                        }
                        for c in cases
                    ],
                }
            ),
            200,
        )
    finally:
        conn.close()


# ------------------------------------------------------------------ #
# PUT /admin/problems/{id}
# ------------------------------------------------------------------ #
@coding_bp.route("/admin/problems/<int:problem_id>", methods=["PUT"])
@token_required
def admin_update_problem(user_id, user_role, problem_id):
    if not _require_admin(user_role):
        return jsonify({"message": "Admin/teacher access required"}), 403

    data = request.get_json(silent=True) or {}
    fields = []
    params = []
    mapping = {
        "title": "title",
        "description": "description",
        "difficulty": "difficulty",
        "constraints": "constraints",
        "time_limit_ms": "time_limit_ms",
        "memory_limit_kb": "memory_limit_kb",
        "is_active": "is_active",
    }
    for k, col in mapping.items():
        if k in data:
            fields.append(f"{col} = ?")
            params.append(data[k])

    if "starter_code" in data:
        fields.append("starter_code = ?")
        sc = data["starter_code"]
        params.append(json.dumps(sc) if not isinstance(sc, str) else sc)
    if "tags" in data:
        fields.append("tags = ?")
        tg = data["tags"]
        params.append(json.dumps(tg) if not isinstance(tg, str) else tg)

    conn = get_connection()
    try:
        cur = conn.cursor()
        if fields:
            params.append(problem_id)
            cur.execute(
                f"UPDATE coding_problems SET {', '.join(fields)} WHERE id = ?",
                tuple(params),
            )

        # Replace test cases if provided
        if "test_cases" in data:
            cur.execute(
                "DELETE FROM coding_testcases WHERE problem_id = ?",
                (problem_id,),
            )
            for i, tc in enumerate(data["test_cases"]):
                cur.execute(
                    "INSERT INTO coding_testcases "
                    "(problem_id, input_data, expected_output, is_sample, weight, order_index) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        problem_id,
                        tc.get("input", ""),
                        tc.get("expected", ""),
                        bool(tc.get("is_sample", False)),
                        float(tc.get("weight", 1.0)),
                        i,
                    ),
                )
        conn.commit()
        return jsonify({"message": "Problem updated", "problem_id": problem_id}), 200
    except Exception as e:
        logger.exception("admin_update_problem failed")
        try:
            conn.rollback()
        except Exception:
            pass
        return jsonify({"message": str(e)}), 500
    finally:
        conn.close()


# ------------------------------------------------------------------ #
# DELETE /admin/problems/{id}  — soft delete (is_active = FALSE)
# ------------------------------------------------------------------ #
@coding_bp.route("/admin/problems/<int:problem_id>", methods=["DELETE"])
@token_required
def admin_delete_problem(user_id, user_role, problem_id):
    if not _require_admin(user_role):
        return jsonify({"message": "Admin/teacher access required"}), 403

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE coding_problems SET is_active = FALSE WHERE id = ?",
            (problem_id,),
        )
        conn.commit()
        return jsonify({"message": "Problem archived", "problem_id": problem_id}), 200
    finally:
        conn.close()


# ------------------------------------------------------------------ #
# GET /admin/submissions
# ------------------------------------------------------------------ #
@coding_bp.route("/admin/submissions", methods=["GET"])
@token_required
def admin_list_submissions(user_id, user_role):
    if not _require_admin(user_role):
        return jsonify({"message": "Admin/teacher access required"}), 403

    reviewed_param = (request.args.get("reviewed") or "").lower()
    problem_id = request.args.get("problem_id")
    limit = int(request.args.get("limit") or 50)

    conn = get_connection()
    try:
        cur = conn.cursor()
        clauses = []
        params = []
        if reviewed_param in ("true", "1", "yes"):
            clauses.append("s.admin_reviewed = TRUE")
        elif reviewed_param in ("false", "0", "no"):
            clauses.append("s.admin_reviewed = FALSE")
        if problem_id:
            clauses.append("s.problem_id = ?")
            params.append(int(problem_id))
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        params.append(limit)

        cur.execute(
            f"SELECT s.id, s.problem_id, s.user_id, s.language, s.status, "
            f"s.tests_passed, s.tests_total, s.score, s.ai_score, s.ai_rubric, "
            f"s.paste_count, s.typing_speed_wpm, s.submitted_at, "
            f"s.admin_reviewed, s.admin_score, "
            f"u.username, p.title AS problem_title "
            f"FROM coding_submissions s "
            f"LEFT JOIN users u ON u.id = s.user_id "
            f"LEFT JOIN coding_problems p ON p.id = s.problem_id "
            f"{where} "
            f"ORDER BY s.submitted_at DESC LIMIT ?",
            tuple(params),
        )
        rows = cur.fetchall()
        out = []
        for r in rows:
            d = _row_to_dict(r)
            out.append(
                {
                    "id": d["id"],
                    "problem_id": d["problem_id"],
                    "problem_title": d.get("problem_title"),
                    "user_id": d["user_id"],
                    "username": d.get("username"),
                    "language": d["language"],
                    "status": d["status"],
                    "tests_passed": d["tests_passed"],
                    "tests_total": d["tests_total"],
                    "score": d["score"],
                    "ai_score": d.get("ai_score"),
                    "ai_rubric": (
                        json.loads(d["ai_rubric"]) if d.get("ai_rubric") else None
                    ),
                    "paste_count": d.get("paste_count") or 0,
                    "typing_speed_wpm": d.get("typing_speed_wpm"),
                    "submitted_at": str(d.get("submitted_at")) if d.get("submitted_at") else None,
                    "admin_reviewed": bool(d.get("admin_reviewed")),
                    "admin_score": d.get("admin_score"),
                }
            )
        return jsonify(out), 200
    finally:
        conn.close()


# ------------------------------------------------------------------ #
# GET /admin/submissions/{id}
# ------------------------------------------------------------------ #
@coding_bp.route("/admin/submissions/<int:submission_id>", methods=["GET"])
@token_required
def admin_get_submission(user_id, user_role, submission_id):
    if not _require_admin(user_role):
        return jsonify({"message": "Admin/teacher access required"}), 403

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT s.*, u.username, p.title AS problem_title, p.description AS problem_description "
            "FROM coding_submissions s "
            "LEFT JOIN users u ON u.id = s.user_id "
            "LEFT JOIN coding_problems p ON p.id = s.problem_id "
            "WHERE s.id = ?",
            (submission_id,),
        )
        row = _row_to_dict(cur.fetchone())
        if not row:
            return jsonify({"message": "Submission not found"}), 404

        return (
            jsonify(
                {
                    "id": row["id"],
                    "problem": {
                        "id": row.get("problem_id"),
                        "title": row.get("problem_title"),
                        "description": row.get("problem_description"),
                    },
                    "user_id": row["user_id"],
                    "username": row.get("username"),
                    "language": row["language"],
                    "source_code": row.get("source_code"),
                    "status": row["status"],
                    "tests_passed": row["tests_passed"],
                    "tests_total": row["tests_total"],
                    "score": row["score"],
                    "ai_score": row.get("ai_score"),
                    "ai_rubric": (
                        json.loads(row["ai_rubric"]) if row.get("ai_rubric") else None
                    ),
                    "stdout": row.get("stdout"),
                    "stderr": row.get("stderr"),
                    "execution_time_ms": row.get("execution_time_ms"),
                    "memory_used_kb": row.get("memory_used_kb"),
                    "paste_count": row.get("paste_count") or 0,
                    "typing_speed_wpm": row.get("typing_speed_wpm"),
                    "submitted_at": str(row.get("submitted_at")) if row.get("submitted_at") else None,
                    "admin_reviewed": bool(row.get("admin_reviewed")),
                    "admin_score": row.get("admin_score"),
                    "admin_feedback": row.get("admin_feedback"),
                }
            ),
            200,
        )
    finally:
        conn.close()


# ------------------------------------------------------------------ #
# POST /admin/submissions/{id}/review
# ------------------------------------------------------------------ #
@coding_bp.route("/admin/submissions/<int:submission_id>/review", methods=["POST"])
@token_required
def admin_review_submission(user_id, user_role, submission_id):
    if not _require_admin(user_role):
        return jsonify({"message": "Admin/teacher access required"}), 403

    data = request.get_json(silent=True) or {}
    score_override = data.get("score")  # may be None -> accept AI score
    feedback = data.get("feedback") or ""

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT ai_score, score FROM coding_submissions WHERE id = ?",
            (submission_id,),
        )
        row = _row_to_dict(cur.fetchone())
        if not row:
            return jsonify({"message": "Submission not found"}), 404

        final_score = (
            float(score_override)
            if score_override is not None
            else (row.get("ai_score") if row.get("ai_score") is not None else row.get("score"))
        )

        cur.execute(
            "UPDATE coding_submissions "
            "SET admin_reviewed = TRUE, admin_score = ?, admin_feedback = ?, "
            "reviewed_by = ?, reviewed_at = NOW() "
            "WHERE id = ?",
            (final_score, feedback, user_id, submission_id),
        )
        conn.commit()
        return (
            jsonify(
                {
                    "message": "Submission reviewed",
                    "submission_id": submission_id,
                    "final_score": final_score,
                }
            ),
            200,
        )
    finally:
        conn.close()
