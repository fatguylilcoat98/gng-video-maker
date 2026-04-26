"""
GNG Video Maker — The Good Neighbor Guard
Built by Christopher Hughes · Sacramento, CA
Created with the help of AI collaborators (Claude · GPT · Gemini · Groq · Perplexity)
Truth · Safety · We Got Your Back
"""

import logging
import os
import asyncio
import aiohttp
import json
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"

async def call_anthropic_api(
    prompt: str,
    model: str = "claude-3-5-sonnet-20241022",
    max_tokens: int = 4000,
    temperature: float = 0.3
) -> str:
    """
    Make an async call to the Anthropic API
    """
    if not ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY environment variable not set")

    headers = {
        "Content-Type": "application/json",
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01"
    }

    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ]
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                ANTHROPIC_API_URL,
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as response:

                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Anthropic API error {response.status}: {error_text}")
                    raise Exception(f"Anthropic API error: {response.status}")

                result = await response.json()
                return result["content"][0]["text"]

    except asyncio.TimeoutError:
        logger.error("Anthropic API call timed out")
        raise Exception("API call timed out")
    except Exception as e:
        logger.error(f"Error calling Anthropic API: {e}")
        raise

async def call_anthropic_with_retry(
    prompt: str,
    max_retries: int = 3,
    **kwargs
) -> str:
    """
    Call Anthropic API with retry logic
    """
    last_error = None

    for attempt in range(max_retries):
        try:
            logger.info(f"Anthropic API call attempt {attempt + 1}")
            result = await call_anthropic_api(prompt, **kwargs)
            return result

        except Exception as e:
            last_error = e
            logger.warning(f"Attempt {attempt + 1} failed: {e}")

            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff
                logger.info(f"Retrying in {wait_time} seconds...")
                await asyncio.sleep(wait_time)
            else:
                logger.error(f"All {max_retries} attempts failed")

    raise last_error

def validate_json_response(response: str, required_fields: list) -> bool:
    """
    Validate that a response contains valid JSON with required fields
    """
    try:
        data = json.loads(response)
        for field in required_fields:
            if field not in data:
                return False
        return True
    except (json.JSONDecodeError, TypeError):
        return False

async def call_anthropic_structured(
    prompt: str,
    required_fields: list,
    max_retries: int = 3,
    **kwargs
) -> Dict[Any, Any]:
    """
    Call Anthropic API and ensure structured JSON response
    """
    for attempt in range(max_retries):
        try:
            response = await call_anthropic_api(prompt, **kwargs)

            # Try to parse as JSON
            if validate_json_response(response, required_fields):
                return json.loads(response)

            # If not valid JSON, try to extract JSON from response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1

            if json_start >= 0 and json_end > json_start:
                json_content = response[json_start:json_end]
                if validate_json_response(json_content, required_fields):
                    return json.loads(json_content)

            logger.warning(f"Invalid JSON response on attempt {attempt + 1}")

        except Exception as e:
            logger.error(f"Structured API call failed on attempt {attempt + 1}: {e}")

        if attempt < max_retries - 1:
            await asyncio.sleep(2 ** attempt)

    raise Exception(f"Failed to get valid structured response after {max_retries} attempts")