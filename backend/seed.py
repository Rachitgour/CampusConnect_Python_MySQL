"""Create repeatable local demo accounts. Run from the project root: python backend/seed.py"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app import database, write_tags  # noqa: E402
from werkzeug.security import generate_password_hash  # noqa: E402

DEMO_PASSWORD = "Campus@123"
DEMO_STUDENTS = [
    {
        "name": "Rudra Shukla", "email": "rudra.demo@campusconnect.local", "college": "CampusConnect University",
        "course": "B.Tech Computer Science", "study_year": "3rd Year",
        "bio": "Learning web development and DSA. Interested in building useful student-focused products and collaborating on projects.",
        "skills": ["HTML", "CSS", "JavaScript", "Python", "MySQL"],
        "interests": ["Web development", "DSA", "Open source"],
    },
    {
        "name": "Aarav Sharma", "email": "aarav.demo@campusconnect.local", "college": "CampusConnect University",
        "course": "B.Tech CSE", "study_year": "3rd Year",
        "bio": "Enjoys backend development, APIs, and database design. Looking for teammates for practical web projects.",
        "skills": ["Python", "Flask", "MySQL", "REST APIs"],
        "interests": ["Backend development", "Hackathons", "Databases"],
    },
    {
        "name": "Priya Kapoor", "email": "priya.demo@campusconnect.local", "college": "Central Institute of Technology",
        "course": "B.Tech IT", "study_year": "2nd Year",
        "bio": "Interested in clean user interfaces, accessibility, and design systems.",
        "skills": ["HTML", "CSS", "Figma", "UI/UX"],
        "interests": ["Web design", "Accessibility", "Product design"],
    },
    {
        "name": "Rohan Mehta", "email": "rohan.demo@campusconnect.local", "college": "CampusConnect University",
        "course": "B.Tech CSE", "study_year": "3rd Year",
        "bio": "Practicing data structures and algorithms and learning how to turn ideas into full-stack projects.",
        "skills": ["Java", "DSA", "Git", "JavaScript"],
        "interests": ["Competitive programming", "Open source", "Web development"],
    },
    {
        "name": "Meera Iyer", "email": "meera.demo@campusconnect.local", "college": "Riverdale Engineering College",
        "course": "B.Tech CSE", "study_year": "4th Year",
        "bio": "Exploring data science and machine learning and looking for project collaborators.",
        "skills": ["Python", "Pandas", "SQL", "Machine Learning"],
        "interests": ["Data science", "AI", "Research"],
    },
]

with database() as connection:
    with connection.cursor() as cursor:
        ids = {}
        for person in DEMO_STUDENTS:
            cursor.execute("SELECT id FROM students WHERE email=%s", (person["email"],))
            existing = cursor.fetchone()
            if existing:
                sid = int(existing["id"])
                cursor.execute(
                    "UPDATE students SET name=%s, password_hash=%s, college=%s, course=%s, study_year=%s, bio=%s WHERE id=%s",
                    (person["name"], generate_password_hash(DEMO_PASSWORD), person["college"], person["course"], person["study_year"], person["bio"], sid),
                )
            else:
                cursor.execute(
                    "INSERT INTO students (name,email,password_hash,college,course,study_year,bio) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                    (person["name"], person["email"], generate_password_hash(DEMO_PASSWORD), person["college"], person["course"], person["study_year"], person["bio"]),
                )
                sid = int(cursor.lastrowid)
            ids[person["email"]] = sid
            cursor.execute("DELETE FROM student_skills WHERE student_id=%s", (sid,))
            cursor.execute("DELETE FROM student_interests WHERE student_id=%s", (sid,))
            write_tags(cursor, "student_skills", "skill", sid, person["skills"])
            write_tags(cursor, "student_interests", "interest", sid, person["interests"])

        rudra_id = ids["rudra.demo@campusconnect.local"]
        aarav_id = ids["aarav.demo@campusconnect.local"]
        cursor.execute("SELECT id FROM collaboration_requests WHERE sender_id=%s AND receiver_id=%s", (aarav_id, rudra_id))
        if not cursor.fetchone():
            cursor.execute(
                "INSERT INTO collaboration_requests (sender_id, receiver_id, message, status) VALUES (%s,%s,%s,'pending')",
                (aarav_id, rudra_id, "Hi Rudra! Want to collaborate on a small web project?"),
            )

print("Demo data is ready.")
print("Demo account: rudra.demo@campusconnect.local")
print(f"Demo password: {DEMO_PASSWORD}")
print("Other demo accounts use the same password.")
