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
    multiple=True,
    help="Path to a git repository. Repeat to recap across multiple repos.",
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
    repo: tuple[Path, ...],
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
      git-recap --repo ~/a --repo ~/b  # recap across multiple repos
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

    repos = repo or (Path("."),)
    multi = len(repos) > 1

    repo_commits: list[tuple[str, list]] = []
    for repo_path in repos:
        try:
            commits = get_commits(repo_path, since=since_resolved, author=author)
        except RuntimeError as e:
            console.print(f"[red]Error ({repo_path}):[/red] {e}")
            raise click.Abort()
        repo_commits.append((repo_path.resolve().name, commits))

    total_commits = sum(len(c) for _, c in repo_commits)
    if total_commits == 0:
        console.print(f"[yellow]No commits found since '{since_resolved}'.[/yellow]")
        return

    if multi:
        sections = []
        for name, commits in repo_commits:
            if commits:
                sections.append(f"=== {name} ({len(commits)} commits) ===\n{format_commits_for_prompt(commits)}")
        commits_text = "\n\n".join(sections)
    else:
        commits = repo_commits[0][1]
        commits_text = format_commits_for_prompt(commits)

    if raw:
        if fmt == "json":
            import json
            if multi:
                out = {
                    name: [
                        {"hash": c.hash, "author": c.author, "date": c.date.isoformat(),
                         "message": c.message, "files_changed": c.files_changed}
                        for c in commits
                    ]
                    for name, commits in repo_commits
                }
                click.echo(json.dumps({"repos": out}, indent=2))
            else:
                serializable = [
                    {"hash": c.hash, "author": c.author, "date": c.date.isoformat(),
                     "message": c.message, "files_changed": c.files_changed}
                    for c in commits
                ]
                click.echo(json.dumps({"commits": serializable}, indent=2))
        elif fmt == "markdown":
            lines = [f"## Commits since {since_resolved}", ""]
            if multi:
                for name, repo_c in repo_commits:
                    if repo_c:
                        lines.append(f"### {name}")
                        for c in repo_c:
                            lines.append(f"- `{c.hash[:7]}` {c.message} — {c.author} ({c.date.strftime('%Y-%m-%d')})")
                        lines.append("")
            else:
                for c in commits:
                    lines.append(f"- `{c.hash[:7]}` {c.message} — {c.author} ({c.date.strftime('%Y-%m-%d')})")
            raw_md = "\n".join(lines)
            click.echo(raw_md)
            if output:
                output.write_text(raw_md, encoding="utf-8")
                console.print(f"[dim]Saved to {output}[/dim]")
        else:
            console.print(Panel(commits_text, title=f"[bold]{total_commits} commits[/bold]", border_style="dim"))
        return

    if fmt not in ("json", "markdown"):
        label = f"{total_commits} commit(s) across {len(repos)} repos" if multi else f"{total_commits} commit(s)"
        console.print(f"[dim]Found {label} since '{since_resolved}'. Summarizing...[/dim]")

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

    repo_label = f"{len(repos)} repos" if multi else repos[0].resolve().name
    if fmt == "json":
        import json
        result = {"since": since_resolved, "commit_count": total_commits, "repos": repo_label, "summary": summary}
        output_text = json.dumps(result, indent=2)
        click.echo(output_text)
    elif fmt == "markdown":
        output_text = "\n".join([
            f"## Git Recap — {total_commits} commit(s) since {since_resolved}",
            "",
            summary,
        ])
        click.echo(output_text)
    else:
        console.print()
        console.print(Panel(
            summary,
            title=f"[bold green]Recap[/bold green] — {total_commits} commit(s) since '{since_resolved}'",
            border_style="green",
            padding=(1, 2),
        ))
        output_text = summary

    if output:
        output.write_text(output_text, encoding="utf-8")
        console.print(f"[dim]Saved to {output}[/dim]")
