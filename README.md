# VOID-AI 0.9.5

VOID-AI is the shared brain for the VOID system. The CLI, HTTP/API, browser
interface and Telegram interface all use the same `VoidCore`, memory,
context, tools, agent loop, task manager and Router9 model gateway.

## Architecture

```text
CLI / Browser / HTTP API / Telegram
                |
             VOID CORE
       +--------+---------+
       |        |         |
   Context    Memory    Tools
       |        |         |
       +--------+---------+
                |
          Agent / Tasks
                |
          Model Router
                |
             Router9
                |
        OpenRouter / models
```

## What is complete in this package

- Router9-only normal model gateway
- Dynamic model discovery through `/v1/models`
- Capability-aware routing for fast, reasoning, coding, research and vision
- Automatic retry/fallback for transient provider failures
- Shared Core/Agent/Task/Tool instances
- Conversation-isolated SQLite memory
- Long-term memory and knowledge search
- Context trimming and retrieved context
- Web search through Jina
- Project scanning and source-code analysis
- Source-evidence verification tool
- Safe read-only Termux diagnostic tool
- PDF/EPUB/text/file upload inspection
- Image analysis
- Video analysis through Gemini when configured
- Image generation through Hugging Face/Gradio when configured
- HTTP API
- OpenAI-compatible VOID `/v1/chat/completions` endpoint
- Browser chat interface at `/`
- Telegram polling for Termux (no public URL required)
- Telegram webhook mode for public hosting

## Termux setup

1. Extract this project.
2. Start Router9 and make sure its API is reachable at `127.0.0.1:20127`.
3. Create the local environment file:

```bash
cd ~/VOID-AI
cp .env.example .env
```

4. Edit `.env` and add only the credentials for features you want.

### Credentials

**Basic text / agent / tasks:** Router9 running. No VOID API key is required
for the default local Router9 setup.

**Web search:** `JINA_API_KEY`

**Vision fallback:** `GEMINI_API_KEY` (only needed if Router9 does not expose a
vision-capable model).

**Video:** `GEMINI_API_KEY`; VOID automatically retries/falls back across the configured Gemini video models.

**Image generation:** `HF_TOKEN`

**Telegram:** `TELEGRAM_BOT_TOKEN`

5. Install dependencies and verify:

```bash
python -m pip install -r requirements.txt
python -m compileall -q void run.py server.py
pytest -q
```

6. Run the local brain:

```bash
python run.py
```

## HTTP / browser interface

Start:

```bash
python server.py
```

Then open:

```text
http://127.0.0.1:8787/
```

Endpoints:

- `GET /` — browser interface
- `GET /health` — runtime/model/memory status
- `GET /status` — status alias
- `GET /models` / `GET /v1/models` — discovered Router9 models
- `POST /chat` — normal chat, agent or task mode; accepts optional `model`, `temperature`, `max_tokens`
- `POST /upload` — base64 file upload + agent inspection
- `POST /vision` — base64 image analysis
- `POST /video` — base64 video analysis
- `POST /image` — image generation
- `POST /clear` — clear one conversation
- `POST /v1/chat/completions` — OpenAI-compatible text interface with message history, model selection and generation parameters

Optional API protection:

```text
VOID_API_KEY=your-local-api-key
```

When set, POST requests require the `X-VOID-API-Key` header.

## Telegram

### Termux / no public URL

The default mode is polling:

```text
TELEGRAM_MODE=polling
```

Run:

```bash
cd ~/VOID-AI
python -m void.telegram_bot
```

The bot supports normal chat, `/agent`, `/task`, `/model`, `/status`, `/tasks`,
`/clear`, image analysis, video analysis, document upload and `/image`.
Telegram chat IDs are used as conversation IDs, so different chats do not share
conversation history.

### Public webhook

For a public host, set:

```text
TELEGRAM_MODE=webhook
TELEGRAM_WEBHOOK_PATH=/telegram
TELEGRAM_WEBHOOK_SECRET=choose-a-secret
```

Then run `python -m void.telegram_bot` on the public server. The webhook URL
must be configured with Telegram using that server's public HTTPS address.

## Verification

Offline verification does not require provider credentials:

```bash
python -m compileall -q void run.py server.py
pytest -q
```

Live Router9 verification requires Router9 to be running. The expected gateway
is:

```text
http://127.0.0.1:20127/v1
```

Do not put API keys directly into the source files or commit `.env`.


## Termux quick start

```bash
cd ~/VOID-AI
python -m pip install -r requirements.txt
cp -n .env.example .env
python scripts/verify_all.py
python run.py
```

For Telegram polling, set `TELEGRAM_BOT_TOKEN` in `.env` and run:

```bash
python -m void.telegram_bot
```

For the browser/API interface:

```bash
python server.py
```

Then open `http://127.0.0.1:8787/`.

Run `python scripts/live_check.py` from an environment with network access to verify configured external services. It never prints credential values.


## Android auto-start (no manual Termux start after reboot)

For a phone-local setup, install **Termux:Boot** once, then run:

```bash
cd ~/VOID-AI
mkdir -p ~/.termux/boot
cp scripts/termux-boot/void-stack ~/.termux/boot/void-stack
chmod +x ~/.termux/boot/void-stack
./scripts/start_void_stack.sh
```

The boot script starts Router9, the VOID web API, and the Telegram polling bot automatically after Android boots. Logs are stored in `~/.void-stack/`.

Useful commands:

```bash
./scripts/status_void_stack.sh
./scripts/stop_void_stack.sh
```

This is still phone-local. For a service that survives phone shutdown, move the same stack to a cloud host such as Render; Render web services provide a public HTTPS URL, but free services can spin down after 15 minutes of inactivity.
