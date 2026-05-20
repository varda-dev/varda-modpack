from __future__ import annotations

from urllib.parse import urlsplit

from lib.common import fail


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
