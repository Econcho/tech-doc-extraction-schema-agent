# Copyright 2025 Google LLC.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""FunHPC provider for LangExtract."""

from __future__ import annotations

import json
from urllib import error
from urllib import request

from langextract.core import base_model
from langextract.core import data
from langextract.core import exceptions
from langextract.core import schema
from langextract.core import types as core_types

try:
  from hook import hook as _hook_raw_output
except ImportError:

  def _hook_raw_output(*args, **kwargs) -> None:
    del args, kwargs


class FunHPCDeepseekLanguageModel(base_model.BaseLanguageModel):
  """LangExtract provider for the FunHPC chat-style completions API."""

  def __init__(
      self,
      model_id: str,
      api_key: str,
      base_url: str = "https://funhpc.com/v1/completions",
      format_type: data.FormatType = data.FormatType.JSON,
      temperature: float | None = None,
      use_response_format: bool = False,
      **kwargs,
  ) -> None:
    self.model_id = model_id
    self.api_key = api_key
    self.base_url = base_url
    self.format_type = format_type
    self.temperature = temperature
    self.use_response_format = use_response_format
    self._extra_kwargs = kwargs.copy()
    super().__init__(
        constraint=schema.Constraint(
            constraint_type=schema.ConstraintType.NONE,
        )
    )

  @property
  def requires_fence_output(self) -> bool:
    if self.format_type == data.FormatType.JSON:
      return False
    return super().requires_fence_output

  def _build_messages(self, prompt: str) -> list[dict[str, str]]:
    messages = [{"role": "user", "content": prompt}]
    if self.format_type == data.FormatType.JSON:
      messages.insert(
          0,
          {
              "role": "system",
              "content": (
                  "You are a helpful assistant that responds in JSON format."
              ),
          },
      )
    return messages

  def _call_api(self, prompt: str, config: dict) -> str:
    payload = {
        "model": self.model_id,
        "messages": self._build_messages(prompt),
    }

    temp = config.get("temperature", self.temperature)
    if temp is not None:
      payload["temperature"] = temp

    if self.format_type == data.FormatType.JSON:
      payload["json"] = True
      if self.use_response_format:
        payload["response_format"] = {"type": "json_object"}

    if (v := config.get("max_output_tokens")) is not None:
      payload["max_tokens"] = v
    for key in [
        "top_p",
        "frequency_penalty",
        "presence_penalty",
        "stop",
        "json",
        "response_format",
    ]:
      if (v := config.get(key)) is not None:
        payload[key] = v

    req = request.Request(
        self.base_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        },
        method="POST",
    )

    try:
      with request.urlopen(req) as response:
        body = response.read().decode("utf-8")
    except error.HTTPError as exc:
      detail = exc.read().decode("utf-8", errors="replace")
      raise exceptions.InferenceRuntimeError(
          "FunHPC API HTTP "
          f"{exc.code}: {detail}. "
          f"request_model={self.model_id}, request_url={self.base_url}",
          original=exc,
      ) from exc
    except error.URLError as exc:
      raise exceptions.InferenceRuntimeError(
          f"FunHPC API request failed: {exc.reason}",
          original=exc,
      ) from exc

    try:
      result = json.loads(body)
      choice = result["choices"][0]
      if "message" in choice and "content" in choice["message"]:
        output_text = choice["message"]["content"]
        _hook_raw_output(
            "funhpc.py-FunHPCDeepseekLanguageModel._call_api-output_text",
            output_text,
            note=f"model_id={self.model_id}",
            max_chars=8000,
        )
        return output_text
      if "text" in choice:
        output_text = choice["text"]
        _hook_raw_output(
            "funhpc.py-FunHPCDeepseekLanguageModel._call_api-output_text",
            output_text,
            note=f"model_id={self.model_id}",
            max_chars=8000,
        )
        return output_text
      raise KeyError("choices[0].message.content/text")
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
      raise exceptions.InferenceRuntimeError(
          f"Unexpected FunHPC API response: {body}",
          original=exc,
      ) from exc

  def infer(self, batch_prompts, **kwargs):
    config = self.merge_kwargs(kwargs)
    for prompt in batch_prompts:
      output_text = self._call_api(prompt, config)
      yield [core_types.ScoredOutput(score=1.0, output=output_text)]
