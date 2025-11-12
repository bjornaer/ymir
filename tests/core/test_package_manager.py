"""
Tests for Ymir package manager.
"""

import os
import tempfile

import pytest
import toml

from ymir.tools.dependency_manager import (
    add_dependency,
    list_dependencies,
    parse_repo_url,
    remove_dependency,
)


class TestParseRepoUrl:
    """Test repository URL parsing."""

    def test_parse_github_short(self):
        """Test parsing short GitHub URL."""
        package, provider = parse_repo_url("github.com/user/repo")
        assert package == "repo"
        assert provider == "github.com"

    def test_parse_gitlab_short(self):
        """Test parsing short GitLab URL."""
        package, provider = parse_repo_url("gitlab.com/user/project")
        assert package == "project"
        assert provider == "gitlab.com"

    def test_parse_https_url(self):
        """Test parsing HTTPS URL."""
        package, provider = parse_repo_url("https://github.com/user/awesome-lib")
        assert package == "awesome-lib"

    def test_parse_git_extension(self):
        """Test parsing URL with .git extension."""
        package, provider = parse_repo_url("https://github.com/user/repo.git")
        assert package == "repo"

    def test_parse_simple_name(self):
        """Test parsing simple package name."""
        package, provider = parse_repo_url("simple-package")
        assert package == "simple-package"
        assert provider == "unknown"


class TestDependencyManagement:
    """Test dependency management functions."""

    def test_add_dependency_new_file(self):
        """Test adding dependency to new file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dep_file = os.path.join(tmpdir, "test_deps.toml")

            add_dependency("github.com/user/lib", "latest", dep_file)

            assert os.path.exists(dep_file)
            with open(dep_file) as f:
                config = toml.load(f)
            assert "lib" in config["dependencies"]

    def test_add_dependency_with_version(self):
        """Test adding dependency with version."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dep_file = os.path.join(tmpdir, "test_deps.toml")

            add_dependency("github.com/user/lib", "v1.2.3", dep_file)

            with open(dep_file) as f:
                config = toml.load(f)
            dep = config["dependencies"]["lib"]
            assert dep["url"] == "github.com/user/lib"
            assert dep["version"] == "v1.2.3"

    def test_remove_dependency(self):
        """Test removing a dependency."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dep_file = os.path.join(tmpdir, "test_deps.toml")

            # Add then remove
            add_dependency("github.com/user/lib1", "latest", dep_file)
            add_dependency("github.com/user/lib2", "latest", dep_file)
            remove_dependency("lib1", dep_file)

            with open(dep_file) as f:
                config = toml.load(f)
            assert "lib1" not in config["dependencies"]
            assert "lib2" in config["dependencies"]

    def test_remove_nonexistent_dependency(self):
        """Test removing non-existent dependency."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dep_file = os.path.join(tmpdir, "test_deps.toml")

            add_dependency("github.com/user/lib", "latest", dep_file)

            with pytest.raises(ValueError, match="not found in dependencies"):
                remove_dependency("nonexistent", dep_file)

    def test_list_dependencies_empty(self):
        """Test listing dependencies from empty file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dep_file = os.path.join(tmpdir, "test_deps.toml")

            # Create empty config
            with open(dep_file, "w") as f:
                toml.dump({"package": {"name": "test"}}, f)

            deps = list_dependencies(dep_file)
            assert deps == {}

    def test_list_dependencies_with_entries(self):
        """Test listing dependencies."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dep_file = os.path.join(tmpdir, "test_deps.toml")

            add_dependency("github.com/user/lib1", "latest", dep_file)
            add_dependency("github.com/user/lib2", "v1.0.0", dep_file)

            deps = list_dependencies(dep_file)
            assert len(deps) == 2
            assert "lib1" in deps
            assert "lib2" in deps

    def test_list_dependencies_nonexistent_file(self):
        """Test listing from non-existent file."""
        deps = list_dependencies("/nonexistent/path/deps.toml")
        assert deps == {}
