"""CLI entry point for git-recap."""

from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.spinner import Spinner
from rich.live import Live

from git_recap.config import load as load_config
from git_recap.git import get_commits, format_commits_for_prompt
from git_recap.summarizer import summarize, DEFAULT_MODEL

console = Console()


@click.command()
@click.option(
    "--repo",
    "-r",
    default=".",
    show_default=True,
    help="Path to the git repository.",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
)
@click.option(
    "--since",
    "-s",
    default=None,
    help='Time range for commits (e.g. "1 day ago", "2026-03-01"). Defaults to 1 week ago.',
)
@click.option(
    "--today",
    is_flag=True,
    default=False,
    help='Shortcut for --since "1 day ago".',
)
@click.option(
    "--week",
    is_flag=True,
    default=False,
    help='Shortcut for --since "1 week ago" (default).',
)
@click.option(
    "--author",
    "-a",
    default=None,
    help="Filter commits by author name or email.",
)
@click.option(
    "--model",
    "-m",
    default=DEFAULT_MODEL,
    show_default=True,
    help="Ollama model to use for summarization.",
)
@click.option(
    "--format",
    "fmt",
    default="text",
    type=click.Choice(["text", "json", "markdown"]),
    show_default=True,
    help="Output format. 'markdown' is suitable for pasting into Notion or Obsidian.",
)
@click.option(
    "--raw",
    is_flag=True,
    default=False,
    help="Print raw commit list without LLM summary.",
)
@click.option(
    "--output",
    "-o",
    default=None,
    help="Save the summary to a file.",
    type=click.Path(path_type=Path),
)
@click.version_option()
def main(
    repo: Path,
    since: str | None,
    today: bool,
    week: bool,
    author: str | None,
    model: str,
    fmt: str,
    raw: bool,
    output: Path | None,
) -> None:
    cfg = load_config()
    """Turn your git commits into a readable summary using a local LLM.

    Examples:

    \b
      git-recap                        # summarize the last week in current repo
      git-recap --today                # just today's commits
      git-recap --week                 # last 7 days (same as default)
      git-recap --since "2026-03-01"   # from a specific date
      git-recap --format json          # machine-readable output
      git-recap --format markdown      # paste into Notion or Obsidian
      git-recap --repo ~/projects/foo  # different repo
      git-recap --raw                  # skip the LLM, just show commits
      git-recap --output summary.txt   # save to file
    """
    if today:
        since_resolved = "1 day ago"
    elif week:
        since_resolved = "1 week ago"
    elif since:
        since_resolved = since
    else:
        since_resolved = cfg.get("since", "1 week ago")

    if model == DEFAULT_MODEL and cfg.get("model"):
        model = cfg["model"]
    if author is None and cfg.get("author"):
        author = cfg["author"]

    try:
        commits = get_commits(repo, since=since_resolved, author=author)
    except RuntimeError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()

    if not commits:
        console.print(f"[yellow]No commits found since '{since_resolved}'.[/yellow]")
        return

    commits_text = format_commits_for_prompt(commits)

    if raw:
        if fmt == "json":
            import json
            serializable = [
                {
                    "hash": c.hash,
                    "author": c.author,
                    "date": c.date.isoformat(),
                    "message": c.message,
                    "files_changed": c.files_changed,
                }
                for c in commits
            ]
            click.echo(json.dumps({"commits": serializable}, indent=2))
        elif fmt == "markdown":
            lines = [f"## Commits since {since_resolved}", ""]
            for c in commits:
                lines.append(f"- `{c.hash[:7]}` {c.message} — {c.author} ({c.date.strftime('%Y-%m-%d')})")
            raw_md = "\n".join(lines)
            click.echo(raw_md)
            if output:
                output.write_text(raw_md, encoding="utf-8")
                console.print(f"[dim]Saved to {output}[/dim]")
        else:
            console.print(Panel(commits_text, title=f"[bold]{len(commits)} commits[/bold]", border_style="dim"))
        return

    if fmt not in ("json", "markdown"):
        console.print(f"[dim]Found {len(commits)} commit(s) since '{since_resolved}'. Summarizing...[/dim]")

    if fmt == "json":
        try:
            summary = summarize(commits_text, model=model)
        except RuntimeError as e:
            console.print(f"[red]Error:[/red] {e}", file=console.stderr)
            raise click.Abort()
    else:
        with Live(Spinner("dots", text=" Thinking..."), console=console, refresh_per_second=10):
            try:
                summary = summarize(commits_text, model=model)
            except RuntimeError as e:
                console.print(f"\n[red]Error:[/red] {e}")
                raise click.Abort()

    if fmt == "json":
        import json
        result = {"since": since_resolved, "commit_count": len(commits), "summary": summary}
        output_text = json.dumps(result, indent=2)
        click.echo(output_text)
    elif fmt == "markdown":
        output_text = "\n".join([
            f"## Git Recap — {len(commits)} commit(s) since {since_resolved}",
            "",
            summary,
        ])
        click.echo(output_text)
    else:
        console.print()
        console.print(Panel(
            summary,
            title=f"[bold green]Recap[/bold green] — {len(commits)} commit(s) since '{since_resolved}'",
            border_style="green",
            padding=(1, 2),
        ))
        output_text = summary

    if output:
        output.write_text(output_text, encoding="utf-8")
        console.print(f"[dim]Saved to {output}[/dim]")
