# Ymir Package Management Guide

Ymir provides a Go-style package manager that allows you to install dependencies directly from Git repositories (GitHub, GitLab, etc.).

## Table of Contents

1. [Quick Start](#quick-start)
2. [Commands](#commands)
3. [Dependency File Format](#dependency-file-format)
4. [Package Installation](#package-installation)
5. [Examples](#examples)

## Quick Start

```bash
# Add a dependency
ymir add github.com/user/awesome-lib

# Install all dependencies
ymir install

# List dependencies
ymir list

# Remove a dependency
ymir remove awesome-lib
```

## Commands

### `ymir add`

Add a dependency to your project and install it.

```bash
ymir add <repo_url> [--version VERSION] [--file FILE]
```

**Options:**
- `--version`: Specific version, tag, or branch to install (default: latest)
- `--file`: Dependency file to update (default: ymir_dependencies.toml)

**Examples:**
```bash
# Add latest version
ymir add github.com/user/math-lib

# Add specific version/tag
ymir add github.com/user/http-lib --version v1.2.3

# Add specific branch
ymir add github.com/user/dev-lib --version develop
```

### `ymir install`

Install dependencies from ymir_dependencies.toml.

```bash
ymir install [--file FILE]
```

**Options:**
- `--file`: Dependency file to install from (default: ymir_dependencies.toml)

**Examples:**
```bash
# Install from default file
ymir install

# Install from custom file
ymir install --file my_deps.toml
```

### `ymir list`

List all dependencies from ymir_dependencies.toml.

```bash
ymir list [--file FILE]
```

**Options:**
- `--file`: Dependency file to list from (default: ymir_dependencies.toml)

**Example:**
```bash
ymir list
```

Output:
```
Dependencies:
  - awesome-lib: github.com/user/awesome-lib
  - http-utils: v2.0.0
  - math-helpers: main
```

### `ymir remove`

Remove a dependency from ymir_dependencies.toml.

```bash
ymir remove <package_name> [--file FILE]
```

**Options:**
- `--file`: Dependency file to update (default: ymir_dependencies.toml)

**Note:** This only removes the dependency from the file. Cached packages remain in `~/.ymir/packages/`.

**Example:**
```bash
ymir remove awesome-lib
```

### `ymir run`

Run a Ymir script.

```bash
ymir run <file> [--verbosity LEVEL]
```

**Example:**
```bash
ymir run examples/main.ymr
ymir run app.ymr --verbosity DEBUG
```

### `ymir build`

Build a Ymir script into a binary executable.

```bash
ymir build [INPUT_FILE] [--output OUTPUT_FILE]
```

**Options:**
- `--output, -o`: Specify the output file path

**Examples:**
```bash
# Build with defaults (input: main.ymr, output: dist/<current_dir_name>)
ymir build

# Build specific file
ymir build src/app.ymr

# Build with custom output
ymir build src/app.ymr --output dist/myapp
```

## Dependency File Format

Ymir uses TOML files for dependency management.

### ymir_dependencies.toml

```toml
[package]
name = "my-project"
version = "1.0.0"

[dependencies]
# URL format (latest version)
"awesome-lib" = "github.com/user/awesome-lib"

# Specific version
"http-lib" = {url = "github.com/user/http-lib", version = "v1.2.3"}

# Specific branch
"dev-utils" = {url = "gitlab.com/team/dev-utils", version = "develop"}

# Using commit hash
"stable-lib" = {url = "github.com/org/stable-lib", version = "abc123"}
```

### Supported URL Formats

Ymir supports various repository URL formats:

```toml
# Short format (GitHub/GitLab)
"package-name" = "github.com/user/repo"
"package-name" = "gitlab.com/user/repo"

# Full HTTPS URL
"package-name" = "https://github.com/user/repo"
"package-name" = "https://gitlab.com/user/repo.git"

# With version specification
"package-name" = {url = "github.com/user/repo", version = "v1.0.0"}
```

### ymir_dependencies.lock

After running `ymir install`, a lock file is generated:

```json
{
  "awesome-lib": {
    "url": "github.com/user/awesome-lib",
    "version": "latest",
    "path": "/Users/username/.ymir/packages/awesome-lib"
  },
  "http-lib": {
    "url": "github.com/user/http-lib",
    "version": "v1.2.3",
    "path": "/Users/username/.ymir/packages/http-lib"
  }
}
```

This ensures reproducible builds.

## Package Installation

### Installation Process

1. **Parse repository URL**: Extract package name and provider
2. **Clone repository**: Clone to `~/.ymir/packages/<package_name>`
3. **Checkout version**: If specified, checkout the tag/branch/commit
4. **Verify**: Calculate and store checksums
5. **Update lock file**: Record exact versions installed

### Package Cache

Packages are cached globally in `~/.ymir/packages/`:

```
~/.ymir/
├── packages/
│   ├── awesome-lib/
│   ├── http-lib/
│   └── math-helpers/
├── checksums.txt
└── ...
```

### Version Resolution

Ymir supports multiple version specifications:

- `latest`: Uses the default branch (usually main/master)
- `v1.2.3`: Checks out the git tag
- `main` or `develop`: Checks out the branch
- `abc123`: Checks out the specific commit

## Examples

### Example 1: Starting a New Project

```bash
# Create project directory
mkdir my-ymir-project
cd my-ymir-project

# Create main script
cat > main.ymr << 'EOF'
module main

func main() {
    print("Hello, Ymir!")
}

main()
EOF

# Add dependencies
ymir add github.com/ymir-lang/stdlib-extended

# Install dependencies
ymir install

# Run
ymir run main.ymr
```

### Example 2: Using Installed Packages

After installing a package, you can import it:

```ymr
module myapp

# Import from installed package
import awesome_lib

func main() {
    # Use functions from the package
    result = awesome_lib.do_something()
    print(str(result))
}

main()
```

### Example 3: Managing Versions

```bash
# Add a specific version
ymir add github.com/user/api-client --version v2.1.0

# Update to a newer version
ymir add github.com/user/api-client --version v2.2.0

# Or edit ymir_dependencies.toml directly:
# "api-client" = {url = "github.com/user/api-client", version = "v2.2.0"}

# Reinstall with new version
ymir install
```

### Example 4: Working with Multiple Projects

Each project can have its own dependencies:

```
project-a/
├── main.ymr
├── ymir_dependencies.toml
└── ymir_dependencies.lock

project-b/
├── app.ymr
├── ymir_dependencies.toml
└── ymir_dependencies.lock
```

Packages are cached globally but each project tracks its own dependencies.

## Best Practices

### 1. Use Version Pinning

Pin dependencies to specific versions for reproducible builds:

```toml
# Good: specific version
"lib" = {url = "github.com/user/lib", version = "v1.2.3"}

# Avoid: latest (can change unexpectedly)
"lib" = "github.com/user/lib"
```

### 2. Commit Lock File

Always commit `ymir_dependencies.lock` to version control:

```bash
git add ymir_dependencies.toml ymir_dependencies.lock
git commit -m "Update dependencies"
```

### 3. Regular Updates

Periodically update dependencies:

```bash
# Check for updates manually
# Update version in ymir_dependencies.toml
ymir install
```

### 4. Minimal Dependencies

Only add dependencies you actually use:

```bash
# Before adding: "Do I really need this?"
ymir add github.com/user/lib
```

### 5. Document Dependencies

Add comments to explain why dependencies are needed:

```toml
[dependencies]
# HTTP client for API calls
"http-client" = {url = "github.com/user/http-client", version = "v2.0.0"}

# Math utilities for matrix operations
"math-ext" = {url = "github.com/org/math-ext", version = "v1.5.0"}
```

## Troubleshooting

### Issue: Package Not Found

```
Error: Package not found
```

**Solution:**
- Verify the repository URL is correct
- Check that you have network access
- Ensure Git is installed

### Issue: Version Not Found

```
Error: Version v1.2.3 not found
```

**Solution:**
- Check that the tag exists: `git ls-remote --tags <repo_url>`
- Try using a branch name instead
- Use `latest` to get the default branch

### Issue: Permission Denied

```
Error: Permission denied (publickey)
```

**Solution:**
- For private repos, ensure SSH keys are set up
- Use HTTPS URLs if you don't have SSH access
- Check repository permissions

## Future Enhancements

Planned features for future releases:

- Semantic version resolution
- Dependency conflict resolution
- Private repository authentication
- Package registry support
- Dependency graph visualization
- Automated security updates

## See Also

- [Syntax Guidelines](syntax_guidelines.md)
- [Concurrency Guide](concurrency.md)
- [HTTP Server Guide](http_server.md)

