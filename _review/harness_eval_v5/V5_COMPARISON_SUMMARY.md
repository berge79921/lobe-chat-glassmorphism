# Harness V5 — default vs cheap_grok_fast Comparison

## Model Profiles

| Layer | default | cheap_grok_fast |
|-------|---------|-----------------|
| Organizer | qwen/qwen3-coder-next | qwen/qwen3-coder-next |
| Worker | google/gemini-3-flash-preview | x-ai/grok-4.1-fast |
| Synth | x-ai/grok-4.1-fast | x-ai/grok-4.1-fast |

## Metrics Comparison

| Metric | Case | default | grok_fast |
|--------|------|---------|-----------|
| **Tool Calls** | Arzthaftung | 57 | 58 |
| | Gewährleistung | 70 | 85 |
| | Interzession | 59 | 54 |
| **Stream Time (ms)** | Arzthaftung | 98,197 | 205,354 |
| | Gewährleistung | 244,319 | 256,643 |
| | Interzession | 256,412 | 194,376 |
| **Synth Latency (ms)** | Arzthaftung | 26,172 | 23,522 |
| | Gewährleistung | 20,566 | 17,012 |
| | Interzession | 19,707 | 16,470 |
| **Final Answer Chars** | Arzthaftung | 6,400 | 5,419 |
| | Gewährleistung | 5,478 | 5,629 |
| | Interzession | 5,833 | 6,100 |

## Qualitative Assessment

### Case 1: Arzthaftung
- **default:** Good dual-track (Delikt + Vertrag), but less specific RS citations
- **grok_fast:** Solid RS citations (RS0022582, RS0111528, RS0026473), 60%/40% Erfolgsaussichten

### Case 2: Gewährleistung
- **default:** Missing some key §§ (no §874 ABGB)
- **grok_fast:** Found §874 ABGB (List über Substanzfehler), more tool calls (85 vs 70), better evidence gathering

### Case 3: Interzession
- **default:** Good §25c/§25d KSchG coverage
- **grok_fast:** Excellent — RS0121054 (Entfall Haftung ohne Anfechtung), RS0113883, RS0048300, full Stufenbau, 70%/50%/40% Erfolgsaussichten

## Conclusion

Both profiles produce V5-quality output (8-section template, Beweislast, Prozessstrategie).
- **grok_fast** tends to use more tools for deeper evidence gathering (Case 2: 85 vs 70)
- **grok_fast** synth is consistently faster (~17s vs ~22s avg)
- Quality is comparable; grok_fast sometimes finds more specific RS citations
- Cost: grok_fast is significantly cheaper (Grok 4.1 Fast is free-tier on OpenRouter)
