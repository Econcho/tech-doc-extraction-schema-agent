from __future__ import annotations

import dataclasses
import enum
import inspect
import json
from pathlib import Path
from typing import Any, Callable

from langextract.core.data import CharInterval
from residual_info_agents.domain.tools.tool_request import ToolRequest
from residual_info_agents.domain.tools.tool_result import ToolResult
from residual_info_agents.tools.get_extraction_result_of_neighbor_text import (
    get_extraction_result_of_neighbor_text,
)
from residual_info_agents.tools.get_neighbor_text_of_resblocks import (
    get_neighbor_text_of_resblocks,
)
from residual_info_agents.tools.get_original_text_from_heading_tree import (
    get_original_text_from_heading_tree,
)


class ToolHandler:
  """Dispatches OpenAI tool calls using a TOOLS.json registry."""

  def __init__(self, tools_json: str | Path | list[dict[str, Any]] | None = None):
    self._tools: dict[str, Callable[..., Any]] = {
        "get_neighbor_text_of_resblocks": get_neighbor_text_of_resblocks,
        "get_extraction_result_of_neighbor_text": (
            get_extraction_result_of_neighbor_text
        ),
        "get_original_text_from_heading_tree": (
            get_original_text_from_heading_tree
        ),
    }
    self._tool_schemas = self._load_tool_schemas(tools_json)
    self._validate_registered_tools()

  def handle_tool_call(
      self,
      tool_request: ToolRequest,
  ) -> ToolResult:
    """Handles one internal tool request and returns a ToolResult object.

    Request arguments are filtered by the called tool's schema. Arguments not
    declared by the tool schema are ignored.
    """

    tool_use_id = tool_request.tool_use_id
    try:
      tool_name = tool_request.tool_name
      self._validate_tool_name(tool_name)
      arguments = self._build_tool_arguments(tool_name, tool_request.args)

      result = self._tools[tool_name](**arguments)
      return self._build_tool_result(tool_use_id, result)
    except Exception as exc:  # pylint: disable=broad-exception-caught
      return self._build_tool_result(
          tool_use_id,
          {
              "error": {
                  "type": type(exc).__name__,
                  "message": str(exc),
              }
          },
      )

  def handle_tool_call_with_raw_output(
      self,
      tool_request: ToolRequest,
  ) -> Any:
    """Handles one internal tool request and returns the raw tool output."""

    tool_name = tool_request.tool_name
    self._validate_tool_name(tool_name)
    arguments = self._build_tool_arguments(tool_name, tool_request.args)
    return self._tools[tool_name](**arguments)

  def _validate_tool_name(self, tool_name: str) -> None:
    if tool_name not in self._tool_schemas:
      raise ValueError(f"Tool is not registered in TOOLS.json: {tool_name}")
    if tool_name not in self._tools:
      raise ValueError(f"Tool has no local handler: {tool_name}")

  def _select_registered_arguments(
      self,
      tool_name: str,
      arguments: dict[str, Any],
  ) -> dict[str, Any]:
    properties = self._schema_properties(tool_name)
    return {
        name: value
        for name, value in arguments.items()
        if name in properties
    }

  def _build_tool_arguments(
      self,
      tool_name: str,
      arguments: dict[str, Any],
  ) -> dict[str, Any]:
    schema_arguments = self._select_registered_arguments(tool_name, arguments)
    self._validate_arguments(tool_name, schema_arguments)
    return {
        **schema_arguments,
        **self._select_runtime_arguments(tool_name, arguments),
    }

  def _select_runtime_arguments(
      self,
      tool_name: str,
      arguments: dict[str, Any],
  ) -> dict[str, Any]:
    """Selects runtime-injected arguments hidden from the OpenAI schema."""

    visible_names = set(self._schema_properties(tool_name))
    signature = inspect.signature(self._tools[tool_name])
    accepted_names = {
        name
        for name, parameter in signature.parameters.items()
        if parameter.kind in (
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            inspect.Parameter.KEYWORD_ONLY,
        )
    }
    return {
        name: value
        for name, value in arguments.items()
        if name not in visible_names and name in accepted_names
    }

  def _validate_arguments(
      self,
      tool_name: str,
      arguments: dict[str, Any],
  ) -> None:
    schema = self._parameters_schema(tool_name)
    properties = self._schema_properties(tool_name)
    required = schema.get("required", [])

    if not isinstance(required, list):
      raise ValueError(f"Invalid required list for tool: {tool_name}")

    missing = [name for name in required if name not in arguments]
    if missing:
      raise ValueError(
          f"Missing required arguments for tool {tool_name}: {missing}"
      )

    if schema.get("additionalProperties") is False:
      extra_names = sorted(set(arguments) - set(properties))
      if extra_names:
        raise ValueError(
            f"Unexpected arguments for tool {tool_name}: {extra_names}"
        )

    for name, value in arguments.items():
      if name in properties:
        self._validate_value(name, value, properties[name])

  def _validate_value(
      self,
      name: str,
      value: Any,
      schema: dict[str, Any],
  ) -> None:
    if "oneOf" in schema:
      variants = schema.get("oneOf")
      if not isinstance(variants, list):
        raise ValueError(f"Invalid oneOf schema for argument: {name}")
      errors = []
      for variant in variants:
        try:
          self._validate_value(name, value, variant)
          return
        except ValueError as exc:
          errors.append(str(exc))
      raise ValueError(
          f"Argument {name!r} does not match any oneOf schema: {errors}"
      )

    json_type = schema.get("type")
    if json_type is None:
      return

    if json_type == "string":
      if not isinstance(value, (str, Path)):
        raise ValueError(f"Argument {name!r} must be a string.")
    elif json_type == "object":
      if not isinstance(value, dict):
        raise ValueError(f"Argument {name!r} must be an object.")
    elif json_type == "array":
      if not isinstance(value, list):
        raise ValueError(f"Argument {name!r} must be an array.")
      self._validate_array_items(name, value, schema)
    elif json_type == "integer":
      if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"Argument {name!r} must be an integer.")
    elif json_type == "boolean":
      if not isinstance(value, bool):
        raise ValueError(f"Argument {name!r} must be a boolean.")
    elif json_type == "number":
      if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"Argument {name!r} must be a number.")
    else:
      raise ValueError(f"Unsupported JSON schema type: {json_type}")

    enum_values = schema.get("enum")
    if enum_values is not None and value not in enum_values:
      raise ValueError(
          f"Argument {name!r} must be one of {enum_values}, got {value!r}."
      )

  def _validate_array_items(
      self,
      name: str,
      values: list[Any],
      schema: dict[str, Any],
  ) -> None:
    item_schema = schema.get("items")
    if item_schema is None:
      return
    if not isinstance(item_schema, dict):
      raise ValueError(f"Invalid items schema for argument: {name}")
    for index, item in enumerate(values):
      self._validate_value(f"{name}[{index}]", item, item_schema)

  def _parameters_schema(self, tool_name: str) -> dict[str, Any]:
    schema = self._tool_schemas[tool_name]
    function_schema = schema.get("function")
    if not isinstance(function_schema, dict):
      raise ValueError(f"Invalid function schema for tool: {tool_name}")
    parameters = function_schema.get("parameters", {})
    if not isinstance(parameters, dict):
      raise ValueError(f"Invalid parameters schema for tool: {tool_name}")
    return parameters

  def _schema_properties(self, tool_name: str) -> dict[str, dict[str, Any]]:
    parameters = self._parameters_schema(tool_name)
    properties = parameters.get("properties", {})
    if not isinstance(properties, dict):
      raise ValueError(f"Invalid properties schema for tool: {tool_name}")
    return {
        name: schema
        for name, schema in properties.items()
        if isinstance(schema, dict)
    }

  @staticmethod
  def _load_tool_schemas(
      tools_json: str | Path | list[dict[str, Any]] | None,
  ) -> dict[str, dict[str, Any]]:
    if tools_json is None:
      tools_json = Path(__file__).with_name("TOOLS.json")

    if isinstance(tools_json, list):
      registry = tools_json
    else:
      registry = json.loads(Path(tools_json).read_text(encoding="utf-8"))

    if not isinstance(registry, list):
      raise ValueError("TOOLS.json must contain a list of tool schemas.")

    schemas: dict[str, dict[str, Any]] = {}
    for tool_schema in registry:
      if not isinstance(tool_schema, dict):
        raise ValueError("Every tool schema must be an object.")
      function_schema = tool_schema.get("function")
      if not isinstance(function_schema, dict):
        raise ValueError("Every tool schema must contain function.")
      tool_name = function_schema.get("name")
      if not isinstance(tool_name, str):
        raise ValueError("Every tool schema function.name must be a string.")
      schemas[tool_name] = tool_schema
    return schemas

  def _validate_registered_tools(self) -> None:
    unknown_to_handler = set(self._tool_schemas) - set(self._tools)
    if unknown_to_handler:
      raise ValueError(
          "Tools are registered but have no local handler: "
          f"{sorted(unknown_to_handler)}"
      )

  def _build_tool_result(self, tool_use_id: str, result: Any) -> ToolResult:
    return ToolResult(
        tool_use_id=tool_use_id,
        result=json.dumps(
            self._to_jsonable(result),
            ensure_ascii=False,
            indent=2,
        ),
    )

  @classmethod
  def _to_jsonable(cls, value: Any) -> Any:
    if dataclasses.is_dataclass(value):
      return cls._to_jsonable(dataclasses.asdict(value))
    if isinstance(value, CharInterval):
      return {
          "start_pos": value.start_pos,
          "end_pos": value.end_pos,
      }
    if isinstance(value, enum.Enum):
      return value.value
    if isinstance(value, Path):
      return str(value)
    if isinstance(value, dict):
      return {
          str(key): cls._to_jsonable(item)
          for key, item in value.items()
      }
    if isinstance(value, (list, tuple)):
      return [cls._to_jsonable(item) for item in value]
    return value
