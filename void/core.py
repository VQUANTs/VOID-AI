from .config import Config
from .models import ModelEngine
from .memory import Memory
from .tools.web import WebSearch
from .context import ContextEngine
from .tools.registry import ToolRegistry
from .agents import Agent
from .tasks import TaskManager
import logging

logger = logging.getLogger(__name__)


class VoidCore:

    def __init__(self):
        self.model = ModelEngine()
        self.memory = Memory()
        self.web = WebSearch()
        self.context = ContextEngine(Config.CONTEXT_MAX_MESSAGES, Config.CONTEXT_MAX_CHARS)

        # Agent/task execution shares the same model, memory, web backend,
        # and uploaded-file tool context as the core.
        self.tools = ToolRegistry(memory=self.memory, web=self.web)
        self.agent = Agent(self.model, max_steps=8, tool_registry=self.tools)
        self.tasks = TaskManager(self.agent, max_steps=12)

    # --------------------------------------------------
    # Web detection
    # --------------------------------------------------

    def needs_web(self, text):
        triggers = [
            "search the web",
            "search online",
            "look it up",
            "latest",
            "current",
            "today",
            "recent",
            "news",
            "what is the newest",
            "what is the latest"
        ]

        text = text.lower()

        return any(
            x in text
            for x in triggers
        )

    # --------------------------------------------------
    # Memory retrieval
    # --------------------------------------------------

    def retrieve_memory(self, user_text):

        memories = []
        knowledge = []

        words = [
            word.strip(
                ".,!?;:\"'()[]{}"
            )
            for word in user_text.lower().split()
        ]

        ignored = {
            "the", "and", "for", "with",
            "that", "this", "what", "how",
            "why", "can", "you", "are",
            "is", "to", "a", "an", "of",
            "in", "on", "my", "me", "i"
        }

        search_terms = [
            word
            for word in words
            if len(word) >= 4
            and word not in ignored
        ]

        search_terms = search_terms[:5]

        seen_memory = set()
        seen_knowledge = set()

        for term in search_terms:

            try:
                results = self.memory.search_memory(
                    term,
                    limit=5
                )

                for row in results:

                    memory_id = row[0]

                    if memory_id not in seen_memory:
                        seen_memory.add(memory_id)
                        memories.append(row)

            except Exception as exc:
                logger.warning("Memory search failed for term %r: %s", term, exc)

            try:
                results = self.memory.search_knowledge(
                    term,
                    limit=5
                )

                for row in results:

                    knowledge_id = row[0]

                    if knowledge_id not in seen_knowledge:
                        seen_knowledge.add(knowledge_id)
                        knowledge.append(row)

            except Exception as exc:
                logger.warning("Knowledge search failed for term %r: %s", term, exc)

        return memories[:10], knowledge[:10]

    # --------------------------------------------------
    # Build model context
    # --------------------------------------------------

    def build_messages(self, user_text, conversation_id="default"):
        memories, knowledge = self.retrieve_memory(user_text)
        retrieved = []

        for row in memories:
            retrieved.append(
                f"[Memory {row[0]}] category={row[1]} importance={row[3]}\n{row[2]}"
            )

        for row in knowledge:
            retrieved.append(
                f"[Knowledge {row[0]}] title={row[1]} category={row[4]}\n"
                f"source={row[3]}\n{row[2]}"
            )

        history = [
            {"role": role, "content": content}
            for role, content in self.memory.recent(Config.CONTEXT_MAX_MESSAGES, conversation_id)
        ]
        return self.context.build(
            Config.SYSTEM_PROMPT,
            history,
            {"role": "user", "content": user_text},
            retrieved_context=retrieved,
        )

    # --------------------------------------------------
    # Extract model answer
    # --------------------------------------------------

    @staticmethod
    def extract_answer(message):

        if not isinstance(message, dict):
            return None

        content = message.get("content")

        if isinstance(content, str) and content.strip():
            return content.strip()

        if isinstance(content, list):

            parts = []

            for item in content:

                if isinstance(item, str) and item.strip():
                    parts.append(item.strip())

                elif isinstance(item, dict):

                    text = item.get("text")

                    if isinstance(text, str) and text.strip():
                        parts.append(text.strip())

            answer = "\\n".join(parts).strip()

            if answer:
                return answer

        reasoning = message.get("reasoning")

        if isinstance(reasoning, str) and reasoning.strip():
            return reasoning.strip()

        return None

    # --------------------------------------------------
    # Ask VOID about an image
    # --------------------------------------------------

    def ask_image(
        self,
        image_bytes,
        mime_type,
        prompt,
        conversation_id="default"
    ):

        if not prompt:
            prompt = (
                "Analyze this image carefully and explain "
                "what is visible in it."
            )

        self.memory.add(
            "user",
            "[IMAGE] " + prompt,
            conversation_id
        )

        try:

            response = self.model.chat_with_image(
                image_bytes,
                mime_type,
                prompt
            )

        except Exception as e:

            raise RuntimeError(
                f"Image model request failed: {e}"
            )

        try:

            response.raise_for_status()

        except Exception as e:

            try:
                error_data = response.json()
            except Exception:
                error_data = response.text

            raise RuntimeError(
                f"Image model HTTP error: {e}\n"
                f"Details: {error_data}"
            )

        try:

            data = response.json()

        except Exception as e:

            raise RuntimeError(
                f"Invalid JSON response from image model: {e}\n"
                f"Raw response: {response.text[:2000]}"
            )

        if "choices" not in data or not data["choices"]:
            raise RuntimeError(
                "Image model returned no usable choices."
            )

        message = data["choices"][0].get(
            "message",
            {}
        )

        answer = self.extract_answer(message)

        if not answer:
            raise RuntimeError(
                "Image model returned an empty answer."
            )

        self.memory.add(
            "assistant",
            answer,
            conversation_id
        )

        return answer

    # --------------------------------------------------
    # Generate an image
    # --------------------------------------------------

    def ask_image_generation(
        self,
        prompt,
        conversation_id="default",
        model=None
    ):

        if not prompt or not prompt.strip():
            raise RuntimeError(
                "Image generation prompt cannot be empty."
            )

        prompt = prompt.strip()

        self.memory.add(
            "user",
            "[IMAGE GENERATION] " + prompt,
            conversation_id
        )

        try:

            image_bytes = self.model.generate_image(
                prompt, model=model
            )

        except Exception as e:

            raise RuntimeError(
                f"Image generation failed: {e}"
            )

        if not image_bytes:
            raise RuntimeError(
                "Image generation returned empty data."
            )

        self.memory.add(
            "assistant",
            "[IMAGE GENERATED] " + prompt,
            conversation_id
        )

        return image_bytes

    # --------------------------------------------------
    # Ask VOID about a video
    # --------------------------------------------------

    def ask_video(
        self,
        video_bytes,
        mime_type,
        prompt,
        conversation_id="default"
    ):

        if not prompt:
            prompt = (
                "Analyze this video carefully. "
                "Describe the important visual and audio "
                "events, explain what is happening, and "
                "include timestamps when useful."
            )

        self.memory.add(
            "user",
            "[VIDEO] " + prompt,
            conversation_id
        )

        try:

            answer = self.model.chat_with_video(
                video_bytes,
                mime_type,
                prompt
            )

        except Exception as e:

            raise RuntimeError(
                f"Video model request failed: {e}"
            )

        if not answer:
            raise RuntimeError(
                "Video model returned an empty answer."
            )

        self.memory.add(
            "assistant",
            answer,
            conversation_id
        )

        return answer

    # --------------------------------------------------
    # Agent / task execution
    # --------------------------------------------------

    def run_agent(self, task, conversation_id="default"):
        if not isinstance(task, str) or not task.strip():
            raise ValueError("task is required")
        messages = [
            {"role": "system", "content": Config.SYSTEM_PROMPT},
            *self.build_messages(task.strip(), conversation_id),
        ]
        answer = self.agent.run(messages)
        self.memory.add("user", "[AGENT] " + task.strip(), conversation_id)
        self.memory.add("assistant", answer, conversation_id)
        return answer

    def run_task(self, description, conversation_id="default"):
        if not isinstance(description, str) or not description.strip():
            raise ValueError("description is required")
        task = self.tasks.run(description.strip(), conversation_id=conversation_id)
        if task.get("result"):
            self.memory.add("user", "[TASK] " + description.strip(), conversation_id)
            self.memory.add("assistant", task["result"], conversation_id)
        return task

    # --------------------------------------------------
    # Ask VOID with an externally supplied message history
    # --------------------------------------------------

    def ask_messages(self, messages, conversation_id="default", model=None, temperature=0.7, max_tokens=None):
        if not isinstance(messages, list) or not messages:
            raise ValueError("messages is required")
        normalized = []
        for item in messages:
            if not isinstance(item, dict):
                raise ValueError("each message must be an object")
            role = item.get("role")
            content = item.get("content")
            if not isinstance(role, str) or not role.strip():
                raise ValueError("message role is required")
            if not isinstance(content, (str, list, dict)):
                raise ValueError("message content must be text or structured content")
            normalized.append(dict(item))
        last_user = next((m.get("content") for m in reversed(normalized) if m.get("role") == "user"), None)
        if not isinstance(last_user, str) or not last_user.strip():
            raise ValueError("a user message is required")
        cid = str(conversation_id or "default")
        # Keep the external history as the model context, while recording the
        # user turn exactly once in VOID memory for subsequent native chats.
        response = self.model.chat(normalized, model=model, stream=False, temperature=temperature, max_tokens=max_tokens)
        response.raise_for_status()
        data = response.json()
        if not data.get("choices"):
            raise RuntimeError("Model returned no choices")
        message = data["choices"][0].get("message", {})
        answer = self.extract_answer(message)
        if not answer:
            raise RuntimeError("Model returned no usable text content")
        self.memory.add("user", last_user.strip(), cid)
        self.memory.add("assistant", answer, cid)
        return answer

    # --------------------------------------------------
    # Ask VOID
    # --------------------------------------------------

    def ask(self, user_text, conversation_id="default", model=None, temperature=0.7, max_tokens=None):

        if not isinstance(user_text, str) or not user_text.strip():
            raise ValueError("user_text is required")

        # Build context from prior turns first. The current user message is
        # appended by build_messages(), then persisted exactly once below.
        messages = self.build_messages(
            user_text.strip(),
            conversation_id
        )

        self.memory.add(
            "user",
            user_text.strip(),
            conversation_id
        )

        # --------------------------------------------------
        # Web research
        # --------------------------------------------------

        if self.needs_web(user_text):

            try:

                results = self.web.search(
                    user_text
                )

                if results:

                    context = "\n\n".join(
                        f"TITLE: {r['title']}\n"
                        f"URL: {r['url']}\n"
                        f"CONTENT:\n"
                        f"{r['content'][:4000]}"
                        for r in results
                    )

                    messages.insert(
                        1,
                        {
                            "role": "system",
                            "content":
                            "WEB RESEARCH RESULTS:\n\n"
                            + context
                            + """

Use these sources when answering.

Distinguish information found in the
sources from your own reasoning.

Do not invent citations or source facts.
"""
                        }
                    )

            except Exception as e:

                print(
                    f"[WEB WARNING] {e}"
                )

        # --------------------------------------------------
        # Model request
        # --------------------------------------------------

        try:

            response = self.model.chat(
                messages,
                model=model,
                stream=False,
                temperature=temperature,
                max_tokens=max_tokens,
            )

        except Exception as e:

            raise RuntimeError(
                f"Model request failed: {e}"
            )

        # --------------------------------------------------
        # HTTP validation
        # --------------------------------------------------

        try:

            response.raise_for_status()

        except Exception as e:

            try:
                error_data = response.json()

            except Exception:
                error_data = response.text

            raise RuntimeError(
                f"Model HTTP error: {e}\n"
                f"Details: {error_data}"
            )

        # --------------------------------------------------
        # JSON validation
        # --------------------------------------------------

        try:

            data = response.json()

        except Exception as e:

            raise RuntimeError(
                f"Invalid JSON response from model: {e}\n"
                f"Raw response: "
                f"{response.text[:2000]}"
            )

        if "choices" not in data:

            raise RuntimeError(
                "Model returned no 'choices' field.\n"
                f"Response: {data}"
            )

        if not data["choices"]:

            raise RuntimeError(
                "Model returned an empty choices list.\n"
                f"Response: {data}"
            )

        choice = data["choices"][0]

        if "message" not in choice:

            raise RuntimeError(
                "Model response has no message field.\n"
                f"Response: {data}"
            )

        message = choice["message"]

        answer = self.extract_answer(
            message
        )

        if answer is None:

            raise RuntimeError(
                "Model returned no usable text content.\n"
                f"Message: {message}"
            )

        # --------------------------------------------------
        # Save assistant response
        # --------------------------------------------------

        self.memory.add(
            "assistant",
            answer,
            conversation_id
        )

        return answer
