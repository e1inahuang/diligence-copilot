"""Batch mode: CSV of tickers in, summary CSV + per-ticker memos out."""
from __future__ import annotations
import asyncio
import csv
from pathlib import Path
from datetime import datetime
import click
from dotenv import load_dotenv
from rich.console import Console
from .orchestrator import run_diligence
from .report import render

load_dotenv()
console = Console()


@click.command()
@click.argument("csv_path", type=click.Path(exists=True))
@click.option("--out-dir", default="reports/batch", help="Output directory.")
def main(csv_path: str, out_dir: str):
    """Run diligence over a CSV with a 'ticker' column."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    summary_path = out / f"summary_{datetime.utcnow().strftime('%Y%m%d_%H%M')}.csv"

    tickers: list[str] = []
    with open(csv_path) as f:
        for row in csv.DictReader(f):
            t = (row.get("ticker") or row.get("Ticker") or "").strip()
            if t:
                tickers.append(t)

    rows = []
    for t in tickers:
        console.print(f"-> {t}")
        try:
            bundle = asyncio.run(run_diligence(t))
            memo = render(bundle)
            (out / f"{bundle.entity.ticker}.md").write_text(memo, encoding="utf-8")
            c = bundle.consensus
            rows.append({
                "ticker": bundle.entity.ticker,
                "name": bundle.entity.name,
                "verdict": c.verdict,
                "conviction": c.conviction_score,
                "confidence": c.overall_confidence,
                "red_flags": " | ".join(c.top_red_flags[:5]),
            })
        except Exception as e:
            console.print(f"[red]Failed {t}: {e}[/red]")
            rows.append({"ticker": t, "name": "", "verdict": "ERROR",
                         "conviction": 0, "confidence": 0, "red_flags": str(e)[:200]})

    with open(summary_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["ticker", "name", "verdict", "conviction", "confidence", "red_flags"])
        w.writeheader()
        w.writerows(rows)
    console.print(f"[green]Summary:[/green] {summary_path}")


if __name__ == "__main__":
    main()
