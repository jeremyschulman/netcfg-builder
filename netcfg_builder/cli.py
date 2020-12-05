# -----------------------------------------------------------------------------
# System Imports
# -----------------------------------------------------------------------------

from importlib import metadata
from pathlib import Path
import sys

# -----------------------------------------------------------------------------
# Public Imports
# -----------------------------------------------------------------------------

import click

# -----------------------------------------------------------------------------
# Private Imports
# -----------------------------------------------------------------------------

from netcfg_builder.build import render
from netcfg_builder import variables

VERSION = metadata.version("netcfg-builder")


def _extra_variable_handler(ctx: click.Context, param: click.Parameter, value: tuple):
    as_dict = dict()

    for expr in value:
        if expr.endswith(".py"):
            variables.load_sourcefile(Path(expr))
            continue

        if "=" in expr:
            key, value = expr.split("=")
            as_dict[key] = value
            continue

        ctx.fail(f"Unhandled extra variable: {expr}")

    return as_dict


@click.command()
@click.version_option(version=VERSION)
@click.option("--hostname", help="device hostname")
@click.option(
    "-t", "--template", help="template file", type=click.File(), required=True
)
@click.option(
    "-e",
    "--extra-variables",
    help="load template variables",
    multiple=True,
    callback=_extra_variable_handler,
)
@click.option(
    "-o",
    "--output",
    help="output filename",
    type=click.File("w+"),
    default=sys.stdout,
)
@click.pass_context
def cli(ctx: click.Context, hostname: str, template, extra_variables, output):

    try:
        tvars = variables.load_variables(hostname=hostname, **extra_variables)

    except Exception as exc:
        ctx.fail(str(exc))

    try:
        content = render(template_fp=Path(template.name), **tvars)  # noqa
        output.write(content)

    except RuntimeError as exc:
        ctx.fail(str(exc))

    except Exception as exc:
        import traceback

        print(traceback.print_exc())
        ctx.fail(str(exc))


def main():
    cli(obj={})
