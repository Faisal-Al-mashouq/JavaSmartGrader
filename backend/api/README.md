# API Layer

FastAPI REST API for JavaSmartGrader. Handles authentication, course management, assignment and question lifecycle, submission handling, grading, and reporting.

## Module Structure

| File | Purpose |
|------|---------|
| `auth.py` | JWT token creation, verification, and role-based access control |
| `dependencies.py` | Shared `get_db` dependency (async SQLAlchemy session) |
| `routes/users.py` | User registration, login, and profile endpoints |
| `routes/courses.py` | Course CRUD and student enrollment |
| `routes/assignments.py` | Assignment CRUD |
| `routes/questions.py` | Question and testcase CRUD (nested under assignments) |
| `routes/submissions.py` | Submission creation and retrieval |
| `routes/grading.py` | Compile results, transcriptions, AI feedback, and grade management |
| `routes/confidence_flags.py` | OCR confidence flag management |
| `routes/generate_report.py` | Assignment report generation |

## Authentication

JWT bearer tokens. Obtain a token via `POST /users/login`, then pass it as:

```
Authorization: Bearer <token>
```

Tokens expire after **30 minutes**.

Role-based access:
- **student** — submit work, view own submissions and grades
- **instructor** — manage courses, assignments, questions, testcases, enrollment, view all submissions, assign grades

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

### Courses — `/courses`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/courses/` | Instructor | Create a new course |
| `GET` | `/courses/me` | Instructor | List own courses |
| `GET` | `/courses/{id}` | Any | Get course by ID |
| `PUT` | `/courses/{id}` | Instructor | Update course fields |
| `DELETE` | `/courses/{id}` | Instructor | Delete course |
| `POST` | `/courses/{id}/enroll/{student_id}` | Instructor | Enroll a student (must have student role) |
| `DELETE` | `/courses/{id}/enroll/{student_id}` | Instructor | Unenroll a student |

#### `POST /courses/`

Query params: `name`, `description` (optional)

Returns: `CourseBase` — `{ id, name, description, instructor_id }`

---

### Assignments — `/assignments`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/assignments/` | Instructor | Create a new assignment |
| `GET` | `/assignments/course/{course_id}` | Any | List assignments for a course |
| `GET` | `/assignments/{id}` | Any | Get assignment by ID |
| `PUT` | `/assignments/{id}` | Instructor | Update assignment fields |
| `DELETE` | `/assignments/{id}` | Instructor | Delete assignment |

#### `POST /assignments/`

Query params: `course_id`, `title`, `description` (optional), `due_date` (optional, ISO 8601)

Returns: `AssignmentBase` — `{ id, course_id, title, description, due_date, rubric_json }`

---

### Questions — `/assignments/{assignment_id}/questions`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `.../questions/` | Instructor | Create a question for the assignment |
| `GET` | `.../questions/` | Any | List all questions for the assignment |
| `GET` | `.../questions/{question_id}` | Any | Get a specific question |
| `PUT` | `.../questions/{question_id}` | Instructor | Update question text |
| `DELETE` | `.../questions/{question_id}` | Instructor | Delete a question |
| `POST` | `.../questions/{question_id}/testcases` | Instructor | Add a testcase to a question |
| `GET` | `.../questions/{question_id}/testcases` | Any | List testcases for a question |
| `DELETE` | `.../questions/{question_id}/testcases/{testcase_id}` | Instructor | Delete a testcase |

#### `POST .../questions/`

Query params: `question_text`

Returns: `QuestionBase` — `{ id, assignment_id, question_text }`

#### `POST .../questions/{question_id}/testcases`

Query params: `input_data`, `expected_output`

Returns: `{ "message": "Testcase added successfully" }`

---

### Submissions — `/submissions`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/submissions/` | Student | Submit an answer for a question |
| `GET` | `/submissions/me` | Any | List current user's submissions |
| `GET` | `/submissions/{id}` | Any | Get submission by ID |
| `GET` | `/submissions/assignment/{id}` | Instructor | List all submissions for an assignment |
| `PUT` | `/submissions/{id}/state` | Instructor | Update submission state |
| `DELETE` | `/submissions/{id}` | Student | Delete own submission |

#### `POST /submissions/`

Query params: `question_id`, `assignment_id`, `image_url` (optional)

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

---

### Confidence Flags — `/confidence-flags`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/confidence-flags/` | Instructor | Create a confidence flag |
| `GET` | `/confidence-flags/transcription/{transcription_id}` | Any | List flags for a transcription |
| `DELETE` | `/confidence-flags/{flag_id}` | Instructor | Delete a confidence flag |

#### `POST /confidence-flags/`

Query params: `transcription_id`, `text_segment`, `confidence_score`, `coordinates` (optional), `suggestions` (optional)

Returns: `ConfidenceFlagBase` — `{ id, transcription_id, text_segment, confidence_score, coordinates, suggestions }`

---

### Reports — `/reports`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/reports/assignment/{assignment_id}` | Instructor | Create a report for an assignment |
| `GET` | `/reports/assignment/{assignment_id}` | Any | List reports for an assignment |
| `GET` | `/reports/{report_id}` | Any | Get a specific report |
| `PUT` | `/reports/{report_id}` | Instructor | Update report text |
| `DELETE` | `/reports/{report_id}` | Instructor | Delete a report |

#### `POST /reports/assignment/{assignment_id}`

Query params: `report_text` (optional)

Returns: `GenerateReportBase` — `{ id, assignment_id, report_text }`
