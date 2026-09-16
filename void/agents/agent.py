import json
import time

from ..tools.registry import ToolRegistry


class Agent:
    """Bounded tool-calling agent loop."""

    def __init__(self, model_engine, max_steps=8, tool_timeout=None, tool_registry=None):
        self.model = model_engine
        self.tools = tool_registry or ToolRegistry()
        self.max_steps = max(1, int(max_steps))
        self.tool_timeout = tool_timeout

    def run(self, messages):
        if not isinstance(messages, list) or not messages:
            raise ValueError("Agent messages must be a non-empty list.")

        working = [dict(m) for m in messages]
        for _step in range(self.max_steps):
            response = self.model.chat_with_tools(
                working, self.tools.definitions()
            )
            data = response.json()
            message = self.model.extract_message(data)
            tool_calls = self.model.extract_tool_calls(data)

            if not tool_calls:
                content = message.get("content")
                if isinstance(content, list):
                    content = "\n".join(
                        x.get("text", "") if isinstance(x, dict) else str(x)
                        for x in content
                    )
                if isinstance(content, str) and content.strip():
                    return content.strip()
                raise RuntimeError("Model returned neither a final answer nor tool calls.")

            assistant_message = dict(message)
            assistant_message["role"] = "assistant"
            assistant_message["tool_calls"] = tool_calls
            working.append(assistant_message)

            for call_index, call in enumerate(tool_calls):
                call_id = call.get("id") or f"call_{_step}_{call_index}"
                function = call.get("function") or {}
                name = function.get("name")
                try:
                    arguments = self.model.parse_tool_arguments(call)
                    result = self.tools.execute(name, arguments)
                    content = self.tools.serialize(result)
                except Exception as error:
                    content = json.dumps({
                        "error": type(error).__name__,
                        "message": str(error),
                        "tool": name,
                    })
                working.append({
                    "role": "tool",
                    "tool_call_id": call_id,
                    "content": content,
                })

        raise RuntimeError(f"Agent stopped after {self.max_steps} steps without a final answer.")
