# JavaSmartGrader

An automated grading system for Java programming assignments, featuring a Python backend and React frontend.

## Project Structure

```
JavaSmartGrader/
├── backend/          # Python API server
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

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Commit your changes (`git commit -m 'Add your feature'`)
4. Push to the branch (`git push origin feature/your-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
