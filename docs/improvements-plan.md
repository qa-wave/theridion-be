# Theridion Studio BE — Implementační plán 10 zlepšení

> Stav: návrh (NECOMMITOVÁNO). Autor: senior produktový inženýr pro Tomáše (QA lead).
> Repo: `/Users/tm/workspaces/projects/theridion-be`. FE `apps/studio`, sidecar `apps/sidecar/theridion_sidecar`.
> Ověřeno proti kódu 2026-05-30: App.tsx 1587 ř./31 useState, RequestPanel 2251 ř., ResponsePanel 1768 ř.

---

## Přehledová tabulka

| # | Bod | Priorita | Náročnost | Pořadí |
|---|-----|----------|-----------|--------|
| 1 | Rozbít App.tsx + Panel monolity (Zustand store) | **P0** | L (5-8 d) | **#2** |
| 2 | Load test: proměnné + auth | **P0** | M (2-3 d) | **#1** |
| 3 | Load test: live progress přes WS/SSE | P1 | M (2-3 d) | #5 |
| 4 | Response viewer guard na obří payloady | **P0** | M (2-4 d) | **#3** |
| 5 | Secret leak — sjednotit `{{secret:NAME}}` | **P0** | M (3-4 d) | #4 |
| 6 | Test coverage request-build/response/substitution | P1 | M (2-3 d) | #6 |
| 7 | Bulk-edit + key/value tabulka headers/params | P1 | S (1-2 d) | #7 |
| 8 | Inline preview/autocomplete `{{var}}` | P2 | M (2-3 d) | #8 |
| 9 | Dokončit i18n CS/EN provider + toggle | P2 | M (2-3 d) | #9 |
| 10 | Guided empty states | P2 | S (1 d) | #10 |

**Top-3 doporučené pořadí:** #2 (load test vars/auth) → #1 (state refaktoring) → #4 (response guard).
Zdůvodnění: #2 odemyká reálné load-testy proti chráněným API (rychlá výhra, malé riziko); #1 je předpoklad pro plynulé UX všech dalších FE bodů; #4 zabraňuje pádu/zamrznutí UI na velkých odpovědích (stabilita).

---

## Bod 1 — Rozbít App.tsx + RequestPanel/ResponsePanel monolity

**Priorita: P0** — každý keystroke re-renderuje celou app; blokuje plynulost všeho ostatního FE.
**Náročnost: L** (5-8 dní).

### Stav v kódu
- `apps/studio/src/App.tsx`: 1587 ř., 31× `useState` (sidecarStatus, collections, tabs, activeId, environments, history, console, network…). Vše drženo nahoře a prop-drillováno dolů.
- `apps/studio/src/components/RequestPanel.tsx` (2251 ř.) a `ResponsePanel.tsx` (1768 ř.) přijímají desítky props → re-render při každé změně rodiče.
- Existující stav: `apps/studio/src/state/{theme.ts,types.ts}`, hooky `useModals.ts`. Zustand zatím není.

### Implementační detail
1. Přidat `zustand` (`apps/studio/package.json`) — lehký, bez boilerplate, vhodný pro desktop.
2. Vytvořit `apps/studio/src/state/requestStore.ts` — slice pro aktivní request draft (url, method, headers, params, body, auth, certConfig, retryConfig). Selektory `useRequestStore(s => s.url)` → komponenty odebírají jen svá pole.
3. Vytvořit `apps/studio/src/state/tabStore.ts` — `tabs`, `activeId`, akce open/close/closeToRight/duplicate; persist přes `zustand/middleware persist` (nahrazuje současný `useState(() => ...)` init z localStorage v App.tsx:95-118).
4. Vytvořit `apps/studio/src/state/uiStore.ts` — modaly, network panel, toasts, splitRatio (UI-only stav, oddělit od dat).
5. Migrovat App.tsx postupně: nejdřív tabs+request draft (největší re-render zdroj), pak network/console, nakonec UI flags. Po každém slice ponechat App.tsx funkční (žádný big-bang).
6. RequestPanel/ResponsePanel: odebírat ze store přes selektory místo props; rozdělit na podkomponenty (`RequestHeadersTab`, `RequestBodyTab`, `RequestAuthTab`, `ResponseBodyView`, `ResponseHeadersView`) v `components/request/` a `components/response/` — každá memoizovaná (`React.memo`).
7. Body editor (`CodeEditor`) izolovat za `memo` + debounce na propisování do store (vstup do bodu 4).

### Rizika
- Velký diff → dělat po slicích, každý s vlastním commitem a zeleným testem.
- localStorage migrace tabů — zachovat formát klíče, jinak ztráta uložených tabů u uživatele.
- Souběh s body 4/7/8 (sahají do týchž panelů) → tento bod dělat **první** z FE skupiny.

### Přínos
- 🎨 Grafický: žádné vizuální cuknutí/flicker při psaní, plynulejší animace panelů.
- ⚙️ Funkční: odděleny data vs UI stav; snadnější přidávání feature bez růstu App.tsx.
- 👤 UX: psaní v URL/body bez lagu i u velkých kolekcí a dlouhých odpovědí.
- 🙋 Pro uživatele: appka „nesekává“; Tomáš (QA) může mít otevřeno mnoho tabů bez zpomalení.

---

## Bod 2 — Load test: podpora proměnných a auth

**Priorita: P0** — bez `{{var}}`/auth nejde load-testovat reálné chráněné endpointy; nejrychlejší výhra.
**Náročnost: M** (2-3 dny).

### Stav v kódu
- `apps/sidecar/theridion_sidecar/api/loadtest.py`: `LoadTestRequest` (ř. 21-27) má jen holé `url/method/headers/body`; `_worker` (ř. ~60) volá `client.request` s nezpracovanými hodnotami.
- Vzor existuje v `api/requests.py`: `execute()` resolvuje `environments.substitute(...)` + `substitute_dict(...)` + `_apply_auth(auth, headers, query, env)` (ř. ~137 nahoru). `AuthConfig` (bearer/basic/apikey) hotová.
- `environments.substitute()` v `environments.py:140`.

### Implementační detail
1. Rozšířit `LoadTestRequest` o `environment_id: str | None`, `collection_id: str | None`, `auth: AuthConfig | None`, `query: dict[str,str]`.
2. V `run_loadtest` před spuštěním workerů (jednou, ne per-request):
   - načíst env: `env = environments.get(req.environment_id)` (404 když chybí, jako v requests.py);
   - vyřešit collection vars stejně jako requests.py;
   - `resolved_url/headers/body/query = environments.substitute*(...)`;
   - `_apply_auth(req.auth, resolved_headers, resolved_query, env)` — vyextrahovat `_apply_auth` z requests.py do sdíleného modulu (`api/_auth.py`) a importovat v obou (DRY).
3. Předat workerům už vyřešené hodnoty (substituce jen 1× → neovlivní throughput).
4. Pozn.: `{{$random}}` builtiny — pokud má každý request mít unikátní hodnotu, řešit per-request substituci jen pro builtiny (volitelný flag `per_request_vars: bool=false`).
5. FE `LoadTestModal.tsx`: přidat výběr environmentu (reuse `EnvDropdown`) + auth sekci (reuse z RequestPanel auth tab).

### Rizika
- Per-request builtiny vs výkon — default vypnuto.
- OAuth2 token refresh během dlouhého běhu (mimo scope; apikey/bearer/basic stačí pro v1).

### Přínos
- 🎨 Grafický: modal dostane env dropdown + auth panel = konzistence s RequestPanel.
- ⚙️ Funkční: load test sdílí substituční/auth pipeline s normálním requestem (jeden zdroj pravdy).
- 👤 UX: stejný request co funguje v Send funguje i v load testu (žádné ruční přepisování tokenů).
- 🙋 Pro uživatele: Tomáš load-testuje reálná staging API s tokenem na pár kliknutí.

---

## Bod 3 — Load test: live progress (WS/SSE)

**Priorita: P1** — dlouhý běh bez zpětné vazby; ne blocker, ale výrazně zlepší pozorovatelnost.
**Náročnost: M** (2-3 dny).

### Stav v kódu
- `loadtest.py` `run_loadtest` dělá `await asyncio.gather(*tasks)` a vrací výsledek až na konci → 0 průběžných dat.
- Sidecar už má WS/SSE infra: `api/websocket.py`, `api/sse_client.py`, `api/ws_advanced.py` → vzor pro streaming.

### Implementační detail
1. Přidat `GET /api/loadtest/stream` (SSE `StreamingResponse`, jednodušší než WS pro one-way push) nebo WS endpoint, dle vzoru `sse_client.py`.
2. Sdílený stav běhu: `asyncio.Queue` nebo lehký in-memory registr `run_id -> stats`. Workeři po každém requestu (nebo po 250 ms tiku) pushnou agregát: aktuální RPS, p50/p95 z rolling okna, error count.
3. Spustit běh jako background task; `POST /run` vrátí `run_id` okamžitě; klient se připojí na stream.
4. FE `LoadTestModal.tsx`: live sparkline RPS + latency (reuse `latency_histogram`/`throughput_timeline` komponenty pokud existují), tlačítko Stop (abort tasks přes `run_id`).
5. Agregace: rolling počítadlo, ne plný seznam latencí v paměti při dlouhém běhu (bound memory — viz riziko).

### Rizika
- Paměť při 300 s × vysokém RPS — držet jen percentil-sketch / rolling okno, ne všechny latence.
- Backwards compat: zachovat stávající synchronní `/run` pro CLI/skripty.

### Přínos
- 🎨 Grafický: živé grafy RPS/latence místo spinneru.
- ⚙️ Funkční: zrušitelný běh, streamovaná agregace, bounded paměť.
- 👤 UX: uživatel vidí trend hned, pozná degradaci dřív než po 5 min.
- 🙋 Pro uživatele: Tomáš sleduje, jak SUT drží zátěž v reálném čase, a může běh utnout.

---

## Bod 4 — Response viewer guard na obří payloady

**Priorita: P0** — velké body zamrazí/shodí UI (Monaco dostane celé tělo); stabilita.
**Náročnost: M** (2-4 dny).

### Stav v kódu
- `ResponsePanel.tsx:65-66` ukládá `body_size`, `body_preview`; `BodyView` (ř. ~502) volá `prettify(res.body, ct)` a posílá do `CodeEditor` (Monaco) celé `res.body`.
- `ResponsePanel.tsx:514-516` další transformace (minify/base64/jwt) na celém těle.

### Implementační detail
1. Definovat práh `RESPONSE_INLINE_LIMIT = 1_000_000` (1 MB) v `lib/`.
2. V `BodyView`: když `res.body_size_bytes > limit` → nezobrazovat v Monacu; místo toho karta „Large response (X MB)“ s akcemi **Raw** (plain `<pre>` s prvními N kB) / **Download** / **Open in viewer**.
3. Parsování přesunout do Web Workeru: `apps/studio/src/lib/jsonWorker.ts` (`new Worker(new URL(...))`) — `prettify`/`JSON.parse` mimo main thread; výsledek streamovat zpět.
4. Virtualizovaný JSON tree pro velké struktury: rozšířit `JsonTreeView.tsx` o virtualizaci (`@tanstack/react-virtual`) — renderovat jen viditelné uzly.
5. Download přes Tauri `save` dialog (desktop) → zápis bez držení v DOM.
6. Guard i na transformace (minify/base64/jwt) — u velkých dělat ve workeru nebo zakázat s hláškou.

### Rizika
- Worker bundling ve Vite/Tauri — ověřit `?worker` import a CSP (desktop má vlastní CSP).
- Monaco model disposal — uvolnit při přepnutí na raw, jinak leak.

### Přínos
- 🎨 Grafický: čistá „large payload“ karta místo zamrzlého editoru.
- ⚙️ Funkční: parsing off-thread, virtualizovaný tree, download velkých těl.
- 👤 UX: appka reaguje i na 50 MB JSON; uživatel volí, jak to chce zobrazit.
- 🙋 Pro uživatele: QA dump endpoint Theridion neshodí; Tomáš si velké tělo stáhne.

---

## Bod 5 — Secret leak risk: sjednotit `{{secret:NAME}}`

**Priorita: P0** — bearer tokeny plaintext v `environments/<uuid>.json`; bezpečnostní riziko.
**Náročnost: M** (3-4 dny).

### Stav v kódu
- `api/secret_encryption.py` (60 ř.): Fernet encrypt/decrypt (PBKDF2 390k iter) — ale **standalone** endpoint, **nenapojeno** na substituci.
- `environments.substitute()` (`environments.py:140`) zná jen plain `{{var}}` a builtiny `{{$...}}`; `_VAR_PATTERN` (ř. 38) nezahrnuje `secret:`.
- FE `SecretsVaultModal.tsx` (143 ř.) je oddělený od env varů → secrety a `{{var}}` žijí ve dvou světech; bearer token se ukládá plaintextem do env JSON.

### Implementační detail
1. Rozšířit `_VAR_PATTERN` (nebo přidat 2. pattern) o syntaxi `{{secret:NAME}}` → namespace pro vault hodnoty.
2. Backend vault store `api/secrets_vault.py`: hodnoty šifrované Fernetem (klíč z OS keychain přes Tauri / passphrase-derived dle `secret_encryption.py`), na disku **nikdy** plaintext.
3. V `substitute()` přidat resolver: když `name` matchne `secret:X`, načíst z vaultu a dešifrovat **až v okamžiku odeslání** requestu (ne při zobrazení).
4. Migrace: detekovat plaintext tokeny v `environments/<uuid>.json` (auth.token apod.), nabídnout „Move to vault“ → nahradit hodnotou `{{secret:NAME}}`.
5. Maskovat secrety v UI/logu/history/network console (`••••`), v cURL exportu (`curl.py`, `curl_log.py`) a v `har_export.py` nahradit placeholderem, ne hodnotou.
6. Sjednotit `SecretsVaultModal` a env editor: secrety jako speciální typ var s ikonou zámku.

### Rizika
- Zpětná kompatibilita existujících env souborů — migrace musí být bezpečná a vratná (backup).
- Klíč management na desktopu — preferovat OS keychain (Tauri plugin) před passphrase v paměti.
- Nezalogovat secret v error stacku.

### Přínos
- 🎨 Grafický: ikona zámku + maskované hodnoty napříč UI.
- ⚙️ Funkční: jednotná `{{secret:NAME}}` syntaxe; šifrování at-rest; maskování v exportech.
- 👤 UX: uživatel zachází se secretem jako s běžnou proměnnou, ale bezpečně.
- 🙋 Pro uživatele: tokeny Tomášova týmu nejsou plaintext na disku ani v HAR/cURL exportu.

---

## Bod 6 — Test coverage: request-build / response / substitution

**Priorita: P1** — tenké pokrytí klíčové logiky; ne blocker, ale snižuje riziko regresí (zvlášť po bodu 1/5).
**Náročnost: M** (2-3 dny).

### Stav v kódu
- Sidecar 65 `test_*.py`, FE 17 test souborů — ale core build/parse/substituce má jen pár testů (bod uvádí „9 unit“ pro tuto oblast).

### Implementační detail
1. **Substituce** (`environments.py`): tabulkové testy resolution order (globals→collection→env→extra→builtin), unknown var zůstává, `{{$random}}` builtiny, nový `{{secret:NAME}}` (bod 5).
2. **Request build** (`requests.py` `_apply_auth` + substituce): bearer/basic/apikey(query|header), apikey s prázdným key, kombinace env+collection vars.
3. **Response parsing** (FE `lib/`): `prettify`/`minifyJson`/`decodeBase64`/`decodeJwt` happy + malformed; large-body guard z bodu 4.
4. **Load test** (`loadtest.py`): substituce + auth resolved jednou (bod 2); percentil výpočet na známém datasetu.
5. Přidat coverage gate v CI (`.github/`) — fail pod prahem na `environments.py`/`requests.py`/`loadtest.py`.

### Rizika
- Po refaktoringu (bod 1) FE testy přepsat na store — koordinovat pořadí.

### Přínos
- 🎨 Grafický: žádný přímý vizuál (kvalita pod kapotou).
- ⚙️ Funkční: regrese v substituci/auth/parsování chycena v CI.
- 👤 UX: méně „proč mi to nevyplnilo token“ bugů u uživatele.
- 🙋 Pro uživatele: Tomáš (QA) má důvěru, že odeslaný request je přesně ten zamýšlený.

---

## Bod 7 — Bulk-edit + key/value tabulka pro headers/params

**Priorita: P1** — produktivita; částečně už existuje, jde o dotažení.
**Náročnost: S** (1-2 dny).

### Stav v kódu
- `RequestPanel.tsx` už má řádkový model s `enabled` togglem (ř. 295-352): `parseHeadersText`/`headersToText` (`state/types.ts`), disabled řádek = `# key: value`, přidání řádku, checkbox `r.enabled` (ř. 439).
- Chybí: přepínač **Bulk edit ↔ tabulka**, hromadný textový režim, paste více řádků.

### Implementační detail
1. Přidat toggle „Key-Value | Bulk Edit“ nad tabulku headers i params.
2. Bulk režim = `<textarea>` s `key: value` per řádek (parsing už existuje: `parseHeadersText`); při přepnutí synchronizovat oba směry.
3. Paste handler: vícenásobné řádky / `key=value` (params) rozparsovat do řádků.
4. Sjednotit komponentu pro headers i query params (`KeyValueTable` v `components/request/`).
5. „Description“ sloupec (volitelný) + smazat řádek, hromadné disable/enable.

### Rizika
- Round-trip ztráta komentářů/pořadí mezi bulk a tabulkou — zachovat raw jako zdroj pravdy.

### Přínos
- 🎨 Grafický: čistá tabulka s toggly + bulk textarea = pohodlnější editace.
- ⚙️ Funkční: hromadný paste z Postmana/cURL/Excelu, enable/disable bez mazání.
- 👤 UX: rychlé hromadné úpravy headers/params, jeden klik mezi režimy.
- 🙋 Pro uživatele: Tomáš nakopíruje hlavičky z dokumentace API hromadně.

---

## Bod 8 — Inline preview/autocomplete pro `{{var}}`

**Priorita: P2** — pohodlí, ne nutnost; zvyšuje objevitelnost proměnných.
**Náročnost: M** (2-3 dny).

### Stav v kódu
- `environments.py` `_VAR_PATTERN` (ř. 38) definuje syntaxi; backend zná seznam proměnných (`environments.get`, globals, collection vars).
- FE `UrlBar.tsx` (494 ř.) — místo pro highlight + autocomplete; `variable_inspector.py` už scanuje `{{var}}` v textu (vzor).

### Implementační detail
1. Endpoint `GET /api/environments/{id}/resolve-preview?text=...` → vrátí seznam nalezených varů s `{name, defined: bool, value_masked}` (reuse `variable_inspector.py`).
2. `UrlBar.tsx`: zvýraznit `{{var}}` — zelená (defined) / červená (undefined). Implementace přes overlay span vrstvu nad inputem (contenteditable highlight nebo Monaco-mini).
3. Autocomplete: na `{{` zobrazit dropdown s dostupnými vary (env + collection + globals + builtiny), výběr vloží `{{name}}`.
4. Hover/tooltip: zobrazit aktuální hodnotu (secret maskovaný dle bodu 5).
5. Rozšířit i na headers/params/body editor (sdílená util `useVarHighlight`).

### Rizika
- Highlight overlay nad nativním inputem je tricky (sync scroll/caret) — zvážit lehký editor.
- Secret hodnoty v tooltipu maskovat (návaznost na bod 5).

### Přínos
- 🎨 Grafický: barevné zvýraznění varů, autocomplete dropdown.
- ⚙️ Funkční: detekce nedefinovaných varů ještě před odesláním.
- 👤 UX: uživatel hned vidí, že `{{baseUrl}}` není definovaný (červeně), s hover hodnotou.
- 🙋 Pro uživatele: Tomáš nepošle request s nevyřešeným `{{token}}` omylem.

---

## Bod 9 — Dokončit/zviditelnit i18n CS/EN

**Priorita: P2** — polish; appka je převážně EN, CS strings nejsou centralizované.
**Náročnost: M** (2-3 dny).

### Stav v kódu
- Žádný i18n provider — App.tsx používá jen `localeCompare` (ř. 193); stringy hardcoded napříč komponentami.

### Implementační detail
1. Přidat lehký i18n (`react-i18next` nebo vlastní Context provider — pro desktop stačí jednoduchý provider).
2. `apps/studio/src/i18n/` s `cs.json`/`en.json`; provider v `main.tsx`/`App.tsx`.
3. Locale toggle v ActivityBar/Settings; persist přes `uiStore` (bod 1) + localStorage.
4. Migrovat stringy postupně: nejdřív hlavní obrazovky (App, RequestPanel, ResponsePanel, NetworkConsole), pak modaly.
5. `t()` helper + lint pravidlo proti novým hardcoded stringům (volitelně).

### Rizika
- Velký rozsah stringů → dělat inkrementálně, ne najednou; default fallback EN.
- Návaznost na bod 1 (locale ve store) — dělat po refaktoringu.

### Přínos
- 🎨 Grafický: konzistentní jazyk celého UI.
- ⚙️ Funkční: centralizované stringy, snadné přidání dalšího jazyka.
- 👤 UX: uživatel přepne CS/EN jedním klikem.
- 🙋 Pro uživatele: Tomášův tým má appku v češtině, dokumentace/sdílení v EN.

---

## Bod 10 — Guided empty states

**Priorita: P2** — onboarding polish.
**Náročnost: S** (1 den).

### Stav v kódu
- `EmptyState.tsx` (35 ř.) — minimální, generický.
- `ResponsePanel.tsx` — prázdný stav před prvním requestem.

### Implementační detail
1. Rozšířit `EmptyState.tsx` o varianty: žádná kolekce, žádný request, žádná odpověď, prázdná historie.
2. Každý empty state: ikona + 1 větný popis + primární CTA („New request“, „Import collection“, „Send“) + odkaz na dokumentaci/zkratku.
3. ResponsePanel prázdný stav: vysvětlit, že po Send se zde objeví tělo/headers/timing + tip na klávesovou zkratku Send.
4. Konzistentní vizuál s `index.css` design tokeny.

### Rizika
- Nízké; čistě prezentační.

### Přínos
- 🎨 Grafický: profesionální prázdné stavy místo holého „nic tu není“.
- ⚙️ Funkční: CTA navádějí k dalšímu kroku.
- 👤 UX: nový uživatel ví, co dělat dál.
- 🙋 Pro uživatele: rychlejší onboarding kolegů do Theridion Studia.

---

## Doporučené pořadí realizace

1. **Bod 2** (load test vars/auth, P0/M) — rychlá výhra, malé riziko, okamžitá hodnota.
2. **Bod 1** (state refaktoring, P0/L) — předpoklad plynulosti pro všechny FE body (4,7,8,9).
3. **Bod 4** (response guard, P0/M) — stabilita; staví na izolovaném editoru z bodu 1.
4. **Bod 5** (secrets, P0/M) — bezpečnost; před širším sdílením.
5. **Bod 3** (live load progress, P1/M) — staví na bodu 2.
6. **Bod 6** (testy, P1/M) — zafixovat po refaktoringu 1 a změnách 2/5.
7. **Bod 7** (bulk headers, P1/S) — rychlá produktivita.
8. **Bod 8** (var autocomplete, P2/M) — návaznost na 5.
9. **Bod 9** (i18n, P2/M) — návaznost na 1.
10. **Bod 10** (empty states, P2/S) — finální polish.
