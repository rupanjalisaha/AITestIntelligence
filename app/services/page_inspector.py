from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait

from app.models import PageInspectionResponse, PageElement


class PageInspector:

    def inspect(self, application_url: str) -> PageInspectionResponse:

        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-dev-shm-usage")

        driver = None

        try:
            driver = webdriver.Chrome(options=options)

            driver.set_page_load_timeout(30)

            driver.get(application_url)

            WebDriverWait(driver, 20).until(
                lambda d: d.execute_script(
                    "return document.readyState"
                ) == "complete"
            )

            elements = []

            interactive_elements = driver.find_elements(
                By.CSS_SELECTOR,
                """
                input,
                textarea,
                select,
                button,
                a,
                [role='button'],
                [role='textbox']
                """
            )

            for element in interactive_elements:

                try:
                    if not element.is_displayed():
                        continue

                    tag = element.tag_name

                    element_type = element.get_attribute("type")

                    text = (
                        element.text.strip()
                        if element.text
                        else ""
                    )

                    element_id = element.get_attribute("id")
                    name = element.get_attribute("name")
                    placeholder = element.get_attribute("placeholder")
                    aria_label = element.get_attribute("aria-label")

                    test_id = (
                        element.get_attribute("data-testid")
                        or element.get_attribute("data-test")
                    )

                    locator_candidates = []

                    if element_id:
                        locator_candidates.append(
                            f"By.ID: {element_id}"
                        )

                    if name:
                        locator_candidates.append(
                            f"By.NAME: {name}"
                        )

                    if test_id:
                        locator_candidates.append(
                            f"By.CSS_SELECTOR: [data-testid='{test_id}']"
                        )

                    if placeholder:
                        locator_candidates.append(
                            f"By.CSS_SELECTOR: "
                            f"[placeholder='{placeholder}']"
                        )

                    if aria_label:
                        locator_candidates.append(
                            f"By.CSS_SELECTOR: "
                            f"[aria-label='{aria_label}']"
                        )

                    if tag == "button" and text:
                        locator_candidates.append(
                            f"By.XPATH: //button[normalize-space()='{text}']"
                        )

                    if tag == "a" and text:
                        locator_candidates.append(
                            f"By.XPATH: //a[normalize-space()='{text}']"
                        )

                    elements.append(
                        PageElement(
                            tag=tag,
                            element_type=element_type,
                            text=text,
                            element_id=element_id,
                            name=name,
                            placeholder=placeholder,
                            aria_label=aria_label,
                            test_id=test_id,
                            locator_candidates=locator_candidates
                        )
                    )

                except WebDriverException:
                    continue

            return PageInspectionResponse(
                application_url=application_url,
                title=driver.title,
                elements=elements
            )

        except TimeoutException:
            raise RuntimeError(
                "Page inspection timed out while loading the application."
            )

        except WebDriverException as exc:
            raise RuntimeError(
                f"Unable to inspect application: {exc}"
            )

        finally:
            if driver:
                driver.quit()