import json
import subprocess
from typing import Tuple, Optional, Any


class OllamaReviewEngine:
    def __init__(self):
        self.ollama_model = "phi3:mini"

    def _parse_ai_json(self, content: str) -> Optional[Tuple[str, str, str,str]]:
        try:
            # Ollama sometimes wraps JSON in ```json...```
            clean_str = content.replace("```json", "").replace("```", "").strip()
            data = json.loads(clean_str)
            return (
                str(data.get("title", "AI Review Unavailable")),
                str(data.get("explanation", "The AI did not provide a detailed explanation.")),
                str(data.get("suggestion", "Consider refactoring based on general code quality guidelines.")),
                str(data.get("severity", "")).lower()  # new

            )
        except json.JSONDecodeError:
            print("      ❌ Phi-3: JSON parsing failed.")
            return None
        except Exception as e:
            print(f"      ❌ Phi-3: Error parsing AI output: {e}")
            return None

    def get_review(self, smell: Any) -> Optional[Tuple[str, str, str,str]]:
        prompt = f"""
You are a professional Python code reviewer.

Analyze the given code smell and respond ONLY with valid JSON.

JSON format:
{{
  "title": "Short professional title",
  "explanation": "Explain WHY this smell occurred, strictly based on the smell type",
  "suggestion": "Actionable refactoring advice specific to this smell type",
  "severity": "info | warning | critical"
}}

Rules:
- Do NOT mention type hints unless the smell type is "missing_type_hints"
- Focus ONLY on the provided smell type
- No generic Python advice

Code smell details:
File: {smell.file}:{smell.line}
Smell type: {smell.type}
Function/Class: {smell.node_name}
Issue: {smell.description}
"""

        try:
            print(f"      Trying Ollama model: {self.ollama_model}")
            result = subprocess.run(
                ["ollama", "run", self.ollama_model, prompt],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='ignore',
                timeout=120
            )

            if result.returncode == 0:
                output = result.stdout.strip()
                parsed_review = self._parse_ai_json(output)
                if parsed_review:
                    print(f"      ✅ Phi-3 ({self.ollama_model.split(':')[-1]}): {parsed_review[0][:50]}...")
                    return parsed_review
            else:
                print(f"  ❌ Ollama ({self.ollama_model.split(':')[-1]}): Command failed with exit code {result.returncode}. Stderr: {result.stderr.strip()[:100]}")

        except FileNotFoundError:
            print("      ❌ Ollama executable not found. Is Ollama installed and in your PATH?")
        except subprocess.TimeoutExpired:
            print(f"      ❌ Ollama ({self.ollama_model.split(':')[-1]}): Command timed out after 120 seconds.")
        except Exception as e:
            print(f"      ❌ Ollama ({self.ollama_model.split(':')[-1]}): Unexpected error during execution: {str(e)[:100]}")

        print(f"      ⚠️ Ollama ({self.ollama_model.split(':')[-1]}): Failed to get a valid review. Falling back.")
        return None


    def get_fix(self, smell: Any, original_source: str) -> Optional[str]:
        """
        Ask Ollama to return a patched version of the SAME function/method
        containing this smell. Returns pure Python code (no JSON, no fences).
        """
        print(f"DEBUG: Using Ollama model: '{self.ollama_model}'")  

        prompt = f"""
You are a professional Python refactoring assistant.

Given this Python function or method that contains a specific code smell,
return a corrected version of the SAME function/method ONLY.

Requirements:
- Preserve the function/method name and signature.
- Keep behavior logically equivalent (only improve style/readability/safety).
- Do NOT add surrounding code (no imports, no extra functions).
- Do NOT wrap the code in ``` or any Markdown.
- Do NOT include any explanations or comments.

Smell type: {smell.type}
File: {smell.file}:{smell.line}
Function/Class: {smell.node_name}
Issue: {smell.description}

Original code:
{original_source}

Return ONLY the fixed function/method code.
"""

        try:
            print(f"      Trying Ollama auto-fix model: {self.ollama_model}")
            result = subprocess.run(
                ["ollama", "run", self.ollama_model, prompt],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
                timeout=180,
            )

            if result.returncode == 0:
                output = result.stdout.strip()
                # Clean up accidental fences if model adds them
                output = output.replace("```python", "").replace("```", "").strip()
                if output:
                    return output
                print("      ❌ Ollama auto-fix: empty output.")
            else:
                print(
                    f"  ❌ Ollama auto-fix ({self.ollama_model.split(':')[-1]}): "
                    f"exit code {result.returncode}. Stderr: {result.stderr.strip()[:100]}"
                )
        except FileNotFoundError:
            print("      ❌ Ollama executable not found for auto-fix. Is it installed and in PATH?")
        except subprocess.TimeoutExpired:
            print(f"      ❌ Ollama auto-fix ({self.ollama_model.split(':')[-1]}): timed out after 120 seconds.")
        except Exception as e:
            print(
                f"      ❌ Ollama auto-fix ({self.ollama_model.split(':')[-1]}): "
                f"Unexpected error: {str(e)[:100]}"
            )

        print(f"      ⚠️ Ollama auto-fix ({self.ollama_model.split(':')[-1]}): failed to get a valid patch.")
        return None
