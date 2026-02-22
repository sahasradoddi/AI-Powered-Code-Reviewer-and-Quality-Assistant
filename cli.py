#!/usr/bin/env python3

import click
import sys
import os
from dataclasses import asdict
from pathlib import Path
import json
import ast
from autofix_engine import AutoFixEngine
from code_quality_analyzer import CodeQualityAnalyzer
from ai_review_engine import AIReviewEngine
from config_loader import load_config

from dotenv import load_dotenv
load_dotenv()

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
    os.system('chcp 65001 > nul')

@click.group()
@click.version_option("1.0.0")
def cli():
    """AI-Powered Code Reviewer CLI"""
    pass

@cli.command()
@click.argument("path", type=click.Path(exists=True))
@click.option("-o", "--output", help="Output directory for reports")
def scan(path, output):
    """Run static analysis and generate quality reports"""
    config = load_config()
    analyzer = CodeQualityAnalyzer()

    project_path = Path(path)

    # Handle single files and directories
    if project_path.is_file() and project_path.suffix == ".py":
        click.echo(f"🔍 Analyzing single file: {project_path.name}")
        analyzer.analyze_file(str(project_path))
        results = analyzer.compute_project_metrics()
    else:
        results = analyzer.analyze_project(str(project_path))

    # Compute docstring coverage for the same path
    coverage_pct, _, _, _ = compute_docstring_coverage(project_path)

    # Pass coverage into project metrics
    results = analyzer.compute_project_metrics(docstring_coverage=coverage_pct)

    output_dir = Path(output or config.get("output_dir", "quality_reports"))
    output_dir.mkdir(exist_ok=True)
    analyzer.generate_reports(results, str(output_dir))
    click.echo("✅ Reports generated!")

@cli.command()
@click.argument("path", type=click.Path(exists=True))
@click.option("-o", "--output", default="reviews.json")
@click.option("--no-openrouter", is_flag=True, help="Disable OpenRouter reviews")
@click.option("--no-ollama", is_flag=True, help="Disable Ollama reviews")
def review(path, output, no_openrouter, no_ollama):
    """Run analysis and generate review comments"""
    config = load_config()
    analyzer = CodeQualityAnalyzer()
    ai_engine = AIReviewEngine(
        use_openrouter=not no_openrouter,
        use_ollama=not no_ollama,
    )

    project_path = Path(path)

    # Same handling as scan
    if project_path.is_file() and project_path.suffix == ".py":
        click.echo(f"🔍 Analyzing single file: {project_path.name}")
        analyzer.analyze_file(str(project_path))
    else:
        _ = analyzer.analyze_project(str(project_path))

    smells = analyzer.smells
    click.echo(f"Found {len(smells)} smells for AI review")

    review_comments = ai_engine.generate_review_comments(smells)
    enhanced = [asdict(c) for c in review_comments]

    output_file = output
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(enhanced, f, indent=2, default=str)
    click.echo(f"Saved {len(review_comments)} reviews to {output_file}")

@cli.command()
@click.argument("file", type=click.Path(exists=True))
def report(file):
    """Pretty-print an existing review JSON"""
    with open(file, "r", encoding="utf-8") as f:
        data = json.load(f)

    for entry in data:
        click.echo(f"[{entry['severity'].upper()}] {entry['file']}:{entry['line']} - {entry['title']}")
        click.echo(f"  {entry['explanation']}")
        click.echo(f"  Suggestion: {entry['suggestion']}")
        click.echo("")

@cli.command()
@click.argument("path", type=click.Path(exists=True))
@click.option("--ai", is_flag=True, help="Use AI-powered auto-fix (function/method-level patches)")
@click.option("--openrouter", is_flag=True, help="Use OpenRouter models for AI auto-fix instead of local Ollama")
@click.option("-o", "--output", help="Output JSON log of applied fixes")
def apply(path, ai, openrouter, output):
    """Apply auto-fixes (basic or AI-powered)"""
    config = load_config()
    analyzer = CodeQualityAnalyzer()
    project_path = Path(path)

    # Run static analysis to get smells
    if project_path.is_file() and project_path.suffix == ".py":
        click.echo(f"🔍 Analyzing single file: {project_path.name}")
        analyzer.analyze_file(str(project_path))
    else:
        _ = analyzer.analyze_project(str(project_path))

    smells = analyzer.smells
    click.echo(f"Found {len(smells)} smells.")

    allowed_smells = config.get("auto_fix_smells", ["unused_imports"])

    # Pass engine choice + allowed smells
    engine = AutoFixEngine(use_openrouter=openrouter)

    if ai:
        click.echo("🤖 Running AI-powered auto-fix (function/method-level patches)...")
        fixes = engine.apply_ai_fixes(smells, allowed_smells=allowed_smells)
    else:
        click.echo("🛠 Running basic auto-fix (unused imports)...")
        fixes = engine.apply_fixes(smells)

    log_path = output or "applied_fixes.json"
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump([asdict(fx) for fx in fixes], f, indent=2, default=str)

    applied_count = sum(1 for fx in fixes if fx.applied)
    click.echo(f"✅ Applied {applied_count} fixes. Log written to {log_path}")

@cli.command()
@click.argument("path", type=click.Path(exists=True))
@click.option("--min-coverage", type=float, help="Fail if total coverage is below this percentage")
@click.option("-v", "--verbose", is_flag=True, help="Show per-file coverage details")
def docstrings(path, min_coverage, verbose):
    """Check docstring coverage"""
    project_path = Path(path)

    coverage_pct, documented, total_objects, per_file = compute_docstring_coverage(project_path)

    click.echo("\n📚 DOCSTRING COVERAGE REPORT")
    click.echo(f"  Files analyzed: {len(per_file)}")
    click.echo(f"  Total objects (functions/classes): {total_objects}")
    click.echo(f"  Documented:    {documented}")
    click.echo(f"  Missing:       {total_objects - documented}")
    click.echo(f"  Coverage:      {coverage_pct:.1f}%")

    if verbose:
        click.echo("\nPer-file coverage:")
        for filename, file_doc, file_total in per_file:
            if file_total == 0:
                pct = 100.0
            else:
                pct = (file_doc / file_total) * 100.0
            click.echo(f"  {filename}: {pct:.1f}% ({file_doc}/{file_total})")

    if min_coverage is not None:
        if coverage_pct < min_coverage:
            click.echo(f"\n❌ Coverage {coverage_pct:.1f}% is below required {min_coverage}%.")
            raise click.Abort()
        else:
            click.echo(f"\n✅ Coverage {coverage_pct:.1f}% meets required {min_coverage}%.")



def compute_docstring_coverage(path: Path):
    """Compute docstring coverage for all functions/classes under path."""
    py_files = []

    if path.is_file() and path.suffix == ".py":
        py_files = [path]
    else:
        for p in path.rglob("*.py"):
            if p.is_file() and not p.name.startswith("__"):
                py_files.append(p)

    total_objects = 0
    documented = 0
    per_file = []

    for f in py_files:
        with open(f, "r", encoding="utf-8") as src:
            try:
                tree = ast.parse(src.read())
            except SyntaxError:
                continue

        file_total = 0
        file_doc = 0

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                file_total += 1
                doc = ast.get_docstring(node, clean=False)
                if doc:
                    file_doc += 1

        total_objects += file_total
        documented += file_doc
        per_file.append((str(f), file_doc, file_total))

    coverage_pct = 0.0 if total_objects == 0 else (documented / total_objects) * 100.0
    return coverage_pct, documented, total_objects, per_file

@cli.command()
@click.argument("paths", nargs=-1, type=click.Path(exists=True))
@click.option("-o", "--output", default=".precommit_temp")
@click.option("--min-quality", type=float, default=6.0)
@click.option("--mode", type=click.Choice(["single", "batch"]), default="single")
def gate(paths, output, min_quality, mode):
    """Quality gate for pre-commit/CI"""
    from pathlib import Path
    import json
    import shutil

    CORE_FILES = {
        "cli.py", "code_quality_analyzer.py", "ai_review_engine.py",
        "autofix_engine.py", "config_loader.py", "main.py",
    }

    if not paths:
        click.echo("No files to analyze")
        sys.exit(0)  # Allow empty commits

    temp_dir = Path(output)
    temp_dir.mkdir(exist_ok=True)

    try:
        if mode == "single":
            # === your existing per-file loop ===
            failed_files = []

            for path_str in paths:
                path = Path(path_str)

                if path.name in CORE_FILES:
                    click.echo(f"⏭️ SKIP core: {path.name}")
                    continue

                click.echo(f"🔍 Gate: {path.name}")

                ctx = click.Context(cli)
                with ctx:
                    ctx.invoke(scan, path=str(path), output=str(temp_dir))

                report_path = temp_dir / "project_quality_report.json"
                with open(report_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                quality = data.get("avg_quality_score", 0.0)
                sev_dist = data.get("severity_distribution", {})

                medium = sev_dist.get("medium", 0)
                high = sev_dist.get("high", 0)
                critical = sev_dist.get("critical", 0)

                if medium > 0 or high > 0 or critical > 0:
                    click.echo(f"❌ FAILED {path.name}")
                    click.echo(f"  Quality: {quality:.1f} | Medium: {medium}")
                    failed_files.append(path.name)
                else:
                    click.echo(f"✅ PASSED {path.name} ({quality:.1f})")

            if failed_files:
                click.echo(f"\n🚫 BLOCKED {len(failed_files)} files:")
                for f in failed_files:
                    click.echo(f"  - {f}")
                raise click.Abort()

            click.echo("🎉 ALL FILES PASSED!")

        else:  # mode == "batch"
            # === new batch behaviour ===
            from pathlib import Path

            paths = [Path(p) for p in paths if Path(p).name not in CORE_FILES]
            if not paths:
                click.echo("No non-core files to analyze in batch")
                sys.exit(0)

            click.echo(f"📊 BATCH MODE: {len(paths)} files")

            # Run scan once over all files (your scan can take a dir or list)
            ctx = click.Context(cli)
            with ctx:
                # simplest: pass the folder (repo root) – scan will see all .py
                ctx.invoke(scan, path=".", output=str(temp_dir))

            report_path = temp_dir / "project_quality_report.json"
            with open(report_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            avg_quality = data.get("avg_quality_score", 0.0)
            total_smells = data.get("total_smells", 0)
            sev_dist = data.get("severity_distribution", {})

            click.echo(f"⭐ Avg Quality: {avg_quality:.1f}/10")
            click.echo(f"🐛 Total Smells: {total_smells}")
            click.echo(f"⚠️ Severity: {sev_dist}")

            if avg_quality < min_quality or total_smells > 0:
                click.echo("🚫 PROJECT FAILED (batch gate)")
                sys.exit(1)
            else:
                click.echo("🎉 PROJECT PASSED (batch gate)")

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    cli()
