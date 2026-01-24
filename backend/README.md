# JavaSmartGrader Backend

Python backend service for the JavaSmartGrader application.

## Requirements

- Python 3.12+

## Installation

```bash
cd backend
pip install -e .
```

## Running the Server

```bash
python main.py
```

## Project Structure

```
backend/
├── main.py           # Application entry point
├── pyproject.toml    # Project configuration and dependencies
└── README.md         # This file
```

## Development

### Adding Dependencies

Edit `pyproject.toml` to add new dependencies:

```toml
[project]
dependencies = [
    "fastapi",
    "uvicorn",
]
```

Then reinstall:

```bash
pip install -e .
```

### Running Tests

```bash
pytest
```

## API Endpoints

*API endpoints will be documented here as they are developed.*

## Configuration

Environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `PORT` | Server port | `8000` |
| `DEBUG` | Enable debug mode | `false` |
