from fastapi import FastAPI, HTTPException
import time

from app.models import (
    TestGenerationRequest,
    TestGenerationResponse,
    TestEvaluationRequest,
    AutomationRunRequest,
    AutomationRunResponse,
    ApiTestGenerationRequest
)

from app.services.test_generator import TestGenerator
from app.services.test_quality_evaluator import TestQualityEvaluator
from app.services.automation_generator import AutomationGenerator
from app.services.page_inspector import PageInspector
from app.services.test_executor import TestExecutor
from app.services.api_test_generator import ApiTestGenerator
from app.services.api_test_executor import ApiTestExecutor


app = FastAPI(
    title="AI Test Intelligence Framework",
    description="AI-powered software testing assistant",
    version="1.0.0"
)


test_generator = TestGenerator()
quality_evaluator = TestQualityEvaluator()
automation_generator = AutomationGenerator()
page_inspector = PageInspector()
test_executor = TestExecutor()

api_test_generator = ApiTestGenerator()
api_test_executor = ApiTestExecutor()


@app.get("/")
def root():
    return {
        "message": "AI Test Intelligence Framework is running"
    }


@app.get("/health")
def health():
    return {
        "status": "UP"
    }


# ============================================================
# TEST GENERATION
# ============================================================

@app.post(
    "/api/v1/tests/generate",
    response_model=TestGenerationResponse
)
def generate_tests(
    request: TestGenerationRequest
):
    try:

        result = test_generator.generate_test_cases(
            request.requirement
        )

        return TestGenerationResponse(
            requirement=request.requirement,
            test_cases=result.test_cases
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=str(exc)
        )


# ============================================================
# TEST EVALUATION
# ============================================================

@app.post(
    "/api/v1/tests/validate"
)
def evaluate_tests(
    request: TestEvaluationRequest
):
    try:

        result = quality_evaluator.evaluate(
            requirement=request.requirement,
            test_cases=request.test_cases
        )

        return result

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=str(exc)
        )

# ============================================================
# UI AUTOMATION RUN
# ============================================================

@app.post(
    "/api/v1/automation/run",
    response_model=AutomationRunResponse
)
def run_automation(
    request: AutomationRunRequest
):
    try:

        overall_start = time.time()

        print(
            "\n========== AUTOMATION RUN STARTED =========="
        )

        # ---------------------------------------------------------
        # 1. Generate test cases
        # ---------------------------------------------------------

        stage_start = time.time()

        print(
            "[1/5] Generating test cases..."
        )

        generated_tests = (
            test_generator.generate_test_cases(
                request.requirement
            )
        )

        print(
            f"[1/5] Test generation completed in "
            f"{time.time() - stage_start:.2f} seconds"
        )

        # ---------------------------------------------------------
        # 2. Select test cases
        # ---------------------------------------------------------

        stage_start = time.time()

        if request.test_case_id:

            print(
                f"[2/5] Selecting test case "
                f"{request.test_case_id}..."
            )

            selected_test_cases = []

            for test_case in generated_tests.test_cases:

                if (
                    test_case.id.upper()
                    == request.test_case_id.upper()
                ):

                    selected_test_cases.append(
                        test_case
                    )

                    break

            if not selected_test_cases:

                raise HTTPException(
                    status_code=404,
                    detail=(
                        f"Test case '{request.test_case_id}' "
                        f"was not found in generated test cases."
                    )
                )

        else:

            print(
                "[2/5] No test_case_id provided. "
                "Executing all generated test cases..."
            )

            selected_test_cases = (
                generated_tests.test_cases
            )

        print(
            f"[2/5] Selected "
            f"{len(selected_test_cases)} test case(s) "
            f"in {time.time() - stage_start:.2f} seconds"
        )

        # ---------------------------------------------------------
        # 3. Inspect application
        # ---------------------------------------------------------

        stage_start = time.time()

        print(
            "[3/5] Inspecting application..."
        )

        inspection = page_inspector.inspect(
            request.application_url
        )

        print(
            f"[3/5] Application inspection completed in "
            f"{time.time() - stage_start:.2f} seconds"
        )

        print(
            f"      Inspected elements: "
            f"{len(inspection.elements)}"
        )

        # ---------------------------------------------------------
        # 4. Generate automation and execute test cases
        # ---------------------------------------------------------

        results = []

        for index, test_case in enumerate(
            selected_test_cases,
            start=1
        ):

            print(
                f"\n========== EXECUTING "
                f"{test_case.id} "
                f"({index}/{len(selected_test_cases)}) =========="
            )

            # -----------------------------------------------------
            # 4a. Generate automation
            # -----------------------------------------------------

            stage_start = time.time()

            print(
                f"[4/5] Generating automation code "
                f"for {test_case.id}..."
            )

            automation = (
                automation_generator.generate_selenium_code(
                    test_case=test_case,
                    application_url=request.application_url,
                    page_elements=inspection.elements
                )
            )

            print(
                f"[4/5] Automation generation completed for "
                f"{test_case.id} in "
                f"{time.time() - stage_start:.2f} seconds"
            )

            # -----------------------------------------------------
            # 5. Execute automation
            # -----------------------------------------------------

            stage_start = time.time()

            print(
                f"[5/5] Executing {test_case.id}..."
            )

            execution_result = test_executor.execute(
                test_case_id=test_case.id,
                code=automation.code
            )

            print(
                f"[5/5] {test_case.id} execution completed in "
                f"{time.time() - stage_start:.2f} seconds"
            )

            # -----------------------------------------------------
            # Store result
            # -----------------------------------------------------

            results.append(
                {
                    "test_case_id": test_case.id,
                    "test_case": test_case,
                    "inspected_elements": len(
                        inspection.elements
                    ),
                    "automation_code": automation.code,
                    "execution": execution_result["execution"],
                    "analysis": execution_result["analysis"]
                }
            )

        # ---------------------------------------------------------
        # Final timing
        # ---------------------------------------------------------

        total_time = time.time() - overall_start

        print(
            f"\nTOTAL AUTOMATION RUN TIME: "
            f"{total_time:.2f} seconds"
        )

        print(
            f"Executed test cases: {len(results)}"
        )

        print(
            "========== AUTOMATION RUN COMPLETED ==========\n"
        )

        return AutomationRunResponse(
            requirement=request.requirement,
            application_url=request.application_url,
            total_test_cases=len(results),
            results=results
        )

    except HTTPException:
        raise

    except Exception as exc:

        print(
            f"\nAUTOMATION RUN FAILED: {exc}"
        )

        raise HTTPException(
            status_code=500,
            detail=str(exc)
        )


# ============================================================
# API TEST GENERATION + EXECUTION
# ============================================================

@app.post(
    "/api/v1/api-tests/run"
)
def run_api_tests(
    request: ApiTestGenerationRequest
):
    try:

        overall_start = time.time()

        print(
            "\n========== API TEST RUN STARTED =========="
        )

        # ---------------------------------------------------------
        # 1. Generate API test cases
        # ---------------------------------------------------------

        stage_start = time.time()

        print(
            "[1/3] Generating API test cases..."
        )

        generated_tests = (
            api_test_generator.generate_api_tests(
                requirement=request.requirement,
                base_url=request.base_url
            )
        )

        print(
            f"[1/3] API test generation completed in "
            f"{time.time() - stage_start:.2f} seconds"
        )

        generated_test_cases = (
            generated_tests.test_cases
        )

        if not generated_test_cases:

            raise HTTPException(
                status_code=422,
                detail=(
                    "No API test cases were generated."
                )
            )

        print(
            f"      Generated test cases: "
            f"{len(generated_test_cases)}"
        )

        # ---------------------------------------------------------
        # 2. Execute every generated API test case
        # ---------------------------------------------------------

        print(
            "[2/3] Executing generated API test cases..."
        )

        results = []

        for index, test_case in enumerate(
            generated_test_cases,
            start=1
        ):

            print(
                f"\n========== EXECUTING API "
                f"{test_case.id} "
                f"({index}/{len(generated_test_cases)}) =========="
            )

            stage_start = time.time()

            try:

                execution_result = (
                    api_test_executor.execute(
                        base_url=request.base_url,
                        test_case=test_case
                    )
                )

                if hasattr(
                    execution_result,
                    "model_dump"
                ):
                    execution_data = (
                        execution_result.model_dump()
                    )

                elif isinstance(
                    execution_result,
                    dict
                ):
                    execution_data = (
                        execution_result
                    )

                else:
                    execution_data = {
                        "result": str(
                            execution_result
                        )
                    }

                results.append(
                    {
                        "test_case_id": test_case.id,
                        "test_case": (
                            test_case.model_dump()
                            if hasattr(
                                test_case,
                                "model_dump"
                            )
                            else test_case
                        ),
                        "execution": execution_data
                    }
                )

                print(
                    f"API {test_case.id} completed in "
                    f"{time.time() - stage_start:.2f} seconds"
                )

            except Exception as exc:

                print(
                    f"API {test_case.id} execution failed: "
                    f"{exc}"
                )

                results.append(
                    {
                        "test_case_id": test_case.id,
                        "test_case": (
                            test_case.model_dump()
                            if hasattr(
                                test_case,
                                "model_dump"
                            )
                            else test_case
                        ),
                        "execution": {
                            "test_case_id": test_case.id,
                            "status": "FAILED",
                            "passed": False,
                            "error": str(exc)
                        }
                    }
                )

        # ---------------------------------------------------------
        # 3. Final result
        # ---------------------------------------------------------

        total_time = time.time() - overall_start

        passed_count = 0
        failed_count = 0

        for result in results:

            execution = result.get(
                "execution",
                {}
            )

            status = str(
                execution.get(
                    "status",
                    ""
                )
            ).upper()

            passed = execution.get(
                "passed"
            )

            if (
                passed is True
                or status == "PASSED"
            ):
                passed_count += 1

            elif (
                passed is False
                or status == "FAILED"
            ):
                failed_count += 1

        print(
            "[3/3] API test execution completed."
        )

        print(
            f"Generated test cases: "
            f"{len(generated_test_cases)}"
        )

        print(
            f"Passed: {passed_count}"
        )

        print(
            f"Failed: {failed_count}"
        )

        print(
            f"TOTAL API TEST RUN TIME: "
            f"{total_time:.2f} seconds"
        )

        print(
            "========== API TEST RUN COMPLETED ==========\n"
        )

        return {
            "requirement": request.requirement,
            "base_url": request.base_url,
            "total_test_cases": len(
                generated_test_cases
            ),
            "passed": passed_count,
            "failed": failed_count,
            "results": results,
            "duration_seconds": round(
                total_time,
                2
            )
        }

    except HTTPException:
        raise

    except Exception as exc:

        print(
            f"\nAPI TEST RUN FAILED: {exc}"
        )

        raise HTTPException(
            status_code=500,
            detail=str(exc)
        )