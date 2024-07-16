import hashlib
import os
import subprocess

import toml

from ymir.interpreter import YmirInterpreter

PACKAGE_CACHE_DIR = os.path.expanduser("~/.ymir/package_cache")
CHECKSUM_FILE = os.path.expanduser("~/.ymir/checksums.txt")


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


def clone_repository(repo_url, dest_dir):
    """Clone a git repository."""
    subprocess.run(["git", "clone", repo_url, dest_dir], check=True)


def build_package(package_dir):
    """Build the Ymir package."""
    dist_dir = os.path.join(package_dir, "dist")
    if not os.path.exists(dist_dir):
        os.makedirs(dist_dir)

    for file in os.listdir(package_dir):
        if file.endswith(".ymr"):
            input_path = os.path.join(package_dir, file)
            output_path = os.path.join(dist_dir, os.path.basename(package_dir))
            interpreter = YmirInterpreter()
            interpreter.build_ymir(input_path, output_path)


def install_dependency(repo_url):
    """Install a Ymir library from a repository URL."""
    package_name = repo_url.split("/")[-1].replace(".git", "")
    dest_dir = os.path.join(PACKAGE_CACHE_DIR, package_name)
    if not os.path.exists(dest_dir):
        clone_repository(repo_url, dest_dir)
        build_package(dest_dir)
        save_checksum(package_name, dest_dir)
    else:
        print(f"Package {package_name} is already installed.")


def install_dependencies_from_file(file_path):
    """Install dependencies listed in a TOML file."""
    with open(file_path, "r") as file:
        config = toml.load(file)
    dependencies = config.get("dependencies", {})
    for package, repo_url in dependencies.items():
        install_dependency(repo_url)
