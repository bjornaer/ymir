# Ymir Release Process

This document describes the process for creating and publishing new releases of Ymir.

## Version Numbering

Ymir follows [Semantic Versioning](https://semver.org/) (MAJOR.MINOR.PATCH):

- **MAJOR**: Incompatible API changes
- **MINOR**: New functionality in a backwards-compatible manner
- **PATCH**: Backwards-compatible bug fixes

### Version Examples
- `v0.1.0` - Initial release
- `v0.2.0` - New features added
- `v0.2.1` - Bug fixes
- `v1.0.0` - First stable release

## Pre-Release Checklist

Before creating a release, ensure the following:

### 1. Code Quality
- [ ] All tests pass: `poetry run pytest`
- [ ] Test coverage > 75%: `poetry run pytest --cov`
- [ ] Linting passes: `poetry run ruff check .`
- [ ] Code formatted: `poetry run black .`
- [ ] No linter errors: `poetry run isort --check-only .`

### 2. Documentation
- [ ] README.md is up-to-date
- [ ] CHANGELOG.md is updated
- [ ] All new features documented
- [ ] Example scripts updated
- [ ] API documentation current

### 3. Version Updates
- [ ] Update version in `pyproject.toml`
- [ ] Update version in documentation
- [ ] Update CHANGELOG.md with release notes

### 4. Testing
- [ ] Run full test suite
- [ ] Test example scripts
- [ ] Test CLI commands
- [ ] Manual smoke tests

## Creating a Release

### Step 1: Update Version

Update the version in `pyproject.toml`:

```toml
[tool.poetry]
name = "ymir"
version = "0.2.0"  # Update this
```

### Step 2: Commit Changes

```bash
git add pyproject.toml CHANGELOG.md
git commit -m "Prepare release v0.2.0"
git push origin main
```

### Step 3: Create Git Tag

```bash
# Create annotated tag
git tag -a v0.2.0 -m "Release v0.2.0: Description of major changes"

# Push tag to trigger release workflow
git push origin v0.2.0
```

### Step 4: Create GitHub Release

1. Go to https://github.com/bjornaer/ymir/releases
2. Click "Draft a new release"
3. Select the tag you just created (v0.2.0)
4. Release title: "Ymir v0.2.0"
5. Description: Copy relevant sections from CHANGELOG.md
6. Click "Publish release"

The GitHub Actions workflow will automatically:
- Build Python wheels
- Build standalone executables for all platforms
- Generate checksums
- Attach all artifacts to the release

### Step 5: Verify Release

After the workflow completes:

1. Check that all artifacts are attached:
   - `ymir-*.whl` (Python wheel)
   - `ymir-*.tar.gz` (Source distribution)
   - `ymir-linux-*` (Linux executable)
   - `ymir-macos-*` (macOS executables)
   - `ymir-windows-*.exe` (Windows executable)
   - `SHA256SUMS` (Checksums file)
   - `requirements.txt`

2. Test the release:
   ```bash
   # Test Python package
   pip install ymir==0.2.0
   ymir --version
   
   # Test executable
   wget https://github.com/bjornaer/ymir/releases/download/v0.2.0/ymir-linux-x86_64
   chmod +x ymir-linux-x86_64
   ./ymir-linux-x86_64 --version
   ```

## Homebrew Release Process

After creating a GitHub release, the Homebrew formula is updated automaticaly:

### Automatic (via CI)

The release workflow attempts to update the formula automatically. Check the workflow logs for the generated formula.

### Manual Steps

1. The workflow will output a `ymir.rb` formula
2. Copy the formula contents
3. Create a PR to your homebrew tap:

```bash
# Clone your tap
git clone https://github.com/bjornaer/homebrew-ymir
cd homebrew-ymir

# Create Formula directory if it doesn't exist
mkdir -p Formula

# Copy the generated formula
# (from workflow artifacts or create manually)
cp /path/to/ymir.rb Formula/ymir.rb

# Commit and push
git add Formula/ymir.rb
git commit -m "Update Ymir to v0.2.0"
git push origin main
```

4. Test the formula:

```bash
# Test installation
brew install --build-from-source bjornaer/ymir/ymir

# Test the installation
ymir --version
ymir run examples/example.ymr

# Audit the formula
brew audit --strict bjornaer/ymir/ymir
```

## Post-Release Tasks

### 1. Announce Release

- [ ] Post on social media
- [ ] Update project website
- [ ] Notify users via mailing list
- [ ] Update GitHub discussions

### 2. Monitor

- [ ] Watch for issues related to new release
- [ ] Monitor download statistics
- [ ] Check CI/CD status
- [ ] Review user feedback

### 3. Documentation

- [ ] Update online documentation
- [ ] Update getting started guide
- [ ] Update installation instructions

## Hotfix Releases

For critical bug fixes:

1. Create a hotfix branch from the release tag:
   ```bash
   git checkout -b hotfix/v0.2.1 v0.2.0
   ```

2. Fix the bug and commit:
   ```bash
   git commit -m "Fix critical bug in X"
   ```

3. Update version to patch level (v0.2.1)

4. Create tag and release:
   ```bash
   git tag -a v0.2.1 -m "Hotfix: Fix critical bug"
   git push origin hotfix/v0.2.1
   git push origin v0.2.1
   ```

5. Merge hotfix back to main:
   ```bash
   git checkout main
   git merge hotfix/v0.2.1
   git push origin main
   ```

## Release Schedule

- **Major releases**: As needed for breaking changes
- **Minor releases**: Monthly or as features are ready
- **Patch releases**: As needed for critical bugs

## Rollback Procedure

If a release has critical issues:

1. Mark the release as pre-release on GitHub
2. Add warning to release notes
3. Create hotfix release with fix
4. Optionally delete the problematic release

## Automation

The release process is automated via GitHub Actions:

- `.github/workflows/release.yml` - Main release workflow
- `.github/workflows/tests.yml` - CI tests

Secrets required:
- `GITHUB_TOKEN` (automatically provided)
- `HOMEBREW_TAP_TOKEN` (for homebrew updates)

## Troubleshooting

### Build Fails

1. Check GitHub Actions logs
2. Test build locally:
   ```bash
   poetry run python scripts/build_executable.py
   ```
3. Fix issues and create new tag

### Wrong Artifacts

1. Delete the release and tag
2. Fix the issue
3. Create new tag and release

### Homebrew Formula Issues

1. Test formula locally
2. Fix formula syntax
3. Update tap repository manually

## Contact

For release questions:
- Email: max.schulkin@gmail.com
- GitHub Issues: https://github.com/bjornaer/ymir/issues

