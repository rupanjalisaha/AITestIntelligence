import re

from app.ai.llm_client import LLMClient
from app.ai.prompts import API_TEST_GENERATION_PROMPT
from app.models import (
    ApiTestCase,
    ApiTestGenerationResult
)


class ApiTestGenerator:

    def __init__(self):
        self.llm_client = LLMClient()

    def generate_api_tests(
        self,
        requirement: str,
        base_url: str
    ) -> ApiTestGenerationResult:

        prompt = API_TEST_GENERATION_PROMPT.format(
            requirement=requirement,
            base_url=base_url
        )

        result = self.llm_client.generate_json(
            prompt
        )

        try:
            test_cases_data = result.get(
                "test_cases",
                []
            )

            normalized_test_cases = (
                self._normalize_test_cases(
                    test_cases_data
                )
            )

            test_cases = [
                ApiTestCase.model_validate(
                    test_case
                )
                for test_case in normalized_test_cases
            ]

            if not test_cases:
                raise RuntimeError(
                    "LLM returned no API test cases."
                )

            validated_test_cases = (
                self._validate_and_filter_test_cases(
                    test_cases=test_cases,
                    requirement=requirement
                )
            )

            if not validated_test_cases:
                raise RuntimeError(
                    "No meaningful API test cases remained "
                    "after validation."
                )

            print(
                f"API test cases returned by LLM: "
                f"{len(test_cases)}"
            )

            print(
                f"API test cases after validation: "
                f"{len(validated_test_cases)}"
            )

            return ApiTestGenerationResult(
                test_cases=validated_test_cases
            )

        except Exception as exc:
            raise RuntimeError(
                f"Generated API test cases failed validation: {exc}"
            )

    @staticmethod
    def _normalize_test_cases(
        test_cases_data: list[dict]
    ) -> list[dict]:
        """
        Normalize common LLM output variations before Pydantic validation.

        Query parameter values are converted to strings because URL query
        parameters are represented as strings by the HTTP layer.
        """

        normalized = []

        for test_case in test_cases_data:

            test_case = dict(
                test_case
            )

            query_params = (
                test_case.get(
                    "query_params",
                    {}
                )
            )

            if isinstance(
                query_params,
                dict
            ):

                test_case["query_params"] = {
                    str(key): str(value)
                    for key, value in query_params.items()
                }

            normalized.append(
                test_case
            )

        return normalized

    def _validate_and_filter_test_cases(
        self,
        test_cases: list[ApiTestCase],
        requirement: str
    ) -> list[ApiTestCase]:
        """
        Remove duplicate or clearly unsupported API test cases.

        The LLM is treated as a candidate generator. This method applies
        deterministic validation before the test cases are returned.
        """

        filtered_test_cases = []

        seen_requests = set()

        requirement_lower = requirement.lower()

        for test_case in test_cases:

            # ------------------------------------------------------
            # 1. Validate query parameters against the requirement
            # ------------------------------------------------------

            unsupported_query_params = []

            for parameter_name in (
                test_case.query_params.keys()
            ):

                if not self._term_supported_by_requirement(
                    parameter_name,
                    requirement_lower
                ):
                    unsupported_query_params.append(
                        parameter_name
                    )

            if unsupported_query_params:

                print(
                    "Rejecting "
                    f"{test_case.id}: unsupported query "
                    f"parameters {unsupported_query_params}"
                )

                continue

            # ------------------------------------------------------
            # 2. Build a normalized request signature
            # ------------------------------------------------------

            signature = self._build_request_signature(
                test_case
            )

            # ------------------------------------------------------
            # 3. Remove duplicate requests
            # ------------------------------------------------------

            if signature in seen_requests:

                print(
                    f"Rejecting {test_case.id}: "
                    "duplicate API request."
                )

                continue

            seen_requests.add(
                signature
            )

            filtered_test_cases.append(
                test_case
            )

        return filtered_test_cases

    @staticmethod
    def _build_request_signature(
        test_case: ApiTestCase
    ) -> tuple:
        """
        Create a deterministic signature representing the actual request.
        """

        headers = tuple(
            sorted(
                (
                    str(key).lower(),
                    str(value)
                )
                for key, value in test_case.headers.items()
            )
        )

        query_params = tuple(
            sorted(
                (
                    str(key).lower(),
                    str(value)
                )
                for key, value in test_case.query_params.items()
            )
        )

        body = repr(
            test_case.body
        )

        return (
            test_case.method.upper(),
            test_case.endpoint,
            headers,
            query_params,
            body
        )

    @staticmethod
    def _term_supported_by_requirement(
        term: str,
        requirement: str
    ) -> bool:
        """
        Check whether a generated query parameter is explicitly mentioned
        by the requirement.

        Word-boundary matching prevents partial matches.
        Example:
            "id" should not match "identity".
        """

        normalized_term = term.strip().lower()

        if not normalized_term:
            return False

        pattern = (
            r"(?<![a-zA-Z0-9_])"
            + re.escape(normalized_term)
            + r"(?![a-zA-Z0-9_])"
        )

        return (
            re.search(
                pattern,
                requirement
            )
            is not None
        )