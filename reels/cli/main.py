from __future__ import annotations

import typer

from reels.cli import build as build_cmd
from reels.cli import ingest as ingest_cmd
from reels.utils.log import setup_logging

app = typer.Typer(no_args_is_help=True)


@app.callback()
def main() -> None:
    setup_logging()


app.command("ingest")(ingest_cmd.run)
app.command("build")(build_cmd.run)
