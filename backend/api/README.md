# API Layer

FastAPI REST API for JavaSmartGrader. Handles authentication, assignment management, submission lifecycle, and grading.

## Module Structure

| File | Purpose |
|------|---------|
| `auth.py` | JWT token creation, verification, and role-based access control |
| `dependencies.py` | Shared `get_db` dependency (async SQLAlchemy session) |
| `routes/users.py` | User registration, login, and profile endpoints |
| `routes/assignments.py` | Assignment and testcase CRUD |
| `routes/submissions.py` | Submission creation and retrieval |
| `routes/grading.py` | Compile results, transcriptions, AI feedback, and grade management |

## Authentication

JWT bearer tokens. Obtain a token via `POST /users/login`, then pass it as:

```
Authorization: Bearer <token>
```

Tokens expire after **30 minutes**.

Role-based access:
- **student** — submit work, view own submissions and grades
- **instructor** — manage assignments, view all submissions, assign grades

---

## Endpoints

### Users — `/users`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/users/register` | None | Register a new user |
| `POST` | `/users/login` | None | Login and receive a JWT token |
| `GET` | `/users/me` | Any | Get current user profile |
| `PATCH` | `/users/me/email` | Any | Update current user's email |
| `DELETE` | `/users/me` | Any | Delete current user's account |

#### `POST /users/register`

```json
{
  "username": "jdoe",
  "password": "secret",
  "email": "jdoe@example.com",
  "role": "student"
}
```

Returns: `UserBase` — `{ id, username, email, role }`

#### `POST /users/login`

Form data (`application/x-www-form-urlencoded`): `username`, `password`

Returns: `{ "access_token": "...", "token_type": "bearer" }`

---

### Assignments — `/assignments`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/assignments/` | Instructor | Create a new assignment |
| `GET` | `/assignments/instructors` | Instructor | List own assignments |
| `GET` | `/assignments/{id}` | Any | Get assignment by ID |
| `PUT` | `/assignments/{id}` | Instructor | Update assignment fields |
| `DELETE` | `/assignments/{id}` | Instructor | Delete assignment |
| `POST` | `/assignments/{id}/testcases` | Instructor | Add a testcase |
| `GET` | `/assignments/{id}/testcases` | Instructor | List testcases |
| `DELETE` | `/assignments/{id}/testcases` | Instructor | Remove a testcase by input |

#### `POST /assignments/`

Query params: `title`, `question`, `description` (optional), `due_date` (optional, ISO 8601)

Returns: `AssignmentBase`

---

### Submissions — `/submissions`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/submissions/` | Student | Submit an answer for an assignment |
| `GET` | `/submissions/me` | Any | List current user's submissions |
| `GET` | `/submissions/{id}` | Any | Get submission by ID |
| `GET` | `/submissions/assignment/{id}` | Instructor | List all submissions for an assignment |
| `PUT` | `/submissions/{id}/state` | Instructor | Update submission state |
| `DELETE` | `/submissions/{id}` | Student | Delete own submission |

#### `POST /submissions/`

Query params: `assignment_id`, `image_url` (optional)

Submission states: `submitted` → `processing` → `graded` / `failed`

---

### Grading — `/grading`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/grading/{id}/compile_result` | Any | Get compile/run result for submission |
| `GET` | `/grading/{id}/transcription` | Any | Get OCR transcription for submission |
| `GET` | `/grading/{id}/ai_feedback` | Any | Get AI-suggested feedback and grade |
| `POST` | `/grading/{id}/grade` | Instructor | Assign a final grade |
| `PUT` | `/grading/{id}/grade` | Instructor | Update an existing grade |

Students can only access grading data for their own submissions. Instructors can access all.
