from app.ai.llm_client import LLMClient


class TestResultAnalyzer:

    def __init__(self):
        self.llm_client = LLMClient()

    def analyze(
        self,
        execution_result: dict
    ) -> dict:

        execution_status = execution_result["status"]

        # PASSED tests do not need AI analysis.
        if execution_status == "PASSED":
            return {
                "status": "PASSED",
                "failure_type": "NONE",
                "root_cause": "No failure detected.",
                "evidence": [
                    "Automated test executed successfully.",
                    "Pytest returned exit code 0."
                ],
                "recommendation": "No action required."
            }

        prompt = f"""
You are a senior QA automation engineer analyzing a browser automation test failure.

The pytest execution result below is authoritative.

Execution Result:
{execution_result}

The test execution status is FAILED.

Your task is to analyze the failure and classify its most likely cause.

Allowed failure types:

- APPLICATION_BUG
- AUTOMATION_DEFECT
- TEST_DATA_ISSUE
- ENVIRONMENT_ISSUE
- INFRASTRUCTURE_ISSUE
- FLAKY_TEST

IMPORTANT RULES:

1. The test has FAILED.
2. Your response status MUST be "FAILED".
3. failure_type MUST be one of the allowed failure types.
4. NEVER return "NONE" for a failed test.
5. Do not invent evidence.
6. Base the analysis only on the supplied execution result.
7. Identify the most likely cause of the failure.
8. Keep the root cause concise.
9. Evidence must refer to information actually present in the execution result.
10. Recommendation must describe a relevant next action.

Failure type guidance:

APPLICATION_BUG:
Use when the application appears to behave incorrectly compared with the expected behavior.

AUTOMATION_DEFECT:
Use when the generated automation appears incorrect, such as an invalid locator, incorrect action sequence, incorrect assertion, or waiting for the wrong UI condition.

TEST_DATA_ISSUE:
Use when the supplied test data is invalid, missing, incorrect, or inconsistent with the scenario being tested.

ENVIRONMENT_ISSUE:
Use when the application environment appears unavailable or unhealthy.

INFRASTRUCTURE_ISSUE:
Use when browser, driver, network, or infrastructure problems appear to be responsible.

FLAKY_TEST:
Use only when the available evidence suggests intermittent or non-deterministic behavior.

Return ONLY valid JSON.

Return exactly this structure:

{{
    "status": "FAILED",
    "failure_type": "AUTOMATION_DEFECT",
    "root_cause": "Describe the most likely root cause.",
    "evidence": [
        "Actual evidence from the execution result."
    ],
    "recommendation": "Recommended next action."
}}
"""

        result = self.llm_client.generate_json(
            prompt
        )

        # Pytest determines the authoritative execution status.
        result["status"] = "FAILED"

        # A failed test can never have NONE as its failure type.
        allowed_failure_types = {
            "APPLICATION_BUG",
            "AUTOMATION_DEFECT",
            "TEST_DATA_ISSUE",
            "ENVIRONMENT_ISSUE",
            "INFRASTRUCTURE_ISSUE",
            "FLAKY_TEST"
        }

        if result.get("failure_type") not in allowed_failure_types:
            result["failure_type"] = "AUTOMATION_DEFECT"

        if not result.get("root_cause"):
            result["root_cause"] = (
                "The automated test failed during execution. "
                "Further investigation is required."
            )

        if not result.get("evidence"):
            result["evidence"] = [
                "Pytest reported a failed test execution."
            ]

        if not result.get("recommendation"):
            result["recommendation"] = (
                "Review the generated automation and "
                "execution evidence."
            )

        return result