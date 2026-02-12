from dataclasses import dataclass, asdict
from typing import List, Any, Optional
import os
import time

from openrouter_engine import OpenRouterReviewEngine
from ollama_engine import OllamaReviewEngine
from rule_based_engine import RuleBasedReviewEngine


@dataclass
class ReviewComment:
    file: str
    line: int
    severity: str
    title: str
    explanation: str
    suggestion: str


class AIReviewEngine:
    def __init__(self, use_openrouter: bool = True, use_ollama: bool = True):
        # Initialize engines conditionally
        self.openrouter_engine: Optional[OpenRouterReviewEngine] = (
            OpenRouterReviewEngine() if use_openrouter else None
        )
        self.ollama_engine: Optional[OllamaReviewEngine] = (
            OllamaReviewEngine() if use_ollama else None
        )
        self.rule_based_engine = RuleBasedReviewEngine()

        # Reduced delay for consolidation phase, actual delays are handled by engines
        self.REQUEST_DELAY = 1.0

    def _normalize_severity(self, ai_severity: str, static_severity: str) -> str:
        ai_severity = (ai_severity or "").lower().strip()
        if ai_severity in {"info", "warning", "critical"}:
            return ai_severity
        # fallback mapping from your existing low/medium/high/critical
        mapping = {
            "low": "info",
            "medium": "warning",
            "high": "critical",
            "critical": "critical",
        }
        return mapping.get(static_severity.lower(), "warning")

    def generate_review_comments(self, smells: List[Any]) -> List[ReviewComment]:
        comments: List[ReviewComment] = []
        total = len(smells)
        print(f"\n🚀 AI REVIEW ENGINE: Processing {total} smells...")
        print("-" * 65)

        for i, smell in enumerate(smells, 1):
            if i > 1:
                time.sleep(self.REQUEST_DELAY)

            file_name = os.path.basename(smell.file)
            print(f"[{i}/{total}] 🔍 Analyzing {file_name}:{smell.line}")

            review_result = None

            # 1. Try OpenRouter if enabled
            if self.openrouter_engine is not None:
                review_result = self.openrouter_engine.get_review(smell)

            # 2. If OpenRouter failed or disabled, try Ollama if enabled
            if review_result is None and self.ollama_engine is not None:
                review_result = self.ollama_engine.get_review(smell)

            # 3. If all AI engines fail or are disabled, use rule-based
            ai_severity = ""
            if review_result is None:
                title, explanation, suggestion = self.rule_based_engine.get_review(smell)
            else:
                # review_result from AI now has 4 elements
                title, explanation, suggestion, ai_severity = review_result

            severity = self._normalize_severity(ai_severity, smell.severity)

            comments.append(
                ReviewComment(
                    file=smell.file,
                    line=smell.line,
                    severity=severity,
                    title=title,
                    explanation=explanation,
                    suggestion=suggestion,
                )
            )

        print("-" * 65)
        print("✅ AI Review Complete.\n")
        return comments