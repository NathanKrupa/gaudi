"""Fixture for LOG-004: print is fine in a Click CLI entry point."""

import click


@click.command()
def main():
    print("Starting...")
    click.echo("Hello")


if __name__ == "__main__":
    main()
