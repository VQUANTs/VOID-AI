import json

from ..tools.registry import ToolRegistry


class Agent:

    def __init__(
        self,
        model_engine,
        max_steps=8
    ):
        self.model = model_engine
        self.tools = ToolRegistry()
        self.max_steps = max_steps

    def run(self, messages):

        for step in range(self.max_steps):

            response = self.model.chat_with_tools(
                messages,
                self.tools.definitions()
            )

            data = response.json()

            message = self.model.extract_message(data)
            tool_calls = self.model.extract_tool_calls(data)

            # -------------------------------
            # FINAL ANSWER
            # -------------------------------

            if not tool_calls:

                content = message.get("content")

                if isinstance(content, str):
                    content = content.strip()

                if content:
                    return content

                reasoning = message.get(
                    "reasoning",
                    ""
                )

                if isinstance(reasoning, str):
                    reasoning = reasoning.strip()

                # Some reasoning models may emit an
                # intermediate reasoning-only message.
                # Do not expose internal reasoning as the
                # final answer. Give the model another turn
                # so it can continue the task.
                if reasoning:

                    messages.append({
                        "role": "assistant",
                        "content": ""
                    })

                    messages.append({
                        "role": "user",
                        "content": (
                            "Continue the task. "
                            "Use the available tools when "
                            "needed, then provide the final "
                            "answer."
                        )
                    })

                    continue

                raise RuntimeError(
                    "Model returned no text content "
                    "and no tool calls.\n"
                    f"Message: {message}"
                )

            # -------------------------------
            # PRESERVE ASSISTANT MESSAGE
            # -------------------------------

            # Preserve the complete provider message.
            # Some reasoning/tool-calling models require
            # additional fields such as "reasoning" on the
            # assistant turn.
            assistant_message = dict(message)

            assistant_message["role"] = "assistant"
            assistant_message["tool_calls"] = tool_calls

            messages.append(assistant_message)

            # -------------------------------
            # EXECUTE TOOLS
            # -------------------------------

            for call in tool_calls:

                call_id = call.get("id")

                function = call.get(
                    "function",
                    {}
                )

                name = function.get("name")

                try:

                    arguments = (
                        self.model
                        .parse_tool_arguments(call)
                    )

                    result = self.tools.execute(
                        name,
                        arguments
                    )

                    content = (
                        self.tools.serialize(result)
                    )

                except Exception as error:

                    content = json.dumps({
                        "error": str(error)
                    })

                messages.append({
                    "role": "tool",
                    "tool_call_id": call_id,
                    "content": content
                })

        raise RuntimeError(
            "Agent stopped after "
            f"{self.max_steps} tool steps."
        )
