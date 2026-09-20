import json
import re

from app.models import AutomationStep


class SeleniumCodeGenerator:

    def generate(
        self,
        test_case_id: str,
        application_url: str,
        steps: list[AutomationStep],
    ) -> str:

        safe_test_case_id = self._safe_identifier(test_case_id)
        artifact_dir = f"artifacts/{test_case_id}"

        lines = [
            "import pytest",
            "from pathlib import Path",
            "from datetime import datetime",
            "from selenium import webdriver",
            "from selenium.webdriver.common.by import By",
            "from selenium.webdriver.support.ui import WebDriverWait, Select",
            "from selenium.webdriver.support import expected_conditions as EC",
            "",
            "",
            "class LocatorFailure(Exception):",
            "    pass",
            "",
            "",
            f"ARTIFACT_DIR = Path({json.dumps(artifact_dir)})",
            "ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)",
            "",
            "",
            "def parse_locator(locator):",
            "    if not locator or ':' not in locator:",
            "        return None, locator",
            "",
            "    strategy, value = locator.split(':', 1)",
            "    strategy = strategy.strip()",
            "    value = value.strip()",
            "",
            "    locator_map = {",
            "        'By.ID': By.ID,",
            "        'By.NAME': By.NAME,",
            "        'By.XPATH': By.XPATH,",
            "        'By.CSS_SELECTOR': By.CSS_SELECTOR,",
            "        'By.CLASS_NAME': By.CLASS_NAME,",
            "        'By.TAG_NAME': By.TAG_NAME,",
            "        'By.LINK_TEXT': By.LINK_TEXT,",
            "        'By.PARTIAL_LINK_TEXT': By.PARTIAL_LINK_TEXT",
            "    }",
            "",
            "    return locator_map.get(strategy), value",
            "",
            "",
            "def find_element(driver, locator, log):",
            "    by, value = parse_locator(locator)",
            "",
            "    if not by:",
            "        raise LocatorFailure(",
            "            f'Unsupported locator: {locator}'",
            "        )",
            "",
            "    try:",
            "        return WebDriverWait(driver, 10).until(",
            "            EC.presence_of_element_located(",
            "                (by, value)",
            "            )",
            "        )",
            "",
            "    except Exception as exc:",
            "        log(",
            "            f'Locator failed: {locator}'",
            "        )",
            "",
            "        raise LocatorFailure(",
            "            f'Locator could not be resolved: {locator}'",
            "        ) from exc",
            "",
            "",
            "@pytest.fixture",
            "def driver():",
            "    driver = webdriver.Chrome()",
            "    yield driver",
            "    driver.quit()",
            "",
            "",
            f"def test_{safe_test_case_id}(driver):",
            "    log_file = ARTIFACT_DIR / 'execution.log'",
            "",
            "    def log(message):",
            "        with open(",
            "            log_file,",
            "            'a',",
            "            encoding='utf-8'",
            "        ) as file:",
            "            timestamp = datetime.now().strftime(",
            "                '%Y-%m-%d %H:%M:%S'",
            "            )",
            "            file.write(",
            "                f'[{timestamp}] {message}\\n'",
            "            )",
            "",
            "    try:",
            f"        log({json.dumps(f'Test {test_case_id} started')})",
            f"        driver.get({json.dumps(application_url)})",
            '        log("Application opened")',
            "",
        ]

        for step in steps:

            generated_step = self._generate_step(step)

            for line in generated_step:

                if line:
                    lines.append(
                        "        " + line
                    )
                else:
                    lines.append("")

        lines.extend([
            '        log("Test completed successfully")',
            "",
            "    except Exception as exc:",
            '        log(f"Test failed: {type(exc).__name__}: {exc}")',
            "        driver.save_screenshot(",
            "            str(ARTIFACT_DIR / 'failure.png')",
            "        )",
            "",
            "        with open(",
            "            ARTIFACT_DIR / 'page_source.html',",
            "            'w',",
            "            encoding='utf-8'",
            "        ) as file:",
            "            file.write(driver.page_source)",
            "",
            "        log('Failure screenshot captured')",
            "        log('Page source captured')",
            "        raise",
            "",
        ])

        code = "\n".join(lines)

        try:

            compile(
                code,
                f"test_{safe_test_case_id}.py",
                "exec",
            )

        except SyntaxError as exc:

            raise ValueError(
                f"Generated Selenium code is invalid Python: {exc}"
            ) from exc

        return code

    def _generate_step(
        self,
        step: AutomationStep,
    ) -> list[str]:

        action = step.action.strip().lower()

        if action == "enter_text":

            return [
                "find_element(",
                "    driver,",
                f"    {json.dumps(step.locator)},",
                "    log",
                ").send_keys(",
                f"    {json.dumps(step.value or '')}",
                ")",
                "",
            ]

        if action == "click":

            return [
                "find_element(",
                "    driver,",
                f"    {json.dumps(step.locator)},",
                "    log",
                ").click()",
                "",
            ]

        if action == "assert_text":

            return [
                "element = find_element(",
                "    driver,",
                f"    {json.dumps(step.locator)},",
                "    log",
                ")",
                f"assert {json.dumps(step.value or '')} in element.text",
                "",
            ]

        if action == "assert_url_contains":

            return [
                "WebDriverWait(driver, 10).until(",
                f"    EC.url_contains({json.dumps(step.value or '')})",
                ")",
                f"assert {json.dumps(step.value or '')} in driver.current_url",
                "",
            ]

        if action == "assert_element_visible":

            return [
                "find_element(",
                "    driver,",
                f"    {json.dumps(step.locator)},",
                "    log",
                ")",
                "",
            ]

        if action == "select":

            return [
                "Select(",
                "    find_element(",
                "        driver,",
                f"        {json.dumps(step.locator)},",
                "        log",
                "    )",
                f").select_by_visible_text({json.dumps(step.value or '')})",
                "",
            ]

        raise ValueError(
            f"Unsupported automation action: {step.action}"
        )

    @staticmethod
    def _safe_identifier(value: str) -> str:

        identifier = re.sub(
            r"\W+",
            "_",
            value.lower(),
        ).strip("_")

        if not identifier:
            identifier = "generated_test"

        if identifier[0].isdigit():
            identifier = f"test_{identifier}"

        return identifier