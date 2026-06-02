"""Typer entrypoint for the AgentMint CLI."""

from __future__ import annotations

import typer

from ._styles import set_no_color

app = typer.Typer(help="AgentMint: signed receipts for AI agent actions.", no_args_is_help=True)


@app.callback()
def main(
    no_color: bool = typer.Option(False, "--no-color", help="Disable ANSI color output."),
) -> None:
    set_no_color(no_color)


from . import actions as _actions  # noqa: E402,F401
from . import chain as _chain  # noqa: E402,F401
from . import doctor as _doctor  # noqa: E402,F401
from . import export as _export  # noqa: E402,F401
from . import init as _init  # noqa: E402,F401
from . import notarise as _notarise  # noqa: E402,F401
from . import plan as _plan  # noqa: E402,F401
from . import privacy as _privacy  # noqa: E402,F401
from . import show as _show  # noqa: E402,F401
from . import verify as _verify  # noqa: E402,F401
from . import watch as _watch  # noqa: E402,F401
