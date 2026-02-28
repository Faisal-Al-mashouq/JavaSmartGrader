# JavaSmartGrader Frontend

React web application for the JavaSmartGrader system.

## Requirements

- Node.js 18+
- npm or yarn

## Installation

```bash
cd frontend
npm install
```

## Available Scripts

### `npm start`

Runs the app in development mode at [http://localhost:3000](http://localhost:3000).

### `npm test`

Launches the test runner in interactive watch mode.

### `npm run build`

Builds the app for production to the `build` folder.

### `npm run eject`

Ejects from Create React App (one-way operation).

## Project Structure

```
frontend/
├── public/                   # Static assets
├── src/
│   ├── components/
│   │   ├── Navbar.jsx        # Top navigation bar
│   │   └── ProtectedRoute.jsx# Auth-gated route wrapper
│   ├── context/
│   │   └── AuthContext.jsx   # Authentication context/provider
│   ├── layout/
│   │   ├── DashboardLayout.jsx
│   │   ├── InstructorLayout.jsx
│   │   └── MainLayout.jsx
│   ├── pages/
│   │   ├── Home.jsx
│   │   ├── Login.jsx
│   │   ├── Dashboard.jsx
│   │   └── dashboard/
│   │       ├── instructor/
│   │       │   ├── InstructorHome.jsx
│   │       │   ├── InstructorGrading.jsx
│   │       │   └── InstructorSubmissions.jsx
│   │       └── student/
│   │           ├── StudentHome.jsx
│   │           ├── StudentUpload.jsx
│   │           └── StudentSubmissions.jsx
│   ├── services/
│   │   └── api.js            # API client for backend communication
│   ├── App.js                # Main application component and routing
│   └── index.js              # Entry point
├── tailwind.config.js        # Tailwind CSS configuration
├── package.json              # Dependencies and scripts
└── README.md                 # This file
```

## Tech Stack

- React 19
- React Router v7
- Tailwind CSS
- Create React App

## Connecting to Backend

The backend API runs on port 8000. API calls are made via `src/services/api.js`.
