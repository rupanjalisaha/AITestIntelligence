from app.ai.llm_client import LLMClient
from app.ai.prompts import TEST_GENERATION_PROMPT
from app.models import TestCaseGenerationResult


class TestGenerator:

    def __init__(self):
        self.llm_client = LLMClient()

    def generate_test_cases(
        self,
        requirement: str
    ) -> TestCaseGenerationResult:

        prompt = TEST_GENERATION_PROMPT.format(
            requirement=requirement
        )

        result = self.llm_client.generate_json(
            prompt
        )

        # ---------------------------------------------------------
        # Normalize optional LLM fields before Pydantic validation.
        # Local LLMs may return null even when the schema expects
        # an empty list/dictionary.
        # ---------------------------------------------------------

        test_cases = result.get(
            "test_cases",
            []
        )

        for test_case in test_cases:

            if test_case.get("preconditions") is None:
                test_case["preconditions"] = []

            if test_case.get("steps") is None:
                test_case["steps"] = []

            if test_case.get("test_data") is None:
                test_case["test_data"] = {}

        result["test_cases"] = test_cases

        # ---------------------------------------------------------
        # Validate normalized result.
        # ---------------------------------------------------------

        try:

            validated_result = (
                TestCaseGenerationResult.model_validate(
                    result
                )
            )

            return validated_result

        except Exception as exc:

            raise RuntimeError(
                f"Generated test cases failed validation: {exc}"
            )