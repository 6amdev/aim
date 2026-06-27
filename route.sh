#!/usr/bin/env bash
# Aim router helper — รันบน server, ต่อ Qdrant ใน docker network 'backend'
# usage: ./route.sh "<งานเป็นภาษาคน>" [top_k]
set -euo pipefail
TASK="${1:?usage: route.sh \"<task>\" [top_k]}"
TOPK="${2:-5}"
REPO="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
docker run --rm --network backend \
  -v aim-cache:/root/.cache \
  -v "$REPO:/app" -w /app \
  -v "$HOME/.env:/secrets/.env:ro" -e AIM_SECRETS_FILE=/secrets/.env \
  aim:dev route "$TASK" --top-k "$TOPK" --llm 2>&1 \
  | grep -viE "warning|fetching|deprecat|TextEmbedding"
