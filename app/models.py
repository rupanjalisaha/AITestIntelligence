from typing import Any, List

from pydantic import BaseModel, Field


class TestGenerationRequest(BaseModel):

    requirement: str = Field(
        ...,
        min_length=10,
        description="Software requirement or user story"
    )


class TestCase(BaseModel):

    id: str
    title: str
    category: str
    priority: str
    preconditions: List[str]
    steps: List[str]
    expected_result: str
    test_data: dict[str, str] = Field(
        default_factory=dict
    )


class TestCaseGenerationResult(BaseModel):

    test_cases: List[TestCase]


class TestGenerationResponse(BaseModel):

    requirement: str
    test_cases: List[TestCase]


class TestEvaluationRequest(BaseModel):

    requirement: str = Field(
        ...,
        min_length=10,
        description="Software requirement or user story"
    )

    test_cases: List[TestCase]


class PageInspectionRequest(BaseModel):

    application_url: str = Field(
        ...,
        min_length=5,
        description="URL of the application to inspect"
    )


class PageElement(BaseModel):

    tag: str
    element_type: str | None = None
    text: str = ""
    element_id: str | None = None
    name: str | None = None
    placeholder: str | None = None
    aria_label: str | None = None
    test_id: str | None = None
    locator_candidates: List[str] = Field(
        default_factory=list
    )


class AutomationGenerationRequest(BaseModel):

    test_case: TestCase

    application_url: str = Field(
        ...,
        min_length=5,
        description="Base URL of the application under test"
    )

    page_elements: List[PageElement] = Field(
        default_factory=list
    )


class AutomationGenerationResponse(BaseModel):

    test_case_id: str
    framework: str
    language: str
    code: str


class AutomationStep(BaseModel):

    action: str
    locator: str | None = None
    value: str | None = None


class AutomationStepGenerationResult(BaseModel):

    steps: List[AutomationStep]


class PageInspectionResponse(BaseModel):

    application_url: str
    title: str
    elements: List[PageElement]


class TestExecutionRequest(BaseModel):

    test_case_id: str
    code: str


class AutomationRunRequest(BaseModel):

    requirement: str = Field(
        ...,
        min_length=10,
        description="Software requirement or user story"
    )

    application_url: str = Field(
        ...,
        min_length=5,
        description="Application URL"
    )

    test_case_id: str | None = Field(
        default=None,
        min_length=3,
        description=(
            "Optional test case ID. "
            "If omitted, all generated test cases are executed."
        )
    )


class AutomationTestRunResult(BaseModel):

    test_case_id: str
    test_case: TestCase
    inspected_elements: int
    automation_code: str
    execution: dict
    analysis: dict


class AutomationRunResponse(BaseModel):

    requirement: str
    application_url: str

    total_test_cases: int

    results: List[AutomationTestRunResult]
    
# ============================================================
# API TESTING MODELS
# ============================================================


class ApiTestGenerationRequest(BaseModel):

    requirement: str = Field(
        ...,
        min_length=10,
        description="API testing requirement or user story"
    )

    base_url: str = Field(
        ...,
        min_length=5,
        description="Base URL of the API under test"
    )


class ApiTestCase(BaseModel):

    id: str
    title: str
    category: str
    priority: str

    method: str

    endpoint: str

    headers: dict[str, str] = Field(
        default_factory=dict
    )

    query_params: dict[str, str] = Field(
        default_factory=dict
    )

    body: Any | None = None

    expected_status: int = Field(
        ...,
        ge=100,
        le=599
    )

    expected_body_contains: List[str] = Field(
        default_factory=list
    )

    expected_headers: dict[str, str] = Field(
        default_factory=dict
    )

    expected_json: dict[str, Any] = Field(
        default_factory=dict
    )

    expected_json_types: dict[str, str] = Field(
        default_factory=dict
    )


class ApiTestGenerationResult(BaseModel):

    test_cases: List[ApiTestCase]


class ApiTestGenerationResponse(BaseModel):

    requirement: str
    base_url: str
    test_cases: List[ApiTestCase]


class ApiTestExecutionRequest(BaseModel):

    base_url: str = Field(
        ...,
        min_length=5,
        description="Base URL of the API under test"
    )

    test_case: ApiTestCase


class ApiTestExecutionResponse(BaseModel):

    test_case_id: str
    title: str
    method: str
    url: str

    status: str
    passed: bool

    expected_status: int
    actual_status: int | None = None

    response_time_ms: float | None = None

    status_validation: bool

    body_validation: bool

    header_validation: bool

    response_body: str = ""

    response_headers: dict[str, str] = Field(
        default_factory=dict
    )

    validation_errors: List[str] = Field(
        default_factory=list
    )