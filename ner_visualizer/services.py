from __future__ import annotations
from typing import Any
import json
import requests
import time
from .cache import get_cached_ner_result, set_cached_ner_result, set_timing_by_text


def send_ner_request(model_url: str, text: str, extra_args: dict[str, Any]) -> dict:
    cached = get_cached_ner_result(model_url, text, extra_args)
    if cached is not None:
        return cached

    start = time.perf_counter()
    try:
        response = requests.post(
            model_url,
            headers={"Content-Type": "application/json"},
            json={"text": text, **extra_args},
            timeout=30,
        )
    except requests.exceptions.ConnectionError as e:
        print(f"Could not reach model at {model_url}: {e}")
        return {}
    except Exception as e:
        print(f"Request to {model_url} failed: {e}")
        return {}

    if response.status_code > 299:
        try:
            error_response = json.loads(response.text)
            print(f"Unsuccessful request to {model_url}: {error_response.get('error', '')}")
        except json.JSONDecodeError:
            print(f"Unsuccessful request to {model_url}: {response.text}")
        return {}

    result = response.json()
    if isinstance(result, dict) and result:
        elapsed = time.perf_counter() - start
        set_cached_ner_result(model_url, text, extra_args, result)
        set_timing_by_text(model_url, text, elapsed)

    return result
