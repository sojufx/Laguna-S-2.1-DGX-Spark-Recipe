# Configuration notes

## Stable 250k profile

```bash
--max-model-len 250000
--max-num-seqs 3
--max-num-batched-tokens 2048
--prefix-match-unit 16
--gpu-memory-utilization 0.68
--kv-cache-dtype fp8
```

## DFlash

This recipe uses:

```json
{
  "model": "/opt/huggingface/models/Laguna-S-2.1-DFlash-NVFP4",
  "num_speculative_tokens": 15,
  "method": "dflash",
  "draft_tensor_parallel_size": 1
}
```

K=15 worked well for the tested long/code-shaped prompts. K=7 may be better for some workloads; benchmark before changing production.

## Prefix cache

`--prefix-match-unit 16` helps repeated agent prefixes by letting vLLM reuse smaller cached prefix chunks. It primarily improves TTFT, not raw decode tokens/sec.

## Thinking

Thinking is disabled:

```bash
--default-chat-template-kwargs '{"enable_thinking":false}'
```

For latency-sensitive coding/agent workflows this has been the better default.

