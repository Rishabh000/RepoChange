"""repo-brain command line interface (Typer).

Commands:
    repo-brain scan                 # show current repo layout
    repo-brain organize --dry-run   # propose a plan, change nothing
    repo-brain organize             # propose, ask approval, then apply + commit
    repo-brain organize --auto      # apply without prompting (used by cron)
    repo-brain search "query"       # semantic search over memory
    repo-brain audit                # show audit log + git history
"""
from __future__ import annotations

import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "agents"))
sys.path.insert(0, str(ROOT / "mcp"))
sys.path.insert(0, str(ROOT / "memory"))

import coordinator  # noqa: E402
import organizer  # noqa: E402
import auditor  # noqa: E402
import filesystem_server as fs  # noqa: E402
import git_server  # noqa: E402
import vector_store  # noqa: E402
import llm  # noqa: E402
from config import TARGET_REPO, MODEL  # noqa: E402

app = typer.Typer(help="repo-brain: an agentic repository second brain.", add_completion=False)
console = Console()


@app.command()
def scan():
    """Show the current files in the target repository."""
    console.print(f"[bold]Scanning[/bold] {TARGET_REPO}")
    table = Table("path", "type", "protected", "ignored", "size")
    for entry in fs.list_files("."):
        table.add_row(
            entry["path"],
            "dir" if entry["is_dir"] else "file",
            "🔒" if entry["protected"] else "",
            "—" if entry.get("ignored") else "",
            "" if entry["size"] is None else str(entry["size"]),
        )
    console.print(table)


def _print_plan(plan: dict) -> int:
    moves = plan.get("moves", [])
    if not moves:
        console.print("[green]Nothing to reorganize - repo is already tidy.[/green]")
        return 0
    console.print("[bold]Proposed moves:[/bold]")
    for move in moves:
        console.print(f"  {move['source']}  →  {move['destination']}"
                      f"   [dim]({move['reason']})[/dim]")
    return len(moves)


@app.command()
def organize(
    dry_run: bool = typer.Option(False, "--dry-run", help="Show the plan only."),
    auto: bool = typer.Option(False, "--auto", help="Apply without prompting."),
):
    """Plan a reorganization; apply it after approval (Phase 8 security flow)."""
    try:
        plan = organizer.make_plan()
    except llm.GeminiNotConfigured as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1)
    count = _print_plan(plan)

    if dry_run or count == 0:
        return

    approved = auto or typer.confirm("Approve?")
    if not approved:
        console.print("[yellow]Aborted. No files were moved.[/yellow]")
        return

    result = coordinator.run_pipeline(dry_run=False, auto=True)
    for outcome in result["moved"]:
        console.print(f"[green]moved[/green] {outcome['moved']} → {outcome['to']}")
    if result.get("commit", {}).get("committed"):
        console.print(f"[cyan]committed[/cyan] {result['commit']['hash']} "
                      f"{result['commit']['message']}")
    console.print(f"[bold]Indexed {len(result['indexed'])} files into memory.[/bold]")


@app.command()
def search(query: str, n: int = typer.Option(5, "--n", help="Max results.")):
    """Semantic search over the memory built by the memory agent."""
    hits = vector_store.search_memory(query, n_results=n)
    if not hits:
        console.print("[yellow]No memories yet. Run 'repo-brain organize' first.[/yellow]")
        return
    console.print(f"[bold]Results for[/bold] \"{query}\":")
    for hit in hits:
        score = "" if hit["score"] is None else f" [dim](score {hit['score']})[/dim]"
        console.print(f"\n[green]{hit['filename']}[/green]{score}")
        console.print(f"  {hit['summary']}")


@app.command()
def audit(limit: int = typer.Option(20, "--limit", help="Entries to show.")):
    """Show the audit log and recent git history."""
    entries = auditor.read_log(limit=limit)
    if not entries:
        console.print("[yellow]No audit entries yet.[/yellow]")
    else:
        table = Table("timestamp", "action", "detail")
        for e in entries:
            detail = e.get("destination") or e.get("message") or ""
            if e.get("action") == "move":
                detail = f"{e.get('source')} → {e.get('destination')}"
            table.add_row(e.get("timestamp", ""), e.get("action", ""), str(detail))
        console.print(table)

    console.print("\n[bold]Git history:[/bold]")
    for commit in git_server.show_log(limit=limit):
        console.print(f"  {commit['hash']}  {commit['message']}")


@app.command()
def rollback():
    """Undo the last commit made by repo-brain (keeps your files in place)."""
    try:
        result = git_server.rollback_last_commit()
        console.print(f"[yellow]Rolled back[/yellow] {result['rolled_back']} "
                      f"{result['message']}")
        console.print("[dim]Working tree preserved; files were not deleted.[/dim]")
    except git_server.GitError as exc:
        console.print(f"[red]{exc}[/red]")


@app.command()
def index():
    """(Re)build semantic memory for all files without moving anything."""
    import memory_agent

    try:
        indexed = memory_agent.index_repo()
    except llm.GeminiNotConfigured as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1)
    console.print(f"[bold]Indexed {len(indexed)} files.[/bold]")


if __name__ == "__main__":
    app()
