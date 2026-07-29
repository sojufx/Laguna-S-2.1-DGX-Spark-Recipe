# Troubleshooting

## Slow first startup

First run may compile and autotune FlashInfer/CUTLASS kernels for `sm_121a`. This can take several minutes.

Look for:

```text
FlashInfer autotune
Warming up FlashInfer attention
Application startup complete
```

## EngineDeadError during restart

`EngineDeadError` can appear when systemd stops the old vLLM process during a restart. If a new process starts and later prints `Application startup complete`, this is usually harmless shutdown noise.

## Power-limited state after OOM

If performance collapses after OOM, check under load:

```bash
nvidia-smi --query-gpu=power.draw,clocks.sm,temperature.gpu,utilization.gpu --format=csv,noheader,nounits
```

Healthy under load should show high GPU utilization and high SM clocks, not ~650 MHz.

## LAN endpoint

This recipe binds to:

```bash
--host 0.0.0.0
```

Use your Spark's LAN IP for local clients:

```text
http://<spark-lan-ip>:8000/v1
```

Do not port-forward this directly to the public internet.

