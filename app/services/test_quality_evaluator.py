import re

from app.ai.llm_client import LLMClient
from app.models import TestCaseGenerationResult


QUALITY_EVALUATION_PROMPT = """
You are a senior QA architect reviewing AI-generated test cases.

Software requirement:
{requirement}

Generated test cases:
{test_cases}

Evaluate the generated test suite for:

1. Requirement relevance
2. Functional coverage
3. Negative coverage
4. Boundary coverage
5. Validation coverage
6. Error-handling coverage
7. Security coverage
8. Duplicate or overlapping scenarios
9. Test executability
10. Missing requirement information

CRITICAL RULE FOR BOUNDARY TESTS:

A boundary test is valid only when the requirement explicitly defines
a boundary, limit, range, threshold, minimum, maximum, length, quantity,
or similar constraint.

Examples:

Requirement:
"Password must contain 8 to 20 characters."

Valid boundary tests:
- 7 characters
- 8 characters
- 20 characters
- 21 characters

Requirement:
"User can purchase between 1 and 10 items."

Valid boundary tests:
- 0 items
- 1 item
- 10 items
- 11 items

But if the requirement only says:

"The user can log in using email and password."

DO NOT assume:
- maximum email length
- minimum password length
- maximum password length
- email length boundaries
- password length boundaries

If a generated test claims to test a boundary that is NOT specified
in the requirement, classify it as a hallucinated boundary scenario.

For hallucinated boundary scenarios:

- Include the test case in missing_scenarios or coverage_gaps.
- Mention that the boundary is not defined by the requirement.
- Recommend defining the missing constraint.
- Do not treat the hallucinated boundary as valid coverage.

IMPORTANT:

- Do not invent requirements.
- Do not invent numeric limits.
- Empty input is not automatically a boundary test.
- Identify semantically duplicate or overlapping test cases.
- Scores must be integers from 0 to 100.

Return ONLY valid JSON.

Use exactly this structure:

{{
  "overall_score": 0,
  "coverage_score": 0,
  "quality_score": 0,
  "duplicate_count": 0,
  "missing_scenarios": [],
  "coverage_gaps": [],
  "recommendations": [],
  "summary": ""
}}

Do not return markdown.
Do not return ```json.
Do not include explanations outside the JSON.
"""


class TestQualityEvaluator:
    """
    Evaluates the quality and coverage of AI-generated test cases.
    """

    def __init__(self):
        self.llm_client = LLMClient()

    def _detect_hallucinated_boundaries(
        self,
        requirement: str,
        test_result: TestCaseGenerationResult
    ) -> list[str]:

        boundary_keywords = [
            "boundary",
            "maximum",
            "minimum",
            "max",
            "min",
            "limit",
            "length",
            "range",
            "threshold",
            "character",
            "characters"
        ]

        constraint_patterns = [
            r"\b\d+\s*(to|-)\s*\d+\b",
            r"\bminimum\b",
            r"\bmaximum\b",
            r"\bmax(?:imum)?\s*(?:of)?\s*\d+",
            r"\bmin(?:imum)?\s*(?:of)?\s*\d+",
            r"\b\d+\s*(?:characters?|items?|digits?|days?|months?|years?)\b",
            r"\bgreater than\b",
            r"\bless than\b",
            r"\bat least\b",
            r"\bat most\b",
            r"\bno more than\b",
            r"\bno less than\b"
        ]

        requirement_lower = requirement.lower()

        has_explicit_constraint = any(
            re.search(pattern, requirement_lower)
            for pattern in constraint_patterns
        )

        if has_explicit_constraint:
            return []

        hallucinated_boundaries = []

        for test_case in test_result.test_cases:

            searchable_text = " ".join([
                test_case.title,
                test_case.category,
                *test_case.steps,
                test_case.expected_result
            ]).lower()

            contains_boundary_language = any(
                keyword in searchable_text
                for keyword in boundary_keywords
            )

            if (
                test_case.category.lower() == "boundary"
                or contains_boundary_language
            ):
                hallucinated_boundaries.append(
                    f"{test_case.id}: '{test_case.title}' "
                    f"claims boundary coverage, but the requirement "
                    f"does not define an explicit boundary or limit."
                )

        return hallucinated_boundaries

    def evaluate(
        self,
        requirement: str,
        test_result: TestCaseGenerationResult
    ) -> dict:

        test_cases_json = test_result.model_dump_json(
            indent=2
        )

        prompt = QUALITY_EVALUATION_PROMPT.format(
            requirement=requirement,
            test_cases=test_cases_json
        )

        ai_report = self.llm_client.generate_json(prompt)

        hallucinated_boundaries = (
            self._detect_hallucinated_boundaries(
                requirement,
                test_result
            )
        )

        if hallucinated_boundaries:

            ai_report["coverage_gaps"].extend(
                hallucinated_boundaries
            )

            ai_report["recommendations"].append(
                "Define explicit boundary or validation limits "
                "in the requirement before creating boundary tests."
            )

            ai_report["quality_score"] = max(
                0,
                ai_report["quality_score"] - 10
            )

            ai_report["overall_score"] = max(
                0,
                ai_report["overall_score"] - 10
            )

            ai_report["summary"] = (
                ai_report.get("summary", "")
                + " The suite also contains one or more "
                  "boundary scenarios that are not supported "
                  "by explicit requirements."
            )

        return ai_report