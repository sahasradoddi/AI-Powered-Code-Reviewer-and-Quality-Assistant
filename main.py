#!/usr/bin/env python3
from dataclasses import asdict
from pathlib import Path
import json
from code_quality_analyzer import CodeQualityAnalyzer
from ai_review_engine import AIReviewEngine

def main():
    print(" CODE ANALYZER + AI REVIEW")
    print("=" * 40)

    project_path = input("Project path (or 'test_project'): ") or "test_project"
    project_path = Path(project_path)

    if not project_path.exists():
        print(" Path not found!")
        return

    # 1. STATIC ANALYSIS FIRST (clean)
    print("🔍 Running static analysis...")
    analyzer = CodeQualityAnalyzer()
    
    if project_path.is_file() and project_path.suffix == '.py':
        print(f"  Analyzing single file: {project_path.name}")
        analyzer.analyze_file(str(project_path))
        results = analyzer.compute_project_metrics()
    else:
        print(f"  Analyzing project: {project_path}")
        results = analyzer.analyze_project(str(project_path))

    # 2. SAVE CLEAN STATIC REPORT FIRST
    analyzer.generate_reports(results, "reports")
    print("✅ Static reports saved (no AI fields)")

    # 3. AI REVIEW SECOND (separate)
    print("\n🤖 Generating AI reviews...")
    engine = AIReviewEngine()
    ai_comments = engine.generate_review_comments(analyzer.smells)

    # 4. PRINT AI COMMENTS ONCE
    print("\n🤖 AI REVIEW COMMENTS:")
    print("-" * 60)
    for c in ai_comments:
        print(f"📄 {Path(c.file).name}:{c.line} [{c.severity.upper()}]")
        print(f"   {c.title}")
        print(f"   💡 {c.explanation}")
        print(f"   🔧 {c.suggestion}")
        print()
    print("✅ AI review complete")

    # 5. SAVE AI SEPARATELY (optional)
    ai_report_path = Path("reports/ai_reviews.json")
    ai_report_path.parent.mkdir(exist_ok=True)
    with open(ai_report_path, 'w', encoding='utf-8') as f:
        json.dump([asdict(c) for c in ai_comments], f, indent=2)
    print(f"💾 AI reviews saved: {ai_report_path}")

if __name__ == "__main__":
    main()
