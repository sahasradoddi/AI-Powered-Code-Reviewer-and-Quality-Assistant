#!/usr/bin/env python3
"""
COMPLETE CODE QUALITY ANALYZER
====================================================================
A single-file Python application that demonstrates ALL milestone requirements:
1. Code Smell Detection (Long Methods, God Classes, Deep Nesting)
2. Severity Classification (Low/Medium/High/Critical)
3. File-level & Project-level Quality Scores
4. Maintainability Index (MI) Calculation
5. Structured JSON & CSV Reports

REAL-LIFE SCENARIO: Generic System Analysis
"""

import ast
import json
import csv
import os
import math
import sys
from collections import defaultdict, Counter
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime # Added for realism, used in sample_code

@dataclass
class CodeSmell:
    """Represents a detected code smell with severity."""
    type: str
    file: str
    node_name: str
    line: int
    severity: str
    description: str

@dataclass
class FileMetrics:
    """File-level quality metrics."""
    file_path: str
    loc: int
    mi: float
    smells: List[CodeSmell]
    quality_score: float

class CodeQualityAnalyzer:
    """Main analyzer system."""

    def __init__(self):
        self.smells = []  # All detected smells
        self.files = {}   # File metrics
        self.severity_weights = {
            'low': 1, 'medium': 2, 'high': 3, 'critical': 5
        }

    def analyze_project(self, project_path: str) -> Dict[str, Any]:
        """Analyze entire project """
        # print("PROJECT CODE QUALITY ANALYSIS STARTED")
        project_path = Path(project_path)

        # Step 1: Parse all Python files
        for py_file in project_path.rglob("*.py"):
            if py_file.is_file() and not py_file.name.startswith('__'):
                print(f"  Analyzing: {py_file.name}")
                self.analyze_file(str(py_file))

        # Step 2: Compute project-level metrics
        project_metrics = self.compute_project_metrics()

        return project_metrics

    def analyze_file(self, file_path: str):
        """DETAILED FILE ANALYSIS - Detects ALL code smells."""
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            tree = ast.parse(f.read())
            metrics = FileMetrics(
            file_path=file_path,
            loc=len([n for n in ast.walk(tree) if isinstance(n, ast.stmt)]),
            mi=0.0,               # Will compute below
            smells=[],
            quality_score=0.0
        )

        # SMELL DETECTION 1: LONG METHODS (Functions > 20 lines)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                func_lines = self.count_lines(node)
                if func_lines > 20:  # LONG METHOD SMELL
                    severity = self.get_method_severity(func_lines)
                    smell = CodeSmell(
                        type="long_method",
                        file=file_path,
                        node_name=node.name,
                        line=node.lineno,
                        severity=severity,
                        description=f"Function {node.name}: {func_lines} lines"
                    )
                    metrics.smells.append(smell)

        # SMELL DETECTION 2: GOD CLASS (Classes > 100 lines or >10 methods)
        class_methods = defaultdict(int)
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_lines = self.count_lines(node)
                methods = sum(1 for n in ast.walk(node) if isinstance(n, ast.FunctionDef))
                class_methods[node.name] = methods

                if class_lines > 100 or methods > 10:
                    severity = "critical" if class_lines > 200 or methods > 15 else "high"
                    smell = CodeSmell(
                        type="god_class",
                        file=file_path,
                        node_name=node.name,
                        line=node.lineno,
                        severity=severity,
                        description=f"Class {node.name}: {class_lines}loc, {methods} methods"
                    )
                    metrics.smells.append(smell)

        # SMELL DETECTION 3: DEEP NESTING (>4 levels)
        max_nesting = self.find_max_nesting(tree)
        if max_nesting > 4:
            severity = "high" if max_nesting > 6 else "medium"
            smell = CodeSmell(
                type="deep_nesting",
                file=file_path,
                node_name="complex logic",
                line=1,
                severity=severity,
                description=f"Max nesting depth: {max_nesting}"
            )
            metrics.smells.append(smell)

        # SMELL DETECTION 4: LONG PARAMETER LIST (>4 args)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                param_count = len(node.args.args)
                if param_count > 4:
                    severity = "high" if param_count > 6 else "medium"
                    smell = CodeSmell(
                        type="long_parameter_list",
                        file=file_path,
                        node_name=node.name,
                        line=node.lineno,
                        severity=severity,
                        description=f"Function {node.name}: {param_count} parameters"
                    )
                    metrics.smells.append(smell)

        # SMELL DETECTION 5: MISSING TYPE HINTS (no annotations)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                has_annotations = any(arg.annotation is not None for arg in node.args.args)
                has_return_hint = node.returns is not None
                if not has_annotations and not has_return_hint:
                    severity = "medium" if len(node.args.args) > 2 else "low"
                    smell = CodeSmell(
                        type="missing_type_hints",
                        file=file_path,
                        node_name=node.name,
                        line=node.lineno,
                        severity=severity,
                        description=f"Function {node.name}: no parameter or return type hints"
                    )
                    metrics.smells.append(smell)

        # SMELL DETECTION 6: UNUSED IMPORTS
        imported_names = set()
        used_names = set()

        # Collect imported names
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                for alias in node.names:
                    imported_names.add(alias.name.split('.')[0])

        # Collect used names (simple version)
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                used_names.add(node.id)

        unused_imports = imported_names - used_names
        if unused_imports:
            severity = "low"
            smell = CodeSmell(
                type="unused_imports",
                file=file_path,
                node_name=", ".join(list(unused_imports)[:3]),
                line=1,
                severity=severity,
                description=f"Unused imports: {', '.join(list(unused_imports)[:3])}"
            )
            metrics.smells.append(smell)

        # SMELL DETECTION 7: MANY LOCAL VARIABLES
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue

            local_vars = set()

            for inner in ast.walk(node):
                # Simple Assign: x = ...
                if isinstance(inner, ast.Assign):
                    for target in inner.targets:
                        if isinstance(target, ast.Name):
                            local_vars.add(target.id)
                        elif isinstance(target, ast.Tuple):
                            for elt in target.elts:
                                if isinstance(elt, ast.Name):
                                    local_vars.add(elt.id)

                # Annotated assignment: x: int = ...
                elif isinstance(inner, ast.AnnAssign):
                    if isinstance(inner.target, ast.Name):
                        local_vars.add(inner.target.id)

            local_count = len(local_vars)

            if local_count > 8:  # threshold; adjust if needed
                severity = "medium" if local_count <= 15 else "high"
                smell = CodeSmell(
                    type="many_local_variables",
                    file=file_path,
                    node_name=node.name,
                    line=node.lineno,
                    severity=severity,
                    description=(
                        f"Function defines {local_count} local variables; "
                        "consider splitting into smaller functions."
                    ),
                )
                metrics.smells.append(smell)

        # SMELL DETECTION 8: FEATURE ENVY (heuristic)
        for class_node in ast.walk(tree):
            if not isinstance(class_node, ast.ClassDef):
                continue

            for node in class_node.body:
                if not isinstance(node, ast.FunctionDef):
                    continue

                base_counts = {}

                for attr in ast.walk(node):
                    if isinstance(attr, ast.Attribute) and isinstance(attr.value, ast.Name):
                        base = attr.value.id  # e.g. self, user, order
                        base_counts[base] = base_counts.get(base, 0) + 1

                if not base_counts:
                    continue

                self_count = base_counts.get("self", 0)

                # Find most-used foreign base
                foreign_items = [(b, c) for b, c in base_counts.items() if b != "self"]
                if not foreign_items:
                    continue

                foreign_base, foreign_count = max(foreign_items, key=lambda x: x[1])

                # Thresholds: must see foreign object enough times and clearly more than self
                if foreign_count >= 5 and foreign_count >= 2 * max(1, self_count):
                    smell = CodeSmell(
                        type="feature_envy",
                        file=file_path,
                        node_name=f"{class_node.name}.{node.name}",
                        line=node.lineno,
                        severity="medium",
                        description=(
                            f"Method uses attributes of '{foreign_base}' much more "
                            "than 'self'; consider moving or refactoring."
                        ),
                    )
                    metrics.smells.append(smell)

        # SMELL DETECTION 9: EXCEPTION SWALLOWING
        for node in ast.walk(tree):
            if isinstance(node, ast.Try):
                for handler in node.handlers:
                    # Broad except: bare "except:" or "except Exception:"
                    is_bare_except = handler.type is None
                    is_exception = (
                        isinstance(handler.type, ast.Name)
                        and handler.type.id == "Exception"
                    )

                    if not (is_bare_except or is_exception):
                        continue

                    # Body effectively empty or just "pass"
                    body = handler.body
                    body_is_empty = len(body) == 0
                    body_is_pass_only = (
                        len(body) == 1 and isinstance(body[0], ast.Pass)
                    )

                    if body_is_empty or body_is_pass_only:
                        smell = CodeSmell(
                            type="exception_swallowing",
                            file=file_path,
                            node_name="<module>",
                            line=handler.lineno,
                            severity="high",
                            description=(
                                "Exception swallowed with broad 'except' "
                                "and no real handling."
                            ),
                        )
                        metrics.smells.append(smell)
        # SMELL DETECTION 10: UNREACHABLE CODE
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                self._mark_unreachable_in_block(
                    file_path=file_path,
                    func_name=node.name,
                    block=node.body,
                    metrics=metrics,
                )



        # MAINTAINABILITY INDEX CALCULATION (MI Formula)
        cc = self.cyclomatic_complexity(tree)  # Branches/loops
        hv = self.halstead_volume(tree)        # Vocabulary complexity
        metrics.mi = self.calculate_mi(hv, cc, metrics.loc)

        # QUALITY SCORE (0-10): MI + smell penalty
        smell_penalty = sum(self.severity_weights[s.severity] for s in metrics.smells)
        metrics.quality_score = max(0, (metrics.mi / 20) - (smell_penalty * 0.5))

        self.files[file_path] = metrics
        self.smells.extend(metrics.smells)

    def _mark_unreachable_in_block(self, file_path: str, func_name: str,
                                block: list, metrics):
        """Detect unreachable statements in a linear block of statements."""
        dead = False
        for stmt in block:
            # If we've already hit a terminating statement in this block,
            # everything that follows is unreachable.
            if dead:
                smell = CodeSmell(
                    type="unreachable_code",
                    file=file_path,
                    node_name=func_name,
                    line=getattr(stmt, "lineno", 1),
                    severity="medium",
                    description="Statement is unreachable (after return/raise/break/continue).",
                )
                metrics.smells.append(smell)

            # If this statement ends control flow in this block, mark remaining as dead
            if isinstance(stmt, (ast.Return, ast.Raise, ast.Break, ast.Continue)):
                dead = True

            # Recurse into nested blocks
            if isinstance(stmt, (ast.If, ast.For, ast.While, ast.With,
                                ast.AsyncFor, ast.AsyncWith, ast.Try)):
                # For all these, we need to walk their internal statement lists
                for attr_name in ("body", "orelse", "finalbody", "handlers"):
                    sub = getattr(stmt, attr_name, None)
                    if not sub:
                        continue

                    # For Try, handlers is a list of ExceptHandler objects,
                    # each with its own .body
                    if attr_name == "handlers":
                        for handler in sub:
                            self._mark_unreachable_in_block(
                                file_path, func_name, handler.body, metrics
                            )
                    else:
                        self._mark_unreachable_in_block(
                            file_path, func_name, sub, metrics
                        )




    def count_lines(self, node: ast.AST) -> int:
        """Count logical lines for a node."""
        return len([n for n in ast.walk(node) if isinstance(n, ast.stmt)])

    def get_method_severity(self, lines: int) -> str:
        """Severity classification for long methods."""
        if lines > 50: return "critical"
        elif lines > 35: return "high"
        elif lines > 25: return "medium"
        return "low"

    def find_max_nesting(self, node: ast.AST, depth: int = 0, max_depth: List[int] = None) -> int:
        """Detect deep nesting levels."""
        if max_depth is None:
            max_depth = [0]

        max_depth[0] = max(max_depth[0], depth)

        # Iterate over all child nodes
        for child in ast.iter_child_nodes(node):
            # If the child node is a control flow construct, increment depth for its children
            if isinstance(child, (ast.If, ast.For, ast.While, ast.With, ast.AsyncFor, ast.AsyncWith, ast.Try)):
                self.find_max_nesting(child, depth + 1, max_depth)
            # For other types of nodes, continue traversing at the current depth
            else:
                self.find_max_nesting(child, depth, max_depth) # Recurse without increasing depth for non-control-flow nodes

        return max_depth[0]

    def cyclomatic_complexity(self, tree: ast.AST) -> int:
        """ cyclomatic complexity (branches/loops)."""
        complexity = 1
        for node in ast.walk(tree):
            if isinstance(node, (ast.If, ast.For, ast.While, ast.Assert)):
                complexity += 1
            elif isinstance(node, ast.BoolOp):
                complexity += len(node.values) - 1
        return complexity

    def halstead_volume(self, tree: ast.AST) -> float:
        """Simplified Halstead Volume """
        operators = set(['+', '-', '*', '/', '==', '!=', 'and', 'or'])
        operands = set()
        total_tokens = 0

        for node in ast.walk(tree):
            if isinstance(node, ast.BinOp):
                total_tokens += 1

                if isinstance(node.left, ast.Name):
                    operands.add(str(node.left.id))
                else:
                    operands.add(type(node.left).__name__) # Add the type name as an operand

                if isinstance(node.right, ast.Name):
                    operands.add(str(node.right.id))
                else:
                    operands.add(type(node.right).__name__) # Add the type name as an operand

        # If no binary operations are found, total_tokens will be 0.
        # This will result in hv being 0, which then causes a math domain error in math.log(hv).
        # The fix is primarily handled in calculate_mi by ensuring hv is at least 1.
        # The existing formula for hv: total_tokens * math.log2(len(operators) + len(operands) + 1)
        # If (len(operators) + len(operands) + 1) becomes 1 or less, math.log2 would be <=0,
        # so ensure the argument to log2 is at least 2.
        log_arg = len(operators) + len(operands) + 1
        if log_arg <= 1:
            log_arg = 2 # Ensures math.log2(log_arg) is at least 1

        return float(total_tokens) * math.log2(log_arg)


    def calculate_mi(self, hv: float, cc: int, loc: int) -> float:
        """Standard MI formula: 171 - 5.2ln(HV) - 0.23CC - 16.2ln(LOC)."""
        # Ensure hv and loc are at least 1 to prevent math domain errors for math.log(0)
        hv = max(1.0, hv)
        loc = max(1, loc) # loc should be at least 1 for any file with code
        return min(100, max(0, 171 - 5.2 * math.log(hv) - 0.23 * cc - 16.2 * math.log(loc)))

    def compute_project_metrics(self, docstring_coverage: float | None = None) -> Dict[str, Any]:
        """PROJECT-LEVEL AGGREGATION & SCORING."""
        total_smells = len(self.smells)
        total_severity = sum(self.severity_weights[s.severity] for s in self.smells)
    
        if len(self.files) == 0:
            avg_quality = 0.0
            project_mi = 0.0
        else:
            avg_quality = sum(f.quality_score for f in self.files.values()) / len(self.files)
            total_loc = sum(f.loc for f in self.files.values())
            if total_loc == 0:
                project_mi = 0.0
            else:
                project_mi = sum(f.mi * f.loc for f in self.files.values()) / total_loc
    
        severity_dist = Counter(s.severity for s in self.smells)
    
        result: Dict[str, Any] = {
            "project_mi": round(project_mi, 1),
            "avg_quality_score": round(avg_quality, 1),
            "total_files": len(self.files),
            "total_smells": total_smells,
            "severity_distribution": dict(severity_dist),
            "files": {path: asdict(metrics) for path, metrics in self.files.items()},
        }
    
        if docstring_coverage is not None:
            result["docstring_coverage"] = round(docstring_coverage, 1)
    
        return result


    def generate_reports(self, project_metrics: Dict[str, Any], output_directory: str):
        """Generate CSV, JSON, and HTML reports."""        
        output_dir = Path(output_directory)
        output_dir.mkdir(exist_ok=True)

        # Timestamp for reports
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        project_metrics['timestamp'] = timestamp

        # 1. JSON Report (EXISTING)
        json_path = output_dir / "project_quality_report.json"
        with open(json_path, 'w') as f:
            json.dump(project_metrics, f, indent=2, default=str)
        print(f"📄 JSON Report: {json_path}")

        # 2. CSV Report (EXISTING - your code stays exactly same)
        csv_path = output_dir / "project_quality_report.csv"
        flat_rows = []
        for file_path, metrics in project_metrics['files'].items():
            if metrics['smells']:
                for smell in metrics['smells']:
                    flat_rows.append({
                        'file': file_path,
                        'smell_type': smell['type'],
                        'function_class': smell['node_name'],
                        'line': smell['line'],
                        'severity': smell['severity'],
                        'description': smell['description'],
                        'file_mi': metrics['mi'],
                        'file_quality': metrics['quality_score']
                    })
            else:
                flat_rows.append({
                    'file': file_path,
                    'smell_type': '',
                    'function_class': '',
                    'line': '',
                    'severity': '',
                    'description': 'No code smells detected',
                    'file_mi': metrics['mi'],
                    'file_quality': metrics['quality_score']
                })

        if flat_rows:
            with open(csv_path, 'w', newline='') as f:
                fieldnames = ['file', 'smell_type', 'function_class', 'line', 'severity', 'description', 'file_mi', 'file_quality']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(flat_rows)
        print(f"📊 CSV Report: {csv_path}")

        # 3. NEW HTML Report
        self._generate_html_report(project_metrics, output_directory)

        # Summary Console Output (UPDATED)
        print(f"\n🚀 PROJECT SUMMARY:")
        print(f"   📈 Project MI: {project_metrics['project_mi']:.1f}")
        print(f"   ⭐ Avg Quality: {project_metrics['avg_quality_score']:.1f}/10")
        print(f"   📁 Files: {project_metrics['total_files']}")
        print(f"   🐛 Total Smells: {project_metrics['total_smells']}")
        print(f"   ⚠️  Severity: {dict(project_metrics['severity_distribution'])}")
        print(f"   📁 Reports generated in: {output_dir}")
        print(f"   🌐 HTML Dashboard: {output_dir}/code_review_dashboard.html")
        print(f"   🎉 Open HTML in browser for beautiful dashboard!")


    def _generate_html_report(self, project_metrics: Dict[str, Any], output_directory: str):
        """Generate beautiful HTML dashboard."""
        output_dir = Path(output_directory)
        html_path = output_dir / "code_review_dashboard.html"

        # Group smells by file
        smells_by_file = defaultdict(list)
        all_smells = []
        for file_path, metrics in project_metrics.get('files', {}).items():
            file_smells = metrics.get('smells', [])
            smells_by_file[file_path] = file_smells
            all_smells.extend(file_smells)

        severity_counts = Counter(s['severity'] for s in all_smells)

        html_content = f"""<!DOCTYPE html>
    <html>
    <head>
        <title>🚀 AI Code Review Dashboard</title>
        <style>
            body {{font-family:Arial,sans-serif;background:#f5f5f5;padding:20px}}
            .container {{max-width:1200px;margin:0 auto;background:white;border-radius:15px;padding:30px;box-shadow:0 10px 30px rgba(0,0,0,0.1)}}
            .header {{background:#4f46e5;color:white;padding:30px;border-radius:10px;text-align:center;margin-bottom:30px}}
            .metrics {{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:20px;margin:30px 0}}
            .metric {{background:#f8fafc;padding:20px;border-radius:10px;text-align:center}}
            .metric-value {{font-size:2.5em;font-weight:bold;margin-bottom:5px}}
            .good {{color:#10b981}} .warning {{color:#f59e0b}} .bad {{color:#ef4444}}
            .severity-grid {{display:grid;grid-template-columns:repeat(4,1fr);gap:15px;margin:30px 0}}
            .severity-card {{padding:15px;border-radius:8px;text-align:center;font-weight:bold}}
            .critical {{background:#fee2e2;color:#dc2626}} .high {{background:#fed7aa;color:#d97706}}
            .medium {{background:#fef3c7;color:#ca8a04}} .low {{background:#d1fae5;color:#059669}}
            table {{width:100%;border-collapse:collapse;margin:30px 0;font-size:14px}}
            th {{background:#1e293b;color:white;padding:12px;text-align:left;font-weight:600}}
            td {{padding:10px;border-bottom:1px solid #e2e8f0}}
            tr:nth-child(even) {{background:#f8fafc}}
            .critical-row {{background:#fee2e2!important}}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🚀 AI Code Review Dashboard</h1>
                <p>Generated: {project_metrics['timestamp']}</p>
            </div>
    
            <div class="metrics">
                <div class="metric">
                    <div class="metric-value {'good' if project_metrics['avg_quality_score']>7 else 'warning' if project_metrics['avg_quality_score']>4 else 'bad'}">
                        {project_metrics['avg_quality_score']:.1f}/10
                    </div>
                    <div>Quality Score</div>
                </div>
                <div class="metric">
                    <div class="metric-value" style="color:#10b981">{project_metrics.get('docstring_coverage', 0):.1f}%</div>
                    <div>Docstring Coverage</div>
                </div>
                <div class="metric">
                    <div class="metric-value" style="color:#8b5cf6">{project_metrics['project_mi']:.1f}</div>
                    <div>Maintainability Index</div>
                </div>
                <div class="metric">
                    <div class="metric-value" style="color:#ef4444">{project_metrics['total_smells']}</div>
                    <div>Total Smells</div>
                </div>
            </div>
    
            <div class="severity-grid">
                <div class="severity-card critical">Critical: {severity_counts.get('critical', 0)}</div>
                <div class="severity-card high">High: {severity_counts.get('high', 0)}</div>
                <div class="severity-card medium">Medium: {severity_counts.get('medium', 0)}</div>
                <div class="severity-card low">Low: {severity_counts.get('low', 0)}</div>
            </div>
    
            <table>
                <tr><th>File</th><th>Smells</th><th>Critical</th><th>High</th><th>Medium</th><th>Low</th><th>Severity</th></tr>
    """
        
        # File table rows
        for file_path, file_smells in smells_by_file.items():
            crit = sum(1 for s in file_smells if s['severity']=='critical')
            high = sum(1 for s in file_smells if s['severity']=='high')
            med = sum(1 for s in file_smells if s['severity']=='medium')
            low = sum(1 for s in file_smells if s['severity']=='low')
            total = len(file_smells)
            severity_class = 'critical-row' if crit > 0 else ''
            
            html_content += f"""
                <tr class="{severity_class}">
                    <td>{Path(file_path).name}</td>
                    <td>{total}</td>
                    <td>{crit}</td>
                    <td>{high}</td>
                    <td>{med}</td>
                    <td>{low}</td>
                    <td><strong>{'CRITICAL' if crit>0 else 'High' if high>0 else 'OK'}</strong></td>
                </tr>
            """
        
        html_content += """
            </table>
            <div style="background:#f1f5f9;padding:20px;border-radius:10px;margin:30px 0">
                <h3>🛠 AI Auto-Fix Results</h3>
                <p>Check <code>applied_fixes.json</code> for AI-generated fixes and safety rollbacks.</p>
            </div>
        </div>
    </body>
    </html>"""
        
        html_path.write_text(html_content, encoding='utf-8')
        print(f"🌐 HTML Dashboard: {html_path}")
    
    
    
def main(project_path: Optional[str] = None):
    """Shows ALL features working. Can take a project_path as input.
    If no path is provided, it will prompt the user.
    """
    print("CODE QUALITY ANALYZER")

    if project_path is None:
        project_path_input = input("Enter the path to the project directory or a single Python file to analyze (e.g., 'Any_project' or 'my_file.py'): ")
        if not project_path_input:
            print("Error: No path provided. Please provide a valid path to analyze.")
            return
        project_path = Path(project_path_input)
    else:
        project_path = Path(project_path)

    if not project_path.exists():
        print(f"Error: Path '{project_path}' does not exist. Please provide a valid path.")
        return

    analyzer = CodeQualityAnalyzer()
    results = {}

    if project_path.is_file() and project_path.suffix == '.py':
        print(f"  Analyzing single file: {project_path.name}")
        analyzer.analyze_file(str(project_path))
        results = analyzer.compute_project_metrics() # Compute metrics for the single file
    elif project_path.is_dir():
        results = analyzer.analyze_project(str(project_path))
    else:
        print("Error: Provided path is neither a Python file nor a directory.")
        return

    print("ANALYSIS COMPLETE!")

    # Ask user for report output path
    report_output_path = input("Enter the directory to store quality reports (e.g., 'my_reports', default: 'quality_reports'): ")
    if not report_output_path:
        report_output_path = "quality_reports"

    # Generate reports in the specified path
    analyzer.generate_reports(results, report_output_path)

    print("\nDEMO COMPLETE!")

if __name__ == "__main__":
    main()
