# Worker Model Comparison — Harness V3 (2026-02-27)

## Test Cases
- **Carmen**: Interzession, §40 EO, §25c/d KSchG
- **Kolar**: Zustellwirksamkeit, ZustG, §158 ZPO
- **Ullrich**: Invaliditätspension, §254/255 ASVG

## Full Regression (3 Cases each)

### Grok 4.1 Fast (`grok_worker`) — DEFAULT

| Case | Tools | RS | Key Findings | Latenz |
|------|-------|----|-------------|--------|
| Carmen | 54 | 8 | §25c YES, §40 EO YES | 103s |
| Kolar | 73 | 6 | ZustG YES, §158 ZPO YES | ~130s |
| Ullrich | 47 | 7 | ASVG-only, 0x ABGB | ~120s |
| **Avg** | **58** | **7** | **3/3 PASS** | **~118s** |

### MiniMax M2.5 (`minimax_worker`)

| Case | Tools | RS | Key Findings | Latenz |
|------|-------|----|-------------|--------|
| Carmen | 33 | 6 | §25c YES, §40 EO YES | 99s |
| Kolar | 33 | 7 | ZustG YES, §158 ZPO YES | 77s |
| Ullrich | 33 | 25 | ASVG-only, 0x ABGB | 121s |
| **Avg** | **33** | **12.7** | **3/3 PASS** | **99s** |

### Flash Lite (`cheap_default`) — BASELINE

| Case | Tools | RS | Key Findings | Latenz |
|------|-------|----|-------------|--------|
| Carmen | 24 | 5 | §25c NO, §40 EO YES | 132s |
| Kolar | ~30 | ~5 | ZustG YES, §158 partial | ~120s |
| Ullrich | ~20 | 2 | ASVG partial | ~130s |
| **Avg** | **~25** | **~4** | **2/3 PASS** | **~127s** |

### DeepSeek V3.2 (`deepseek_worker`) — Carmen only

| Case | Tools | RS | Key Findings | Latenz |
|------|-------|----|-------------|--------|
| Carmen | 26 | 5 | §25c NO, §40 EO YES | 172s |

## Ranking

1. **Grok 4.1 Fast** — Best overall (most tool calls, robust, consistent)
2. **MiniMax M2.5** — Surprisingly strong (fastest, deepest RS at Ullrich, finds §25c)
3. Flash Lite — Budget option, misses §25c, fewer RS
4. DeepSeek V3.2 — Slowest, fewest tools, no §25c

## Caveats

- MiniMax consistently hits 33 tool calls (appears to be internal limit)
- MiniMax sometimes returns raw XML tool-call blobs instead of text (Synth compensates)
- Grok makes 54-73 tool calls = more thorough but slightly slower
- All models use same Organizer (Qwen) and Synth (Gemini 3 Flash)

## Cost per Query (estimate)

| Model | Input $/1M | Output $/1M | Est. Cost/Query |
|-------|-----------|-------------|----------------|
| Flash Lite | $0.10 | $0.40 | ~$0.003 |
| Grok 4.1 Fast | $0.20 | $0.50 | ~$0.008 |
| MiniMax M2.5 | ~$0.50 | ~$0.50 | ~$0.005 |
| DeepSeek V3.2 | $0.25 | $0.40 | ~$0.006 |

## Recommendation

**Default: `grok_worker`** — Best quality/robustness trade-off
**Budget alt: `minimax_worker`** — When speed matters and cost must be minimal
**Not recommended: `deepseek_worker`** — Slow, no advantage over others
