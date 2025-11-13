import os

import click

from ymir.interpreter import YmirInterpreter
from ymir.tools.dependency_manager import (
    add_dependency,
    install_dependencies_from_file,
    install_dependency,
    list_dependencies,
    remove_dependency,
)


@click.group()
def cli():
    """Ymir - A modern programming language for machine learning systems."""
    pass


@cli.command()
@click.argument("file", type=click.Path(exists=True))
@click.option("--verbosity", type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]), default="INFO")
@click.option("--no-stdlib", is_flag=True, help="Skip loading the standard library (faster startup)")
@click.option(
    "--interpreter",
    "-i",
    "use_interpreter",
    is_flag=True,
    help="Use interpreter mode instead of LLVM (default: LLVM)",
)
@click.option(
    "--mode",
    type=click.Choice(["llvm", "interpret", "auto"]),
    default=None,
    help="Override execution mode (default: llvm)",
)
def run(file, verbosity, no_stdlib, use_interpreter, mode):
    """Run a Ymir script (uses LLVM compilation by default)."""
    try:
        # If --interpreter/-i flag is set, use interpret mode
        # Otherwise use mode if specified, else default to "llvm"
        execution_mode = "interpret" if use_interpreter else (mode or "llvm")
        interpreter = YmirInterpreter(verbosity=verbosity, load_stdlib=not no_stdlib)
        interpreter.run_ymir_script(file, mode=execution_mode)
    except Exception as e:
        click.echo(f"Error running {file}: {e}")


@cli.command()
@click.argument("repo_url", required=False)
@click.option(
    "--file", type=click.Path(exists=True), default="ymir_dependencies.toml", help="Dependency file to install from."
)
def install(repo_url, file):
    """Install a Ymir library from a repository URL or install dependencies from a file."""
    if repo_url:
        click.echo(f"Installing {repo_url}...")
        install_dependency(repo_url)
        click.echo(f"✓ Successfully installed {repo_url}")
    else:
        click.echo(f"Installing dependencies from {file}...")
        install_dependencies_from_file(file)
        click.echo("✓ All dependencies installed")


@cli.command()
@click.argument("repo_url")
@click.option("--version", default="latest", help="Version or tag to install")
@click.option("--file", type=click.Path(), default="ymir_dependencies.toml", help="Dependency file to add to.")
def add(repo_url, version, file):
    """Add a dependency to ymir_dependencies.toml and install it."""
    try:
        click.echo(f"Adding {repo_url} ({version})...")
        add_dependency(repo_url, version, file)
        click.echo(f"✓ Added {repo_url} to {file}")
        click.echo(f"Installing {repo_url}...")
        install_dependency(repo_url, version)
        click.echo(f"✓ Successfully installed {repo_url}")
    except Exception as e:
        click.echo(f"Error adding dependency: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.argument("package_name")
@click.option("--file", type=click.Path(), default="ymir_dependencies.toml", help="Dependency file to remove from.")
def remove(package_name, file):
    """Remove a dependency from ymir_dependencies.toml."""
    try:
        click.echo(f"Removing {package_name}...")
        remove_dependency(package_name, file)
        click.echo(f"✓ Removed {package_name} from {file}")
        click.echo("Note: Package files are still cached. Use 'ymir clean' to remove cached packages.")
    except Exception as e:
        click.echo(f"Error removing dependency: {e}", err=True)
        raise click.Abort()


@cli.command("list")
@click.option("--file", type=click.Path(), default="ymir_dependencies.toml", help="Dependency file to list from.")
def list_cmd(file):
    """List all dependencies from ymir_dependencies.toml."""
    try:
        deps = list_dependencies(file)
        if not deps:
            click.echo("No dependencies found.")
        else:
            click.echo("Dependencies:")
            for package, info in deps.items():
                version = info if isinstance(info, str) else info.get("version", "latest")
                click.echo(f"  - {package}: {version}")
    except Exception as e:
        click.echo(f"Error listing dependencies: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.argument("input_file", required=False, type=click.Path())
@click.option("--output", "-o", "output_file", type=click.Path(), help="Output file path")
@click.argument("arch", required=False, type=str, default=None)
def build(input_file, output_file, arch):
    """Build a Ymir script into a binary."""
    try:
        if not input_file:
            input_file = os.path.join(os.getcwd(), "main.ymr")
        if not output_file:
            output_file = os.path.join(os.getcwd(), "dist", os.path.basename(os.getcwd()))

        click.echo(f"Building {input_file}...")
        interpreter = YmirInterpreter()
        interpreter.build_ymir(input_file, output_file, arch=arch)
        click.echo(f"✓ Built successfully: {output_file}")
    except Exception as e:
        click.echo(f"Error building {input_file}: {e}", err=True)
        raise click.Abort()


if __name__ == "__main__":
    cli()
