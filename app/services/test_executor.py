import subprocess
from pathlib import Path
import time

from app.services.test_result_analyzer import TestResultAnalyzer


class TestExecutor:

    MAX_RETRIES = 2
    RETRY_DELAY_SECONDS = 2
    LOCATOR_FAILURE_MARKER = "LocatorFailure"

    def __init__(self):
        self.analyzer = TestResultAnalyzer()

    def execute(
        self,
        test_case_id: str,
        code: str,
    ) -> dict:

        generated_tests_dir = Path("generated_tests")
        generated_tests_dir.mkdir(
            exist_ok=True
        )

        test_file = (
            generated_tests_dir
            / f"test_{test_case_id.lower()}.py"
        )

        test_file.write_text(
            code,
            encoding="utf-8"
        )

        attempts = []

        total_start_time = time.time()

        max_attempts = self.MAX_RETRIES + 1

        for attempt_number in range(
            1,
            max_attempts + 1
        ):

            print(
                f"\n========== TEST ATTEMPT "
                f"{attempt_number}/{max_attempts} =========="
            )

            start_time = time.time()

            try:

                result = subprocess.run(
                    [
                        "pytest",
                        str(test_file),
                        "-v"
                    ],
                    capture_output=True,
                    text=True
                )

                duration = round(
                    time.time() - start_time,
                    2
                )

                status = (
                    "PASSED"
                    if result.returncode == 0
                    else "FAILED"
                )

                attempt_result = {
                    "attempt": attempt_number,
                    "status": status,
                    "exit_code": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "duration_seconds": duration
                }

            except Exception as exc:

                duration = round(
                    time.time() - start_time,
                    2
                )

                attempt_result = {
                    "attempt": attempt_number,
                    "status": "FAILED",
                    "exit_code": -1,
                    "stdout": "",
                    "stderr": str(exc),
                    "duration_seconds": duration
                }

            attempts.append(
                attempt_result
            )

            print(
                f"Attempt {attempt_number}: "
                f"{attempt_result['status']} "
                f"({attempt_result['duration_seconds']}s)"
            )

            # =====================================================
            # PASSED
            # =====================================================

            if attempt_result["status"] == "PASSED":

                total_duration = round(
                    time.time() - total_start_time,
                    2
                )

                # -------------------------------------------------
                # Passed on first attempt
                # -------------------------------------------------

                if attempt_number == 1:

                    execution_result = {
                        "test_case_id": test_case_id,
                        "status": "PASSED",
                        "exit_code": 0,
                        "stdout": attempt_result["stdout"],
                        "stderr": attempt_result["stderr"],
                        "duration_seconds": total_duration,
                        "test_file": str(test_file),
                        "attempts": attempts,
                        "retry_count": 0,
                        "flaky": False
                    }

                    analysis = {
                        "status": "PASSED",
                        "failure_type": "NONE",
                        "root_cause": "No failure detected.",
                        "evidence": [
                            "Test passed on the first attempt.",
                            "Pytest returned exit code 0."
                        ],
                        "recommendation": "No action required."
                    }

                    print(
                        "\nTest passed on first attempt. "
                        "No retry performed."
                    )

                    return {
                        "execution": execution_result,
                        "analysis": analysis
                    }

                # -------------------------------------------------
                # Passed after locator retry
                # -------------------------------------------------

                execution_result = {
                    "test_case_id": test_case_id,
                    "status": "FLAKY",
                    "exit_code": 0,
                    "stdout": attempt_result["stdout"],
                    "stderr": attempt_result["stderr"],
                    "duration_seconds": total_duration,
                    "test_file": str(test_file),
                    "attempts": attempts,
                    "retry_count": attempt_number - 1,
                    "flaky": True
                }

                failed_attempts = [
                    attempt["attempt"]
                    for attempt in attempts
                    if attempt["status"] == "FAILED"
                ]

                analysis = {
                    "status": "FLAKY",
                    "failure_type": "FLAKY_TEST",
                    "root_cause": (
                        "The test failed because of a locator-resolution "
                        "failure on an earlier attempt but passed after retry."
                    ),
                    "evidence": [
                        f"Failed attempts: {failed_attempts}",
                        f"Passed on attempt {attempt_number}.",
                        "Retries were allowed only for LocatorFailure."
                    ],
                    "recommendation": (
                        "Review the locator and application timing "
                        "if locator failures continue."
                    )
                }

                print(
                    "\nTest passed after locator retry. "
                    "No further retry performed."
                )

                return {
                    "execution": execution_result,
                    "analysis": analysis
                }

            # =====================================================
            # FAILED
            # =====================================================

            locator_failure = self._is_locator_failure(
                attempt_result
            )

            # -----------------------------------------------------
            # Non-locator failure
            # -----------------------------------------------------

            if not locator_failure:

                print(
                    "\nTest failed for a non-locator reason. "
                    "No retry will be performed."
                )

                total_duration = round(
                    time.time() - total_start_time,
                    2
                )

                execution_result = {
                    "test_case_id": test_case_id,
                    "status": "FAILED",
                    "exit_code": attempt_result["exit_code"],
                    "stdout": attempt_result["stdout"],
                    "stderr": attempt_result["stderr"],
                    "duration_seconds": total_duration,
                    "test_file": str(test_file),
                    "attempts": attempts,
                    "retry_count": 0,
                    "flaky": False
                }

                analysis = self._analyze_failure(
                    test_case_id=test_case_id,
                    final_attempt=attempt_result,
                    attempts=attempts,
                    total_duration=total_duration,
                    test_file=test_file,
                )

                return {
                    "execution": execution_result,
                    "analysis": analysis
                }

            # -----------------------------------------------------
            # Locator failure
            # -----------------------------------------------------

            if attempt_number < max_attempts:

                print(
                    "\nLocator failure detected. "
                    f"Retrying in {self.RETRY_DELAY_SECONDS} seconds..."
                )

                time.sleep(
                    self.RETRY_DELAY_SECONDS
                )

                continue

            # -----------------------------------------------------
            # Last locator attempt already failed
            # -----------------------------------------------------

            print(
                "\nLocator failure persisted on the final attempt. "
                "No further retry."
            )

        # =========================================================
        # ALL LOCATOR ATTEMPTS FAILED
        # =========================================================

        final_attempt = attempts[-1]

        total_duration = round(
            time.time() - total_start_time,
            2
        )

        execution_result = {
            "test_case_id": test_case_id,
            "status": "FAILED",
            "exit_code": final_attempt["exit_code"],
            "stdout": final_attempt["stdout"],
            "stderr": final_attempt["stderr"],
            "duration_seconds": total_duration,
            "test_file": str(test_file),
            "attempts": attempts,
            "retry_count": len(attempts) - 1,
            "flaky": False
        }

        print(
            "\nTest failed after "
            f"{len(attempts)} attempts."
        )

        analysis = self._analyze_failure(
            test_case_id=test_case_id,
            final_attempt=final_attempt,
            attempts=attempts,
            total_duration=total_duration,
            test_file=test_file,
        )

        return {
            "execution": execution_result,
            "analysis": analysis
        }

    def _is_locator_failure(
        self,
        attempt_result: dict,
    ) -> bool:

        output = "\n".join([
            attempt_result.get("stdout", ""),
            attempt_result.get("stderr", ""),
        ])

        return (
            self.LOCATOR_FAILURE_MARKER
            in output
        )

    def _analyze_failure(
        self,
        test_case_id: str,
        final_attempt: dict,
        attempts: list[dict],
        total_duration: float,
        test_file: Path,
    ) -> dict:

        try:

            print(
                "Sending compact failure information "
                "to AI failure analyzer..."
            )

            analysis_input = {
                "test_case_id": test_case_id,
                "status": "FAILED",
                "exit_code": final_attempt["exit_code"],
                "stdout": final_attempt["stdout"],
                "stderr": final_attempt["stderr"],
                "duration_seconds": total_duration,
                "test_file": str(test_file),
                "retry_count": max(
                    0,
                    len(attempts) - 1
                ),
                "attempt_summary": [
                    {
                        "attempt": attempt["attempt"],
                        "status": attempt["status"],
                        "exit_code": attempt["exit_code"],
                        "duration_seconds": attempt[
                            "duration_seconds"
                        ]
                    }
                    for attempt in attempts
                ]
            }

            analysis = self.analyzer.analyze(
                analysis_input
            )

        except Exception as exc:

            print(
                f"AI failure analysis unavailable: {exc}"
            )

            analysis = {
                "status": "FAILED",
                "failure_type": "UNKNOWN",
                "root_cause": (
                    "The test failed during execution. "
                    "AI failure analysis was unavailable."
                ),
                "evidence": [
                    f"Total attempts: {len(attempts)}",
                    f"AI analysis error: {str(exc)}"
                ],
                "recommendation": (
                    "Review the final pytest output, "
                    "failure screenshot, and page source."
                )
            }

        self._append_analysis_to_log(
            test_case_id=test_case_id,
            analysis=analysis
        )

        return analysis

    def _append_analysis_to_log(
        self,
        test_case_id: str,
        analysis: dict
    ):

        artifact_dir = (
            Path("artifacts")
            / test_case_id
        )

        log_file = (
            artifact_dir
            / "execution.log"
        )

        if not log_file.exists():
            return

        timestamp = time.strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        with open(
            log_file,
            "a",
            encoding="utf-8"
        ) as file:

            file.write(
                f"[{timestamp}] "
                f"Failure type: "
                f"{analysis.get('failure_type', 'UNKNOWN')}\n"
            )

            file.write(
                f"[{timestamp}] "
                f"Root cause: "
                f"{analysis.get('root_cause', 'Unknown')}\n"
            )

            file.write(
                f"[{timestamp}] "
                f"Recommendation: "
                f"{analysis.get('recommendation', 'None')}\n"
            )