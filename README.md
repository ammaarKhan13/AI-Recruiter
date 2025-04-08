# AI Recruiter

A comprehensive AI-powered recruitment system that automates and enhances the hiring process using multiple AI agents.

## Features

- **Multi-Agent System**: Coordinated AI agents that handle different aspects of the recruitment process
- **Job Description Analysis**: Extracts key requirements, responsibilities, and skills from job postings
- **Resume Parsing**: Automatically extracts structured information from candidate resumes
- **Skill Matching**: Uses semantic understanding to match candidates with job requirements
- **Knowledge Graph**: Represents skills and their relationships for intelligent recommendations
- **Interview Scheduling**: Generates personalized interview invitations and manages scheduling
- **Analytics Dashboard**: Provides insights into the recruitment pipeline
- **Feedback Loop**: Continuously improves the system based on hiring outcomes

## Tech Stack

- **Backend**: FastAPI, Python 3.9+
- **Database**: SQLite, Neo4j
- **AI/ML**: Ollama (LLaMA2), Sentence Transformers
- **Frontend**: React, TypeScript, Material-UI
- **Development**: Black, Flake8, MyPy

## Prerequisites

- Python 3.9 or higher
- SQLite
- Neo4j 4.4 or higher (optional, for knowledge graph features)
- Node.js 16 or higher (for frontend)
- Ollama installed and running locally

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/ai-recruiter.git
cd ai-recruiter
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
# On Windows
venv\Scripts\activate
# On macOS/Linux
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your settings
```

5. Start Ollama service and pull required models:
```bash
# Start Ollama (if not already running)
ollama serve

# Pull the models
ollama pull llama2
```

6. Initialize the database:
```bash
cd backend
python init_db.py
```

## Usage

1. Start the backend server:
```bash
cd backend
uvicorn main:app --reload
```

2. Start the frontend development server (if available):
```bash
cd frontend
npm install
npm start
```

3. Access the application at http://localhost:3000

4. API documentation is available at http://localhost:8000/docs

## Project Structure

```
ai-recruiter/
├── backend/
│   ├── agents/             # AI agents for different tasks
│   ├── api/                # FastAPI routes and endpoints
│   ├── db/                 # Database models and connection
│   ├── knowledge_graph/    # Neo4j graph integration
│   └── utils/              # Utility functions
├── frontend/               # React frontend application
├── tests/                  # Test suite
├── data/                   # Example data and datasets
├── models/                 # Saved models and embeddings
└── notebooks/              # Jupyter notebooks for experimentation
```

## Development

Run tests:
```bash
pytest
```

Format code:
```bash
black backend
```

Run linting:
```bash
flake8 backend
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Ollama for providing local LLM capabilities
- Neo4j for graph database support
- FastAPI for the high-performance API framework 