from app.models import (
    AutomationStep,
    AutomationStepGenerationResult,
    TestCase,
)
from app.services.ui_test_validator import UITestValidator


def create_valid_test_case(**overrides):
    data = {
        "id": "TC001",
        "title": "Valid Login",
        "category": "Functional",
        "priority": "High",
        "preconditions": [],
        "steps": [
            "Open SauceDemo",
            "Enter username and password",
            "Click login"
        ],
        "expected_result": "User is logged in successfully",
        "test_data": {
            "username": "standard_user",
            "password": "secret_sauce"
        }
    }

    data.update(overrides)

    return TestCase(**data)


def test_valid_test_case_has_no_validation_errors():
    validator = UITestValidator()

    test_case = create_valid_test_case()

    errors = validator.validate_test_case(test_case)

    assert errors == []


def test_invalid_category_is_rejected():
    validator = UITestValidator()

    test_case = create_valid_test_case(
        category="Unsupported"
    )

    errors = validator.validate_test_case(test_case)

    assert any(
        "Unsupported test category" in error
        for error in errors
    )


def test_duplicate_test_case_id_is_rejected():
    validator = UITestValidator()

    first = create_valid_test_case(
        id="TC001"
    )

    second = create_valid_test_case(
        id="TC001",
        title="Another Login Test"
    )

    errors = validator.validate_test_suite(
        [first, second]
    )

    assert any(
        "Duplicate test case ID" in error
        for error in errors
    )


def test_navigate_action_is_rejected():
    validator = UITestValidator()

    automation = AutomationStepGenerationResult(
        steps=[
            AutomationStep(
                action="navigate",
                locator=None,
                value=None
            )
        ]
    )

    errors = validator.validate_automation_steps(
        result=automation,
        page_elements=[]
    )

    assert any(
        "navigate action is not allowed" in error
        for error in errors
    )


def test_invalid_locator_format_is_rejected():
    validator = UITestValidator()

    automation = AutomationStepGenerationResult(
        steps=[
            AutomationStep(
                action="click",
                locator="invalid-locator",
                value=None
            )
        ]
    )

    errors = validator.validate_automation_steps(
        result=automation,
        page_elements=[]
    )

    assert any(
        "invalid locator" in error
        for error in errors
    )


def test_generated_input_value_must_match_test_data():
    validator = UITestValidator()

    test_case = create_valid_test_case()

    automation = AutomationStepGenerationResult(
        steps=[
            AutomationStep(
                action="enter_text",
                locator="By.ID: user-name",
                value="wrong_username"
            ),
            AutomationStep(
                action="enter_text",
                locator="By.ID: password",
                value="secret_sauce"
            ),
            AutomationStep(
                action="click",
                locator="By.ID: login-button",
                value=None
            ),
            AutomationStep(
                action="assert_url_contains",
                locator=None,
                value="inventory"
            )
        ]
    )

    errors = validator.validate_automation_alignment(
        test_case=test_case,
        automation=automation
    )

    assert any(
        "Generated input value" in error
        for error in errors
    )


def test_positive_login_requires_outcome_assertion():
    validator = UITestValidator()

    test_case = create_valid_test_case()

    automation = AutomationStepGenerationResult(
        steps=[
            AutomationStep(
                action="enter_text",
                locator="By.ID: user-name",
                value="standard_user"
            ),
            AutomationStep(
                action="enter_text",
                locator="By.ID: password",
                value="secret_sauce"
            ),
            AutomationStep(
                action="click",
                locator="By.ID: login-button",
                value=None
            )
        ]
    )

    errors = validator.validate_automation_alignment(
        test_case=test_case,
        automation=automation
    )

    assert any(
        "no outcome assertion" in error
        for error in errors
    )