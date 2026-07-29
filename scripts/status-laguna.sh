#!/usr/bin/env bash
set -euo pipefail

PORT="${VLLM_PORT:-8000}"

systemctl is-active vllm-laguna.service || true
ss -ltnp | grep ":${PORT}" || true
free -h
nvidia-smi --query-gpu=name,power.draw,clocks.sm,temperature.gpu,utilization.gpu --format=csv,noheader,nounits || true

