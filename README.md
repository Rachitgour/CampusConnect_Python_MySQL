# CampusConnect — Student Collaboration & Skill-Sharing Platform

CampusConnect helps college students discover peers by skills/interests, view profiles, and send collaboration requests. This version uses the agreed stack: **HTML, CSS, JavaScript, Python (Flask), REST APIs, and MySQL**. It does **not** use EJS, Node.js, Express, or MongoDB.

## Project structure

```text
CampusConnect_Python_MySQL/
├── frontend/
│   ├── index.html             # Landing page design
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   ├── discover.html
│   ├── profile.html
│   ├── student.html            # Public student profile, ID in query string
│   ├── requests.html
│   ├── css/style.css
│   └── js/app.js
├── backend/
│   ├── app.py                  # Flask REST API and static-file host
│   └── seed.py                 # Optional demo data
├── database/schema.sql         # MySQL tables and relationships
├── requirements.txt
├── .env.example
└── README.md
```

The frontend source is separate from the backend source. During local development, Flask serves the static frontend from `frontend/` and serves JSON APIs under `/api` so that browser session cookies work on the same origin without CORS setup.

## Requirements

- Python 3.10 or newer recommended
- MySQL 8.x (or a compatible MySQL server)
- VS Code

## First-time setup

### 1. Create the MySQL schema

Open MySQL Workbench (or the MySQL command line), then run the complete file `database/schema.sql`. It creates the `campusconnect` database and four tables: `students`, `student_skills`, `student_interests`, and `collaboration_requests`.

Example command line, from the project folder:

```bash
mysql -u root -p < database/schema.sql
```

Enter the password for your local MySQL user when prompted.

### 2. Create your local environment file

Copy `.env.example` to `.env`, then put your own local MySQL password in `MYSQL_PASSWORD`. Change `SECRET_KEY` to a long private random string.

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

macOS/Linux:

```bash
cp .env.example .env
```

### 3. Install Python packages

It is recommended to use a virtual environment.

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

### 4. Optional: add demo students

From the project root, with MySQL running and `.env` configured:

```bash
python backend/seed.py
```

Demo login:

- **Email:** `rudra.demo@campusconnect.local`
- **Password:** `Campus@123`

The seed script creates/updates five sample students and a pending collaboration request from Aarav Sharma to the demo account. This password is for local demonstration only. To make chat available in an already-created database, run `database/chat_migration.sql` once in MySQL Workbench; it adds the `chat_messages` table without deleting current student or request data.

### 5. Start CampusConnect

From the project root:

```bash
python backend/app.py
```

Open <http://127.0.0.1:5000>. Keep the terminal running while using the site.

Check the backend/database connection at <http://127.0.0.1:5000/api/health>. A successful response looks like:

```json
{"status":"ok","database":"connected"}
```

## Features in this starter

- Landing page with the CampusConnect branding, hero, features, three-step process, optional featured-student strip, and footer
- Responsive navbar and mobile hamburger menu
- Registration and login with password hashing and server-side sessions
- Student dashboard with counts and recommendations
- Student discovery/search by name, college, course, biography, skills, and interests
- Public student profile pages
- Edit profile, skills, and interests
- Send collaboration requests
- Review received/sent requests and accept/reject pending incoming requests
- Chat with accepted collaborators; pending/rejected relationships cannot read or send messages
- Chat messages persist in MySQL and the open thread refreshes every four seconds
- MySQL foreign keys and normalized tables for skills/interests/chat messages

## REST API overview

All request/response bodies use JSON. Authenticated endpoints use the Flask session cookie created by the login/register endpoint. The frontend and API are same-origin when run as documented.

| Method | Endpoint | Purpose | Authentication |
|---|---|---|---|
| GET | `/api/health` | Check MySQL connection | No |
| GET | `/api/auth/me` | Check session and get the signed-in user | No |
| POST | `/api/auth/register` | Create an account and sign in | No |
| POST | `/api/auth/login` | Sign in | No |
| POST | `/api/auth/logout` | Sign out | Session optional |
| GET | `/api/public/students?limit=3` | Public student cards for landing page | No |
| GET | `/api/dashboard` | Dashboard counts and recommendations | Yes |
| GET | `/api/students?q=python` | Search students | Yes |
| GET | `/api/students/:id` | View another student's profile and request status | Yes |
| PUT | `/api/profile` | Update signed-in profile | Yes |
| POST | `/api/requests` | Send a collaboration request; JSON body includes `receiver_id` and optional `message` | Yes |
| GET | `/api/requests?type=received` | List received requests | Yes |
| GET | `/api/requests?type=sent` | List sent requests | Yes |
| PATCH | `/api/requests/:id` | Accept/reject request; JSON body `{"status":"accepted"}` or `{"status":"rejected"}` | Yes (receiver only) |
| GET | `/api/chat/conversations` | List accepted collaborators | Yes |
| GET | `/api/chat/conversations/:request_id/messages` | Load the latest messages for an accepted collaboration | Yes (participant only) |
| POST | `/api/chat/conversations/:request_id/messages` | Send message; JSON body `{"message":"Hello"}` | Yes (participant in accepted collaboration only) |

## Data model

- **students** stores account credentials and basic profile data.
- **student_skills** stores one skill per row, linked to a student.
- **student_interests** stores one interest per row, linked to a student.
- **collaboration_requests** links a sender and receiver, with `pending`, `accepted`, or `rejected` status.

Skills and interests are separate tables to keep the MySQL schema relational and searchable. Passwords are stored as Werkzeug password hashes, never as plain text.

## Important limitations / next steps

- This is a beginner-friendly local starter. Run through registration, login, profile editing, search, and request flows on your machine after completing setup.
- Before any public deployment, add CSRF protection for session-authenticated state-changing requests, stronger rate limiting, production logging, HTTPS-only cookies, deployment-specific secret management, and a security review.
- The API uses a session cookie because the HTML and API are served from the same local origin. Do not test state-changing endpoints from an untrusted site.
- The demo account and password are not intended for production.
