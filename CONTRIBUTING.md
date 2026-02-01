# Contributing to MedAgentBench Green Agent

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## Development Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd MedAgentBench
   ```

2. **Install dependencies**
   ```bash
   pip install -e ".[test]"
   ```

3. **Set up environment**
   ```bash
   cp .env.example .env
   # Edit .env and add your GOOGLE_API_KEY
   ```

4. **Run tests**
   ```bash
   pytest tests/ -v
   ```

## Code Style

- Follow PEP 8 style guidelines
- Use type hints where appropriate
- Write docstrings for all public functions and classes
- Keep functions focused and single-purpose (following Karpathy principles)

## PocketFlow Guidelines

When adding new nodes:

1. **Follow the prep → exec → post pattern**
   - `prep`: Read from shared store
   - `exec`: Compute (no shared access)
   - `post`: Write to shared store, return action

2. **Keep exec() pure**
   - No shared store access in exec()
   - Should be idempotent if retries enabled
   - Let Node's retry mechanism handle exceptions

3. **Use clear action names**
   - Return "default" for normal flow
   - Use descriptive names for branches ("valid", "invalid", "success", "failure")

## Testing

- Write tests for all new nodes and flows
- Use pytest fixtures for common test data
- Test both success and failure paths
- Mock external dependencies (A2A calls, LLM calls)

## Pull Request Process

1. Create a feature branch from `main`
2. Make your changes with clear, atomic commits
3. Add tests for new functionality
4. Update documentation as needed
5. Ensure all tests pass
6. Submit a pull request with a clear description

## Commit Messages

Follow conventional commits:
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `test:` Test changes
- `refactor:` Code refactoring
- `chore:` Build/tooling changes

Example:
```
feat: add support for batch task processing

- Implement BatchTaskNode for multiple task evaluation
- Add tests for batch processing
- Update documentation
```

## Adding New Tasks

1. Add task definition to `src/nodes.py` in `SAMPLE_TASKS`
2. Include ground truth with answer, readonly flag, and post_count
3. Add test cases in `tests/test_nodes.py`
4. Update documentation

## Questions?

Open an issue for:
- Bug reports
- Feature requests
- Questions about implementation
- Documentation improvements

Thank you for contributing! 🙏
