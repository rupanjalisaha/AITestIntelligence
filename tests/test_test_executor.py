import subprocess
from unittest.mock import Mock, patch

from app.services.test_executor import TestExecutor


TEST_CODE = """
def test_generated():
    assert True
"""


def create_executor():
    executor = TestExecutor()

    executor.analyzer = Mock()

    executor.analyzer.analyze.return_value = {
        "status": "FAILED",
        "failure_type": "AUTOMATION_DEFECT",
        "root_cause": "Test failure",
        "evidence": [],
        "recommendation": "Review the failure"
    }

    return executor


def test_passed_test_does_not_retry():
    executor = create_executor()

    success_result = subprocess.CompletedProcess(
        args=[],
        returncode=0,
        stdout="1 passed",
        stderr=""
    )

    with patch(
        "app.services.test_executor.subprocess.run",
        return_value=success_result
    ) as mock_run:

        result = executor.execute(
            test_case_id="TC001",
            code=TEST_CODE
        )

    assert result["execution"]["status"] == "PASSED"
    assert result["execution"]["retry_count"] == 0
    assert len(result["execution"]["attempts"]) == 1

    mock_run.assert_called_once()


def test_non_locator_failure_does_not_retry():
    executor = create_executor()

    failure_result = subprocess.CompletedProcess(
        args=[],
        returncode=1,
        stdout="AssertionError: expected value",
        stderr=""
    )

    with patch(
        "app.services.test_executor.subprocess.run",
        return_value=failure_result
    ) as mock_run:

        result = executor.execute(
            test_case_id="TC002",
            code=TEST_CODE
        )

    assert result["execution"]["status"] == "FAILED"
    assert result["execution"]["retry_count"] == 0
    assert len(result["execution"]["attempts"]) == 1

    mock_run.assert_called_once()

    executor.analyzer.analyze.assert_called_once()


def test_locator_failure_retries_and_can_become_flaky():
    executor = create_executor()

    locator_failure = subprocess.CompletedProcess(
        args=[],
        returncode=1,
        stdout="LocatorFailure: locator could not be resolved",
        stderr=""
    )

    success_result = subprocess.CompletedProcess(
        args=[],
        returncode=0,
        stdout="1 passed",
        stderr=""
    )

    with patch(
        "app.services.test_executor.subprocess.run",
        side_effect=[
            locator_failure,
            success_result
        ]
    ) as mock_run, patch(
        "app.services.test_executor.time.sleep"
    ) as mock_sleep:

        result = executor.execute(
            test_case_id="TC003",
            code=TEST_CODE
        )

    assert result["execution"]["status"] == "FLAKY"
    assert result["execution"]["retry_count"] == 1
    assert len(result["execution"]["attempts"]) == 2

    assert mock_run.call_count == 2
    mock_sleep.assert_called_once_with(2)

    executor.analyzer.analyze.assert_not_called()