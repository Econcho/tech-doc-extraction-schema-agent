from __future__ import annotations

from typing import Any


class OpenAIClient:
  """Thin OpenAI SDK wrapper compatible with TriageAgent.

  TriageAgent calls `client.chat.completions.create(...)`. This wrapper exposes
  the underlying OpenAI client's `chat` resource directly, so an OpenAIClient
  instance can be passed as the `client` argument without adapter code.
  """

  def __init__(
      self,
      api_key: str | None = None,
      base_url: str | None = None,
      **kwargs: Any,
  ) -> None:
    try:
      import openai  # pylint: disable=import-outside-toplevel
    except ImportError as exc:
      raise ImportError(
          "OpenAIClient requires the openai package. "
          'Install it with `pip install -e ".[openai]"`.'
      ) from exc

    self._client = openai.OpenAI(
        api_key=api_key,
        base_url=base_url,
        **kwargs,
    )

  @property
  def chat(self) -> Any:
    """Expose `OpenAI.chat` for direct Chat Completions calls."""

    return self._client.chat

  @property
  def raw_client(self) -> Any:
    """Return the underlying OpenAI SDK client."""

    return self._client
