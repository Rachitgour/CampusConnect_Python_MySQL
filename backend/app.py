"""CampusConnect REST API (Flask + MySQL).

The frontend is plain HTML/CSS/browser JavaScript in ../frontend.
This Flask app serves those files and provides JSON endpoints under /api.
"""
from __future__ import annotations

import os
import re
from contextlib import contextmanager
from datetime import date, datetime
from functools import wraps
from pathlib import Path
from typing import Any, Iterable

import pymysql
from dotenv import load_dotenv
from flask import Flask, jsonify, request, session, send_from_directory
from pymysql.cursors import DictCursor
from pymysql.err import IntegrityError, MySQLError
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"
load_dotenv(BASE_DIR / ".env")

app = Flask(__name__, static_folder=str(FRONTEND_DIR), static_url_path="")
app.config.update(
    SECRET_KEY=os.getenv("SECRET_KEY", "local-only-change-this-secret"),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.getenv("COOKIE_SECURE", "0") == "1",
    PERMANENT_SESSION_LIFETIME=60 * 60 * 24 * 7,
    MAX_CONTENT_LENGTH=64 * 1024,
)

EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
MAX_TAGS = 30


def get_connection():
    """Create one MySQL connection for a request operation."""
    return pymysql.connect(
        host=os.getenv("MYSQL_HOST", "127.0.0.1"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        user=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD", ""),
        database=os.getenv("MYSQL_DATABASE", "campusconnect"),
        charset="utf8mb4",
        cursorclass=DictCursor,
        autocommit=False,
        connect_timeout=5,
    )


@contextmanager
def database():
    """Commit successful operations, roll back on errors, and always close."""
    connection = get_connection()
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def parse_tags(value: Any, limit: int = MAX_TAGS, item_max_length: int = 100) -> list[str]:
    """Accept a JSON array or comma-separated string; return unique clean values."""
    values = value if isinstance(value, list) else str(value or "").split(",")
    clean: list[str] = []
    seen: set[str] = set()
    for item in values:
        text = str(item or "").strip()
        if not text:
            continue
        text = text[:item_max_length]
        marker = text.casefold()
        if marker not in seen:
            clean.append(text)
            seen.add(marker)
        if len(clean) >= limit:
            break
    return clean


def initials(name: str) -> str:
    return "".join(part[0] for part in str(name or "Student").split()[:2]).upper() or "ST"


def iso(value: Any) -> str | None:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return str(value) if value is not None else None


def tags_for_students(cursor, student_ids: Iterable[int]) -> tuple[dict[int, list[str]], dict[int, list[str]]]:
    ids = list(dict.fromkeys(int(item) for item in student_ids if item is not None))
    skills: dict[int, list[str]] = {item: [] for item in ids}
    interests: dict[int, list[str]] = {item: [] for item in ids}
    if not ids:
        return skills, interests
    placeholders = ",".join(["%s"] * len(ids))
    cursor.execute(
        f"SELECT student_id, skill FROM student_skills WHERE student_id IN ({placeholders}) ORDER BY skill",
        ids,
    )
    for row in cursor.fetchall():
        skills[int(row["student_id"])].append(row["skill"])
    cursor.execute(
        f"SELECT student_id, interest FROM student_interests WHERE student_id IN ({placeholders}) ORDER BY interest",
        ids,
    )
    for row in cursor.fetchall():
        interests[int(row["student_id"])].append(row["interest"])
    return skills, interests


def serialize_students(cursor, rows: list[dict[str, Any]], include_email: bool = False) -> list[dict[str, Any]]:
    skills, interests = tags_for_students(cursor, [row["id"] for row in rows])
    result = []
    for row in rows:
        sid = int(row["id"])
        item = {
            "id": sid,
            "name": row.get("name", ""),
            "initials": initials(row.get("name", "")),
            "college": row.get("college", "") or "",
            "course": row.get("course", "") or "",
            "year": row.get("study_year", "") or "",
            "bio": row.get("bio", "") or "",
            "skills": skills.get(sid, []),
            "interests": interests.get(sid, []),
            "created_at": iso(row.get("created_at")),
        }
        if include_email:
            item["email"] = row.get("email", "")
        result.append(item)
    return result


def get_student(cursor, student_id: int, include_email: bool = False) -> dict[str, Any] | None:
    cursor.execute(
        "SELECT id, name, email, password_hash, college, course, study_year, bio, created_at "
        "FROM students WHERE id = %s",
        (student_id,),
    )
    rows = cursor.fetchall()
    if not rows:
        return None
    profile = serialize_students(cursor, rows, include_email=include_email)[0]
    if include_email:
        profile["email"] = rows[0]["email"]
    return profile


def list_students(cursor, exclude_id: int | None = None, limit: int = 200) -> list[dict[str, Any]]:
    if exclude_id is None:
        cursor.execute(
            "SELECT id, name, email, college, course, study_year, bio, created_at "
            "FROM students ORDER BY created_at DESC LIMIT %s",
            (limit,),
        )
    else:
        cursor.execute(
            "SELECT id, name, email, college, course, study_year, bio, created_at "
            "FROM students WHERE id <> %s ORDER BY created_at DESC LIMIT %s",
            (exclude_id, limit),
        )
    return serialize_students(cursor, cursor.fetchall())


def write_tags(cursor, table: str, column: str, student_id: int, tags: list[str]) -> None:
    # Table/column identifiers come only from hard-coded values in this module.
    if table not in {"student_skills", "student_interests"} or column not in {"skill", "interest"}:
        raise ValueError("Invalid tag table")
    if tags:
        cursor.executemany(
            f"INSERT INTO {table} (student_id, {column}) VALUES (%s, %s)",
            [(student_id, tag) for tag in tags],
        )


def current_student_id() -> int | None:
    value = session.get("student_id")
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        session.clear()
        return None


def login_required(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        if current_student_id() is None:
            return jsonify({"error": "Please log in to continue."}), 401
        return function(*args, **kwargs)
    return wrapped


def json_body() -> dict[str, Any]:
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def error(message: str, status: int):
    return jsonify({"error": message}), status


def get_request_rows(cursor, student_id: int, request_type: str) -> list[dict[str, Any]]:
    if request_type == "sent":
        cursor.execute(
            "SELECT r.id, r.status, r.message, r.created_at, s.id AS other_id "
            "FROM collaboration_requests r JOIN students s ON s.id = r.receiver_id "
            "WHERE r.sender_id = %s ORDER BY r.created_at DESC",
            (student_id,),
        )
    else:
        cursor.execute(
            "SELECT r.id, r.status, r.message, r.created_at, s.id AS other_id "
            "FROM collaboration_requests r JOIN students s ON s.id = r.sender_id "
            "WHERE r.receiver_id = %s ORDER BY r.created_at DESC",
            (student_id,),
        )
    rows = cursor.fetchall()
    people = {person["id"]: person for person in list_students_by_ids(cursor, [row["other_id"] for row in rows])}
    return [
        {
            "id": int(row["id"]),
            "status": row["status"],
            "message": row["message"] or "",
            "created_at": iso(row["created_at"]),
            "student": people.get(int(row["other_id"])),
        }
        for row in rows
    ]


def list_students_by_ids(cursor, student_ids: Iterable[int]) -> list[dict[str, Any]]:
    ids = list(dict.fromkeys(int(item) for item in student_ids))
    if not ids:
        return []
    placeholders = ",".join(["%s"] * len(ids))
    cursor.execute(
        "SELECT id, name, email, college, course, study_year, bio, created_at "
        f"FROM students WHERE id IN ({placeholders})",
        ids,
    )
    return serialize_students(cursor, cursor.fetchall())


@app.get("/")
def home_page():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.get("/api/health")
def health():
    try:
        with database() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1 AS ok")
                cursor.fetchone()
        return jsonify({"status": "ok", "database": "connected"})
    except MySQLError:
        return jsonify({"status": "error", "database": "unavailable", "message": "Check your MySQL service and .env settings."}), 503


@app.get("/api/auth/me")
def auth_me():
    student_id = current_student_id()
    if student_id is None:
        return jsonify({"authenticated": False, "user": None})
    try:
        with database() as connection:
            with connection.cursor() as cursor:
                user = get_student(cursor, student_id, include_email=True)
        if user is None:
            session.clear()
            return jsonify({"authenticated": False, "user": None})
        return jsonify({"authenticated": True, "user": user})
    except MySQLError:
        return error("The database is not available. Check your MySQL setup.", 503)


@app.post("/api/auth/register")
def register():
    data = json_body()
    name = str(data.get("name", "")).strip()[:80]
    email = str(data.get("email", "")).strip().lower()[:160]
    password = str(data.get("password", ""))
    college = str(data.get("college", "")).strip()[:120]
    course = str(data.get("course", "")).strip()[:100]
    year = str(data.get("year", "")).strip()[:40]
    skills = parse_tags(data.get("skills"), item_max_length=80)
    interests = parse_tags(data.get("interests"), item_max_length=100)

    if not name or not email or not password:
        return error("Name, email, and password are required.", 400)
    if not EMAIL_PATTERN.match(email):
        return error("Enter a valid email address.", 400)
    if len(password) < 8:
        return error("Use a password with at least 8 characters.", 400)

    try:
        with database() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO students (name, email, password_hash, college, course, study_year) "
                    "VALUES (%s, %s, %s, %s, %s, %s)",
                    (name, email, generate_password_hash(password), college, course, year),
                )
                student_id = int(cursor.lastrowid)
                write_tags(cursor, "student_skills", "skill", student_id, skills)
                write_tags(cursor, "student_interests", "interest", student_id, interests)
                user = get_student(cursor, student_id, include_email=True)
    except IntegrityError:
        return error("An account with that email already exists.", 409)
    except MySQLError:
        return error("Could not create your account. Check that MySQL is running and the schema is installed.", 503)

    session.clear()
    session["student_id"] = student_id
    session.permanent = True
    return jsonify({"message": "Welcome to CampusConnect!", "user": user}), 201


@app.post("/api/auth/login")
def login():
    data = json_body()
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))
    if not email or not password:
        return error("Enter your email and password.", 400)
    try:
        with database() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT id, password_hash FROM students WHERE email = %s", (email,))
                user_row = cursor.fetchone()
                if not user_row or not check_password_hash(user_row["password_hash"], password):
                    return error("Email or password is incorrect.", 401)
                student_id = int(user_row["id"])
                user = get_student(cursor, student_id, include_email=True)
    except MySQLError:
        return error("The database is not available. Check your MySQL setup.", 503)
    session.clear()
    session["student_id"] = student_id
    session.permanent = True
    return jsonify({"message": "You are signed in.", "user": user})


@app.post("/api/auth/logout")
def logout():
    session.clear()
    return jsonify({"message": "You have been logged out."})


@app.get("/api/public/students")
def public_students():
    try:
        limit = min(max(int(request.args.get("limit", "3")), 1), 6)
        with database() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT id, name, email, college, course, study_year, bio, created_at "
                    "FROM students ORDER BY created_at DESC LIMIT %s", (limit,)
                )
                data = serialize_students(cursor, cursor.fetchall())
        return jsonify({"data": data, "count": len(data)})
    except (ValueError, MySQLError):
        return jsonify({"data": [], "count": 0})


@app.get("/api/dashboard")
@login_required
def dashboard():
    student_id = current_student_id()
    try:
        with database() as connection:
            with connection.cursor() as cursor:
                user = get_student(cursor, student_id, include_email=True)
                students = list_students(cursor, exclude_id=student_id, limit=200)
                cursor.execute("SELECT COUNT(*) AS total FROM students WHERE id <> %s", (student_id,))
                student_count = int(cursor.fetchone()["total"])
                cursor.execute("SELECT COUNT(*) AS total FROM collaboration_requests WHERE receiver_id = %s AND status = 'pending'", (student_id,))
                pending_received = int(cursor.fetchone()["total"])
                cursor.execute("SELECT COUNT(*) AS total FROM collaboration_requests WHERE sender_id = %s AND status = 'pending'", (student_id,))
                pending_sent = int(cursor.fetchone()["total"])
        return jsonify({"user": user, "student_count": student_count, "pending_received": pending_received, "pending_sent": pending_sent, "recommended": students[:3]})
    except MySQLError:
        return error("Could not load the dashboard. Check your MySQL connection.", 503)


@app.get("/api/students")
@login_required
def students_search():
    query = str(request.args.get("q", "")).strip().casefold()[:80]
    student_id = current_student_id()
    try:
        with database() as connection:
            with connection.cursor() as cursor:
                students = list_students(cursor, exclude_id=student_id, limit=500)
        if query:
            students = [student for student in students if query in " ".join([
                student.get("name", ""), student.get("college", ""), student.get("course", ""),
                student.get("bio", ""), " ".join(student.get("skills", [])), " ".join(student.get("interests", []))
            ]).casefold()]
        return jsonify({"data": students[:100], "count": len(students[:100]), "query": query})
    except MySQLError:
        return error("Could not search students. Check your MySQL connection.", 503)


@app.get("/api/students/<int:student_id>")
@login_required
def student_detail(student_id: int):
    viewer_id = current_student_id()
    if student_id == viewer_id:
        return error("Use your own Profile page to view or edit your profile.", 400)
    try:
        with database() as connection:
            with connection.cursor() as cursor:
                student = get_student(cursor, student_id)
                if not student:
                    return error("Student not found.", 404)
                cursor.execute("SELECT id, status FROM collaboration_requests WHERE sender_id = %s AND receiver_id = %s", (viewer_id, student_id))
                outgoing = cursor.fetchone()
                cursor.execute("SELECT id, status FROM collaboration_requests WHERE sender_id = %s AND receiver_id = %s", (student_id, viewer_id))
                incoming = cursor.fetchone()
                connected = bool((outgoing and outgoing["status"] == "accepted") or (incoming and incoming["status"] == "accepted"))
        return jsonify({"student": student, "relationship": {
            "connected": connected,
            "outgoing_status": outgoing["status"] if outgoing else None,
            "incoming_status": incoming["status"] if incoming else None,
            "accepted_request_id": (int(outgoing["id"]) if outgoing and outgoing["status"] == "accepted" else int(incoming["id"]) if incoming and incoming["status"] == "accepted" else None),
        }})
    except MySQLError:
        return error("Could not load this profile. Check your MySQL connection.", 503)


@app.put("/api/profile")
@login_required
def update_profile():
    data = json_body()
    student_id = current_student_id()
    name = str(data.get("name", "")).strip()[:80]
    if not name:
        return error("Your name cannot be empty.", 400)
    college = str(data.get("college", "")).strip()[:120]
    course = str(data.get("course", "")).strip()[:100]
    year = str(data.get("year", "")).strip()[:40]
    bio = str(data.get("bio", "")).strip()[:500]
    skills = parse_tags(data.get("skills"), item_max_length=80)
    interests = parse_tags(data.get("interests"), item_max_length=100)
    try:
        with database() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE students SET name=%s, college=%s, course=%s, study_year=%s, bio=%s WHERE id=%s",
                    (name, college, course, year, bio, student_id),
                )
                cursor.execute("DELETE FROM student_skills WHERE student_id=%s", (student_id,))
                cursor.execute("DELETE FROM student_interests WHERE student_id=%s", (student_id,))
                write_tags(cursor, "student_skills", "skill", student_id, skills)
                write_tags(cursor, "student_interests", "interest", student_id, interests)
                user = get_student(cursor, student_id, include_email=True)
        return jsonify({"message": "Your profile has been updated.", "user": user})
    except MySQLError:
        return error("Could not save your profile. Check your MySQL connection.", 503)


@app.post("/api/requests")
@login_required
def send_request():
    data = json_body()
    sender_id = current_student_id()
    try:
        receiver_id = int(data.get("receiver_id"))
    except (TypeError, ValueError):
        return error("Choose a student to send a request to.", 400)
    message = str(data.get("message", "")).strip()[:500]
    if receiver_id == sender_id:
        return error("You cannot send a request to yourself.", 400)
    try:
        with database() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT id FROM students WHERE id=%s", (receiver_id,))
                if not cursor.fetchone():
                    return error("Student not found.", 404)
                cursor.execute("SELECT id, status FROM collaboration_requests WHERE sender_id=%s AND receiver_id=%s", (sender_id, receiver_id))
                existing = cursor.fetchone()
                if existing:
                    if existing["status"] in {"pending", "accepted"}:
                        return error("A request already exists for this student.", 409)
                    cursor.execute(
                        "UPDATE collaboration_requests SET status='pending', message=%s, created_at=CURRENT_TIMESTAMP "
                        "WHERE id=%s", (message, existing["id"])
                    )
                    request_id = int(existing["id"])
                else:
                    cursor.execute("SELECT status FROM collaboration_requests WHERE sender_id=%s AND receiver_id=%s", (receiver_id, sender_id))
                    reverse = cursor.fetchone()
                    if reverse and reverse["status"] == "accepted":
                        return error("You are already connected with this student.", 409)
                    if reverse and reverse["status"] == "pending":
                        return error("This student has already sent you a request. Check your Requests page.", 409)
                    cursor.execute(
                        "INSERT INTO collaboration_requests (sender_id, receiver_id, message, status) VALUES (%s, %s, %s, 'pending')",
                        (sender_id, receiver_id, message),
                    )
                    request_id = int(cursor.lastrowid)
        return jsonify({"message": "Collaboration request sent.", "data": {"id": request_id, "status": "pending"}}), 201
    except IntegrityError:
        return error("A request already exists for this student.", 409)
    except MySQLError:
        return error("Could not send the collaboration request. Check your MySQL connection.", 503)


@app.get("/api/requests")
@login_required
def requests_list():
    request_type = "sent" if request.args.get("type") == "sent" else "received"
    try:
        with database() as connection:
            with connection.cursor() as cursor:
                data = get_request_rows(cursor, current_student_id(), request_type)
        return jsonify({"data": data, "count": len(data)})
    except MySQLError:
        return error("Could not load collaboration requests. Check your MySQL connection.", 503)


@app.patch("/api/requests/<int:request_id>")
@login_required
def respond_to_request(request_id: int):
    status = str(json_body().get("status", "")).strip().lower()
    if status not in {"accepted", "rejected"}:
        return error("Status must be accepted or rejected.", 400)
    try:
        with database() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT id, receiver_id, status FROM collaboration_requests WHERE id=%s", (request_id,))
                row = cursor.fetchone()
                if not row:
                    return error("Request not found.", 404)
                if int(row["receiver_id"]) != current_student_id():
                    return error("You can only respond to requests sent to you.", 403)
                if row["status"] != "pending":
                    return error("This request has already been reviewed.", 409)
                cursor.execute("UPDATE collaboration_requests SET status=%s WHERE id=%s", (status, request_id))
        return jsonify({"message": f"Request {status}.", "data": {"id": request_id, "status": status}})
    except MySQLError:
        return error("Could not update the request. Check your MySQL connection.", 503)


def get_accepted_chat_request(cursor, request_id: int, student_id: int) -> dict[str, Any] | None:
    """Return a collaboration request only when this student belongs to it."""
    cursor.execute(
        "SELECT id, sender_id, receiver_id, status FROM collaboration_requests WHERE id=%s",
        (request_id,),
    )
    row = cursor.fetchone()
    if not row:
        return None
    if student_id not in {int(row["sender_id"]), int(row["receiver_id"])}:
        return {"_forbidden": True}
    return row


@app.get("/api/chat/conversations")
@login_required
def chat_conversations():
    """List accepted collaboration partners; pending requests never appear here."""
    student_id = current_student_id()
    try:
        with database() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT r.id AS request_id, r.sender_id, r.receiver_id, r.updated_at, "
                    "other.id AS student_id, other.name AS student_name, other.college, other.course, other.study_year, "
                    "last_msg.message AS last_message, last_msg.created_at AS last_message_at "
                    "FROM collaboration_requests r "
                    "JOIN students other ON other.id = CASE WHEN r.sender_id=%s THEN r.receiver_id ELSE r.sender_id END "
                    "LEFT JOIN (SELECT m1.collaboration_request_id, m1.message, m1.created_at "
                    "           FROM chat_messages m1 "
                    "           JOIN (SELECT collaboration_request_id, MAX(id) AS max_id "
                    "                 FROM chat_messages GROUP BY collaboration_request_id) latest "
                    "             ON latest.max_id = m1.id) last_msg "
                    "  ON last_msg.collaboration_request_id = r.id "
                    "WHERE r.status='accepted' AND (r.sender_id=%s OR r.receiver_id=%s) "
                    "ORDER BY COALESCE(last_msg.created_at, r.updated_at) DESC, r.id DESC",
                    (student_id, student_id, student_id),
                )
                rows = cursor.fetchall()
        # Defensive de-duplication in case older data contains accepted rows in both directions.
        conversations = []
        seen_students: set[int] = set()
        for row in rows:
            other_id = int(row["student_id"])
            if other_id in seen_students:
                continue
            seen_students.add(other_id)
            conversations.append({
                "request_id": int(row["request_id"]),
                "student": {
                    "id": other_id,
                    "name": row["student_name"],
                    "initials": initials(row["student_name"]),
                    "college": row["college"] or "",
                    "course": row["course"] or "",
                    "year": row["study_year"] or "",
                },
                "last_message": row["last_message"] or "No messages yet. Say hello!",
                "last_message_at": iso(row["last_message_at"]),
            })
        return jsonify({"data": conversations, "count": len(conversations)})
    except MySQLError:
        return error("Could not load chats. Make sure the chat_messages table has been created.", 503)


@app.get("/api/chat/conversations/<int:request_id>/messages")
@login_required
def chat_messages(request_id: int):
    student_id = current_student_id()
    try:
        with database() as connection:
            with connection.cursor() as cursor:
                relationship = get_accepted_chat_request(cursor, request_id, student_id)
                if not relationship:
                    return error("Conversation not found.", 404)
                if relationship.get("_forbidden"):
                    return error("You are not a participant in this conversation.", 403)
                if relationship["status"] != "accepted":
                    return error("Chat is available only after the collaboration request is accepted.", 403)
                cursor.execute(
                    "SELECT recent.id, recent.sender_id, recent.message, recent.created_at, s.name AS sender_name "
                    "FROM (SELECT id, sender_id, message, created_at FROM chat_messages "
                    "      WHERE collaboration_request_id=%s ORDER BY id DESC LIMIT 100) recent "
                    "JOIN students s ON s.id = recent.sender_id ORDER BY recent.id ASC",
                    (request_id,),
                )
                rows = cursor.fetchall()
        messages = [{
            "id": int(row["id"]),
            "sender_id": int(row["sender_id"]),
            "sender_name": row["sender_name"],
            "message": row["message"],
            "created_at": iso(row["created_at"]),
            "is_mine": int(row["sender_id"]) == student_id,
        } for row in rows]
        return jsonify({"data": messages, "count": len(messages)})
    except MySQLError:
        return error("Could not load messages. Make sure the chat_messages table has been created.", 503)


@app.post("/api/chat/conversations/<int:request_id>/messages")
@login_required
def send_chat_message(request_id: int):
    student_id = current_student_id()
    message = str(json_body().get("message", "")).strip()
    if not message:
        return error("Type a message before sending.", 400)
    if len(message) > 2000:
        return error("Messages must be 2,000 characters or fewer.", 400)
    try:
        with database() as connection:
            with connection.cursor() as cursor:
                relationship = get_accepted_chat_request(cursor, request_id, student_id)
                if not relationship:
                    return error("Conversation not found.", 404)
                if relationship.get("_forbidden"):
                    return error("You are not a participant in this conversation.", 403)
                if relationship["status"] != "accepted":
                    return error("Chat is available only after the collaboration request is accepted.", 403)
                cursor.execute(
                    "INSERT INTO chat_messages (collaboration_request_id, sender_id, message) VALUES (%s, %s, %s)",
                    (request_id, student_id, message),
                )
                message_id = int(cursor.lastrowid)
                cursor.execute(
                    "SELECT m.id, m.sender_id, m.message, m.created_at, s.name AS sender_name "
                    "FROM chat_messages m JOIN students s ON s.id=m.sender_id WHERE m.id=%s",
                    (message_id,),
                )
                row = cursor.fetchone()
        return jsonify({"message": "Message sent.", "data": {
            "id": int(row["id"]),
            "sender_id": int(row["sender_id"]),
            "sender_name": row["sender_name"],
            "message": row["message"],
            "created_at": iso(row["created_at"]),
            "is_mine": True,
        }}), 201
    except MySQLError:
        return error("Could not send the message. Check your MySQL connection and chat table.", 503)


@app.errorhandler(404)
def not_found(_error):
    if request.path.startswith("/api/"):
        return jsonify({"error": "Endpoint not found."}), 404
    return jsonify({"error": "Page or file not found."}), 404


@app.errorhandler(MySQLError)
def mysql_error(_error):
    app.logger.exception("A MySQL error occurred")
    return jsonify({"error": "MySQL is unavailable. Check your database service and .env settings."}), 503


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", "5000")), debug=os.getenv("FLASK_DEBUG", "1") == "1")
