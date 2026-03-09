import click
import sys
import logging

from app.core.cli import commands as core_commands
from app.core.logging import setup_logging

@click.group()
@click.option('--debug', is_flag=True, help='Enable debug logging')
def cli(debug):
    """VASCULAR Command Line Interface"""
    # Setup logging based on debug flag
    log_level = logging.DEBUG if debug else logging.INFO
    setup_logging(level=log_level)

# Add subcommands
cli.add_command(core_commands.test_db)
cli.add_command(core_commands.process_reports)
cli.add_command(core_commands.test_email)

if __name__ == "__main__":
    cli()