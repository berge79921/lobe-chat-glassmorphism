# LegalChat Agentic Harness Minimal Run

- Timestamp (UTC): `2026-02-27T19:07:25.347038+00:00`
- Dry run: `False`
- Mode: `deep`
- Query: `Welche Chancen hat der Rekurs gegen den Beschluss des BG Traun?`
- Model profile: `default`
- Organizer backend: `openrouter`
- MCP mode: `local_http`
- Organizer model: `qwen/qwen3-coder-next`
- Worker model: `google/gemini-3-flash-preview`
- Synth model: `x-ai/grok-4.1-fast`
- File context: `12047` chars, `2` files, `0` OCR

## Organizer
- latency_ms: `11915.34`
- used_fallback: `False`

## Workstreams
1. `Zustellungsrechtliche Wirksamkeit nach § 163 Geo iVm HZÜ & ZMR`
   goal: `Prüfung, ob Zustellung an abgemeldete Adresse gemäß § 163 Abs 1 Geo iVm § 17 ZMR wirksam ist – insb. ob 'gewöhnlicher Aufenthalt' vorliegt oder Annahmeverweigerung gem § 163 Abs 5 Geo geltend gemacht werden konnte`
   tools: `['search_by_paragraph', 'search_by_schlagwort', 'hot_rs_lookup', 'get_rechtssatz', 'search_ogh_rechtssaetze']`
2. `Rechtsmittelführungskompetenz & Rekursbegründetheit gegen BG-Traun-Beschluss`
   goal: `Klärung der Rechtsmittelführungsbedingungen (§ 48 Abs 1 ZPO iVm § 163 Geo) und der Rekursbegründetheit bei Verletzung der Zustellvorschriften im Rechtshilfeverfahren`
   tools: `['search_by_paragraph', 'hot_rs_lookup', 'get_rechtssatz', 'search_kommentar_paragraph', 'search_by_schlagwort', 'search_ogh_rechtssaetze']`
3. `US-Insolvenzrechtliche Konsequenzen & Foreign Representative Status`
   goal: `Prüfung, ob Alexander Meghji als Litigation Administrator die erforderliche Prozessbefugnis im Sinne von § 163 Geo iVm Art 2 HZÜ besitzt – insb. im Lichte des US-Chapter-11-Plans und dessen Effective Date`
   tools: `['search_by_schlagwort', 'search_ogh_entscheidungen', 'hot_rs_lookup', 'get_rechtssatz', 'search_by_paragraph', 'search_ogh_rechtssaetze']`

## Execution Stats
- subagent_count: `3`
- stream_total_ms: `87373.82`
- tool_calls_total: `101`
- tool_calls_ok: `101`
- tool_ok_rate: `1.0`
- synth_latency_ms: `26777.57`
- final_answer_chars: `6526`
- citation_gate_mode: `enforce`
- citation_gate_applied: `True`
- citation_gate_pass_before: `False`
- citation_gate_pass_after: `True`

## Stream Details
- `Rechtsmittelführungskompetenz & Rekursbegründetheit gegen BG-Traun-Beschluss`: ms=27945.99 | tools_ok=35/35 | answer_chars=3595
- `US-Insolvenzrechtliche Konsequenzen & Foreign Representative Status`: ms=31928.89 | tools_ok=36/36 | answer_chars=3756
- `Zustellungsrechtliche Wirksamkeit nach § 163 Geo iVm HZÜ & ZMR`: ms=27498.94 | tools_ok=30/30 | answer_chars=3741

