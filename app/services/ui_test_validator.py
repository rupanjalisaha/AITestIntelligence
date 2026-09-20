from app.models import (
AutomationStepGenerationResult,
PageElement,
TestCase,
)

class UITestValidator:


    SUPPORTED_ACTIONS = {
        "enter_text",
        "click",
        "select",
        "assert_text",
        "assert_url_contains",
        "assert_element_visible",
    }

    SUPPORTED_LOCATOR_STRATEGIES = {
        "By.ID",
        "By.NAME",
        "By.XPATH",
        "By.CSS_SELECTOR",
        "By.CLASS_NAME",
        "By.TAG_NAME",
        "By.LINK_TEXT",
        "By.PARTIAL_LINK_TEXT",
    }

    CATEGORY_VALUES = {
        "functional",
        "negative",
        "validation",
        "boundary",
        "security",
        "error handling",
        "integration",
    }

    PRIORITY_VALUES = {
        "high",
        "medium",
        "low",
    }

    def validate_test_case(
        self,
        test_case: TestCase,
    ) -> list[str]:

        errors = []

        if not test_case.id.strip():
            errors.append(
                "Test case ID is empty."
            )

        if not test_case.title.strip():
            errors.append(
                f"{test_case.id}: Test case title is empty."
            )

        if not test_case.category.strip():
            errors.append(
                f"{test_case.id}: Test case category is empty."
            )

        elif (
            test_case.category.strip().lower()
            not in self.CATEGORY_VALUES
        ):
            errors.append(
                f"{test_case.id}: Unsupported test category "
                f"'{test_case.category}'."
            )

        if (
            test_case.priority.strip().lower()
            not in self.PRIORITY_VALUES
        ):
            errors.append(
                f"{test_case.id}: Invalid priority "
                f"'{test_case.priority}'."
            )

        if not test_case.steps:
            errors.append(
                f"{test_case.id}: Test case contains no steps."
            )

        else:

            for index, step in enumerate(
                test_case.steps,
                start=1
            ):

                if not step.strip():
                    errors.append(
                        f"{test_case.id}: Step {index} is empty."
                    )

        if not test_case.expected_result.strip():
            errors.append(
                f"{test_case.id}: Expected result is empty."
            )

        return errors

    def validate_test_suite(
        self,
        test_cases: list[TestCase],
    ) -> list[str]:

        errors = []

        if not test_cases:
            return [
                "No test cases were generated."
            ]

        ids = set()
        titles = set()

        for test_case in test_cases:

            errors.extend(
                self.validate_test_case(
                    test_case
                )
            )

            normalized_id = (
                test_case.id.strip().lower()
            )

            if normalized_id in ids:
                errors.append(
                    f"Duplicate test case ID: "
                    f"{test_case.id}"
                )
            else:
                ids.add(
                    normalized_id
                )

            normalized_title = (
                test_case.title.strip().lower()
            )

            if normalized_title in titles:
                errors.append(
                    f"Duplicate test case title: "
                    f"{test_case.title}"
                )
            else:
                titles.add(
                    normalized_title
                )

        return errors

    def validate_automation_steps(
        self,
        result: AutomationStepGenerationResult,
        page_elements: list[PageElement],
    ) -> list[str]:

        errors = []

        if not result.steps:
            return [
                "Generated automation contains no steps."
            ]

        available_locators = set()

        for element in page_elements:

            available_locators.update(
                element.locator_candidates
            )

            if element.element_id:
                available_locators.add(
                    f"By.ID: {element.element_id}"
                )

            if element.name:
                available_locators.add(
                    f"By.NAME: {element.name}"
                )

        for index, step in enumerate(
            result.steps,
            start=1
        ):

            action = (
                step.action or ""
            ).strip().lower()

            # -----------------------------------------------------
            # ACTION VALIDATION
            # -----------------------------------------------------

            if action == "navigate":
                errors.append(
                    f"Automation step {index}: "
                    "navigate action is not allowed. "
                    "Application navigation must be handled "
                    "by the automation framework."
                )
                continue

            if action not in self.SUPPORTED_ACTIONS:

                errors.append(
                    f"Automation step {index}: "
                    f"unsupported action "
                    f"'{step.action}'."
                )

                continue

            # -----------------------------------------------------
            # URL ASSERTION
            #
            # assert_url_contains is special:
            # it does NOT use a page-element locator.
            # -----------------------------------------------------

            if action == "assert_url_contains":

                if step.locator:
                    errors.append(
                        f"Automation step {index}: "
                        "'assert_url_contains' must not have "
                        "a locator. Use the URL fragment in "
                        "the 'value' field."
                    )

                if step.value is None:

                    errors.append(
                        f"Automation step {index}: "
                        "'assert_url_contains' requires a value."
                    )

                elif not str(
                    step.value
                ).strip():

                    errors.append(
                        f"Automation step {index}: "
                        "'assert_url_contains' requires a "
                        "non-empty expected value."
                    )

                continue

            # -----------------------------------------------------
            # LOCATOR-BASED ACTIONS
            # -----------------------------------------------------

            if action in {
                "enter_text",
                "click",
                "select",
                "assert_text",
                "assert_element_visible",
            }:

                if (
                    not step.locator
                    or not step.locator.strip()
                ):

                    errors.append(
                        f"Automation step {index}: "
                        f"'{action}' requires a locator."
                    )

                else:

                    locator_error = (
                        self._validate_locator(
                            step.locator,
                            index,
                        )
                    )

                    if locator_error:
                        errors.append(
                            locator_error
                        )

                    elif (
                        available_locators
                        and step.locator.strip()
                        not in available_locators
                    ):

                        errors.append(
                            f"Automation step {index}: "
                            f"Locator '{step.locator}' "
                            "was not found in inspected "
                            "page elements."
                        )

            # -----------------------------------------------------
            # VALUE VALIDATION
            # -----------------------------------------------------

            if action in {
                "enter_text",
                "select",
                "assert_text",
            }:

                if step.value is None:

                    errors.append(
                        f"Automation step {index}: "
                        f"'{action}' requires a value."
                    )

            # -----------------------------------------------------
            # ASSERT TEXT
            # -----------------------------------------------------

            if action == "assert_text":

                if step.value is not None:
                    if not str(
                        step.value
                    ).strip():

                        errors.append(
                            f"Automation step {index}: "
                            "'assert_text' requires a "
                            "non-empty expected value."
                        )

        return errors

    def validate_automation_alignment(
        self,
        test_case: TestCase,
        automation: AutomationStepGenerationResult,
    ) -> list[str]:

        errors = []

        test_data = (
            test_case.test_data
            or {}
        )

        enter_text_steps = [
            step
            for step in automation.steps
            if step.action.strip().lower()
            == "enter_text"
        ]

        generated_values = [
            step.value
            for step in enter_text_steps
        ]

        # ---------------------------------------------------------
        # Every generated input must exist in test_data.
        # ---------------------------------------------------------

        expected_values = list(
            test_data.values()
        )

        for step in enter_text_steps:

            if step.value not in expected_values:

                errors.append(
                    f"{test_case.id}: Generated input value "
                    f"'{step.value}' is not present in "
                    "test_data."
                )

        # ---------------------------------------------------------
        # Every non-empty test-data value must be used.
        # ---------------------------------------------------------

        for key, expected_value in test_data.items():

            if expected_value != "":

                if expected_value not in generated_values:

                    errors.append(
                        f"{test_case.id}: Test data mismatch "
                        f"for '{key}'. Expected "
                        f"'{expected_value}', but generated "
                        f"automation uses {generated_values}."
                    )

                continue

            # -----------------------------------------------------
            # Empty values must have a matching empty input.
            # -----------------------------------------------------

            matching_blank_input = any(
                step.value == ""
                and self._locator_matches_key(
                    step.locator,
                    key,
                )
                for step in enter_text_steps
            )

            if not matching_blank_input:

                errors.append(
                    f"{test_case.id}: Test data field "
                    f"'{key}' must be entered as an "
                    "empty value."
                )

        # ---------------------------------------------------------
        # EXPECTED RESULT ANALYSIS
        # ---------------------------------------------------------

        expected_result = (
            test_case.expected_result
            .strip()
            .lower()
        )

        positive_login = any(
            phrase in expected_result
            for phrase in {
                "logged in successfully",
                "login successful",
                "user is logged in",
                "successfully logged in",
            }
        )

        negative_login = any(
            phrase in expected_result
            for phrase in {
                "not logged in",
                "login fails",
                "login failed",
                "should not log in",
                "user remains logged out",
            }
        )

        url_assertions = [
            step
            for step in automation.steps
            if step.action.strip().lower()
            == "assert_url_contains"
        ]

        # ---------------------------------------------------------
        # Successful test must validate its outcome.
        # ---------------------------------------------------------

        if positive_login and not url_assertions:

            has_other_assertion = any(
                step.action.strip().lower()
                in {
                    "assert_text",
                    "assert_element_visible",
                }
                for step in automation.steps
            )

            if not has_other_assertion:

                errors.append(
                    f"{test_case.id}: Expected successful login, "
                    "but generated automation has no outcome "
                    "assertion."
                )

        # ---------------------------------------------------------
        # Negative login must not assert positive navigation.
        # ---------------------------------------------------------

        if negative_login:

            positive_url_fragments = {
                "inventory",
                "dashboard",
                "home",
            }

            for step in url_assertions:

                value = (
                    step.value or ""
                ).strip().lower()

                if value in positive_url_fragments:

                    errors.append(
                        f"{test_case.id}: Expected login failure, "
                        f"but automation asserts successful "
                        f"navigation using URL fragment "
                        f"'{step.value}'."
                    )

        return errors

    def _validate_locator(
        self,
        locator: str,
        step_index: int,
    ) -> str | None:

        if ":" not in locator:

            return (
                f"Automation step {step_index}: "
                f"invalid locator '{locator}'. "
                "Expected 'By.<STRATEGY>: <VALUE>'."
            )

        strategy, value = locator.split(
            ":",
            1
        )

        strategy = strategy.strip()
        value = value.strip()

        if strategy not in self.SUPPORTED_LOCATOR_STRATEGIES:

            return (
                f"Automation step {step_index}: "
                f"unsupported locator strategy "
                f"'{strategy}'."
            )

        if not value:

            return (
                f"Automation step {step_index}: "
                "locator value is empty."
            )

        return None

    def _locator_matches_key(
        self,
        locator: str | None,
        key: str,
    ) -> bool:

        if not locator:
            return False

        locator_text = locator.lower()
        key_text = key.lower()

        synonyms = {
            "username": [
                "username",
                "user-name",
                "user_name",
                "user",
            ],
            "password": [
                "password",
                "pass",
                "pwd",
            ],
            "email": [
                "email",
                "e-mail",
            ],
        }

        terms = synonyms.get(
            key_text,
            [key_text],
        )

        return any(
            term in locator_text
            for term in terms
        )