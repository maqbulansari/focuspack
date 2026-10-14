# Contributing to focuspack

Thank you for your interest in contributing to **focuspack**! We welcome bug fixes, documentation improvements, new features, and community suggestions.

---

## 🛠️ Development Setup

### 1. Prerequisites
- Python 3.9+ (Python 3.10+ recommended)
- `git`

### 2. Clone the Repository
```bash
git clone https://github.com/maqbulansari/focuspack.git
cd focuspack
```

### 3. Create a Virtual Environment
```bash
python -m venv .venv

# On Linux/macOS:
source .venv/bin/activate

# On Windows:
.venv\Scripts\activate
```

### 4. Install Dependencies in Editable Mode
```bash
pip install -e ".[dev,all]"
```

---

## 🧪 Running Tests & Linting

### Run Test Suite
```bash
pytest
```

### Run Tests with Coverage
```bash
pytest --cov=focuspack
```

### Code Formatting and Linting
We use [Ruff](https://github.com/astral-sh/ruff) for fast, consistent linting and formatting:
```bash
ruff check .
ruff format .
```

---

## 🚀 Submitting a Pull Request

1. **Create a topic branch:**
   ```bash
   git checkout -b feature/my-new-feature
   ```
2. **Make your changes:**
   - Write clean, type-annotated code.
   - Add unit tests under `tests/` covering new functionality.
3. **Verify tests pass:**
   ```bash
   pytest
   ```
4. **Commit with conventional messages:**
   ```bash
   git commit -m "feat: add support for Go interface extraction"
   ```
5. **Push and open a PR** against the `main` branch.

---

## 🐛 Reporting Bugs & Requesting Features

- Use GitHub Issues to submit reports.
- Include Python version, OS, exact command run, and error output where applicable.
- For feature requests, explain the use case and expected developer workflow.
