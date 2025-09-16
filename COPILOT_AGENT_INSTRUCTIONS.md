# Copilot Coding Agent Instructions for BookmarkExtractor

## Project Overview
BookmarkExtractor is a Python-based application for extracting, categorizing, and managing bookmarks from various browsers. It includes modules for keyword extraction, topic modeling, dead link management, and a GUI for user interaction.

## Coding Agent Best Practices

### 1. Code Style
- Follow [PEP 8](https://peps.python.org/pep-0008/) for Python code style.
- Use 4 spaces for indentation.
- Prefer explicit imports over wildcard imports.
- Add docstrings to all public classes, methods, and functions.

### 2. Commit Messages
- Use clear, concise commit messages in imperative mood (e.g., "Add bookmark importer module").
- Reference related issues or features when relevant.

### 3. Pull Requests
- Group related changes in a single PR.
- Include a summary of changes and testing instructions in the PR description.
- Ensure all code passes linting and tests before submitting.

### 4. Testing
- Add or update tests for new features and bug fixes.
- Use `pytest` for running tests (if/when tests are present).

### 5. Dependency Management
- List all dependencies in `requirements.txt` and/or `requirements_Version2.txt`.
- Use the minimal required versions for dependencies.

### 6. Sensitive Data
- Do not commit API keys, credentials, or other sensitive data. Use `apikey.txt` for local secrets and add it to `.gitignore`.

### 7. Documentation
- Update `README.md` and `README_topic_modeling_Version2.md` as features change.
- Document new modules and major functions with clear docstrings.

### 8. File Organization
- Place new analyzers in `analyzers/`.
- Place new GUI components in `gui/`.
- Place new processing logic in `processing/`.
- Place new worker classes in `workers/`.
- Place configuration in `config/`.

### 9. Issue Tracking
- Reference issues in commits and PRs when applicable.
- Use GitHub Issues for feature requests and bug reports.

### 10. Communication
- Leave clear comments for complex logic or design decisions.

---

For more information, see [Best practices for Copilot coding agent in your repository](https://gh.io/copilot-coding-agent-tips).
