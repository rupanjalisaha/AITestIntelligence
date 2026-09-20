from difflib import SequenceMatcher

from selenium.webdriver.common.by import By


class SelfHealingService:

    def heal_locator(
        self,
        driver,
        failed_locator: str,
        expected_text: str | None = None
    ) -> str | None:

        if not failed_locator:
            return None

        strategy, value = self._parse_locator(
            failed_locator
        )

        elements = driver.find_elements(
            By.XPATH,
            "//*"
        )

        candidates = []

        for element in elements:

            try:
                if not element.is_displayed():
                    continue

                element_id = element.get_attribute("id")
                name = element.get_attribute("name")
                aria_label = element.get_attribute("aria-label")
                test_id = (
                    element.get_attribute("data-testid")
                    or element.get_attribute("data-test")
                )
                placeholder = element.get_attribute("placeholder")
                text = element.text.strip()

                attributes = [
                    element_id,
                    name,
                    aria_label,
                    test_id,
                    placeholder,
                    text
                ]

                attributes = [
                    attr.strip()
                    for attr in attributes
                    if attr and attr.strip()
                ]

                score = 0

                # Compare against the failed locator value.
                for attribute in attributes:
                    score = max(
                        score,
                        self._similarity(
                            value,
                            attribute
                        )
                    )

                # If expected text is available,
                # use it as an additional signal.
                if expected_text and text:
                    score = max(
                        score,
                        self._similarity(
                            expected_text,
                            text
                        )
                    )

                if score >= 0.45:
                    candidates.append(
                        (
                            score,
                            element
                        )
                    )

            except Exception:
                continue

        if not candidates:
            return None

        candidates.sort(
            key=lambda item: item[0],
            reverse=True
        )

        best_element = candidates[0][1]

        return self._build_best_locator(
            best_element
        )

    def _build_best_locator(
        self,
        element
    ) -> str | None:

        test_id = (
            element.get_attribute("data-testid")
            or element.get_attribute("data-test")
        )

        if test_id:
            return f"By.CSS_SELECTOR: [data-testid='{test_id}']"

        element_id = element.get_attribute("id")

        if element_id:
            return f"By.ID: {element_id}"

        name = element.get_attribute("name")

        if name:
            return f"By.NAME: {name}"

        aria_label = element.get_attribute("aria-label")

        if aria_label:
            return (
                "By.CSS_SELECTOR: "
                f"[aria-label='{aria_label}']"
            )

        placeholder = element.get_attribute("placeholder")

        if placeholder:
            return (
                "By.CSS_SELECTOR: "
                f"[placeholder='{placeholder}']"
            )

        text = element.text.strip()

        if text:
            return (
                "By.XPATH: "
                f"//*[normalize-space(text())="
                f"'{text}']"
            )

        return None

    def _parse_locator(
        self,
        locator: str
    ) -> tuple[str, str]:

        if ":" not in locator:
            return "", locator

        strategy, value = locator.split(
            ":",
            1
        )

        return (
            strategy.strip(),
            value.strip()
        )

    def _similarity(
        self,
        first: str,
        second: str
    ) -> float:

        return SequenceMatcher(
            None,
            first.lower(),
            second.lower()
        ).ratio()