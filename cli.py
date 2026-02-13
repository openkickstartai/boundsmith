"""BoundSmith CLI — hunt boundary condition blind spots."""
import json
from pathlib import Path

import typer

from boundsmith import (
    extract_boundaries, find_uncovered, generate_test_file,
    scan_path, scan_tests,
)

app = typer.Typer(
    name="boundsmith",
    help="\U0001f3f9 BoundSmith — hunt uncovered boundary conditions in Python code",
)


@app.command()
def scan(
    src: Path = typer.Argument(..., help="Source directory or .py file to scan"),
    tests: Path = typer.Option(None, "--tests", "-t", help="Test dir to cross-check"),
    generate: Path = typer.Option(None, "--generate", "-g", help="Output test file"),
    as_json: bool = typer.Option(False, "--json", help="JSON output for CI"),
):
    """Scan Python source for boundary conditions and find uncovered ones."""
    if src.is_file():
        if src.suffix != ".py":
            typer.echo(f"Error: {src} is not a Python file", err=True)
            raise typer.Exit(1)
        boundaries = extract_boundaries(src.read_text("utf-8"), str(src))
    elif src.is_dir():
        boundaries = scan_path(src)
    else:
        typer.echo(f"Error: {src} not found", err=True)
        raise typer.Exit(1)

    if tests and not tests.exists():
        typer.echo(f"Error: test path {tests} not found", err=True)
        raise typer.Exit(1)
    test_values = scan_tests(tests) if tests else set()

    uncovered = find_uncovered(boundaries, test_values) if test_values else boundaries

    if as_json:
        data = [{"file": b.file, "line": b.line, "var": b.variable,
                 "op": b.operator, "value": b.value,
                 "triplet": list(b.triplet), "expr": b.expression}
                for b in uncovered]
        typer.echo(json.dumps(data, indent=2))
    else:
        total, miss = len(boundaries), len(uncovered)
        typer.echo(f"\U0001f3f9 BoundSmith: {total} boundaries, {miss} uncovered\n")
        for b in uncovered:
            typer.echo(f"  \u26a0  {b.file}:{b.line}  {b.expression}")
            typer.echo(f"     \u2192 test with: {b.triplet}\n")

    if generate and uncovered:
        generate.write_text(generate_test_file(uncovered), encoding="utf-8")
        typer.echo(f"\u2705 Generated {len(uncovered)} tests \u2192 {generate}")

    if uncovered and test_values:
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
