# Theridion Studio — Produktová roadmapa: zpět k jádru

> Stav: návrh 2026-05-30. Autor: syntéza 4 agentů (architekt, PM, produkt, UX).
> Princip: **core + progressive disclosure**. Declutter ≠ delete — nic se nemaže, jen schovává za Cmd+K / Advanced / opt-in.

## Původní myšlenka (ověřeno z git historie)

Commity #1–12 (`Initial scaffold: Tauri shell + Python FastAPI sidecar` → `file-based persistence` → `Folder hierarchy (Bruno parity)` → `SOAP/WS-Security`):

**Theridion = lokální, file-based, git-native API klient s enterprise protokoly (SOAP/WS-Security, gRPC, Kafka) bez cloud lock-inu.** Bruno-killer s tím, co Bruno nemá.

Balast přidaný post-MVP: Flows, Traffic, Monitors, Silk (FE testy), Spin (BE testy), Hub Overview — **6 cizích produktů nalepených do jedné ActivityBar**. Žádný není v původní myšlence.

## Diagnóza „je to hrozné"

- ActivityBar: **7 ikon** (z toho 1 je jádro).
- RequestPanel: **9 tabů** (Params/Headers/Body/Auth/Certs/Tests/Scripts/Retry/Notes).
- Sidebar: ~4 inline akce trvale viditelné na každé z 28+ položek = vizuální šum.
- RequestTabBar toolbar: 6 akcí v řadě, polovina disabled/redundantní.
- App.tsx: 1587 ř., 31× useState → každý keystroke re-renderuje vše.

## Killer angle (zachovat a zvýraznit)

File-based + git-native + **enterprise protokoly viditelné** + embedded load testing + offline AI test generation. To je mezera na trhu — Postman/Insomnia jsou cloud-first, Bruno nemá SOAP/gRPC/load/AI.

---

## Vlna 0 — Declutter (1–2 dny, NULOVÝ data loss, max efekt)

| # | Funkčnost | Soubor | Typ | Náročnost |
|---|-----------|--------|-----|-----------|
| 0.1 | ActivityBar 7→1: default jen **Requests**; ostatní za „+" / Cmd+K | `ActivityBar.tsx`, `App.tsx` | declutter | S |
| 0.2 | RequestPanel 9→4 tabů (Params/Headers/Body/Auth); Certs/Retry/Notes za „Advanced", **Tests+Scripts merge** | `RequestPanel.tsx` | declutter | S |
| 0.3 | Sidebar inline akce jen na hover (`opacity-0 group-hover:opacity-100`) | `Sidebar.tsx` | declutter | S |
| 0.4 | Toolbar: **Share kill** (cloud feature v local-first), „More" → Cmd+K; **Protocols ZŮSTÁVÁ** (diferenciátor) | `RequestTabBar.tsx` | declutter | S |
| 0.5 | ResponsePanel: Diff/Codegen/Analyze → jeden „⋮" menu | `ResponsePanel.tsx` | declutter | S |

Cíl: 5 minut po deployi appka vypadá jako soustředěný API klient, ne jako 7 produktů.

## Vlna 1 — Core solidity (Now, ~2 týdny)

| # | Funkčnost | Typ | Náročnost | Plán |
|---|-----------|-----|-----------|------|
| 1.1 | State refactor na Zustand (App.tsx → request/tab/ui store) — plynulost, žádný flicker | core | L | Bod 1 |
| 1.2 | Response guard na obří payloady (>1 MB → karta + download, parsing ve workeru) — stabilita | core | M | Bod 4 |
| 1.3 | Bulk-edit + key/value tabulka headers/params (paste z dokumentace) | obal | S | Bod 7 |

> Hotovo dnes: **load-test vars/auth** (Bod 2), **secrets Fernet vault backend** (Bod 5 BE), **protokoly viditelné**, **brand favicon**, **tab a11y**.

## Vlna 2 — Obal hodnotou (Next)

| # | Funkčnost | Typ | Náročnost | Plán |
|---|-----------|-----|-----------|------|
| 2.1 | `{{secret:NAME}}` UI sjednocení + maskování v exportech (backend hotový) | core/sec | M | Bod 5 FE |
| 2.2 | Var autocomplete + highlight (`{{var}}` zelená/červená, nepošle nevyřešený token) | obal | M | Bod 8 |
| 2.3 | Live load-test progress (SSE, sparkline RPS/latence, Stop) | obal | M | Bod 3 |
| 2.4 | AI test generation zviditelnit (offline Ollama) — diferenciátor | obal | M | — |
| 2.5 | Collection runner + HTML trace report zvýraznit | core | M | — |
| 2.6 | Test coverage gate v CI (substituce/auth/parsování) | obal | M | Bod 6 |

## Vlna 3 — Later (podle adopce)

| # | Funkčnost | Typ | Náročnost |
|---|-----------|-----|-----------|
| 3.1 | Moduly opt-in: persistence volby + Settings „Modules" toggle + module picker za „+" (ADR-005 Fáze 1–3) | platform | M |
| 3.2 | i18n CS/EN provider + toggle | obal | M |
| 3.3 | Guided empty states (varianty: žádná kolekce/request/odpověď/historie) | obal | S |
| 3.4 | Hub/Monitors/Silk/Spin: opt-in, plná impl jen on-demand; kandidáti na standalone/cut | platform | L |

## Rizika

- **Skrytí modulu, který někdo používá** → nic nemazat, jen přesunout za „+"/Cmd+K; přidat EmptyState fallback.
- **localStorage migrace tabů** → Zustand `persist` musí použít stejný klíč `theridion_tabs` + `migrate` fn, jinak ztráta uložených tabů.
- **Secrets zpětná kompat** → migrace plaintext tokenů opt-in („Move to vault"), ne automatická.
- **hubOverview** v local-first desktopu je outlier → podmíněné zobrazení `if hubConnected`.

## Pořadí realizace

Vlna 0 (declutter) **hned** → Vlna 1 (core) → Vlna 2 (obal) → Vlna 3 (later). Vlna 0 je 1 hodina–2 dny práce s okamžitým „už to není hrozné" efektem.
