# Contributing to Ymir

Thank you for your interest in contributing to Ymir! This document provides guidelines and instructions for contributing to the project.

## Getting Started

> **Ymir is mid-rewrite.** Read [`PLAN.md`](PLAN.md) before starting — it has the
> current phase, what is blocked, and what is not worth working on yet. The language
> itself is defined by [`docs/spec/`](docs/spec/), which is normative.

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR_USERNAME/ymir.git`
3. Create a new branch: `git checkout -b feature/your-feature-name`

The Python implementation in `ymir-legacy-py/` is **frozen**. Please do not send
fixes for it — its bugs are documentation for the rewrite, catalogued in
[`ymir-legacy-py/README.md`](ymir-legacy-py/README.md).

## Development Guidelines

### Code Style
- Go code: standard `gofmt`, no exceptions
- Use meaningful variable and function names
- Add docstrings to functions and classes
- Keep functions focused and single-purpose
- Use type hints where possible

### Testing
- Language behavior is tested by the conformance suite, not by unit tests:
  `python3 conformance/run.py --ymir "./bin/ymir run"`
- **Any change to language behavior needs a conformance case.** A rule with no case
  is not a rule. See [`conformance/README.md`](conformance/README.md).
- Never weaken a conformance case to make code pass. Fix the code, or change the
  spec deliberately and say so in the commit message.
- Unit tests are for compiler internals, where the conformance suite cannot reach.

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

1. **Find the rule in [`docs/spec/`](docs/spec/) first.** If the behavior is not
   specified, that is the finding — open it as an open question rather than deciding
   it in code. Inventing semantics in an implementation is how the previous one
   ended up with two of them.
2. Changing the language means changing the spec chapter **and** the conformance
   cases, in a commit that says what it invalidates.
3. Do not add a second execution engine or a fallback fast path. The legacy
   implementation's worst bug — `func main()` running under one engine and silently
   doing nothing under the other — came from exactly that.
4. Check the locked decisions in [`docs/spec/00-overview.md`](docs/spec/00-overview.md)
   before proposing anything that contradicts one.

## Questions or Need Help?

- Open a discussion in GitHub Discussions
- Check existing issues and discussions first
- Be clear and provide context
- Be patient and respectful

## License

By contributing to Ymir, you agree that your contributions will be licensed under the MIT License.
