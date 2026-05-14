from __future__ import annotations

import http.client
import json
import sys
import time
from typing import Any
from urllib.parse import urlsplit

from lib.common import fail


class HttpRequestError(RuntimeError):
  def __init__(self, message: str, *, http_status: int | None = None):
    super().__init__(message)
    self.http_status = http_status


def request_url_parts(url: str, *, label: str = "URL") -> tuple[str, str, str]:
  parsed = urlsplit(url)

  if parsed.scheme not in {"http", "https"}:
    fail(f"Unsupported {label} scheme: {parsed.scheme}")

  if not parsed.netloc:
    fail(f"{label} is missing a host: {url}")

  path = parsed.path or "/"
  if parsed.query:
    path = f"{path}?{parsed.query}"

  return parsed.scheme, parsed.netloc, path


def response_body_to_text(body: Any) -> str:
  if body is None:
    return ""
  if isinstance(body, (dict, list)):
    return json.dumps(body, indent=2, ensure_ascii=False)
  if isinstance(body, bytes):
    return body.decode("utf-8", errors="replace")
  return str(body)


def parse_response_body(response: http.client.HTTPResponse, raw: bytes) -> Any:
  if not raw:
    return None

  content_type = (response.getheader("Content-Type") or "").lower()
  if "json" in content_type:
    try:
      return json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as err:
      raise HttpRequestError(
        f"HTTP response returned invalid JSON for status {response.status}: {err}"
      ) from err

  if "text/" in content_type or "charset=" in content_type:
    return raw.decode("utf-8", errors="replace")

  try:
    return raw.decode("utf-8")
  except UnicodeDecodeError:
    return raw


def retry_delay_for_attempt(
  attempt: int,
  *,
  base_delay: int = 5,
  retry_after: str | None = None,
) -> int:
  delay = base_delay * attempt
  if retry_after:
    try:
      delay = max(delay, int(retry_after))
    except ValueError:
      pass
  return delay


def http_request(
  method: str,
  url: str,
  *,
  headers: dict[str, str] | None = None,
  json_body: Any | None = None,
  raw_body: bytes | None = None,
  timeout: int = 120,
  retryable_statuses: set[int] | None = None,
  max_attempts: int = 1,
  retry_base_delay: int = 5,
  retry_label: str = "HTTP request",
) -> tuple[int, Any, dict[str, str]]:
  if json_body is not None and raw_body is not None:
    fail("http_request accepts either json_body or raw_body, not both")

  retryable_statuses = retryable_statuses or set()
  status = 0
  body: Any = None
  response_headers: dict[str, str] = {}
  scheme, host, path = request_url_parts(url)
  request_headers = dict(headers or {})

  if json_body is not None:
    raw_body = json.dumps(json_body, ensure_ascii=False).encode("utf-8")
    request_headers.setdefault("Content-Type", "application/json")

  if raw_body is not None:
    request_headers["Content-Length"] = str(len(raw_body))

  connection_class = (
    http.client.HTTPSConnection if scheme == "https" else http.client.HTTPConnection
  )

  for attempt in range(1, max_attempts + 1):
    connection = connection_class(host, timeout=timeout)

    try:
      connection.request(method, path, body=raw_body, headers=request_headers)
      response = connection.getresponse()
      raw = response.read()
      status = response.status
      body = parse_response_body(response, raw)
      response_headers = {key.lower(): value for key, value in response.headers.items()}
    except (OSError, http.client.HTTPException) as err:
      raise HttpRequestError(f"{retry_label} failed: {err}") from err
    finally:
      connection.close()

    if status not in retryable_statuses or attempt >= max_attempts:
      return status, body, response_headers

    delay = retry_delay_for_attempt(
      attempt,
      base_delay=retry_base_delay,
      retry_after=response_headers.get("retry-after"),
    )
    print(
      f"{retry_label} returned HTTP {status}; retrying in {delay}s.",
      file=sys.stderr,
    )
    time.sleep(delay)

  return status, body, response_headers
