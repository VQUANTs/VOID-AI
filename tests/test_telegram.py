from void.telegram_bot import TelegramBot


class FakeModel:
    def __init__(self):
        self.models = ["openrouter/openrouter/free", "openrouter/test-coder"]
        self.refreshes = 0

    def get_status(self):
        return {
            "route": "fast",
            "model": "openrouter/openrouter/free",
            "provider": "router9",
            "models": list(self.models),
            "total_usage": {"total_tokens": 42},
            "context_available": 8192,
        }

    def refresh_models(self, force=False):
        self.refreshes += 1
        if not self.models:
            self.models = ["openrouter/openrouter/free", "openrouter/test-coder"]
        return self.models


class FakeMemory:
    def clear(self, _chat_id):
        pass


class FakeAI:
    def __init__(self):
        self.model = FakeModel()
        self.memory = FakeMemory()


class FakeTools:
    def definitions(self):
        return []


class FakeAgent:
    tools = FakeTools()


def bot_for_test():
    bot = TelegramBot.__new__(TelegramBot)
    bot.ai = FakeAI()
    bot.agent = FakeAgent()
    bot.tasks = None
    bot.chat_models = {}
    bot.sent = []
    bot.send_message = lambda chat_id, text: bot.sent.append((chat_id, text))
    bot.send_typing = lambda _chat_id: None
    return bot


def test_telegram_model_selection_and_reset():
    bot = bot_for_test()
    assert bot.handle_command(7, "/model", "openrouter/test-coder")
    assert bot.chat_models["7"] == "openrouter/test-coder"
    assert bot.handle_command(7, "/model", "auto")
    assert "7" not in bot.chat_models


def test_telegram_models_command_refreshes_empty_registry():
    bot = bot_for_test()
    bot.ai.model.models = []
    assert bot.handle_command(7, "/models")
    assert bot.ai.model.refreshes == 1
    assert "openrouter/test-coder" in bot.sent[-1][1]


def test_telegram_status_includes_models_tokens_context():
    bot = bot_for_test()
    assert bot.handle_command(7, "/status")
    message = bot.sent[-1][1]
    assert "MODELS" in message
    assert "TOKENS" in message
    assert "CONTEXT" in message
