#!/usr/bin/env python3
"""
Build standalone executable for Ymir using PyInstaller.

This script builds platform-specific executables that include:
- Ymir interpreter
- Standard library files
- All dependencies
"""

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


def get_platform_name():
    """Get normalized platform name."""
    system = platform.system().lower()
    machine = platform.machine().lower()

    if system == "darwin":
        if machine == "arm64":
            return "macos-arm64"
        else:
            return "macos-x86_64"
    elif system == "linux":
        return f"linux-{machine}"
    elif system == "windows":
        return f"windows-{machine}"
    else:
        return f"{system}-{machine}"


def build_executable():
    """Build the executable using PyInstaller."""
    # Get project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    # Paths
    cli_path = project_root / "ymir" / "cli" / "ymir_cli.py"
    stdlib_path = project_root / "ymir" / "stdlib"
    dist_dir = project_root / "dist"
    build_dir = project_root / "build"

    # Clean previous builds
    if dist_dir.exists():
        print(f"Cleaning {dist_dir}")
        shutil.rmtree(dist_dir)
    if build_dir.exists():
        print(f"Cleaning {build_dir}")
        shutil.rmtree(build_dir)

    # Build executable
    platform_name = get_platform_name()
    executable_name = f"ymir-{platform_name}"

    print(f"Building executable: {executable_name}")
    print(f"CLI path: {cli_path}")
    print(f"Stdlib path: {stdlib_path}")

    # PyInstaller command
    cmd = [
        "pyinstaller",
        "--onefile",
        "--name",
        executable_name,
        "--add-data",
        f"{stdlib_path}{os.pathsep}ymir/stdlib",
        "--hidden-import",
        "ymir",
        "--hidden-import",
        "ymir.core",
        "--hidden-import",
        "ymir.stdlib",
        "--hidden-import",
        "ymir.tools",
        "--hidden-import",
        "click",
        "--hidden-import",
        "toml",
        "--hidden-import",
        "numpy",
        "--clean",
        str(cli_path),
    ]

    print(f"Running: {' '.join(cmd)}")

    try:
        subprocess.run(cmd, check=True, cwd=project_root)
        print("\n✓ Build successful!")
        print(f"Executable: {dist_dir / executable_name}")

        # Create a symlink without platform suffix
        if platform.system() != "Windows":
            symlink_path = dist_dir / "ymir"
            executable_path = dist_dir / executable_name
            if symlink_path.exists():
                symlink_path.unlink()
            os.symlink(executable_path.name, symlink_path)
            print(f"Symlink: {symlink_path} -> {executable_name}")

        return 0
    except subprocess.CalledProcessError as e:
        print(f"\n✗ Build failed: {e}")
        return 1


def main():
    """Main entry point."""
    print("=" * 60)
    print("Ymir Executable Builder")
    print("=" * 60)
    print(f"Platform: {platform.system()} {platform.machine()}")
    print(f"Python: {sys.version}")
    print()

    return build_executable()


if __name__ == "__main__":
    sys.exit(main())
