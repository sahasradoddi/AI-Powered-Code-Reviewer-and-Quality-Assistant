#!/usr/bin/env python3
import argparse
from dataclasses import asdict
from pathlib import Path
import json
import ast
from autofix_engine import AutoFixEngine  # new import
from code_quality_analyzer import CodeQualityAnalyzer
from ai_review_engine import AIReviewEngine
from config_loader import load_config

from dotenv import load_dotenv
load_dotenv()  # Loads your .env file automatically


def cmd_scan(args):
    config = load_config()
    analyzer = CodeQualityAnalyzer()

    project_path = Path(args.path)

    # Handle single files and directories
    if project_path.is_file() and project_path.suffix == ".py":
        print(f"🔍 Analyzing single file: {project_path.name}")
        analyzer.analyze_file(str(project_path))
        results = analyzer.compute_project_metrics()
    else:
        results = analyzer.analyze_project(str(project_path))

    # 🔹 NEW: compute docstring coverage for the same path
    coverage_pct, _, _, _ = compute_docstring_coverage(project_path)

    # 🔹 Pass coverage into project metrics
    results = analyzer.compute_project_metrics(docstring_coverage=coverage_pct)

    output_dir = Path(args.output or config.get("output_dir", "quality_reports"))
    output_dir.mkdir(exist_ok=True)
    analyzer.generate_reports(results, str(output_dir))


def cmd_review(args):
    config = load_config()
    analyzer = CodeQualityAnalyzer()
    ai_engine = AIReviewEngine(
        use_openrouter=not args.no_openrouter,
        use_ollama=not args.no_ollama,
    )

    project_path = Path(args.path)

    # Same handling as scan
    if project_path.is_file() and project_path.suffix == ".py":
        print(f"🔍 Analyzing single file: {project_path.name}")
        analyzer.analyze_file(str(project_path))
    else:
        _ = analyzer.analyze_project(str(project_path))

    smells = analyzer.smells
    print(f"Found {len(smells)} smells for AI review")

    review_comments = ai_engine.generate_review_comments(smells)
    enhanced = [asdict(c) for c in review_comments]

    output_file = args.output or "reviews.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(enhanced, f, indent=2, default=str)
    print(f"Saved {len(review_comments)} reviews to {output_file}")


def cmd_report(args):
    with open(args.file, "r", encoding="utf-8") as f:
        data = json.load(f)

    for entry in data:
        print(f"[{entry['severity'].upper()}] {entry['file']}:{entry['line']} - {entry['title']}")
        print(f"  {entry['explanation']}")
        print(f"  Suggestion: {entry['suggestion']}")
        print()


def cmd_apply(args):
    config = load_config()  # ✅ Load config for allowed_smells
    analyzer = CodeQualityAnalyzer()
    project_path = Path(args.path)

    # Run static analysis to get smells
    if project_path.is_file() and project_path.suffix == ".py":
        print(f"🔍 Analyzing single file: {project_path.name}")
        analyzer.analyze_file(str(project_path))
    else:
        _ = analyzer.analyze_project(str(project_path))

    smells = analyzer.smells
    print(f"Found {len(smells)} smells.")

    allowed_smells = config.get("auto_fix_smells", ["unused_imports"])  # ✅ From config

    # ✅ Pass engine choice + allowed smells
    engine = AutoFixEngine(use_openrouter=args.openrouter)

    if args.ai:
        print("🤖 Running AI-powered auto-fix (function/method-level patches)...")
        fixes = engine.apply_ai_fixes(smells, allowed_smells=allowed_smells)  # ✅ Correct method + param
    else:
        print("🛠 Running basic auto-fix (unused imports)...")
        fixes = engine.apply_fixes(smells)  # ✅ Simple non-AI path

    log_path = args.output or "applied_fixes.json"
    from dataclasses import asdict
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump([asdict(fx) for fx in fixes], f, indent=2, default=str)

    applied_count = sum(1 for fx in fixes if fx.applied)
    print(f"✅ Applied {applied_count} fixes. Log written to {log_path}")



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


def cmd_docstrings(args):
    project_path = Path(args.path)

    coverage_pct, documented, total_objects, per_file = compute_docstring_coverage(project_path)

    print("\nDOCSTRING COVERAGE REPORT")
    print(f"  Files analyzed: {len(per_file)}")
    print(f"  Total objects (functions/classes): {total_objects}")
    print(f"  Documented:    {documented}")
    print(f"  Missing:       {total_objects - documented}")
    print(f"  Coverage:      {coverage_pct:.1f}%")

    if args.verbose:
        print("\nPer-file coverage:")
        for filename, file_doc, file_total in per_file:
            if file_total == 0:
                pct = 100.0
            else:
                pct = (file_doc / file_total) * 100.0
            print(f"  {filename}: {pct:.1f}% ({file_doc}/{file_total})")

    threshold = args.min_coverage
    if threshold is not None:
        if coverage_pct < threshold:
            print(f"\n❌ Coverage {coverage_pct:.1f}% is below required {threshold}%.")
            raise SystemExit(1)
        else:
            print(f"\n✅ Coverage {coverage_pct:.1f}% meets required {threshold}%.")


def main():
    parser = argparse.ArgumentParser(
        prog="code-reviewer",
        description="AI-Powered Code Reviewer CLI",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # scan
    p_scan = subparsers.add_parser("scan", help="Run static analysis and generate quality reports")
    p_scan.add_argument("path", help="Project path (directory or file)")
    p_scan.add_argument("-o", "--output", help="Output directory for reports")
    p_scan.set_defaults(func=cmd_scan)

    # review
    p_review = subparsers.add_parser("review", help="Run analysis and generate review comments")
    p_review.add_argument("path", help="Project path (directory or file)")
    p_review.add_argument("-o", "--output", help="Output JSON file for reviews")
    p_review.add_argument("--no-openrouter", action="store_true", help="Disable OpenRouter reviews")
    p_review.add_argument("--no-ollama", action="store_true", help="Disable Ollama reviews")
    p_review.set_defaults(func=cmd_review)

    # report
    p_report = subparsers.add_parser("report", help="Pretty-print an existing review JSON")
    p_report.add_argument("file", help="Path to reviews.json")
    p_report.set_defaults(func=cmd_report)

    # docstrings
    p_doc = subparsers.add_parser("docstrings", help="Check docstring coverage")
    p_doc.add_argument("path", help="Project path (directory or file)")
    p_doc.add_argument("--min-coverage", type=float, default=None, help="Fail if total coverage is below this percentage")
    p_doc.add_argument("-v", "--verbose", action="store_true", help="Show per-file coverage details")
    p_doc.set_defaults(func=cmd_docstrings)

    # ✅ apply - ALL arguments defined here
    p_apply = subparsers.add_parser("apply", help="Apply auto-fixes (basic or AI-powered)")
    p_apply.add_argument("path", help="Project path (directory or file)")
    p_apply.add_argument("--ai", action="store_true", help="Use AI-powered auto-fix (function/method-level patches)")
    p_apply.add_argument("--openrouter", action="store_true", help="Use OpenRouter models for AI auto-fix instead of local Ollama")
    p_apply.add_argument("-o", "--output", help="Output JSON log of applied fixes", default=None)
    p_apply.set_defaults(func=cmd_apply)

    # ✅ Single parse at end
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
