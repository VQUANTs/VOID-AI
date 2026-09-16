import os
from void.telegram_bot import TelegramBot


def test_telegram_command_aliases_and_models(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    bot = TelegramBot()
    sent = []
    bot.send_message = lambda chat_id, text: sent.append((chat_id, text))
    bot.ai.model.get_status = lambda: {"route":"fast", "model":"router9/test", "models":["router9/test","router9/other"], "provider":"router9"}
    assert bot.handle_command(1, "/model", "") is True
    assert bot.handle_command(1, "/models", "") is True
    assert "router9/test" in sent[-1][1]


def test_telegram_start_alias(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    bot = TelegramBot()
    sent=[]
    bot.send_message=lambda chat_id,text: sent.append(text)
    assert bot.handle_command(7, "/start@void_test_bot", "") is True
    assert "VOID CORE ONLINE" in sent[0]
