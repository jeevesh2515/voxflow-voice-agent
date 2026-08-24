# Contributing to VoxFlow Voice Agent

Thank you for your interest in contributing to **VoxFlow Voice Agent**! We welcome contributions from the community to help make voice operations for supply chains faster, more reliable, and accessible.

---

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Local Development Setup](#local-development-setup)
- [Development Workflow](#development-workflow)
  - [Branch Naming](#branch-naming)
  - [Commit Message Conventions](#commit-message-conventions)
- [Testing & Quality Assurance](#testing--quality-assurance)
  - [Backend Tests & Linting](#backend-tests--linting)
  - [Frontend Tests & Build](#frontend-tests--build)
- [Pull Request Process](#pull-request-process)
- [Security Disclosures](#security-disclosures)

---

## 📜 Code of Conduct

Please review our [Code of Conduct](CODE_OF_CONDUCT.md) before contributing. All participants are expected to adhere to its standards to maintain a welcoming and inclusive environment.

---

## 🚀 Getting Started

### Prerequisites

- **Python:** 3.11+ (Python 3.12/3.14 compatible)
- **Node.js:** 20+ or 22+ (LTS recommended)
- **Package Manager:** `npm` or `pnpm`
- **Database:** SQLite (local development) / PostgreSQL 15+ (production / Supabase)

### Local Development Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/jeevesh2515/voxflow-voice-agent.git
   cd voxflow-voice-agent
   ```

2. **Backend Setup (`apps/api`):**
   ```bash
   cd apps/api
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Frontend Setup (`apps/web`):**
   ```bash
   cd ../web
   npm install
   ```

4. **Environment Configuration:**
   Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

5. **Start Dev Servers:**
   - **Backend API:**
     ```bash
     cd apps/api
     uvicorn voxflow_api.main:app --host 0.0.0.0 --port 8000 --reload
     ```
   - **Frontend App:**
     ```bash
     cd apps/web
     npm run dev
     ```

---

## 🛠️ Development Workflow

### Branch Naming

Follow conventional branch naming formats:
- `feat/<feature-name>` for new features or capabilities
- `fix/<bug-name>` for bug fixes and patches
- `docs/<doc-topic>` for documentation updates
- `perf/<optimization>` for performance improvements
- `refactor/<module>` for structural code refactoring

### Commit Message Conventions

We use [Conventional Commits](https://www.conventionalcommits.org/):
```text
<type>(<scope>): <short description>

[optional body]
```
Examples:
- `feat(telephony): add latency telemetry to connect turn responses`
- `fix(groq): implement exponential backoff on HTTP 429 rate limits`
- `docs(readme): update community standards checklist`

---

## 🧪 Testing & Quality Assurance

Before submitting any Pull Request, ensure all tests and lint checks pass cleanly.

### Backend Tests & Linting

```bash
cd apps/api

# Run full test suite
pytest tests/ -q

# Run fast linter
ruff check .

# Run auto-formatter check
ruff format --check .
```

### Frontend Tests & Build

```bash
cd apps/web

# Run ESLint
npm run lint

# Verify static production build
npm run build
```

---

## 📥 Pull Request Process

1. Fork the repository and create your branch from `main`.
2. Ensure new features are covered by dedicated unit/integration tests in `apps/api/tests/`.
3. Update relevant documentation (`README.md`, `DAY_TRACKER.md`, `ARCHITECTURE.md`) when modifying interfaces.
4. Verify zero lint errors and 100% test pass rate.
5. Push to your fork and submit a Pull Request describing your changes using our [PR Template](.github/PULL_REQUEST_TEMPLATE.md).
6. A project maintainer will review your submission promptly.

---

## 🔒 Security Disclosures

If you discover a security vulnerability, please refer to our [Security Policy](SECURITY.md) to report it privately. Do not disclose vulnerabilities via public GitHub issues.
