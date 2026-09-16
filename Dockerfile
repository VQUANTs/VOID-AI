FROM node:22-bookworm-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    NODE_ENV=production \
    npm_config_update_notifier=false

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-pip ca-certificates curl \
    && rm -rf /var/lib/apt/lists/* \
    && npm install -g 9router@0.5.75

WORKDIR /app
COPY requirements.txt ./requirements.txt
RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt

COPY . .
RUN chmod +x scripts/render_start.sh scripts/render_proxy.py \
    && python3 -m compileall -q void scripts/render_start.py scripts/render_proxy.py

EXPOSE 10000

CMD ["./scripts/render_start.sh"]
