import re


class TestDataResolver:

    def __init__(self):
        self.test_data = {
            "username": "standard_user",
            "password": "secret_sauce"
        }

    def resolve(self, value: str | None) -> str | None:

        if value is None:
            return None

        pattern = r"\{\{([^{}]+)\}\}"

        def replace(match):
            key = match.group(1).strip()

            if key not in self.test_data:
                raise ValueError(
                    f"Test data not found for key: {key}"
                )

            return self.test_data[key]

        return re.sub(
            pattern,
            replace,
            value
        )