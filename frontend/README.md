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

The page will reload when you make changes.

### `npm test`

Launches the test runner in interactive watch mode.

### `npm run build`

Builds the app for production to the `build` folder.

### `npm run eject`

Ejects from Create React App (one-way operation).

## Project Structure

```
frontend/
├── public/              # Static assets
├── src/
│   ├── App.js           # Main application component
│   ├── App.css          # Application styles
│   ├── index.js         # Entry point
│   └── index.css        # Global styles
├── package.json         # Dependencies and scripts
└── README.md            # This file
```

## Tech Stack

- React 19
- Create React App
- Testing Library

## Development

### Adding Components

Create new components in the `src/` directory:

```jsx
// src/components/GradeDisplay.js
function GradeDisplay({ score, maxScore }) {
  return (
    <div className="grade-display">
      <span>{score}</span> / <span>{maxScore}</span>
    </div>
  );
}

export default GradeDisplay;
```

### Connecting to Backend

The backend API runs on port 8000. Configure a proxy in `package.json`:

```json
{
  "proxy": "http://localhost:8000"
}
```

Then make API calls:

```jsx
fetch('/api/submissions')
  .then(res => res.json())
  .then(data => console.log(data));
```

## Testing

Run tests with:

```bash
npm test
```

Write tests using Testing Library:

```jsx
import { render, screen } from '@testing-library/react';
import App from './App';

test('renders app', () => {
  render(<App />);
  expect(screen.getByText(/learn react/i)).toBeInTheDocument();
});
```
