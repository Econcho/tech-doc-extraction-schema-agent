import dataclasses
import enum
import json
from pathlib import Path
import re
import sys
from typing import Any

import yaml

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parents[2]))

from residual_info_agents.clients.openai_client import OpenAIClient
from residual_info_agents.domain.runtime.heading_runtime_context import (
    HeadingRuntimeContext,
)
from residual_info_agents.domain.runtime.resblock_runtime_info import (
    ResBlockRuntimeInfo,
)
from residual_info_agents.domain.runtime.triage_working_context import (
    TriageWorkingContext,
)
from residual_info_agents.domain.tools.tool_request import ToolRequest
from residual_info_agents.domain.tools.tool_result import ToolResult
from residual_info_agents.tools.tool_handler import ToolHandler


class TriageAgent:
    def __init__(
        self,
        config: Path,
        tools: Path,
    ):
        config_path = Path(config)
        tools_path = Path(tools)

        self.config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        self.skill = ""
        self.tools = json.loads(tools_path.read_text(encoding="utf-8"))
        self.model_name = self.config.get("model_name")
        self.client = self.build_client()
        self.toolhandler = self.build_toolhandler()
        self.static_context = self.build_static_context()
        self.working_context: TriageWorkingContext | None = None

    def build_client(self) -> Any:
        self.client = OpenAIClient(
            api_key=self.config.get("api_key"),
            base_url=self.config.get("base_url"),
        )
        return self.client

    def build_toolhandler(self) -> Any:
        return ToolHandler(self.tools)

    def build_static_context(self) -> str:
        """Builds prompt context that does not change during the loop."""

        self.skill = self._read_config_text("skill")
        schema_description = self._read_config_text("schema_description")
        self.static_context = (
            f"{self.skill}\n\n"
            "## Schema Description\n\n"
            f"{schema_description}"
        )
        return self.static_context

    def build_working_context(
        self,
        resinfo_json: str | Path,
    ) -> TriageWorkingContext:
        """Builds runtime context from residual-info JSON."""

        resinfo_path = Path(resinfo_json)
        resinfo_data = json.loads(resinfo_path.read_text(encoding="utf-8"))
        self.working_context = TriageWorkingContext(
            resblocks=[
                ResBlockRuntimeInfo(
                    block_id=int(block["block_id"]),
                    text=str(block.get("text", "")),
                    heading_tree=list(block.get("heading_tree", [])),
                )
                for block in resinfo_data.get("resblocks", [])
            ],
        )
        return self.working_context

    def build_messages(self) -> list[dict[str, Any]]:
        return [
            {
                "role": "user",
                "content": self._message_content(),
            },
        ]

    def build_tool_request(
        self,
        openai_tool_call: Any,
        **optional_parameters: Any,
    ) -> ToolRequest:
        """Wraps an OpenAI tool call as an internal ToolRequest."""

        tool_call_data = self._normalize_openai_tool_call(openai_tool_call)
        function = tool_call_data.get("function")
        if not isinstance(function, dict):
            raise ValueError("OpenAI tool call must contain function.")

        tool_name = function.get("name")
        if not isinstance(tool_name, str):
            raise ValueError("OpenAI tool call function.name must be a string.")

        args = self._parse_tool_arguments(function.get("arguments", {}))
        args.update(optional_parameters)
        return ToolRequest(
            tool_use_id=str(tool_call_data.get("id", "")),
            tool_name=tool_name,
            args=args,
        )

    def apply_tool_result_to_working_context(
        self,
        tool_request: ToolRequest,
        tool_result: ToolResult,
    ) -> None:
        """Stores tool evidence in block or heading runtime context."""

        if self.working_context is None:
            return

        result_data = json.loads(tool_result.result or "null")
        if isinstance(result_data, dict) and "error" in result_data:
            self._append_tool_result_to_requested_blocks(
                tool_request, tool_result
            )
            return

        if tool_request.tool_name == "get_original_text_from_heading_tree":
            for item in self._ensure_result_list(result_data):
                if not isinstance(item, dict):
                    continue
                heading_tree = item.get("heading_tree")
                content = item.get("content")
                if isinstance(heading_tree, list) and isinstance(content, str):
                    self._upsert_heading_context(
                        heading_tree=heading_tree,
                        content=content,
                        source_tool_use_id=tool_request.tool_use_id,
                    )
            self._decrease_tool_budget_for_requested_blocks(tool_request)
            return

        if tool_request.tool_name in {
            "get_neighbor_text_of_resblocks",
            "get_extraction_result_of_neighbor_text",
        }:
            for item in self._ensure_result_list(result_data):
                if not isinstance(item, dict):
                    continue
                block_id = item.get("resblock_id")
                if block_id is None:
                    continue
                self._append_tool_result_to_block(
                    block_id=int(block_id),
                    tool_result=self._tool_result_for_single_output(
                        tool_request, item
                    ),
                )

    def parse_and_save_conclusion(self, conclusion: str) -> list[str]:
        """Save conclusion JSON and return block ids included in this turn."""

        conclusion_data = self._parse_json_text(conclusion)
        new_conclusions = self._extract_conclusions(conclusion_data)
        block_ids = [
            str(item["block_id"])
            for item in new_conclusions
            if "block_id" in item
        ]

        conclusion_path = Path(".conlusions") / "conclusion.json"
        conclusion_path.parent.mkdir(parents=True, exist_ok=True)

        if (
            not conclusion_path.exists()
            or not conclusion_path.read_text(encoding="utf-8").strip()
        ):
            merged_data = {"conclusions": new_conclusions}
        else:
            existing_data = json.loads(
                conclusion_path.read_text(encoding="utf-8")
            )
            existing_conclusions = self._extract_conclusions(existing_data)
            merged_data = {
                "conclusions": existing_conclusions + new_conclusions
            }

        conclusion_path.write_text(
            json.dumps(merged_data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return block_ids

    def delete_blocks_by_ids(
        self,
        ids: list[str],
        message: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Remove resblocks whose block_id is in ids from runtime context."""

        id_set = {str(block_id) for block_id in ids}
        if self.working_context is None:
            return message

        self.working_context.resblocks = [
            block
            for block in self.working_context.resblocks
            if str(block.block_id) not in id_set
        ]

        for item in message:
            if item.get("role") == "user":
                item["content"] = self._message_content()
        return message

    def _message_content(self) -> str:
        return (
            f"{self.static_context}\n\n"
            "Residual Blocks Information: \n\n"
            f"{self._working_context_to_json()}"
        )

    def _working_context_to_json(self) -> str:
        return json.dumps(
            self._to_jsonable(self.working_context),
            ensure_ascii=False,
            indent=2,
        )

    def _read_config_text(self, config_key: str) -> str:
        value = self.config.get(config_key)
        if value is None:
            return ""

        path = Path(value)
        if path.exists():
            return path.read_text(encoding="utf-8")

        project_path = Path(__file__).resolve().parents[2] / path
        if project_path.exists():
            return project_path.read_text(encoding="utf-8")

        return str(value)

    def _append_tool_result_to_requested_blocks(
        self,
        tool_request: ToolRequest,
        tool_result: ToolResult,
    ) -> None:
        block_ids = tool_request.args.get("resblock_ids", [])
        if not isinstance(block_ids, list):
            return
        for block_id in block_ids:
            self._append_tool_result_to_block(int(block_id), tool_result)

    def _append_tool_result_to_block(
        self,
        block_id: int,
        tool_result: ToolResult,
    ) -> None:
        block = self._get_runtime_block_by_id(block_id)
        block.tool_results.append(tool_result)
        block.tool_budget_left = max(0, block.tool_budget_left - 1)

    def _decrease_tool_budget_for_requested_blocks(
        self,
        tool_request: ToolRequest,
    ) -> None:
        block_ids = tool_request.args.get("resblock_ids", [])
        if not isinstance(block_ids, list):
            return
        for block_id in block_ids:
            block = self._get_runtime_block_by_id(int(block_id))
            block.tool_budget_left = max(0, block.tool_budget_left - 1)

    def _get_runtime_block_by_id(self, block_id: int) -> ResBlockRuntimeInfo:
        if self.working_context is None:
            raise ValueError("working_context has not been built.")
        for block in self.working_context.resblocks:
            if block.block_id == block_id:
                return block
        raise ValueError(f"Unknown runtime block id: {block_id}")

    def _upsert_heading_context(
        self,
        heading_tree: list[str],
        content: str,
        source_tool_use_id: str,
    ) -> None:
        if self.working_context is None:
            return
        key = tuple(str(item) for item in heading_tree)
        for context in self.working_context.heading_contexts:
            if tuple(context.heading_tree) == key:
                return
        self.working_context.heading_contexts.append(
            HeadingRuntimeContext(
                heading_tree=[str(item) for item in heading_tree],
                content=content,
                source_tool_use_id=source_tool_use_id,
            )
        )

    def _tool_result_for_single_output(
        self,
        tool_request: ToolRequest,
        output: dict[str, Any],
    ) -> ToolResult:
        return ToolResult(
            tool_use_id=tool_request.tool_use_id,
            result=json.dumps(
                {
                    "tool_name": tool_request.tool_name,
                    "output": output,
                },
                ensure_ascii=False,
                indent=2,
            ),
        )

    @staticmethod
    def _ensure_result_list(result_data: Any) -> list[Any]:
        if isinstance(result_data, list):
            return result_data
        return [result_data]

    def _select_resblocks_for_tool_request(
        self,
        tool_request: ToolRequest,
        resblocks_data: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        requested_ids = tool_request.args.get("resblock_ids")
        if not isinstance(requested_ids, list):
            raise ValueError("Tool request args must contain resblock_ids list.")

        active_blocks = {
            block.block_id: block
            for block in (
                self.working_context.resblocks if self.working_context else []
            )
        }
        source_blocks = {
            int(block["block_id"]): block
            for block in resblocks_data
            if "block_id" in block
        }

        selected_blocks = []
        for raw_id in requested_ids:
            block_id = int(raw_id)
            runtime_block = active_blocks.get(block_id)
            if runtime_block is None:
                raise ValueError(
                    f"Tool request references inactive block: {block_id}"
                )
            if runtime_block.tool_budget_left <= 0:
                raise ValueError(f"Tool budget exhausted for block: {block_id}")
            if block_id not in source_blocks:
                raise ValueError(f"Residual source block not found: {block_id}")
            selected_blocks.append(source_blocks[block_id])
        return selected_blocks

    def _collect_tool_call_block_ids(self, tool_calls: list[Any]) -> set[str]:
        block_ids: set[str] = set()
        for tool_call in tool_calls:
            tool_call_data = self._normalize_openai_tool_call(tool_call)
            function = tool_call_data.get("function")
            if not isinstance(function, dict):
                continue
            args = self._parse_tool_arguments(function.get("arguments", {}))
            requested_ids = args.get("resblock_ids", [])
            if not isinstance(requested_ids, list):
                continue
            block_ids.update(str(block_id) for block_id in requested_ids)
        return block_ids

    def _extract_conclusion_ids(self, conclusion: str) -> list[str]:
        conclusion_data = self._parse_json_text(conclusion)
        conclusions = self._extract_conclusions(conclusion_data)
        return [
            str(item["block_id"])
            for item in conclusions
            if "block_id" in item
        ]

    @staticmethod
    def _normalize_openai_tool_call(openai_tool_call: Any) -> dict[str, Any]:
        if hasattr(openai_tool_call, "model_dump"):
            tool_call_data = openai_tool_call.model_dump()
            if isinstance(tool_call_data, dict):
                return tool_call_data
        if isinstance(openai_tool_call, dict):
            return openai_tool_call
        raise TypeError(
            f"Unsupported OpenAI tool call type: {type(openai_tool_call)!r}"
        )

    @staticmethod
    def _parse_tool_arguments(arguments: dict[str, Any] | str) -> dict[str, Any]:
        if isinstance(arguments, dict):
            return dict(arguments)
        if isinstance(arguments, str):
            parsed = json.loads(arguments) if arguments.strip() else {}
            if not isinstance(parsed, dict):
                raise ValueError("Tool arguments JSON must decode to an object.")
            return parsed
        raise TypeError(f"Unsupported tool arguments type: {type(arguments)!r}")

    @staticmethod
    def _parse_json_text(text: str) -> dict[str, Any] | list[Any]:
        """Parse raw JSON, including JSON wrapped in a Markdown code fence."""

        stripped_text = text.strip()
        fenced_match = re.search(
            r"```(?:json)?\s*(.*?)\s*```",
            stripped_text,
            flags=re.DOTALL,
        )
        if fenced_match:
            stripped_text = fenced_match.group(1).strip()
        return json.loads(stripped_text)

    @staticmethod
    def _extract_conclusions(
        data: dict[str, Any] | list[Any],
    ) -> list[dict[str, Any]]:
        """Normalize supported conclusion JSON shapes to a conclusion list."""

        if isinstance(data, dict):
            conclusions = data.get("conclusions", [])
        elif isinstance(data, list):
            conclusions = data
        else:
            raise ValueError("Conclusion JSON must be an object or a list.")

        if not isinstance(conclusions, list):
            raise ValueError(
                "Conclusion JSON field 'conclusions' must be a list."
            )
        return [dict(item) for item in conclusions if isinstance(item, dict)]

    @classmethod
    def _to_jsonable(cls, value: Any) -> Any:
        if dataclasses.is_dataclass(value):
            return cls._to_jsonable(dataclasses.asdict(value))
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

    def main_loop(
        self,
        resinfo_json: str | Path = None,
    ) -> dict[str, Any]:
        if not self.static_context:
            self.build_static_context()

        if resinfo_json is None:
            raise ValueError("resinfo_json must be provided")

        resinfo_path = Path(resinfo_json)
        resinfo_data = json.loads(resinfo_path.read_text(encoding="utf-8"))

        if self.working_context is None:
            self.build_working_context(resinfo_path)

        turn_num = 0
        max_turns = int(self.config.get("max_turns", 10))
        project_root = Path(__file__).resolve().parents[2]
        original_doc_ref = project_root / Path(
            resinfo_data["original_doc_ref"]
        )
        extraction_doc_ref = project_root / Path(
            resinfo_data["extraction_doc_ref"]
        )

        while self.working_context and self.working_context.resblocks:
            before_context = self._working_context_to_json()
            messages = self.build_messages()
            print(f"Turn {turn_num}")
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                response_format={"type": "json_object"},
                tools=self.tools,
            )
            content = response.choices[0].message.content
            print(f"Content: {content}")
            tool_calls = response.choices[0].message.tool_calls
            print(f"Tool calls: {tool_calls}")

            if content:
                ids = self._extract_conclusion_ids(content)
                tool_block_ids = self._collect_tool_call_block_ids(
                    tool_calls or []
                )
                overlap = set(ids) & tool_block_ids
                if overlap:
                    raise ValueError(
                        "Blocks cannot have both conclusion and tool call "
                        f"in the same turn: {sorted(overlap)}"
                    )
                ids = self.parse_and_save_conclusion(content)
                id_set = {str(block_id) for block_id in ids}
                self.working_context.resblocks = [
                    block
                    for block in self.working_context.resblocks
                    if str(block.block_id) not in id_set
                ]

            if tool_calls:
                for tool_call in tool_calls:
                    tool_request = self.build_tool_request(tool_call)
                    selected_resblocks = self._select_resblocks_for_tool_request(
                        tool_request,
                        resinfo_data.get("resblocks", []),
                    )
                    tool_request.args.update({
                        "doc_ref": original_doc_ref,
                        "extraction_doc_ref": extraction_doc_ref,
                        "resblocks": selected_resblocks,
                    })
                    tool_result = self.toolhandler.handle_tool_call(
                        tool_request
                    )
                    self.apply_tool_result_to_working_context(
                        tool_request, tool_result
                    )

            turn_num += 1
            if not content and not tool_calls:
                break
            if before_context == self._working_context_to_json():
                break
            if turn_num >= max_turns:
                break

        return self._to_jsonable(self.working_context)


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parents[2]
    triage_agent_dir = Path(__file__).resolve().parent

    agent = TriageAgent(
        config=triage_agent_dir / "config.yaml",
        tools=triage_agent_dir / "TOOLS.json",
    )
    result = agent.main_loop(
        resinfo_json=(
            project_root
            / "residual_info_agents"
            / "data"
            / "blocks_ignore_testcase.json"
        ),
    )
    print(result)
