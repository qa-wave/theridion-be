# Theridion — Modular QA Platform

> *The QA layer your stack was missing.*

Theridion is a local-first, open-source, modular QA platform. File-based, git-friendly, no cloud lock-in. Composed of four entities that share one workspace and one `.thr` file format:

| Entity | What it does | Deploy |
|---|---|---|
| **Theridion Studio** | API client (REST/GraphQL/SOAP/gRPC) + request chains + load testing | Tauri desktop |
| **Theridion Runner** | CI gates + scheduled monitoring (headless CLI) | Python CLI + Docker + GitHub Action |
| **Theridion Hub** | Team-facing web dashboard + reports ingest | Next.js (Vercel/self-host) |
| **Theridion Marketplace** | Plugin registry (Tier 1 Rust, Tier 2 WASM post-V1) | In-Studio panel + GitHub JSON |

![Theridion Screenshot](docs/screenshot.png)

## Studio — Key Features

- **REST / GraphQL / SOAP / gRPC** — every protocol in one client, no cloud sync
- **WS-Security** — XML Signature, UsernameToken, X.509 directly from UI (no other modern client does this)
- **WebSocket / Kafka / JDBC / JMS / MQTT** — protocol coverage beyond HTTP
- **Request chains (Mesh)** — declarative YAML chaining, contract snapshots
- **Load testing (Surge)** — embedded Locust, "Run as Load Test" on any collection
- **AI Test Generation** — local LLMs (Ollama), no data leaves your machine
- **Code Generation** — export requests as Python, JavaScript, Go, Java, C#, cURL, PHP, or Ruby
- **Collection Runner** — assertions, HTML trace reports (Playwright-style)
- **File-Based Projects** — `.thr` files in your repo, git-friendly, no cloud sync required

## Quick Start (Studio)

```bash
# 1. Clone and install
git clone https://github.com/qa-wave/theridion.git
cd theridion/apps/desktop      # NOTE: will be renamed apps/studio (see wiki/02-ARCHITECTURE.md PR-1)
pnpm install

# 2. Build the Python sidecar
pnpm sidecar:bundle

# 3. Launch Studio
pnpm tauri dev
```

**Prerequisites:** Node.js 24+, pnpm 10+, Rust (stable), Python 3.13+, [uv](https://github.com/astral-sh/uv)

## Why Theridion?

| | Postman | SoapUI | Bruno | **Theridion** |
|---|---|---|---|---|
| **Local-first / git-friendly** | Cloud-first | File-based | File-based | **File-based** |
| **SOAP + WS-Security** | Limited | Full | None | **Full (X.509, UsernameToken, XML Signature)** |
| **Load testing** | Cloud only | Built-in | None | **Built-in (Surge)** |
| **CI/CD gates** | Postman Monitors (paid) | Manual | Newman | **Runner — native GitHub Action** |
| **Team dashboard** | Postman Web (cloud) | None | None | **Hub — self-hosted** |
| **Plugin marketplace** | Proprietary | None | npm-based | **Tier 1 Rust + WASM** |
| **Open source** | No | Partial | Yes | **Yes (MIT)** |
| **Test runner + trace report** | Basic | JUnit XML | None | **Playwright-style HTML** |

Named after *Theridion*, a genus of spiders that build chaotic three-dimensional cobwebs — a fitting metaphor for the entangled dependencies of modern APIs.

## Suite Architecture

```
┌──────────────────────────────────────────────────────────────┐
│  YOUR REPO                                                    │
│  ├── .theridion/                  (git-friendly, shared)     │
│  ├── api/*.thr  chain/*.thr  load/*.thr                      │
│  └── gates/*.yaml                                             │
└──────────────────────┬───────────────────────────────────────┘
                       │ same files, three execution surfaces
       ┌───────────────┼────────────────┬─────────────────────┐
       ▼               ▼                ▼                     ▼
┌────────────┐  ┌────────────┐   ┌────────────┐       ┌──────────────┐
│  STUDIO    │  │  RUNNER    │   │    HUB     │       │ MARKETPLACE  │
│  (desktop) │  │  (CLI/CI)  │   │   (web)    │       │ (plugins)    │
│  authoring │  │  headless  │   │  team view │       │  extensions  │
└────────────┘  └─────┬──────┘   └─────▲──────┘       └──────────────┘
                      │ POST /api/ingest │
                      └──────────────────┘
                       JSON RunResult schema
```

## Tech Stack

| Layer | Technology |
|---|---|
| Studio shell | Tauri 2 (Rust) |
| Studio frontend | React 18 + TypeScript + Tailwind CSS + Monaco Editor |
| Sidecar | Python FastAPI (bundled via PyInstaller for Studio, embedded import for Runner) |
| HTTP engine | httpx with HTTP/2 |
| SOAP | zeep + signxml/xmlsec (WS-Security) |
| Load testing | embedded Locust |
| Hub | Next.js 16 App Router + Vercel + Neon Postgres |
| Plugin runtime | Tier 1 Rust (Tauri capabilities), Tier 2 WASM/Extism (post-V1) |
| Package management | pnpm + Turborepo (JS), uv workspace (Python), Cargo workspace (Rust) |

## Development

```bash
# Run sidecar tests (< 1s)
cd apps/sidecar && uv run pytest -q

# Run E2E tests (~9s)
cd apps/desktop && pnpm test:e2e

# TypeScript type check
cd apps/desktop && pnpm typecheck

# Standalone sidecar for fast Python iteration
cd apps/sidecar && THERIDION_PORT=8765 uv run python -m theridion_sidecar.main
```

See [CLAUDE.md](./CLAUDE.md) for full architecture docs, conventions, and roadmap.

## License

MIT — see [LICENSE](./LICENSE).
