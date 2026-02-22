# autofix_engine.py
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any, Optional
import ast
import json

from ollama_engine import OllamaReviewEngine
from openrouter_engine import OpenRouterReviewEngine


@dataclass
class AutoFix:
    file: str
    line: int
    smell_type: str
    node_name: str
    original_code: str
    fixed_code: str
    applied: bool
    reason: str


class AutoFixEngine:
    def __init__(self, use_openrouter: bool = False):
        self.ollama = None
        self.openrouter = None
        if use_openrouter:
            self.openrouter = OpenRouterReviewEngine()
        else:
            self.ollama = OllamaReviewEngine()

    # ------------------------------
    # SIMPLE NON-AI FIXES (unused_imports)
    # ------------------------------
    def apply_fixes(self, smells: List[Any]) -> List[AutoFix]:
        """Very simple, line-level auto-fixes for safe patterns (unused_imports)."""
        fixes: List[AutoFix] = []

        smells_by_file: Dict[str, List[Any]] = {}
        for s in smells:
            smells_by_file.setdefault(s.file, []).append(s)

        for file_path, file_smells in smells_by_file.items():
            path = Path(file_path)
            if not path.is_file():
                continue

            lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()

            for smell in file_smells:
                if smell.type != "unused_imports":
                    continue

                idx = max(0, smell.line - 1)
                if idx >= len(lines):
                    continue

                original_line = lines[idx]

                if original_line.lstrip().startswith("#"):
                    fixes.append(
                        AutoFix(
                            file=file_path,
                            line=smell.line,
                            smell_type=smell.type,
                            node_name=getattr(smell, "node_name", ""),
                            original_code=original_line,
                            fixed_code=original_line,
                            applied=False,
                            reason="Import already commented",
                        )
                    )
                    continue

                fixed_line = "# AUTO-FIX: unused import\n" + original_line
                lines[idx] = fixed_line

                fixes.append(
                    AutoFix(
                        file=file_path,
                        line=smell.line,
                        smell_type=smell.type,
                        node_name=getattr(smell, "node_name", ""),
                        original_code=original_line,
                        fixed_code=fixed_line,
                        applied=True,
                        reason="Commented out unused import",
                    )
                )

            path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        return fixes

    # ------------------------------
    # AI HELPERS
    # ------------------------------
    def _get_ai_fix(self, smell: Any, before_src: str) -> Optional[str]:
        """Route to correct AI engine based on constructor choice."""
        if self.openrouter is not None:
            return self.openrouter.get_fix(smell, before_src)
        if self.ollama is not None:
            return self.ollama.get_fix(smell, before_src)
        return None

    def _get_node_source(self, source_lines: List[str], node: ast.AST) -> str:
        """Extract the original code for a function/method/class node."""
        start = node.lineno - 1
        end = getattr(node, "end_lineno", node.lineno)
        return "\n".join(source_lines[start:end])

    def _replace_node_source(
        self, source_lines: List[str], node: ast.AST, new_code: str
    ) -> List[str]:
        """Replace the node's source in the list of lines with new_code."""
        start = node.lineno - 1
        end = getattr(node, "end_lineno", node.lineno)
        new_lines = new_code.splitlines()
        return source_lines[:start] + new_lines + source_lines[end:]

    def _find_target_node(self, tree: ast.AST, smell: Any) -> Optional[ast.AST]:
        """Find the FunctionDef/ClassDef that corresponds to this smell."""
        target_name = getattr(smell, "node_name", None)
        target_line = getattr(smell, "line", None)

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if target_name and node.name != target_name:
                    continue
                if target_line is not None and abs(node.lineno - target_line) > 5:
                    continue
                return node
        return None

    # ------------------------------
    # AI-POWERED FIXES
    # ------------------------------
    def apply_ai_fixes(self, smells: List[Any], allowed_smells: List[str] = None) -> List[AutoFix]:
        """Call AI to patch functions/methods for selected smells."""
        if allowed_smells is None:
            allowed_smells = ["long_method", "long_parameter_list", "missing_type_hints", "unused_imports"]
            
        fixes: List[AutoFix] = []
        smells_by_file: Dict[str, List[Any]] = {}
        for s in smells:
            smells_by_file.setdefault(s.file, []).append(s)

        for file_path, file_smells in smells_by_file.items():
            path = Path(file_path)
            if not path.is_file():
                continue

            original_text = path.read_text(encoding="utf-8", errors="ignore")
            lines = original_text.splitlines()
            original_backup = original_text  # for rollback

            try:
                tree = ast.parse(original_text)
            except SyntaxError:
                print(f" ⚠️ Skipping auto-fix for {file_path} (syntax error).")
                continue

            file_fixes = []  # Track fixes for this file

            for smell in file_smells:
                if smell.type not in allowed_smells:
                    continue

                node = self._find_target_node(tree, smell)
                if node is None:
                    continue

                before_src = self._get_node_source(lines, node)
                fixed_src = self._get_ai_fix(smell, before_src)  
                if not fixed_src:
                    fixes.append(
                        AutoFix(
                            file=file_path,
                            line=smell.line,
                            smell_type=smell.type,
                            node_name=getattr(smell, "node_name", ""),
                            original_code=before_src,
                            fixed_code="",
                            applied=False,
                            reason="AI did not return a valid fix",
                        )
                    )
                    continue

                lines = self._replace_node_source(lines, node, fixed_src)
                file_fixes.append(
                    AutoFix(
                        file=file_path,
                        line=smell.line,
                        smell_type=smell.type,
                        node_name=getattr(smell, "node_name", ""),
                        original_code=before_src,
                        fixed_code=fixed_src,
                        applied=True,  # tentative
                        reason="AI patch applied",
                    )
                )

            # ✅ SAFETY: Validate syntax before writing
            new_text = "\n".join(lines) + "\n"
            try:
                ast.parse(new_text)
                path.write_text(new_text, encoding="utf-8")
                # All good, commit fixes
                fixes.extend(file_fixes)
                print(f" ✅ AI fixes applied to {path.name}")
            except SyntaxError:
                print(f" ❌ AI patch broke syntax in {file_path}. Rolling back.")
                path.write_text(original_backup, encoding="utf-8")
                # Mark all fixes for this file as failed
                for fx in file_fixes:
                    fx.applied = False
                    fx.reason = "AI patch broke syntax; rolled back"
                fixes.extend(file_fixes)

        return fixes
