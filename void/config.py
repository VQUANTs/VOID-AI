import os


class Config:

    VERSION = "0.4.0"

    GEMINI_API_KEY = os.getenv(
        "GEMINI_API_KEY",
        ""
    )

    JINA_API_KEY = os.getenv(
        "JINA_API_KEY",
        ""
    )

    JINA_URL = "https://s.jina.ai/"

    GROQ_API_KEY = os.getenv(
        "GROQ_API_KEY",
        ""
    )

    GROQ_URL = (
        "https://api.groq.com/openai/v1/"
        "chat/completions"
    )

    GROQ_MODEL = "openai/gpt-oss-20b"


    GEMINI_URL = (
        "https://generativelanguage.googleapis.com/"
        "v1beta/openai/chat/completions"
    )

    GEMINI_MODEL = "gemini-3.6-flash"

    DEFAULT_MODEL = GEMINI_MODEL

    MODELS = {
        "fast": [
            GEMINI_MODEL
        ],
        "coding": [
            GEMINI_MODEL
        ],
        "reasoning": [
            GEMINI_MODEL
        ],
        "cyber": [
            GEMINI_MODEL
        ],
        "research": [
            GEMINI_MODEL
        ]
    }

    FALLBACK_MODEL = GEMINI_MODEL

    SYSTEM_PROMPT = """You are VOID CORE.

You are a serious AI research, engineering,
programming, and cybersecurity-learning assistant.

Core capabilities:
- general reasoning
- programming
- software engineering
- cybersecurity education
- defensive security
- authorized security research
- CTFs and isolated security labs
- web research
- technical analysis
- documentation
- system architecture
- code and log analysis

Be direct, technically precise, practical, and honest.

For cybersecurity:
- explain concepts deeply
- analyze code, logs, configurations, and vulnerabilities
- help construct isolated educational laboratories
- help with authorized testing
- distinguish authorized/laboratory activity from
  targeting real systems
- never assume authorization for an external target

Do not invent facts, commands, results, vulnerabilities,
or sources.

When web research is supplied, prioritize supplied sources
and distinguish sourced facts from your own reasoning.

When solving difficult technical problems:
1. Understand the problem.
2. Break it into components.
3. Choose the appropriate capability.
4. Produce the solution.
5. Check the result for obvious errors.

Your goal is to help the user learn, build, debug,
research, and understand.
"""
