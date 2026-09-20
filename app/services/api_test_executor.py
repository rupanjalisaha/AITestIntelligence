import json
import time
from urllib.parse import urljoin

import requests

from app.models import (
    ApiTestCase,
    ApiTestExecutionResponse
)


class ApiTestExecutor:

    REQUEST_TIMEOUT_SECONDS = 30
    MAX_RESPONSE_BODY_LENGTH = 5000

    def execute(
        self,
        base_url: str,
        test_case: ApiTestCase
    ) -> ApiTestExecutionResponse:

        url = self._build_url(
            base_url=base_url,
            endpoint=test_case.endpoint
        )

        validation_errors = []

        actual_status = None
        response_time_ms = None

        response_body = ""
        response_headers = {}

        status_validation = False
        body_validation = False
        header_validation = False

        try:

            print(
                "\n========== API TEST EXECUTION STARTED =========="
            )

            print(
                f"Test Case: {test_case.id}"
            )

            print(
                f"Method: {test_case.method.upper()}"
            )

            print(
                f"URL: {url}"
            )

            start_time = time.time()

            response = requests.request(
                method=test_case.method.upper(),
                url=url,
                headers=test_case.headers,
                params=test_case.query_params,
                json=test_case.body,
                timeout=self.REQUEST_TIMEOUT_SECONDS
            )

            response_time_ms = round(
                (time.time() - start_time) * 1000,
                2
            )

            actual_status = response.status_code

            response_body = response.text[
                :self.MAX_RESPONSE_BODY_LENGTH
            ]

            response_headers = {
                key: value
                for key, value in response.headers.items()
            }

            print(
                f"Status: {actual_status}"
            )

            print(
                f"Response time: {response_time_ms} ms"
            )

            # --------------------------------------------------
            # STATUS VALIDATION
            # --------------------------------------------------

            status_validation = (
                actual_status
                == test_case.expected_status
            )

            if not status_validation:

                validation_errors.append(
                    "Expected HTTP status "
                    f"{test_case.expected_status}, "
                    f"but received {actual_status}."
                )

            # --------------------------------------------------
            # BODY CONTAINS VALIDATION
            # --------------------------------------------------

            body_validation = True

            for expected_value in (
                test_case.expected_body_contains
            ):

                if expected_value not in response.text:

                    body_validation = False

                    validation_errors.append(
                        "Expected response body to contain "
                        f"'{expected_value}'."
                    )

            # --------------------------------------------------
            # JSON VALIDATION
            # --------------------------------------------------

            json_validation = self._validate_json_response(
                response_text=response.text,
                test_case=test_case,
                validation_errors=validation_errors
            )

            if not json_validation:
                body_validation = False

            # --------------------------------------------------
            # HEADER VALIDATION
            # --------------------------------------------------

            header_validation = True

            for (
                expected_name,
                expected_value
            ) in test_case.expected_headers.items():

                actual_value = response.headers.get(
                    expected_name
                )

                if actual_value is None:

                    header_validation = False

                    validation_errors.append(
                        "Expected response header "
                        f"'{expected_name}' to exist."
                    )

                    continue

                if (
                    expected_value.lower()
                    not in actual_value.lower()
                ):

                    header_validation = False

                    validation_errors.append(
                        "Expected response header "
                        f"'{expected_name}' to contain "
                        f"'{expected_value}', "
                        f"but received '{actual_value}'."
                    )

            # --------------------------------------------------
            # FINAL RESULT
            # --------------------------------------------------

            passed = (
                status_validation
                and body_validation
                and header_validation
            )

            status = (
                "PASSED"
                if passed
                else "FAILED"
            )

            print(
                f"API TEST RESULT: {status}"
            )

            print(
                "================================================\n"
            )

            return ApiTestExecutionResponse(
                test_case_id=test_case.id,
                title=test_case.title,
                method=test_case.method.upper(),
                url=url,
                status=status,
                passed=passed,
                expected_status=test_case.expected_status,
                actual_status=actual_status,
                response_time_ms=response_time_ms,
                status_validation=status_validation,
                body_validation=body_validation,
                header_validation=header_validation,
                response_body=response_body,
                response_headers=response_headers,
                validation_errors=validation_errors
            )

        except requests.exceptions.Timeout:

            validation_errors.append(
                "API request timed out after "
                f"{self.REQUEST_TIMEOUT_SECONDS} seconds."
            )

            return ApiTestExecutionResponse(
                test_case_id=test_case.id,
                title=test_case.title,
                method=test_case.method.upper(),
                url=url,
                status="FAILED",
                passed=False,
                expected_status=test_case.expected_status,
                actual_status=None,
                response_time_ms=response_time_ms,
                status_validation=False,
                body_validation=False,
                header_validation=False,
                response_body="",
                response_headers={},
                validation_errors=validation_errors
            )

        except requests.exceptions.RequestException as exc:

            validation_errors.append(
                f"HTTP request failed: {str(exc)}"
            )

            return ApiTestExecutionResponse(
                test_case_id=test_case.id,
                title=test_case.title,
                method=test_case.method.upper(),
                url=url,
                status="FAILED",
                passed=False,
                expected_status=test_case.expected_status,
                actual_status=None,
                response_time_ms=response_time_ms,
                status_validation=False,
                body_validation=False,
                header_validation=False,
                response_body="",
                response_headers={},
                validation_errors=validation_errors
            )

    @staticmethod
    def _build_url(
        base_url: str,
        endpoint: str
    ) -> str:

        base_url = base_url.rstrip("/") + "/"
        endpoint = endpoint.lstrip("/")

        return urljoin(
            base_url,
            endpoint
        )

    @staticmethod
    def _validate_json_response(
        response_text: str,
        test_case: ApiTestCase,
        validation_errors: list[str]
    ) -> bool:
        """
        Validate structured JSON assertions.

        expected_json:
            Exact values for specified JSON paths.

        Example:
            {
                "page": 1,
                "total_pages": 2
            }

        expected_json_types:
            Expected JSON types for specified JSON paths.

        Example:
            {
                "page": "integer",
                "data": "array"
            }
        """

        has_json_assertions = bool(
            test_case.expected_json
            or test_case.expected_json_types
        )

        if not has_json_assertions:
            return True

        try:

            response_json = json.loads(
                response_text
            )

        except json.JSONDecodeError:

            validation_errors.append(
                "Response body is not valid JSON, "
                "but structured JSON validation was requested."
            )

            return False

        validation_passed = True

        # ------------------------------------------------------
        # EXPECTED JSON VALUES
        # ------------------------------------------------------

        for (
            path,
            expected_value
        ) in test_case.expected_json.items():

            exists, actual_value = (
                ApiTestExecutor._get_json_path(
                    response_json,
                    path
                )
            )

            if not exists:

                validation_passed = False

                validation_errors.append(
                    f"Expected JSON field '{path}' "
                    "to exist."
                )

                continue

            if actual_value != expected_value:

                validation_passed = False

                validation_errors.append(
                    f"Expected JSON field '{path}' "
                    f"to equal {expected_value!r}, "
                    f"but received {actual_value!r}."
                )

        # ------------------------------------------------------
        # EXPECTED JSON TYPES
        # ------------------------------------------------------

        valid_types = {
            "string",
            "integer",
            "number",
            "boolean",
            "object",
            "array",
            "null"
        }

        for (
            path,
            expected_type
        ) in test_case.expected_json_types.items():

            exists, actual_value = (
                ApiTestExecutor._get_json_path(
                    response_json,
                    path
                )
            )

            if not exists:

                validation_passed = False

                validation_errors.append(
                    f"Expected JSON field '{path}' "
                    "to exist for type validation."
                )

                continue

            normalized_type = (
                expected_type.strip().lower()
            )

            if normalized_type not in valid_types:

                validation_passed = False

                validation_errors.append(
                    f"Unsupported expected JSON type "
                    f"'{expected_type}' for field '{path}'. "
                    f"Supported types: "
                    f"{sorted(valid_types)}."
                )

                continue

            if not ApiTestExecutor._matches_json_type(
                actual_value,
                normalized_type
            ):

                validation_passed = False

                actual_type = (
                    ApiTestExecutor._get_json_type_name(
                        actual_value
                    )
                )

                validation_errors.append(
                    f"Expected JSON field '{path}' "
                    f"to have type '{normalized_type}', "
                    f"but received type '{actual_type}'."
                )

        return validation_passed

    @staticmethod
    def _get_json_path(
        data,
        path: str
    ) -> tuple[bool, object]:
        """
        Resolve a simple dot-separated JSON path.

        Examples:
            page
            total_pages
            data.0.id
        """

        if not path:
            return False, None

        current = data

        for part in path.split("."):

            if isinstance(
                current,
                dict
            ):

                if part not in current:
                    return False, None

                current = current[part]

                continue

            if isinstance(
                current,
                list
            ):

                try:
                    index = int(part)

                except ValueError:
                    return False, None

                if (
                    index < 0
                    or index >= len(current)
                ):
                    return False, None

                current = current[index]

                continue

            return False, None

        return True, current

    @staticmethod
    def _matches_json_type(
        value,
        expected_type: str
    ) -> bool:

        if expected_type == "null":
            return value is None

        if expected_type == "boolean":
            return isinstance(
                value,
                bool
            )

        if expected_type == "integer":
            return (
                isinstance(value, int)
                and not isinstance(value, bool)
            )

        if expected_type == "number":
            return (
                isinstance(value, (int, float))
                and not isinstance(value, bool)
            )

        if expected_type == "string":
            return isinstance(
                value,
                str
            )

        if expected_type == "object":
            return isinstance(
                value,
                dict
            )

        if expected_type == "array":
            return isinstance(
                value,
                list
            )

        return False

    @staticmethod
    def _get_json_type_name(
        value
    ) -> str:

        if value is None:
            return "null"

        if isinstance(value, bool):
            return "boolean"

        if isinstance(value, int):
            return "integer"

        if isinstance(value, float):
            return "number"

        if isinstance(value, str):
            return "string"

        if isinstance(value, dict):
            return "object"

        if isinstance(value, list):
            return "array"

        return type(value).__name__