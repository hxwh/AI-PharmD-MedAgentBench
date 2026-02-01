"""Utility function to call Google Gemini API."""

import os
from google import genai


def call_gemini(prompt: str, model: str = "gemini-2.0-flash-lite", **kwargs) -> str:
    """Call Google Gemini API with a prompt.

    Args:
        prompt: The text prompt to send to Gemini
        model: The model name to use (default: gemini-2.0-flash-lite)
        **kwargs: Additional parameters for the API call

    Returns:
        The response text from Gemini

    Raises:
        ValueError: If GOOGLE_API_KEY is not set
        Exception: If the API call fails
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY environment variable not set")

    # Create client with API key
    client = genai.Client(api_key=api_key)

    try:
        # Make the API call
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            **kwargs
        )

        return response.text
    finally:
        # Close the client
        client.close()