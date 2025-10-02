"""HTTPX transport wrapper for logging raw OpenAI API requests/responses.

This module captures Layer 3: Raw HTTP calls to OpenAI API.
Intercepts at the transport layer to log complete request/response data.

Usage:
    from src.testing.mock_adapters.httpx_logging_transport import get_logging_transport

    # Configure OpenAI SDK to use logging transport
    embeddings = OpenAIEmbeddings(
        http_client=httpx.Client(transport=get_logging_transport())
    )
"""

import json
import time
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import uuid4

import httpx


class LoggingHTTPXTransport(httpx.HTTPTransport):
    """HTTPX transport that logs all OpenAI API requests/responses.

    Captures complete HTTP interactions:
    - Request: method, URL, headers, body
    - Response: status, headers, body
    - Metadata: timing, tokens, cost
    - Correlation: links to YAML fixtures and LangChain logs
    """

    def __init__(self, log_dir: Optional[str] = None, *args: Any, **kwargs: Any):
        """Initialize logging transport.

        Args:
            log_dir: Directory to save raw API logs
            *args, **kwargs: Passed to parent HTTPTransport
        """
        super().__init__(*args, **kwargs)

        if log_dir is None:
            log_dir = "tests/fixtures/mock_adapters/raw_api"

        self.log_dir = Path(log_dir)
        self.embeddings_dir = self.log_dir / "embeddings"
        self.chat_dir = self.log_dir / "chat"

        # Create directories
        self.embeddings_dir.mkdir(parents=True, exist_ok=True)
        self.chat_dir.mkdir(parents=True, exist_ok=True)

        # Store current correlation ID (set by RecordingWrapper)
        self._current_correlation_id: Optional[str] = None

    def set_correlation_id(self, correlation_id: str) -> None:
        """Set correlation ID for next request.

        Links this HTTP log to YAML fixture and LangChain log.

        Args:
            correlation_id: Unique ID shared across all 3 layers
        """
        self._current_correlation_id = correlation_id

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        """Intercept and log HTTP request/response.

        Args:
            request: HTTPX request object

        Returns:
            HTTPX response object
        """
        # Generate correlation ID if not set
        correlation_id = self._current_correlation_id or f"req_{uuid4().hex[:12]}"
        self._current_correlation_id = None  # Reset after use

        # Determine API type from URL
        url_str = str(request.url)
        if "/embeddings" in url_str:
            api_type = "embeddings"
            save_dir = self.embeddings_dir
        elif "/chat/completions" in url_str:
            api_type = "chat"
            save_dir = self.chat_dir
        else:
            api_type = "unknown"
            save_dir = self.log_dir

        # Parse request body
        request_body = {}
        if request.content:
            try:
                request_body = json.loads(request.content)
            except json.JSONDecodeError:
                request_body = {"_raw": request.content.decode("utf-8", errors="replace")}

        # Start timing
        start_time = time.time()

        # Call actual API
        response = super().handle_request(request)

        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000

        # Read response content (required for httpx streaming responses)
        response_content = response.read() if hasattr(response, "read") else response.content

        # Parse response body
        response_body = {}
        try:
            response_body = json.loads(response_content)
        except json.JSONDecodeError:
            response_body = {"_raw": response_content.decode("utf-8", errors="replace")}

        # Extract token usage and calculate cost
        usage = response_body.get("usage", {})
        model = request_body.get("model", "unknown")
        cost_usd = self._calculate_cost(usage, model, api_type)

        # Build log entry
        log_entry = {
            "correlation_id": correlation_id,
            "layer": "raw_openai_api",
            "timestamp": time.time(),
            "timestamp_iso": time.strftime("%Y-%m-%dT%H:%M:%S.%fZ", time.gmtime()),
            "api_type": api_type,
            "request": {
                "method": request.method,
                "url": str(request.url),
                "headers": {
                    k: v
                    for k, v in request.headers.items()
                    if k.lower() not in ["authorization", "api-key"]  # Redact secrets
                },
                "body": request_body,
            },
            "response": {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "body": response_body,
            },
            "metadata": {
                "duration_ms": round(duration_ms, 2),
                "tokens": {
                    "prompt": usage.get("prompt_tokens", 0),
                    "completion": usage.get("completion_tokens", 0),
                    "total": usage.get("total_tokens", 0),
                },
                "cost_usd": cost_usd,
                "model": model,
                "openai_request_id": response.headers.get("x-request-id", "unknown"),
            },
        }

        # Save to file
        log_file = save_dir / f"{correlation_id}.json"
        with open(log_file, "w") as f:
            json.dump(log_entry, f, indent=2)

        print(f"📡 [Layer 3] Raw API: {correlation_id} → {log_file}")

        return response

    def _calculate_cost(self, usage: Dict[str, int], model: str, api_type: str) -> float:
        """Calculate cost in USD for API call.

        Args:
            usage: Token usage dict (prompt_tokens, completion_tokens, total_tokens)
            model: Model name
            api_type: "embeddings" or "chat"

        Returns:
            Cost in USD (rounded to 8 decimals)
        """
        # Pricing as of October 2024
        pricing = {
            "text-embedding-3-small": {"input": 0.00002 / 1000},
            "text-embedding-3-large": {"input": 0.00013 / 1000},
            "text-embedding-ada-002": {"input": 0.00010 / 1000},
            "gpt-4o-mini": {"input": 0.150 / 1_000_000, "output": 0.600 / 1_000_000},
            "gpt-4o-mini-2024-07-18": {"input": 0.150 / 1_000_000, "output": 0.600 / 1_000_000},
            "gpt-4o": {"input": 2.50 / 1_000_000, "output": 10.00 / 1_000_000},
            "gpt-3.5-turbo": {"input": 0.50 / 1_000_000, "output": 1.50 / 1_000_000},
        }

        model_pricing = pricing.get(model, {"input": 0, "output": 0})

        if api_type == "embeddings":
            total_tokens = usage.get("total_tokens", 0)
            cost = total_tokens * model_pricing.get("input", 0)
        else:  # chat
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            input_cost = prompt_tokens * model_pricing.get("input", 0)
            output_cost = completion_tokens * model_pricing.get("output", 0)
            cost = input_cost + output_cost

        return round(cost, 8)


# Global instance
_logging_transport: Optional[LoggingHTTPXTransport] = None


def get_logging_transport() -> LoggingHTTPXTransport:
    """Get or create global logging transport instance."""
    global _logging_transport
    if _logging_transport is None:
        _logging_transport = LoggingHTTPXTransport()
    return _logging_transport
