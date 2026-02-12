import json
from typing import Tuple, Any


class RuleBasedReviewEngine:
    def get_review(self, smell: Any) -> Tuple[str, str, str]:
        """Professional fallback templates for various code smells."""
        templates = {
            "long_method": (
                f"Function '{smell.node_name}' too long",
                f"{smell.description}. Violates Single Responsibility Principle. Methods should ideally do one thing well.",
                "Extract 2-3 focused helper methods (e.g., for validation, computation, I/O) to improve readability and maintainability."
            ),

            "god_class": (
                f"Class '{smell.node_name}' violates SRP",
                f"{smell.description}. This class has too many responsibilities, making it hard to understand, test, and maintain.",
                "Split this class into several smaller, more focused classes, each handling a single responsibility. Consider patterns like Facade or Strategy."
            ),

            "deep_nesting": (
                "Excessive nesting detected",
                f"{smell.description}. Deeply nested code reduces readability and increases cognitive load, creating 'arrow code' that is hard to follow.",
                "Use guard clauses, early returns, or refactor complex conditions into separate functions to flatten the code structure."
            ),

            "long_parameter_list": (
                f"Function '{smell.node_name}' has too many parameters",
                f"{smell.description}. A long parameter list makes a function harder to call, understand, and test.",
                "Group related parameters into a custom object (Data Transfer Object) or a named tuple. Consider if the function is doing too many things and can be split."
            ),

            "missing_type_hints": (
                f"Function '{smell.node_name}' missing type hints",
                f"{smell.description}. Lack of type hints reduces code clarity and makes static analysis tools less effective, hindering developer understanding.",
                "Add type hints to function parameters and return values to improve code readability, enable static analysis, and reduce runtime errors."
            ),

            "unused_imports": (
                "Unused imports detected",
                f"Unused imports like {smell.node_name} increase file size and can cause confusion. They indicate dead code or incomplete refactoring.",
                "Remove all unused import statements to clean up the code, improve readability, and prevent potential naming conflicts. Use a linter to identify them."
            ),

            # NEW: exception_swallowing
            "exception_swallowing": (
                "Exceptions are being swallowed",
                f"{smell.description}. Swallowing exceptions (especially with bare 'except' or 'except Exception') hides real errors and makes debugging very difficult.",
                "Handle specific exception types and either log, re-raise, or convert them into meaningful error messages. Avoid bare 'except:' unless you re-raise immediately."
            ),

            # NEW: unreachable_code
            "unreachable_code": (
                "Unreachable code detected",
                f"{smell.description}. Code after a terminating statement (return/raise/break/continue) will never execute and can confuse future readers.",
                "Remove unreachable statements or refactor control flow so that all remaining code paths are actually executable."
            ),

            # NEW: feature_envy
            "feature_envy": (
                f"Method '{smell.node_name}' may exhibit feature envy",
                f"{smell.description}. When a method mostly uses another object's data instead of its own, it suggests the behavior may belong on that other object.",
                "Consider moving this behavior closer to the data it uses (e.g., onto the other class) or introducing a dedicated service/utility to own this logic."
            ),

            # NEW: many_local_variables
            "many_local_variables": (
                f"Function '{smell.node_name}' uses many local variables",
                f"{smell.description}. A large number of local variables often indicates that the function is doing too much and is hard to reason about.",
                "Split the function into smaller, focused helpers, each handling a clear subtask. This reduces cognitive load and makes testing easier."
            ),
        }

        return templates.get(
            smell.type,
            (
                f"Issue: {smell.type} detected",
                f"A '{smell.type}' code smell was detected: {smell.description}. This indicates a potential area for improvement in code quality or design.",
                "Review the code for opportunities to refactor according to common coding standards and SOLID principles."
            ),
        )
