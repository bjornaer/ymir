import hashlib
import json
import logging
import os
import subprocess
from typing import Dict

import toml

logger = logging.getLogger("ymir.dependency_manager")

PACKAGE_CACHE_DIR = os.path.expanduser("~/.ymir/packages")
CHECKSUM_FILE = os.path.expanduser("~/.ymir/checksums.txt")
LOCK_FILE = "ymir_dependencies.lock"


def get_checksum(file_path):
    """Calculate the SHA256 checksum of a file."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def verify_checksum(package_name, file_path):
    """Verify the checksum of a file against the stored checksums."""
    checksum = get_checksum(file_path)
    with open(CHECKSUM_FILE, "r") as f:
        for line in f:
            name, stored_checksum = line.strip().split()
            if name == package_name:
                return checksum == stored_checksum
    return False


def save_checksum(package_name, file_path):
    """Save the checksum of a file to the checksum file."""
    checksum = get_checksum(file_path)
    with open(CHECKSUM_FILE, "a") as f:
        f.write(f"{package_name} {checksum}\n")


def parse_repo_url(repo_url: str) -> tuple:
    """
    Parse a repository URL to extract the package name.

    Supports:
    - github.com/user/repo
    - gitlab.com/user/repo
    - https://github.com/user/repo
    - https://github.com/user/repo.git
    """
    # Remove .git suffix if present
    repo_url = repo_url.replace(".git", "")

    # Extract package name from URL
    parts = repo_url.rstrip("/").split("/")
    if len(parts) >= 2:
        package_name = parts[-1]
        provider = parts[-3] if len(parts) >= 3 else "unknown"
    else:
        package_name = repo_url
        provider = "unknown"

    return package_name, provider


def clone_repository(repo_url: str, dest_dir: str, version: str = "latest"):
    """Clone a git repository at a specific version."""
    os.makedirs(PACKAGE_CACHE_DIR, exist_ok=True)

    logger.info(f"Cloning {repo_url} to {dest_dir}")

    # Add https:// if not present and it's a github/gitlab URL
    if not repo_url.startswith(("http://", "https://", "git@")):
        repo_url = f"https://{repo_url}"

    # Clone the repository
    subprocess.run(["git", "clone", repo_url, dest_dir], check=True, capture_output=True)

    # Checkout specific version if not latest
    if version != "latest":
        subprocess.run(["git", "checkout", version], cwd=dest_dir, check=True, capture_output=True)
        logger.info(f"Checked out version {version}")


def build_package(package_dir: str):
    """Build the Ymir package (placeholder for future build logic)."""
    # For now, packages are just .ymr files that can be imported directly
    # In the future, this could compile to bytecode or native binaries
    logger.info(f"Package {package_dir} is ready to use")


def install_dependency(repo_url: str, version: str = "latest"):
    """Install a Ymir library from a repository URL."""
    package_name, provider = parse_repo_url(repo_url)
    dest_dir = os.path.join(PACKAGE_CACHE_DIR, package_name)

    if os.path.exists(dest_dir):
        logger.info(f"Package {package_name} is already installed at {dest_dir}")
        return dest_dir

    try:
        clone_repository(repo_url, dest_dir, version)
        build_package(dest_dir)
        save_checksum(package_name, dest_dir)
        logger.info(f"Successfully installed {package_name}")
        return dest_dir
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to install {package_name}: {e}")
        raise RuntimeError(f"Failed to install {package_name}: {e}")


def install_dependencies_from_file(file_path: str = "ymir_dependencies.toml"):
    """Install dependencies listed in a TOML file."""
    if not os.path.exists(file_path):
        logger.warning(f"Dependency file {file_path} not found")
        return

    with open(file_path, "r") as file:
        config = toml.load(file)

    dependencies = config.get("dependencies", {})
    if not dependencies:
        logger.info("No dependencies to install")
        return

    lock_data = {}
    for package, version_or_url in dependencies.items():
        # Version or URL can be a string
        if isinstance(version_or_url, str):
            # Check if it's a URL or a version
            if "/" in version_or_url:
                repo_url = version_or_url
                version = "latest"
            else:
                # It's just a version, need to construct URL from package name
                repo_url = package
                version = version_or_url
        else:
            # It's a dict with version and possibly url
            repo_url = version_or_url.get("url", package)
            version = version_or_url.get("version", "latest")

        logger.info(f"Installing {package} from {repo_url} (version: {version})")
        dest_dir = install_dependency(repo_url, version)

        # Record in lock file
        lock_data[package] = {"url": repo_url, "version": version, "path": dest_dir}

    # Write lock file
    with open(LOCK_FILE, "w") as f:
        json.dump(lock_data, f, indent=2)
    logger.info(f"Dependencies locked in {LOCK_FILE}")


def add_dependency(repo_url: str, version: str = "latest", file_path: str = "ymir_dependencies.toml"):
    """Add a dependency to the dependencies file."""
    package_name, _ = parse_repo_url(repo_url)

    # Create file if it doesn't exist
    if not os.path.exists(file_path):
        config = {"package": {"name": "", "version": "0.1.0"}, "dependencies": {}}
    else:
        with open(file_path, "r") as f:
            config = toml.load(f)

    # Ensure dependencies section exists
    if "dependencies" not in config:
        config["dependencies"] = {}

    # Add the dependency
    config["dependencies"][package_name] = repo_url if version == "latest" else {"url": repo_url, "version": version}

    # Write back to file
    with open(file_path, "w") as f:
        toml.dump(config, f)

    logger.info(f"Added {package_name} to {file_path}")


def remove_dependency(package_name: str, file_path: str = "ymir_dependencies.toml"):
    """Remove a dependency from the dependencies file."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Dependency file {file_path} not found")

    with open(file_path, "r") as f:
        config = toml.load(f)

    if "dependencies" not in config or package_name not in config["dependencies"]:
        raise ValueError(f"Package {package_name} not found in dependencies")

    del config["dependencies"][package_name]

    with open(file_path, "w") as f:
        toml.dump(config, f)

    logger.info(f"Removed {package_name} from {file_path}")


def list_dependencies(file_path: str = "ymir_dependencies.toml") -> Dict:
    """List all dependencies from the dependencies file."""
    if not os.path.exists(file_path):
        return {}

    with open(file_path, "r") as f:
        config = toml.load(f)

    return config.get("dependencies", {})
