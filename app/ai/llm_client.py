import json
import time

import requests

from app.config import settings


class LLMClient:
    """
    Client responsible for communicating with the Ollama LLM service.
    """

    OLLAMA_CONNECT_TIMEOUT = 10
    OLLAMA_READ_TIMEOUT = 300

    def __init__(self):
        self.base_url = settings.ollama_base_url
        self.model = settings.ollama_model

    def generate(self, prompt: str) -> str:
        """
        Send a prompt to Ollama and return the generated text.
        """

        url = f"{self.base_url}/api/generate"

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": True,
            "format": "json",
            "options": {
                "num_ctx": 4096,
                "num_predict": 700,
                "temperature": 0
            }
        }

        print("\n========== OLLAMA REQUEST STARTED ==========")
        print(f"Model: {self.model}")
        print(f"Prompt length: {len(prompt)} characters")
        print("Context: 4096")
        print("Max output tokens: 700")
        print("Temperature: 0")
        print(
            f"Timeout: {self.OLLAMA_READ_TIMEOUT} seconds"
        )

        start_time = time.time()

        generated_parts = []
        final_data = None

        try:
            with requests.post(
                url,
                json=payload,
                stream=True,
                timeout=(
                    self.OLLAMA_CONNECT_TIMEOUT,
                    self.OLLAMA_READ_TIMEOUT
                )
            ) as response:

                response.raise_for_status()

                for line in response.iter_lines(
                    decode_unicode=True
                ):
                    if not line:
                        continue

                    try:
                        data = json.loads(line)

                    except json.JSONDecodeError as exc:
                        raise RuntimeError(
                            "Invalid streaming response from Ollama: "
                            f"{exc}"
                        )

                    chunk = data.get(
                        "response",
                        ""
                    )

                    if chunk:
                        generated_parts.append(
                            chunk
                        )

                    final_data = data

                    if data.get("done") is True:
                        break

            elapsed = time.time() - start_time

            print(
                f"OLLAMA RESPONSE RECEIVED IN "
                f"{elapsed:.2f} SECONDS"
            )

            if final_data:

                prompt_tokens = final_data.get(
                    "prompt_eval_count"
                )

                generated_tokens = final_data.get(
                    "eval_count"
                )

                prompt_eval_duration = final_data.get(
                    "prompt_eval_duration"
                )

                eval_duration = final_data.get(
                    "eval_duration"
                )

                if prompt_tokens is not None:
                    print(
                        f"Prompt tokens: {prompt_tokens}"
                    )

                if generated_tokens is not None:
                    print(
                        f"Generated tokens: {generated_tokens}"
                    )

                if prompt_eval_duration is not None:
                    print(
                        "Prompt evaluation time: "
                        f"{prompt_eval_duration / 1_000_000_000:.2f}s"
                    )

                if eval_duration is not None:
                    print(
                        "Generation time: "
                        f"{eval_duration / 1_000_000_000:.2f}s"
                    )

            print(
                "============================================\n"
            )

            generated_text = "".join(
                generated_parts
            )

            if not generated_text:
                raise RuntimeError(
                    "Ollama returned an empty response."
                )

            return generated_text

        except requests.exceptions.ConnectionError:
            raise RuntimeError(
                "Unable to connect to Ollama. "
                "Make sure Ollama is running."
            )

        except requests.exceptions.Timeout:
            raise RuntimeError(
                "Ollama request timed out after "
                "300 seconds."
            )

        except requests.exceptions.RequestException as exc:
            raise RuntimeError(
                f"Ollama request failed: {exc}"
            )

    def generate_json(
        self,
        prompt: str
    ) -> dict:
        """
        Generate a JSON response from Ollama.
        """

        print(
            "\n========== GENERATE_JSON STARTED =========="
        )

        response = self.generate(prompt)

        print(
            "\n========== RAW LLM RESPONSE =========="
        )
        print(response)
        print(
            "======================================\n"
        )

        try:
            result = json.loads(response)

            print(
                "JSON parsing successful."
            )

            return result

        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"LLM returned invalid JSON: {exc}"
            )