import copy
import json
import re

from app.ai.llm_client import LLMClient
from app.ai.prompts import (
    SELENIUM_AUTOMATION_PROMPT,
    AUTOMATION_REPAIR_PROMPT,
)
from app.models import (
    AutomationStepGenerationResult,
    AutomationGenerationResponse,
    TestCase,
    PageElement,
)
from app.services.selenium_code_generator import SeleniumCodeGenerator
from app.services.ui_test_validator import UITestValidator


class AutomationGenerator:

    MAX_REPAIR_ATTEMPTS = 1

    def __init__(self):
        self.llm_client = LLMClient()
        self.selenium_code_generator = SeleniumCodeGenerator()
        self.validator = UITestValidator()

    def generate_automation_steps(
        self,
        test_case: TestCase,
        application_url: str,
        page_elements: list[PageElement],
    ) -> AutomationStepGenerationResult:

        test_case_json = test_case.model_dump_json(
            indent=2
        )

        test_data = test_case.test_data or {}

        test_data_json = str(
            test_data
        )

        page_elements_json = "\n".join(
            element.model_dump_json()
            for element in page_elements
        )

        # ---------------------------------------------------------
        # FIRST GENERATION
        # ---------------------------------------------------------

        print(
            f"\n========== GENERATING AUTOMATION FOR "
            f"{test_case.id} =========="
        )

        prompt = SELENIUM_AUTOMATION_PROMPT.format(
            application_url=application_url,
            test_case=test_case_json,
            test_data=test_data_json,
            page_elements=page_elements_json,
        )

        result = self.llm_client.generate_json(
            prompt
        )

        # ---------------------------------------------------------
        # NORMALIZE COMMON AI OUTPUT MISTAKES
        # ---------------------------------------------------------

        result = self._normalize_automation_result(
            result=result,
            test_case=test_case,
            application_url=application_url,
        )

        (
            validated_result,
            validation_errors,
        ) = self._validate_generated_automation(
            test_case=test_case,
            result=result,
            page_elements=page_elements,
        )

        # ---------------------------------------------------------
        # FIRST GENERATION PASSED
        # ---------------------------------------------------------

        if not validation_errors:

            print(
                f"Automation generation validated successfully "
                f"for {test_case.id}."
            )

            return validated_result

        # ---------------------------------------------------------
        # FIRST GENERATION FAILED
        # ---------------------------------------------------------

        print(
            f"\nAutomation generation failed validation "
            f"for {test_case.id}."
        )

        print(
            "Validation errors:"
        )

        for error in validation_errors:
            print(
                f"- {error}"
            )

        if self.MAX_REPAIR_ATTEMPTS <= 0:
            raise RuntimeError(
                f"Generated automation for {test_case.id} "
                f"failed validation:\n"
                + "\n".join(
                    f"- {error}"
                    for error in validation_errors
                )
            )

        # ---------------------------------------------------------
        # AI REPAIR
        # ---------------------------------------------------------

        print(
            "\n========== AUTOMATION REPAIR "
            "ATTEMPT 1/1 =========="
        )

        return self._repair_automation_steps(
            test_case=test_case,
            application_url=application_url,
            page_elements=page_elements,
            test_data_json=test_data_json,
            original_result=result,
            validation_errors=validation_errors,
        )

    def _normalize_automation_result(
        self,
        result: dict,
        test_case: TestCase,
        application_url: str,
    ) -> dict:

        normalized_result = copy.deepcopy(
            result
        )

        steps = normalized_result.get(
            "steps",
            []
        )

        if not isinstance(steps, list):
            return normalized_result

        for step in steps:

            if not isinstance(step, dict):
                continue

            action = str(
                step.get("action", "")
            ).strip().lower()

            # -----------------------------------------------------
            # Normalize malformed assert_text output.
            #
            # Some local models may use:
            # "expected_text": "..."
            #
            # Our schema requires:
            # "value": "..."
            # -----------------------------------------------------

            if action == "assert_text":

                if (
                    step.get("value") is None
                    and step.get("expected_text") is not None
                ):
                    step["value"] = step.get(
                        "expected_text"
                    )

                step.pop(
                    "expected_text",
                    None
                )

            # -----------------------------------------------------
            # Normalize malformed assert_url_contains output.
            #
            # Some models may use:
            # "expected_url": "..."
            #
            # or:
            # "locator": "By.URL: ..."
            #
            # URL assertions do NOT use page-element locators.
            # -----------------------------------------------------

            if action == "assert_url_contains":

                if (
                    step.get("value") is None
                    and step.get("expected_url") is not None
                ):
                    step["value"] = self._extract_url_fragment(
                        step.get("expected_url")
                    )

                step.pop(
                    "expected_url",
                    None
                )

                locator = step.get(
                    "locator"
                )

                if (
                    isinstance(locator, str)
                    and locator.strip().lower().startswith(
                        "by.url:"
                    )
                ):

                    url_from_locator = (
                        locator.split(
                            ":",
                            1
                        )[1].strip()
                    )

                    if not step.get("value"):
                        inferred_fragment = (
                            self._infer_url_fragment_from_test_case(
                                test_case=test_case,
                                url=url_from_locator,
                                application_url=application_url,
                            )
                        )

                        if inferred_fragment:
                            step["value"] = (
                                inferred_fragment
                            )

                    # assert_url_contains must never have
                    # a page-element locator.
                    step["locator"] = None

                elif locator:

                    # Any locator on assert_url_contains is invalid.
                    # Remove it. Validation will ensure that the
                    # remaining value is valid.
                    step["locator"] = None

        return normalized_result

    @staticmethod
    def _extract_url_fragment(
        url: str | None,
    ) -> str | None:

        if not url:
            return None

        url = str(
            url
        ).strip()

        if not url:
            return None

        # Remove query string and fragment.
        clean_url = url.split(
            "?",
            1
        )[0].split(
            "#",
            1
        )[0]

        # Extract the path.
        match = re.search(
            r"https?://[^/]+(/.*)?$",
            clean_url,
            re.IGNORECASE,
        )

        if not match:
            return None

        path = match.group(1)

        if not path or path == "/":
            return None

        parts = [
            part
            for part in path.strip(
                "/"
            ).split(
                "/"
            )
            if part
        ]

        if not parts:
            return None

        return parts[-1].replace(
            ".html",
            ""
        )

    @staticmethod
    def _infer_url_fragment_from_test_case(
        test_case: TestCase,
        url: str | None,
        application_url: str,
    ) -> str | None:

        expected_result = (
            test_case.expected_result or ""
        ).lower()

        # Explicitly supported known outcome:
        # "reaches the inventory page"
        if "inventory page" in expected_result:
            return "inventory"

        # Check whether the malformed URL itself already contains
        # a useful non-root path.
        url_fragment = (
            AutomationGenerator._extract_url_fragment(
                url
            )
        )

        if url_fragment:
            return url_fragment

        # No safe URL fragment could be inferred.
        return None

    def _validate_generated_automation(
        self,
        test_case: TestCase,
        result: dict,
        page_elements: list[PageElement],
    ) -> tuple[
        AutomationStepGenerationResult | None,
        list[str],
    ]:

        errors = []

        # ---------------------------------------------------------
        # SCHEMA VALIDATION
        # ---------------------------------------------------------

        try:

            validated_result = (
                AutomationStepGenerationResult.model_validate(
                    result
                )
            )

        except Exception as exc:

            return (
                None,
                [
                    f"Schema validation failed: {exc}"
                ],
            )

        # ---------------------------------------------------------
        # SEMANTIC VALIDATION
        # ---------------------------------------------------------

        semantic_errors = (
            self.validator.validate_automation_steps(
                result=validated_result,
                page_elements=page_elements,
            )
        )

        errors.extend(
            semantic_errors
        )

        # ---------------------------------------------------------
        # TEST CASE / DATA ALIGNMENT
        # ---------------------------------------------------------

        alignment_errors = (
            self.validator.validate_automation_alignment(
                test_case=test_case,
                automation=validated_result,
            )
        )

        errors.extend(
            alignment_errors
        )

        if errors:

            return (
                validated_result,
                errors,
            )

        return (
            validated_result,
            [],
        )

    def _repair_automation_steps(
        self,
        test_case: TestCase,
        application_url: str,
        page_elements: list[PageElement],
        test_data_json: str,
        original_result: dict,
        validation_errors: list[str],
    ) -> AutomationStepGenerationResult:

        test_case_json = test_case.model_dump_json(
            indent=2
        )

        page_elements_json = "\n".join(
            element.model_dump_json()
            for element in page_elements
        )

        generated_automation_json = json.dumps(
            original_result,
            indent=2,
            ensure_ascii=False,
        )

        validation_errors_text = "\n".join(
            f"- {error}"
            for error in validation_errors
        )

        repair_prompt = AUTOMATION_REPAIR_PROMPT.format(
            application_url=application_url,
            page_elements=page_elements_json,
            test_case=test_case_json,
            test_data=test_data_json,
            generated_automation=generated_automation_json,
            validation_errors=validation_errors_text,
        )

        print(
            "Sending validation errors to AI for automation repair..."
        )

        repaired_result = self.llm_client.generate_json(
            repair_prompt
        )

        # ---------------------------------------------------------
        # NORMALIZE REPAIRED OUTPUT
        # ---------------------------------------------------------

        repaired_result = self._normalize_automation_result(
            result=repaired_result,
            test_case=test_case,
            application_url=application_url,
        )

        # ---------------------------------------------------------
        # VALIDATE REPAIRED OUTPUT
        # ---------------------------------------------------------

        (
            validated_repaired_result,
            repaired_validation_errors,
        ) = self._validate_generated_automation(
            test_case=test_case,
            result=repaired_result,
            page_elements=page_elements,
        )

        if repaired_validation_errors:

            print(
                "\n========== AUTOMATION REPAIR FAILED =========="
            )

            print(
                "Remaining validation errors:"
            )

            for error in repaired_validation_errors:
                print(
                    f"- {error}"
                )

            raise RuntimeError(
                f"Automation repair failed for {test_case.id}:\n"
                + "\n".join(
                    f"- {error}"
                    for error in repaired_validation_errors
                )
            )

        print(
            "\n========== AUTOMATION REPAIR SUCCESSFUL =========="
        )

        print(
            f"Repaired automation for {test_case.id} "
            f"passed validation."
        )

        return validated_repaired_result

    def generate_selenium_code(
        self,
        test_case: TestCase,
        application_url: str,
        page_elements: list[PageElement],
    ) -> AutomationGenerationResponse:

        automation_steps = self.generate_automation_steps(
            test_case=test_case,
            application_url=application_url,
            page_elements=page_elements,
        )

        code = self.selenium_code_generator.generate(
            test_case_id=test_case.id,
            application_url=application_url,
            steps=automation_steps.steps,
        )

        try:
            compile(
                code,
                f"test_{test_case.id}.py",
                "exec",
            )
        except SyntaxError as exc:
            raise RuntimeError(
                f"Generated Selenium code failed syntax validation: "
                f"{exc}"
            ) from exc

        return AutomationGenerationResponse(
            test_case_id=test_case.id,
            framework="selenium",
            language="python",
            code=code,
        )