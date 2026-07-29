#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="${PYTHON_BIN:-$HOME/vllm-026/bin/python}"
MODEL="${VLLM_MODEL:-/opt/huggingface/models/Laguna-S-2.1-NVFP4-latest}"
DRAFT_MODEL="${VLLM_DRAFT_MODEL:-/opt/huggingface/models/Laguna-S-2.1-DFlash-NVFP4}"
HOST="${VLLM_HOST:-0.0.0.0}"
PORT="${VLLM_PORT:-8000}"
SERVED_MODEL_NAME="${SERVED_MODEL_NAME:-ornith}"

export VLLM_TARGET_DEVICE="${VLLM_TARGET_DEVICE:-cuda}"
export CUTE_DSL_ARCH="${CUTE_DSL_ARCH:-sm_121a}"
export PATH="/usr/local/cuda/bin:${PATH}"
export MAX_JOBS="${MAX_JOBS:-4}"
export FLASHINFER_DISABLE_VERSION_CHECK="${FLASHINFER_DISABLE_VERSION_CHECK:-1}"
export PYTORCH_CUDA_ALLOC_CONF="${PYTORCH_CUDA_ALLOC_CONF:-expandable_segments:True}"

exec "$PYTHON_BIN" -m vllm.entrypoints.openai.api_server \
  --model "$MODEL" \
  --host "$HOST" \
  --port "$PORT" \
  --served-model-name "$SERVED_MODEL_NAME" \
  --tensor-parallel-size 1 \
  --trust-remote-code \
  --enable-auto-tool-choice \
  --tool-call-parser poolside_v1 \
  --reasoning-parser poolside_v1 \
  --override-generation-config '{"temperature":0.6,"top_p":0.95}' \
  --default-chat-template-kwargs '{"enable_thinking":false}' \
  --max-num-seqs 3 \
  --max-num-batched-tokens 2048 \
  --prefix-match-unit 16 \
  --speculative-config "{\"model\":\"$DRAFT_MODEL\",\"num_speculative_tokens\":15,\"method\":\"dflash\",\"draft_tensor_parallel_size\":1}" \
  --max-model-len 250000 \
  --gpu-memory-utilization 0.68 \
  --kv-cache-dtype fp8 \
  --api-key "${VLLM_API_KEY:?Set VLLM_API_KEY}"
