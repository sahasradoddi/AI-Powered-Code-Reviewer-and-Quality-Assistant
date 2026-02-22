import json
import os
import pathlib
import requests
from typing import Tuple, Optional, Any, List
from dotenv import load_dotenv

try:  # Python 3.11+
    import tomllib
except ImportError:  # Python <=3.10
    import tomli as tomllib


class OpenRouterReviewEngine:
    def __init__(self):
        # Default lists (used if config missing) - STABLE FREE MODELS
        default_models = [
            "qwen/qwen2.5-coder:free",
            "deepseek/deepseek-coder-v2:free",
            "google/gemma-2-9b-it:free",
        ]
        default_fallback = [
            "meta-llama/llama-3.2-1b-instruct:free",
            "microsoft/phi-3-mini-128k-instruct:free",
        ]

        config_models, config_fallback = self._load_model_config_from_pyproject()
        self.openrouter_models: List[str] = config_models or default_models
        self.fallback_openrouter_models: List[str] = config_fallback or default_fallback

        print("DEBUG effective models:", self.openrouter_models)
        print("DEBUG effective fallback:", self.fallback_openrouter_models)

        # Load .env
        env_path = os.path.join(os.path.dirname(__file__), ".env")
        load_dotenv(dotenv_path=env_path)

        self.api_key = os.getenv("OPENROUTER_API_KEY")
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"

    def _load_model_config_from_pyproject(self) -> Tuple[Optional[list], Optional[list]]:
        pyproject_path = pathlib.Path.cwd() / "pyproject.toml"
        if not pyproject_path.is_file():
            print(f" ⚠️ pyproject.toml not found at {pyproject_path}")
            return None, None

        try:
            with open(pyproject_path, "rb") as f:
                data = tomllib.load(f)
            cfg = data.get("tool", {}).get("ai_reviewer", {})
            return cfg.get("openrouter_models"), cfg.get("fallback_openrouter_models")
        except Exception as e:
            print(f" ⚠️ Could not read pyproject.toml model config: {e}")
            return None, None

    # ----------------- REVIEW PATH (JSON OUTPUT) -----------------
    def _parse_ai_json(self, content: str) -> Optional[Tuple[str, str, str]]:
        try:
            clean_str = content.replace("```json", "").replace("```", "").strip()
            data = json.loads(clean_str)
            return (
                str(data.get("title", "AI Review Unavailable")),
                str(
                    data.get(
                        "explanation",
                        "The AI did not provide a detailed explanation.",
                    )
                ),
                str(
                    data.get(
                        "suggestion",
                        "Consider refactoring based on general code quality guidelines.",
                    )
                ),
            )
        except json.JSONDecodeError:
            print("      ❌ OpenRouter: JSON parsing failed.")
            return None
        except Exception as e:
            print(f"      ❌ OpenRouter: Error parsing AI output: {e}")
            return None

    def get_review(self, smell: Any) -> Optional[Tuple[str, str, str]]:
        if not self.api_key:
            print("      ⚠️ OPENROUTER_API_KEY not set. Skipping OpenRouter review.")
            return None

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "http://localhost:3000",
            "X-Title": "Code Review Project",
            "Content-Type": "application/json",
        }

        # Handle nodename / node_name safely
        node_name = getattr(smell, "nodename", getattr(smell, "node_name", ""))

        prompt = (
            "Return ONLY JSON: {'title': '...', 'explanation': '...', 'suggestion': '...'}\n"
            f"Review the following code smell: Type: {smell.type}, "
            f"Node: {node_name}, Description: {smell.description}"
        )

        all_models_to_try = self.openrouter_models + self.fallback_openrouter_models

        for model_id in all_models_to_try:
            payload = {
                "model": model_id,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are a Python expert. Output valid JSON only. "
                            "Do not include any preambles or explanations outside the JSON object."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.2,
            }

            try:
                print(f"      Trying OpenRouter model: {model_id}")
                response = requests.post(
                    self.api_url, headers=headers, json=payload, timeout=40
                )

                if response.status_code == 200:
                    data = response.json()
                    raw_content = data["choices"][0]["message"]["content"]
                    parsed_review = self._parse_ai_json(raw_content)
                    if parsed_review:
                        print(
                            f"      ✅ OpenRouter ({model_id.split('/')[-1]}): "
                            f"{parsed_review[0][:50]}..."
                        )
                        return parsed_review

                elif response.status_code == 401:
                    print(
                        "      ❌ OpenRouter: Invalid API Key. "
                        "Please check your OPENROUTER_API_KEY."
                    )
                    return None
                elif response.status_code == 429:
                    print(
                        f"      ⏭️  OpenRouter ({model_id.split('/')[-1]}): "
                        "Rate limit hit. Trying next model."
                    )
                    continue
                elif response.status_code in [500, 503, 504]:
                    print(
                        f"      ⏭️  OpenRouter ({model_id.split('/')[-1]}): "
                        f"Server error ({response.status_code}). Trying next model."
                    )
                    continue
                else:
                    print(
                        f"      ⏭️  OpenRouter ({model_id.split('/')[-1]}): "
                        f"API error (Status {response.status_code}). Trying next model."
                    )
                    continue

            except requests.exceptions.Timeout:
                print(
                    f"      ❌ OpenRouter ({model_id.split('/')[-1]}): "
                    "Request timed out after 40 seconds. Trying next model."
                )
                continue
            except requests.exceptions.ConnectionError as ce:
                print(
                    f"      ❌ OpenRouter ({model_id.split('/')[-1]}): "
                    f"Connection error: {ce}. Check internet/proxy. Trying next model."
                )
                continue
            except Exception as e:
                print(
                    f"      ❌ OpenRouter ({model_id.split('/')[-1]}): "
                    f"Unexpected error: {str(e)[:100]}. Trying next model."
                )
                continue

        print("      ⚠️ OpenRouter: All models failed or no API key. Falling back.")
        return None

    # ----------------- AUTO-FIX PATH (CODE OUTPUT) -----------------
    def get_fix(self, smell: Any, original_source: str) -> Optional[str]:
        """
        Ask OpenRouter to return a patched version of the SAME function/method
        containing this smell. Returns pure Python code (no fences, no comments).
        """
        if not self.api_key:
            print("      ⚠️ OPENROUTER_API_KEY not set. Skipping OpenRouter auto-fix.")
            return None

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "http://localhost:3000",
            "X-Title": "Code Review Project",
            "Content-Type": "application/json",
        }

        node_name = getattr(smell, "nodename", getattr(smell, "node_name", ""))

        prompt = f"""
You are a professional Python refactoring assistant.

Given this Python function or method that contains a specific code smell,
return a corrected version of the SAME function/method ONLY.

Requirements:
- Preserve the function/method name and signature exactly
- Keep behavior logically equivalent (only improve style/readability/safety)
- Do NOT add surrounding code (no imports, no extra functions)
- Do NOT wrap the code in ``` or any Markdown
- Do NOT include any explanations or comments
- Return ONLY valid Python code

Smell type: {smell.type}
File: {smell.file}:{smell.line}
Function/Class: {node_name}
Issue: {smell.description}

Original code:
{original_source}

Return ONLY the fixed function/method code.
""".strip()

        all_models_to_try = self.openrouter_models + self.fallback_openrouter_models

        for model_id in all_models_to_try:
            payload = {
                "model": model_id,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are a Python refactoring assistant. "
                            "Return ONLY valid Python code for the fixed function/method. "
                            "No markdown, no explanations, pure Python code only."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.1,  # Lower for more consistent code
            }

            try:
                print(f"      Trying OpenRouter auto-fix model: {model_id}")
                response = requests.post(
                    self.api_url, headers=headers, json=payload, timeout=45
                )

                if response.status_code == 200:
                    data = response.json()
                    # Correct list indexing (same as review path)
                    raw_content = data["choices"][0]["message"]["content"]

                    # Clean code output
                    code = (
                        raw_content.replace("```python", "")
                        .replace("``` py", "")
                        .replace("```", "")
                        .strip()
                    )

                    # More permissive: accept any non-empty code;
                    # later AST parse in AutoFixEngine will reject broken patches.
                    if code:
                        print("------ RAW FIXED CODE START ------")
                        print(code)
                        print("------ RAW FIXED CODE END ------")
                        print(
                            f"      ✅ OpenRouter auto-fix succeeded: {len(code)} chars"
                        )
                        return code
                    else:
                        print(
                            "      ❌ OpenRouter auto-fix: empty output, "
                            "trying next model."
                        )

                elif response.status_code == 401:
                    print("      ❌ OpenRouter auto-fix: invalid API key.")
                    return None
                elif response.status_code == 429:
                    print(
                        f"      ⏭️ OpenRouter auto-fix ({model_id.split('/')[-1]}): "
                        "rate limit, trying next model."
                    )
                    continue
                elif response.status_code in (500, 503, 504):
                    print(
                        f"      ⏭️ OpenRouter auto-fix ({model_id.split('/')[-1]}): "
                        f"server error {response.status_code}, trying next model."
                    )
                    continue
                else:
                    print(
                        f"      ⏭️ OpenRouter auto-fix ({model_id.split('/')[-1]}): "
                        f"API error {response.status_code}"
                    )
                    continue

            except requests.exceptions.Timeout:
                print(
                    f"      ❌ OpenRouter auto-fix ({model_id.split('/')[-1]}): "
                    "timeout"
                )
                continue
            except requests.exceptions.ConnectionError:
                print(
                    f"      ❌ OpenRouter auto-fix ({model_id.split('/')[-1]}): "
                    "connection error"
                )
                continue
            except Exception as e:
                print(
                    f"      ❌ OpenRouter auto-fix ({model_id.split('/')[-1]}): "
                    f"{str(e)[:80]}"
                )
                continue

        print("      ⚠️ OpenRouter auto-fix: all models failed.")
        return None
