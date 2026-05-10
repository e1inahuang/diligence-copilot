"""CLI entry point."""
from __future__ import annotations
import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime
import click
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from .orchestrator import run_diligence
from .report import render

load_dotenv()
console = Console()


@click.command()
@click.argument("query")
@click.option("--out", "-o", default=None, help="Output markdown path. Default: reports/<TICKER>_<date>.md")
@click.option("--print-only", is_flag=True, help="Print to stdout, don't write file.")
def main(query: str, out: str | None, print_only: bool):
    """Run preliminary diligence on a public ticker or company name."""
    if not os.getenv("OPENAI_API_KEY"):
        console.print("[red]OPENAI_API_KEY missing in environment.[/red]")
        sys.exit(1)
    if not os.getenv("TAVILY_API_KEY"):
        console.print("[yellow]TAVILY_API_KEY missing — news/litigation will be empty.[/yellow]")

    console.print(Panel(f"Running diligence on [bold]{query}[/bold] ...", expand=False))
    bundle = asyncio.run(run_diligence(query))
    md = render(bundle)

    if print_only:
        console.print(md)
        return

    ticker = bundle.entity.ticker
    date = datetime.utcnow().strftime("%Y%m%d")
    if out is None:
        out_dir = Path("reports")
        out_dir.mkdir(exist_ok=True)
        out = out_dir / f"{ticker}_{date}.md"
    Path(out).write_text(md, encoding="utf-8")
    console.print(f"[green]Report written to[/green] {out}")
    console.print(
        f"[dim]Verdict:[/dim] [bold]{bundle.consensus.verdict}[/bold]  "
        f"[dim]Conviction:[/dim] {bundle.consensus.conviction_score:.2f}  "
        f"[dim]Confidence:[/dim] {bundle.consensus.overall_confidence:.2f}"
    )


if __name__ == "__main__":
    main()
