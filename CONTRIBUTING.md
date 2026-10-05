# Contributing to StudyLens

Thank you for your interest in contributing to StudyLens! StudyLens is a private, local-AI adaptive learning tool designed to evaluate student written explanations for Software Engineering concepts.

---

## 1. Code of Conduct

All contributors are expected to adhere to our [`CODE_OF_CONDUCT.md`](file:///C:/Users/Microsoft/Desktop/StudyLens-Antigravity/CODE_OF_CONDUCT.md). Please read it before participating.

---

## 2. Getting Started & Local Setup

### Prerequisites
* **Python**: 3.10 or newer
* **Node.js**: 18.0 or newer
* **Ollama**: Installed and running locally
* **Model**: `ollama pull gemma3:1b`

### Backend Setup
```powershell
cd backend
python -m venv .venv
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# Linux/macOS:
# source .venv/bin/activate

python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### Frontend Setup
In a separate terminal window:
```powershell
cd frontend
npm install
npm run dev
```

---

## 3. How to Run Tests

Before submitting any pull request, verify that all backend tests and frontend builds pass cleanly:

### Backend Test Suite
```powershell
python -m pytest backend/tests/
```

### Evaluation Suite
```powershell
python evaluation/run_evaluation.py
```

### Frontend Production Build
```powershell
cd frontend
npm run build
```

---

## 4. Development & Architecture Principles

* **Separation of AI and Mastery Logic:**
  - The local LLM (`Gemma 3:1B`) is strictly an **interpreter** for student written answers.
  - All mastery calculations, level boundaries, retest decisions, and question selections must remain in **deterministic Python services** (`mastery_service.py` and `retest_service.py`).
* **No Cloud AI Dependencies:**
  - Do not introduce dependencies on external paid cloud AI APIs (OpenAI, Anthropic, cloud Gemini).
* **No Accidental Secrets or Database Commits:**
  - Do not commit `.env` files, API keys, or `.db` database files.
* **Vanilla CSS Styling:**
  - The frontend uses standard CSS modules / plain CSS. Do not add utility CSS frameworks like Tailwind CSS without prior discussion.

---

## 5. Potential Contribution Ideas

Looking for ways to contribute? Here are several high-value areas for future enhancement:

1. **Expand Software Engineering Content:** Add new Software Engineering concepts (e.g. Design Patterns, Refactoring, Database Normalization) and validated question sets to `app/seed.py`.
2. **Evaluation Dataset Expansion:** Add more edge-case student answers (partial explanations, syntax queries) to `evaluation/test_cases.json`.
3. **Alternative Local Model Support:** Implement adapters for other open-weight local models (e.g. Llama 3, Phi-3) within `app/ai/ollama_client.py`.
4. **Mastery Visualization Enhancements:** Expand chart visualizations on the frontend Progress page using vanilla SVG or lightweight charting libraries.

---

## 6. Pull Request & Commit Workflow

1. Fork the repository and create a feature branch (`git checkout -b feature/my-feature`).
2. Implement your changes following existing code style and documentation practices.
3. Write unit tests for new backend logic.
4. Ensure `pytest` and `npm run build` pass without warnings or errors.
5. Commit your changes with clear, descriptive commit messages.
6. Open a Pull Request on GitHub describing the motivation and testing steps.
