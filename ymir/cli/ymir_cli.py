import os

import click

from ymir.interpreter import YmirInterpreter
from ymir.tools.dependency_manager import (
    install_dependencies_from_file,
    install_dependency,
)


@click.group()
def cli():
    pass


@cli.command()
@click.argument("file", type=click.Path(exists=True))
def run(file):
    """Run a Ymir script."""
    try:
        interpreter = YmirInterpreter()
        interpreter.run_ymir_script(file)
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
        install_dependency(repo_url)
    else:
        install_dependencies_from_file(file)


@cli.command()
@click.argument("input_file", required=False, type=click.Path())
@click.argument("output_file", required=False, type=click.Path())
@click.argument("arch", required=False, type=str, default=None)
def build(input_file, output_file, arch):
    """Build a Ymir script into a binary."""
    try:
        if not input_file:
            input_file = os.path.join(os.getcwd(), "main.ymr")
        if not output_file:
            output_file = os.path.join(os.getcwd(), "dist", os.path.basename(os.getcwd()))
        interpreter = YmirInterpreter()
        interpreter.build_ymir(input_file, output_file, arch=arch)
    except Exception as e:
        click.echo(f"Error building {input_file}: {e}")


if __name__ == "__main__":
    cli()
