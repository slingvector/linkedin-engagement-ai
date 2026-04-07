# Important Engineering Notes

## Core Principles

All development follows **SOLID principles** with strict separation of concerns:

- **Single Responsibility** — one reason to change per class/module
- **Open/Closed** — extend via new services, never modify existing ones
- **Dependency Inversion** — inject via FastAPI `Depends`, never instantiate inside handlers

**Critical constraints:**

| Rule | Detail |
|------|--------|
| **NO HARDCODING** | Business logic params, API URLs, thresholds → YAML / `.env` only |
| **Environment Parity** | Runs identically on dev machine and Docker container |
| **Traceability** | All decisions (weights, retry counts, timeouts) configurable without code changes |
| **Portability** | "Runs on my machine" is not acceptable — Docker proves it |

## Standards Reference

See [DEVELOPER_STANDARDS.md](DEVELOPER_STANDARDS.md) for the complete backend + frontend rulebook.