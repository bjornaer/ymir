# Contributing to Ymir

Thank you for your interest in contributing to Ymir! This document provides guidelines and instructions for contributing to the project.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR_USERNAME/ymir.git`
3. Install dependencies: `poetry install`
4. Create a new branch: `git checkout -b feature/your-feature-name`

## Development Guidelines

### Code Style
- Follow PEP 8 style guidelines
- Use meaningful variable and function names
- Add docstrings to functions and classes
- Keep functions focused and single-purpose
- Use type hints where possible

### Testing
- Write unit tests for new features
- Ensure all tests pass before submitting: `poetry run pytest`
- Aim for good test coverage
- Include edge cases in your tests

### Commit Messages
- Use clear and descriptive commit messages
- Start with a verb in present tense (e.g., "Add", "Fix", "Update")
- Reference issue numbers when applicable
- Keep commits focused and atomic

## Pull Request Process

1. Update documentation if needed
2. Run all tests and ensure they pass
3. Update the README.md if necessary
4. Submit a pull request with a clear description of changes
5. Link any relevant issues
6. Wait for review and address any feedback

## Adding New Features

When adding new features to Ymir:

1. First open an issue describing the feature
2. Discuss implementation approach with maintainers
3. Follow the language design principles
4. Include appropriate tests and documentation
5. Update examples if relevant

## Bug Reports

When reporting bugs:

1. Use the bug report template
2. Include a minimal reproducible example
3. Specify your environment details
4. Describe expected vs actual behavior
5. Include any relevant error messages

## Code Review Process

- All code changes require review
- Address reviewer feedback promptly
- Keep discussions focused and professional
- Be open to suggestions and improvements

## Development Environment

- Use Poetry for dependency management
- Recommended IDE: VS Code with Python extension
- Enable linting (flake8, mypy)
- Configure git hooks for pre-commit checks

## Language Features

When working on language features:

1. Follow the parser implementation in `ymir/core/parser.py`
2. Maintain consistency with existing syntax
3. Document new language features thoroughly
4. Include examples in test files

## Questions or Need Help?

- Open a discussion in GitHub Discussions
- Check existing issues and discussions first
- Be clear and provide context
- Be patient and respectful

## License

By contributing to Ymir, you agree that your contributions will be licensed under the MIT License.
