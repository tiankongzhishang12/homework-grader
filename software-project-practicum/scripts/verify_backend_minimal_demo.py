from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from decimal import Decimal
from http.cookiejar import CookieJar
from pathlib import Path


DEMO = {
    "school_code": "DEMO_SCHOOL",
    "school_name": "Demo School",
    "class_code": "DEMO_CLASS",
    "class_name": "Demo Class",
    "teacher_no": "DEMO_TEACHER",
    "teacher_name": "Demo Teacher",
    "student_no": "DEMO_STUDENT_001",
    "student_name": "Demo Student",
    "course_code": "DEMO_COURSE",
    "course_name": "Demo Course",
    "assessment_title": "DEMO_ASSESSMENT_MINIMAL_GRADING",
    "submission_source_id": "DEMO_SUBMISSION_001",
}


SCORE_PAYLOAD = {
    "student_id": "anon-001",
    "rubric_id": "DEMO_RUBRIC_V1",
    "raw_total_score": 88.0,
    "max_total_score": 100.0,
    "percentile_score": 88,
    "grade": "accept",
    "overall_confidence": 0.91,
    "review_flag": "none",
    "dimension_scores": [
        {
            "criterion_id": "demo-correctness",
            "criterion_name": "Correctness",
            "score": 45.0,
            "max_score": 50.0,
            "confidence": 0.93,
            "evidence": "Demo answer covers the expected core requirements.",
            "reasoning": "The response satisfies the key correctness checks.",
            "improvement": "Keep the reasoning concise and evidence-based.",
        },
        {
            "criterion_id": "demo-traceability",
            "criterion_name": "Traceability",
            "score": 43.0,
            "max_score": 50.0,
            "confidence": 0.89,
            "evidence": "Demo answer links requirements to implementation notes.",
            "reasoning": "Traceability is mostly complete for the minimal demo.",
            "improvement": "Add more explicit artifact references in real submissions.",
        },
    ],
    "comment": {
        "strengths": "Demo grading import path is exercised.",
        "weaknesses": "This is synthetic data only.",
        "suggestions": "Use real workspace data after this smoke test passes.",
        "full_text": "Synthetic demo result for backend minimal grading verification.",
    },
    "traceability_analysis": {
        "extracted_requirements": ["demo requirement"],
        "hld_coverage": [],
        "lld_coverage": [],
        "consistency_issues": [],
        "uncovered_requirements": [],
    },
    "metadata": {
        "model_name": "VERIFY_BACKEND_MINIMAL_DEMO",
        "source": "verify_backend_minimal_demo.py",
    },
}


class StepResult:
    def __init__(self, name: str, ok: bool, detail: str):
        self.name = name
        self.ok = ok
        self.detail = detail


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify the Homework Grader backend minimal grading demo with DEMO_* data."
    )
    parser.add_argument("--apply", action="store_true", help="Actually write DEMO_* data, workspace files, and call backend APIs.")
    parser.add_argument("--base-url", default=os.environ.get("HOMEWORK_GRADER_BASE_URL", "http://localhost:8080"))
    parser.add_argument("--db-host", default=os.environ.get("HOMEWORK_GRADER_DB_HOST", "localhost"))
    parser.add_argument("--db-port", type=int, default=int(os.environ.get("HOMEWORK_GRADER_DB_PORT", "3306")))
    parser.add_argument("--db-name", default=os.environ.get("HOMEWORK_GRADER_DB_NAME", "homework_grader"))
    parser.add_argument("--db-user", default=os.environ.get("HOMEWORK_GRADER_DB_USER", "root"))
    parser.add_argument("--db-password", default=os.environ.get("HOMEWORK_GRADER_DB_PASSWORD", ""))
    parser.add_argument("--mysql-client", default=os.environ.get("HOMEWORK_GRADER_MYSQL_CLIENT"), help="Optional path to mysql client executable.")
    parser.add_argument("--workspace", default=os.environ.get("HOMEWORK_GRADER_WORKSPACE", "software-project-practicum/workspace/practicum-batch"))
    parser.add_argument("--report", default="docs/handoff/backend-minimal-demo-manual-test-record.md")
    parser.add_argument("--api-username", default=os.environ.get("HOMEWORK_GRADER_API_USERNAME"))
    parser.add_argument("--api-password", default=os.environ.get("HOMEWORK_GRADER_API_PASSWORD"))
    parser.add_argument("--poll-interval", type=float, default=1.0)
    parser.add_argument("--max-polls", type=int, default=30)
    return parser.parse_args()


def import_mysql_driver():
    try:
        import pymysql  # type: ignore

        return "pymysql", pymysql
    except ImportError:
        pass
    try:
        import mysql.connector  # type: ignore

        return "mysql.connector", mysql.connector
    except ImportError:
        return None, None


def connect_db(args: argparse.Namespace):
    driver_name, driver = import_mysql_driver()
    if driver is None:
        return MysqlCliConnection(args)
    if driver_name == "pymysql":
        return driver.connect(
            host=args.db_host,
            port=args.db_port,
            user=args.db_user,
            password=args.db_password,
            database=args.db_name,
            charset="utf8mb4",
            autocommit=False,
            cursorclass=driver.cursors.DictCursor,
        )
    return driver.connect(
        host=args.db_host,
        port=args.db_port,
        user=args.db_user,
        password=args.db_password,
        database=args.db_name,
        autocommit=False,
    )


class MysqlCliConnection:
    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.client = args.mysql_client or shutil.which("mysql")
        if not self.client:
            default_windows_client = r"C:\Program Files\MySQL\MySQL Server 9.3\bin\mysql.exe"
            if Path(default_windows_client).exists():
                self.client = default_windows_client
        if not self.client:
            raise RuntimeError(
                "No MySQL Python driver or mysql client found. Install 'pymysql'/'mysql-connector-python', "
                "add mysql to PATH, or pass --mysql-client."
            )

    def cursor(self):
        return MysqlCliCursor(self)

    def commit(self):
        return None

    def close(self):
        return None

    def run_sql(self, sql: str):
        command = [
            self.client,
            "--protocol=tcp",
            "-h",
            self.args.db_host,
            "-P",
            str(self.args.db_port),
            "-u",
            self.args.db_user,
            "--default-character-set=utf8mb4",
            "--batch",
            "--raw",
            self.args.db_name,
            "-e",
            sql,
        ]
        if self.args.db_password:
            command.insert(8, "--password=" + self.args.db_password)
        completed = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if completed.returncode != 0:
            raise RuntimeError((completed.stderr or completed.stdout).strip())
        return completed.stdout


class MysqlCliCursor:
    def __init__(self, connection: MysqlCliConnection):
        self.connection = connection
        self.description = None
        self._rows = []
        self.lastrowid = 0

    def execute(self, sql: str, params=()):
        formatted = format_sql(sql, params)
        wants_rows = formatted.lstrip().lower().startswith("select")
        if wants_rows:
            stdout = self.connection.run_sql(formatted)
            self._rows, self.description = parse_mysql_batch(stdout)
        else:
            stdout = self.connection.run_sql(formatted + "; select last_insert_id() as id")
            rows, description = parse_mysql_batch(stdout)
            self.description = description
            self._rows = rows
            self.lastrowid = int(rows[-1][0]) if rows else 0

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def fetchall(self):
        return self._rows

    def close(self):
        return None


def parse_mysql_batch(stdout: str):
    lines = [line for line in stdout.splitlines() if line.strip()]
    if not lines:
        return [], []
    headers = lines[0].split("\t")
    rows = []
    for line in lines[1:]:
        values = [None if value == "NULL" else value for value in line.split("\t")]
        rows.append(tuple(values))
    return rows, [(header,) for header in headers]


def format_sql(sql: str, params=()):
    formatted = sql
    for value in params:
        formatted = formatted.replace("%s", sql_literal(value), 1)
    return formatted


def sql_literal(value):
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (int, float, Decimal)):
        return str(value)
    text = str(value).replace("\\", "\\\\").replace("'", "''")
    return "'" + text + "'"


def fetch_one(conn, sql: str, params=()):
    cursor = conn.cursor()
    try:
        cursor.execute(sql, params)
        row = cursor.fetchone()
        if row is None:
            return None
        if isinstance(row, dict):
            return row
        columns = [desc[0] for desc in cursor.description]
        return dict(zip(columns, row))
    finally:
        cursor.close()


def fetch_all(conn, sql: str, params=()):
    cursor = conn.cursor()
    try:
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        if not rows:
            return []
        if isinstance(rows[0], dict):
            return list(rows)
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in rows]
    finally:
        cursor.close()


def execute(conn, sql: str, params=()):
    cursor = conn.cursor()
    try:
        cursor.execute(sql, params)
        return cursor.lastrowid
    finally:
        cursor.close()


def ensure_row(conn, table: str, key_column: str, key_value, insert_values: dict):
    row = fetch_one(conn, f"select id from {table} where {key_column} = %s limit 1", (key_value,))
    if row:
        return int(row["id"]), False
    columns = list(insert_values.keys())
    placeholders = ", ".join(["%s"] * len(columns))
    column_sql = ", ".join(columns)
    values = [insert_values[column] for column in columns]
    row_id = execute(conn, f"insert into {table} ({column_sql}) values ({placeholders})", values)
    return int(row_id), True


def ensure_demo_data(conn):
    created = []

    school_id, made = ensure_row(
        conn,
        "organization_unit",
        "unit_code",
        DEMO["school_code"],
        {
            "parent_id": None,
            "unit_code": DEMO["school_code"],
            "unit_name": DEMO["school_name"],
            "unit_type": "SCHOOL",
            "grade_year": None,
            "sort_order": 0,
            "status": 1,
        },
    )
    if made:
        created.append("organization_unit:DEMO_SCHOOL")

    class_row = fetch_one(
        conn,
        "select id from organization_unit where parent_id = %s and unit_code = %s limit 1",
        (school_id, DEMO["class_code"]),
    )
    if class_row:
        class_org_id = int(class_row["id"])
    else:
        class_org_id = int(
            execute(
                conn,
                "insert into organization_unit (parent_id, unit_code, unit_name, unit_type, grade_year, sort_order, status) "
                "values (%s, %s, %s, %s, %s, %s, %s)",
                (school_id, DEMO["class_code"], DEMO["class_name"], "CLASS", 2026, 1, 1),
            )
        )
        created.append("organization_unit:DEMO_CLASS")

    teacher_id, made = ensure_row(
        conn,
        "teacher",
        "teacher_no",
        DEMO["teacher_no"],
        {
            "org_unit_id": school_id,
            "teacher_no": DEMO["teacher_no"],
            "teacher_name": DEMO["teacher_name"],
            "phone": None,
            "email": "demo-teacher@example.invalid",
            "status": 1,
        },
    )
    if made:
        created.append("teacher:DEMO_TEACHER")

    student_id, made = ensure_row(
        conn,
        "student",
        "student_no",
        DEMO["student_no"],
        {
            "class_org_id": class_org_id,
            "student_no": DEMO["student_no"],
            "student_name": DEMO["student_name"],
            "gender": None,
            "enrollment_year": 2026,
            "status": 1,
        },
    )
    if made:
        created.append("student:DEMO_STUDENT_001")

    course_id, made = ensure_row(
        conn,
        "course",
        "course_code",
        DEMO["course_code"],
        {
            "course_code": DEMO["course_code"],
            "course_name": DEMO["course_name"],
            "credit": Decimal("1.0"),
            "course_type": "DEMO",
            "status": 1,
        },
    )
    if made:
        created.append("course:DEMO_COURSE")

    offering = fetch_one(
        conn,
        "select id from course_offering where course_id = %s and org_unit_id = %s and academic_year = %s and term = %s and offering_name = %s limit 1",
        (course_id, school_id, "2026", "demo", "Demo Offering"),
    )
    if offering:
        course_offering_id = int(offering["id"])
    else:
        course_offering_id = int(
            execute(
                conn,
                "insert into course_offering (course_id, org_unit_id, academic_year, term, offering_name, status) "
                "values (%s, %s, %s, %s, %s, %s)",
                (course_id, school_id, "2026", "demo", "Demo Offering", 1),
            )
        )
        created.append("course_offering:Demo Offering")

    teaching_class = fetch_one(
        conn,
        "select id from teaching_class where course_offering_id = %s and class_code = %s limit 1",
        (course_offering_id, DEMO["class_code"]),
    )
    if teaching_class:
        teaching_class_id = int(teaching_class["id"])
    else:
        teaching_class_id = int(
            execute(
                conn,
                "insert into teaching_class (course_offering_id, class_code, class_name, status) values (%s, %s, %s, %s)",
                (course_offering_id, DEMO["class_code"], DEMO["class_name"], 1),
            )
        )
        created.append("teaching_class:DEMO_CLASS")

    ensure_join(
        conn,
        "course_offering_teacher",
        "course_offering_id = %s and teacher_id = %s and role = %s",
        (course_offering_id, teacher_id, "OWNER"),
        {
            "course_offering_id": course_offering_id,
            "teacher_id": teacher_id,
            "role": "OWNER",
            "status": 1,
        },
        created,
        "course_offering_teacher:DEMO_TEACHER",
    )
    ensure_join(
        conn,
        "teaching_class_student",
        "teaching_class_id = %s and student_id = %s",
        (teaching_class_id, student_id),
        {
            "teaching_class_id": teaching_class_id,
            "student_id": student_id,
            "join_status": "ACTIVE",
        },
        created,
        "teaching_class_student:DEMO_STUDENT_001",
    )

    assessment = fetch_one(
        conn,
        "select id from assessment where course_offering_id = %s and title = %s limit 1",
        (course_offering_id, DEMO["assessment_title"]),
    )
    if assessment:
        assessment_id = int(assessment["id"])
    else:
        assessment_id = int(
            execute(
                conn,
                "insert into assessment (course_offering_id, title, assessment_type, submission_format, grading_mode, total_score, weight, allow_resubmit, status) "
                "values (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (course_offering_id, DEMO["assessment_title"], "HOMEWORK", "FILE", "AI", Decimal("100.00"), Decimal("1.00"), 1, 1),
            )
        )
        created.append("assessment:DEMO_ASSESSMENT_MINIMAL_GRADING")

    submission = fetch_one(
        conn,
        "select id from submission where assessment_id = %s and student_id = %s and source_submission_id = %s limit 1",
        (assessment_id, student_id, DEMO["submission_source_id"]),
    )
    if submission:
        submission_id = int(submission["id"])
    else:
        submission_id = int(
            execute(
                conn,
                "insert into submission (assessment_id, student_id, attempt_no, submit_status, submitted_at, is_late, source_platform, source_submission_id, status) "
                "values (%s, %s, %s, %s, now(), %s, %s, %s, %s)",
                (assessment_id, student_id, 1, "UPLOADED", 0, "VERIFY_SCRIPT", DEMO["submission_source_id"], 1),
            )
        )
        created.append("submission:DEMO_SUBMISSION_001")

    conn.commit()
    return {
        "schoolId": school_id,
        "classOrgId": class_org_id,
        "teacherId": teacher_id,
        "studentId": student_id,
        "courseId": course_id,
        "courseOfferingId": course_offering_id,
        "teachingClassId": teaching_class_id,
        "assessmentId": assessment_id,
        "submissionId": submission_id,
        "created": created,
    }


def ensure_join(conn, table: str, where_sql: str, where_params: tuple, values: dict, created: list, label: str):
    row = fetch_one(conn, f"select id from {table} where {where_sql} limit 1", where_params)
    if row:
        return int(row["id"])
    columns = list(values.keys())
    row_id = execute(
        conn,
        f"insert into {table} ({', '.join(columns)}) values ({', '.join(['%s'] * len(columns))})",
        [values[column] for column in columns],
    )
    created.append(label)
    return int(row_id)


def prepare_workspace(workspace: Path):
    scores_dir = workspace / "scores"
    scores_dir.mkdir(parents=True, exist_ok=True)
    mapping_path = workspace / "student-mapping.csv"
    score_path = scores_dir / "anon-001.json"
    mapping_path.write_text("anon_id,student_number,name\nanon-001,DEMO_STUDENT_001,Demo Student\n", encoding="utf-8")
    score_path.write_text(json.dumps(SCORE_PAYLOAD, ensure_ascii=False, indent=2), encoding="utf-8")
    return mapping_path, score_path


class ApiClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        cookie_jar = CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))

    def request(self, method: str, path: str, body=None):
        data = None
        headers = {"Accept": "application/json"}
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(self.base_url + path, data=data, headers=headers, method=method)
        try:
            with self.opener.open(request, timeout=15) as response:
                raw = response.read().decode("utf-8")
                return response.status, json.loads(raw) if raw else None
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                payload = raw
            return exc.code, payload
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Backend service is not reachable at {self.base_url}: {exc}") from exc

    def login(self, username: str, password: str):
        return self.request("POST", "/api/auth/login", {"username": username, "password": password})


def check_backend_reachable(base_url: str):
    client = ApiClient(base_url)
    status, payload = client.request("GET", "/api/auth/me")
    if status in (200, 401):
        return StepResult("backend reachable", True, f"HTTP {status}: {payload}")
    return StepResult("backend reachable", False, f"HTTP {status}: {payload}")


def unwrap_api(payload):
    if isinstance(payload, dict) and "data" in payload:
        return payload.get("data")
    return payload


def run_api_flow(args: argparse.Namespace, ids: dict):
    client = ApiClient(args.base_url)
    results = []
    if args.api_username and args.api_password:
        status, payload = client.login(args.api_username, args.api_password)
        results.append(StepResult("api login", status == 200, f"HTTP {status}: {payload}"))
        if status != 200:
            return results, None, None, None

    start_status, start_payload = client.request("POST", f"/api/assessments/{ids['assessmentId']}/grading/start")
    results.append(StepResult("POST grading/start", start_status == 200, f"HTTP {start_status}: {start_payload}"))
    if start_status != 200:
        return results, None, None, None

    progress_data = None
    for _ in range(args.max_polls):
        status, payload = client.request("GET", f"/api/assessments/{ids['assessmentId']}/grading/progress")
        progress_data = unwrap_api(payload)
        results.append(StepResult("GET grading/progress", status == 200, f"HTTP {status}: {payload}"))
        if status != 200:
            break
        if isinstance(progress_data, dict) and progress_data.get("status") in ("COMPLETED", "FAILED"):
            break
        time.sleep(args.poll_interval)

    final_status, final_payload = client.request("GET", f"/api/assessments/{ids['assessmentId']}/final-results")
    final_data = unwrap_api(final_payload)
    results.append(StepResult("GET final-results", final_status == 200, f"HTTP {final_status}: {final_payload}"))

    score_status, score_payload = client.request("GET", f"/api/submissions/{ids['submissionId']}/score-items")
    score_data = unwrap_api(score_payload)
    results.append(StepResult("GET score-items", score_status == 200, f"HTTP {score_status}: {score_payload}"))

    final_result_id = None
    if isinstance(final_data, list) and final_data:
        final_result_id = final_data[0].get("id")
    confirm_payload = None
    if final_result_id:
        confirm_status, confirm_payload = client.request(
            "PUT",
            f"/api/final-results/{final_result_id}/confirm",
            {"teacher_id": ids["teacherId"]},
        )
        results.append(StepResult("PUT final-results/confirm", confirm_status == 200, f"HTTP {confirm_status}: {confirm_payload}"))
    else:
        results.append(StepResult("PUT final-results/confirm", False, "No finalResultId available from final-results response."))

    return results, progress_data, final_data, score_data


def verify_database(conn, ids: dict):
    final_rows = fetch_all(
        conn,
        "select * from final_result where submission_id = %s order by id desc",
        (ids["submissionId"],),
    )
    score_rows = fetch_all(
        conn,
        "select sir.* from score_item_result sir join grading_run gr on gr.id = sir.grading_run_id where gr.submission_id = %s order by sir.id",
        (ids["submissionId"],),
    )
    checks = []
    checks.append(StepResult("db final_result exists", len(final_rows) >= 1, f"count={len(final_rows)}"))
    if final_rows:
        final_score = float(final_rows[0]["final_score"])
        checks.append(
            StepResult(
                "db final_score matches demo score",
                abs(final_score - float(SCORE_PAYLOAD["raw_total_score"])) < 0.01,
                f"final_score={final_score}, expected={SCORE_PAYLOAD['raw_total_score']}",
            )
        )
        checks.append(
            StepResult(
                "db confirm review_status",
                str(final_rows[0].get("review_status")) == "CONFIRMED",
                f"review_status={final_rows[0].get('review_status')}",
            )
        )
        checks.append(
            StepResult(
                "db confirmed_at present",
                final_rows[0].get("confirmed_at") is not None,
                f"confirmed_at={final_rows[0].get('confirmed_at')}",
            )
        )
    checks.append(
        StepResult(
            "db score_item_result count",
            len(score_rows) >= len(SCORE_PAYLOAD["dimension_scores"]),
            f"count={len(score_rows)}, expected>={len(SCORE_PAYLOAD['dimension_scores'])}",
        )
    )
    return checks, final_rows, score_rows


def write_report(args, dry_run: bool, ids=None, workspace_files=None, api_results=None, db_checks=None, conclusion=False, failures=None):
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    failures = failures or []
    ids = ids or {}
    workspace_files = workspace_files or {}
    api_results = api_results or []
    db_checks = db_checks or []
    lines = [
        "# 后端最小阅卷 Demo 自动验收记录",
        "",
        f"- 测试时间：{datetime.now().isoformat(timespec='seconds')}",
        f"- 测试模式：{'dry-run' if dry_run else 'apply'}",
        f"- 后端地址：`{args.base_url}`",
        f"- 数据库：`{args.db_user}@{args.db_host}:{args.db_port}/{args.db_name}`",
        f"- workspace：`{args.workspace}`",
        "",
        "## Demo 标识",
        "",
        f"- assessmentId：`{ids.get('assessmentId', '')}`",
        f"- teacherId：`{ids.get('teacherId', '')}`",
        f"- studentId：`{ids.get('studentId', '')}`",
        f"- submissionId：`{ids.get('submissionId', '')}`",
        f"- finalResultId：`{ids.get('finalResultId', '')}`",
        "",
        "## Workspace 文件",
        "",
        f"- student-mapping.csv：`{workspace_files.get('mapping', '')}`",
        f"- scores/anon-001.json：`{workspace_files.get('score', '')}`",
        "",
        "## 接口调用结果",
        "",
    ]
    if api_results:
        for result in api_results:
            lines.append(f"- [{'PASS' if result.ok else 'FAIL'}] {result.name}: {result.detail}")
    else:
        lines.append("- dry-run 未调用接口。")
    lines.extend(["", "## 数据库验证结果", ""])
    if db_checks:
        for result in db_checks:
            lines.append(f"- [{'PASS' if result.ok else 'FAIL'}] {result.name}: {result.detail}")
    else:
        lines.append("- dry-run 未连接或验证数据库。")
    lines.extend(["", "## 结论", "", "PASS" if conclusion else "FAIL" if not dry_run else "DRY-RUN"])
    lines.extend(["", "## 失败原因", ""])
    if failures:
        for failure in failures:
            lines.append(f"- {failure}")
    else:
        lines.append("- 无。")
    lines.extend(
        [
            "",
            "## 后续建议",
            "",
            "- dry-run 通过后，再显式追加 `--apply` 执行真实验收。",
            "- 若接口返回 401，请传入 `--api-username` 和 `--api-password`，或先确认本地后端认证配置。",
            "- 本脚本只写入或复用 DEMO_* 标识数据，不删除真实数据，不修改 schema。",
        ]
    )
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report_path


def print_dry_run_plan(args):
    print("本脚本会向本地 homework_grader 数据库写入 demo 数据。")
    print("默认不执行写入，除非传入 --apply。")
    print("")
    print("Dry-run plan:")
    print("- Check optional MySQL Python driver only when --apply is used.")
    print("- Would upsert/reuse DEMO_* organization, teacher, student, course, class, assessment, and submission data.")
    print(f"- Would write workspace files under: {Path(args.workspace).resolve()}")
    print("- Would call backend grading/start, poll progress, query final-results and score-items, then confirm final_result.")
    print(f"- Would write report: {Path(args.report).resolve()}")


def main() -> int:
    args = parse_args()
    if not args.apply:
        print_dry_run_plan(args)
        write_report(args, dry_run=True)
        return 0

    print("本脚本会向本地 homework_grader 数据库写入 demo 数据。")
    print("--apply detected: executing demo writes and backend verification.")

    failures = []
    conn = None
    ids = {}
    workspace_files = {}
    api_results = []
    db_checks = []
    try:
        backend_check = check_backend_reachable(args.base_url)
        api_results.append(backend_check)
        if not backend_check.ok:
            raise RuntimeError(backend_check.detail)
        if "HTTP 401" in backend_check.detail and not (args.api_username and args.api_password):
            raise RuntimeError("Backend requires authentication. Re-run with --api-username and --api-password before applying demo writes.")
        conn = connect_db(args)
        ids = ensure_demo_data(conn)
        mapping_path, score_path = prepare_workspace(Path(args.workspace))
        workspace_files = {"mapping": str(mapping_path), "score": str(score_path)}
        api_results, progress_data, final_data, score_data = run_api_flow(args, ids)

        if not isinstance(progress_data, dict) or progress_data.get("status") != "COMPLETED":
            failures.append(f"progress.status is not COMPLETED: {progress_data}")
        else:
            summary = progress_data.get("importSummary") or {}
            if int(summary.get("importedCount", 0) or 0) < 1:
                failures.append(f"importSummary.importedCount < 1: {summary}")

        if not isinstance(final_data, list) or not final_data:
            failures.append("final-results response has no rows.")
        else:
            ids["finalResultId"] = final_data[0].get("id")
            final_score = float(final_data[0].get("final_score") or final_data[0].get("finalScore") or 0)
            if abs(final_score - float(SCORE_PAYLOAD["raw_total_score"])) >= 0.01:
                failures.append(f"final_result.final_score mismatch: {final_score}")

        if not isinstance(score_data, list) or len(score_data) < len(SCORE_PAYLOAD["dimension_scores"]):
            failures.append(f"score-items count too low: {0 if not isinstance(score_data, list) else len(score_data)}")

        db_checks, _final_rows, _score_rows = verify_database(conn, ids)
        for check in db_checks:
            if not check.ok:
                failures.append(f"{check.name}: {check.detail}")

        for result in api_results:
            if not result.ok:
                failures.append(f"{result.name}: {result.detail}")

        conclusion = not failures
        report_path = write_report(args, False, ids, workspace_files, api_results, db_checks, conclusion, failures)
        print(f"Report written: {report_path}")
        print("PASS" if conclusion else "FAIL")
        return 0 if conclusion else 1
    except Exception as exc:  # noqa: BLE001
        failures.append(str(exc))
        report_path = write_report(args, False, ids, workspace_files, api_results, db_checks, False, failures)
        print(f"FAIL: {exc}")
        print(f"Report written: {report_path}")
        return 1
    finally:
        if conn is not None:
            conn.close()


if __name__ == "__main__":
    sys.exit(main())
