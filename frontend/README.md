# JavaSmartGrader Frontend

React frontend for instructors and students to manage courses, assignments, submissions, and grading workflows.

## Requirements

- Node.js 18+
- npm

## Install and Run

```bash
cd frontend
npm install
npm start
```

Development server: [http://localhost:3000](http://localhost:3000)

## Scripts

- `npm start` - Run development server
- `npm test` - Run tests in watch mode
- `npm run build` - Build production bundle
- `npm run eject` - Eject Create React App config (irreversible)

## Backend Connection

- API client is configured in `src/services/api.js`
- Default backend base URL: `http://localhost:8000`
- Start the API from `backend/` (see `backend/README.md`): `uv run task dev` (MinIO-friendly S3) or `uv run task local` (typical AWS-style S3 client)
- Student submission uploads use **multipart/form-data** (`question_id`, `assignment_id`, `file`) to `POST /submissions/`; see `src/services/submissionService.js` and dashboard upload pages.

## Tech Stack

- React 19
- React Router 7
- Tailwind CSS
- Axios
- Create React App

## Structure (High Level)

```text
frontend/
├── public/          # Static assets
├── src/components/  # Reusable UI pieces
├── src/context/     # Global auth/app context
├── src/layout/      # Shared page layouts
├── src/pages/       # Route-level pages
└── src/services/    # API client and service helpers
```
