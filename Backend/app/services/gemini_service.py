from google import genai
from google.genai import types

import os
import time

from dotenv import load_dotenv


# =========================================================
# LOAD ENVIRONMENT VARIABLES
# =========================================================

load_dotenv()


# =========================================================
# GEMINI SETTINGS
# =========================================================

GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.8-flash",
)

MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 3
GEMINI_TIMEOUT_MILLISECONDS = 120000


# =========================================================
# GEMINI API KEY
# =========================================================

gemini_api_key = os.getenv(
    "GEMINI_API_KEY"
)

if not gemini_api_key:
    raise RuntimeError(
        "GEMINI_API_KEY is not configured"
    )


# =========================================================
# GEMINI CLIENT
# =========================================================

gemini_client = genai.Client(
    api_key=gemini_api_key,
    http_options=types.HttpOptions(
        timeout=GEMINI_TIMEOUT_MILLISECONDS,
        retry_options=types.HttpRetryOptions(
            attempts=1
        )
    )
)


# =========================================================
# GENERATE TEXT
# =========================================================

def generate_text(
    prompt: str
) -> str:

    if not prompt.strip():
        raise ValueError(
            "Gemini prompt cannot be empty"
        )

    last_error = None

    for attempt in range(
        1,
        MAX_RETRIES + 1
    ):

        try:

            interaction = gemini_client.interactions.create(
                model=GEMINI_MODEL,
                input=prompt,
                store=False
            )

            output_text = getattr(
                interaction,
                "output_text",
                None
            )

            if not output_text:
                raise RuntimeError(
                    "Gemini returned an empty response"
                )

            return output_text.strip()

        except Exception as error:

            last_error = error

            error_text = str(
                error
            ).lower()

            # =================================================
            # QUOTA / RATE LIMIT
            # =================================================

            if (
                "429" in error_text
                or "resource_exhausted" in error_text
                or "quota" in error_text
            ):
                raise RuntimeError(
                    "Gemini API quota exceeded. "
                    "Please check your Gemini API quota/billing "
                    "or wait until the quota resets."
                ) from error

            # =================================================
            # FINAL ATTEMPT
            # =================================================

            if attempt >= MAX_RETRIES:
                break

            # =================================================
            # RETRY TEMPORARY ERRORS
            # =================================================

            if (
                "timeout" in error_text
                or "timed out" in error_text
                or "connection" in error_text
                or "503" in error_text
                or "500" in error_text
            ):
                time.sleep(
                    RETRY_DELAY_SECONDS
                )
                continue

            break

    raise RuntimeError(
        f"Gemini request failed: {str(last_error)}"
    ) from last_error