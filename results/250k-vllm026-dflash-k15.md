# Benchmark snapshot: 250k vLLM 0.26 DFlash K15

```text
Hardware: 1x NVIDIA DGX Spark / GB10 / 128GB unified memory
Runtime: vLLM 0.26
Model: poolside/Laguna-S-2.1-NVFP4
Draft: poolside/Laguna-S-2.1-DFlash-NVFP4
Context: 250,000 tokens
KV cache dtype: fp8
Speculative decode: DFlash K=15
Prefix cache: enabled
Prefix match unit: 16
```

## Startup

```text
GPU KV cache size: 319,138 tokens
Maximum concurrency for 250,000 tokens/request: 1.28x
Current KV cache memory: ~11.36 GiB
```

## Throughput

```text
single short:        13.6 tok/s
single code:         44.7 tok/s
single agent:        22.7 tok/s
single long-context: 39.5 tok/s

C1 aggregate:        43.6 tok/s
C2 aggregate:        56.3 tok/s
C3 aggregate:        79.1 tok/s
```

These numbers are from practical OpenAI-compatible requests and are intended as a stable recipe baseline.

