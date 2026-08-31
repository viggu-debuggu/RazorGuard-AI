# Contributing to RazorGuard AI

Thank you for your interest in contributing to RazorGuard AI! Follow these guidelines to get started.

## Development Setup

1. **Virtual Environment**: Create and activate a Python virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```
2. **Install Dependencies**: Install the required development dependencies:
   ```bash
   pip install -r backend/requirements.txt
   ```
3. **Database Setup**: By default, the application runs on SQLite (`razorguard.db`) in development, but switches to PostgreSQL in production.

## Testing Guidelines

Before submitting any code changes, ensure all tests pass:
```bash
# Run the pytest suite
python -m pytest

# Run ML model training validation
python ml/train.py

# Run RAG retrieval quality evaluation
python rag/eval_rag.py
```

## Pull Request Process

1. Create a new feature branch for your changes.
2. Maintain clean, descriptive commit messages.
3. Ensure no credentials or secrets are committed.
4. Verify all tests pass locally and in the GitHub Actions CI pipeline.
5. Submit a pull request detailing the changes and linking any related issues.
