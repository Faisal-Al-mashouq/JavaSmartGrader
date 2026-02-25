# JavaSmartGrader

An automated grading system for Java programming assignments, featuring a Python backend and React frontend.

## Project Structure

```
JavaSmartGrader/
├── backend/          # Python API server
│   └── sandbox/      # Async sandbox worker (Docker-based Java compile & execute)
├── frontend/         # React web application
├── dataset/          # Training and test datasets
├── experiments/      # Experiment logs and results
└── model/            # Trained model files
```

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 18+
- npm or yarn
- Docker (for sandbox worker)
- Redis (for job queue)

### Backend Setup

```bash
cd backend
pip install -e .
python main.py
```

### Frontend Setup

```bash
cd frontend
npm install
npm start
```

The frontend runs at http://localhost:3000

## Features

- Automated grading of Java code submissions
- Customizable grading criteria and rubrics
- Detailed feedback generation for students
- Web-based interface for managing submissions
- API for integration with learning management systems

## Documentation

- [Backend Documentation](backend/README.md)
- [Frontend Documentation](frontend/README.md)

## Contributing

### Setup

1. Fork the repository
2. Install the pre-commit hooks (one-time):
   ```bash
   pip install pre-commit
   pre-commit install
   ```

### Workflow

1. Create a feature branch (`git checkout -b feature/your-feature`)
2. Commit your changes (`git commit -m 'Add your feature'`)
3. Push to the branch (`git push origin feature/your-feature`)
4. Open a Pull Request

### Code Style

This project uses [EditorConfig](https://editorconfig.org/) to enforce consistent formatting (indentation, line endings, charset, final newline). Most editors support it natively or via a plugin.

**Backend (Python)** uses [Ruff](https://docs.astral.sh/ruff/) for linting and [Black](https://black.readthedocs.io/) for formatting. Both are configured in `backend/pyproject.toml`.

- **Pre-commit hooks** — Automatically run Ruff, Black, and EditorConfig checks before each commit. Install with the setup steps above.
- **CI checks** — A GitHub Action runs all linters on every PR and push to `main`. PRs that violate the rules will show a failing check.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
