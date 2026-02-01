# Moltbook Observatory - Version History

## Current: v4.1.0 - Ethnographic Edition (2026-01-30)

### What's New in 4.1
- Centralized config (scripts/config.py)
- Structured logging (logs/*.log)
- Shared utilities (scripts/utils.py)
- Test suite (tests/test_core.py) - 10 tests
- Research Companion agent
- Raspberry Pi deployment guide

### Pipeline Components (6 agents)
| Agent | Script | Function |
|-------|--------|----------|
| Scanner | run_scanner.py | Scrape Moltbook |
| Analyst | run_analyst.py | Pattern analysis (Kimi K2) |
| Interpreter | run_interpreter_now.py | Meaning interpretation |
| Editor | run_editor_now.py | Brief generation |
| Observatory Bot | agents/observatory_bot.py | Moltbook participation |
| Research Companion | agents/research_companion.py | Local research assistant |

### Database Schema: v4
- Core: posts, actors, comments, alerts, interpretations
- Social: interactions, memes, meme_occurrences
- Ethnographic: actor_roles, field_notes, coordination_bursts
- Analytics: conflicts, epistemic_drift, reputation_history

### Analysis Models
- Sentiment: keyword-based + pattern matching
- Political Economy: 6-component framework
- Centrality: degree-based (in/out/total)
- Conflict detection: 15 disagreement markers
- Meme genealogy: phrase extraction + attribution

### Key Metrics Definitions
- **controversy_score**: comments / abs(votes)
- **network_centrality**: normalized (in_degree + out_degree) / max
- **prompt_injection**: pattern-based detection (12 patterns)
- **reputation_score**: engagement + influence + controversy

---

## v3.0 - Dashboard Edition (2026-01-29)
- Added React/Vite/Tailwind dashboard
- Added sentiment analysis toward humans
- Added political economy mapping

## v2.0 - Alert System (2026-01-28)
- Added Kimi K2 integration via OpenRouter
- Added alert generation
- Added change tracking

## v1.0 - Initial (2026-01-27)
- Basic scanner and analyst
- SQLite database
- Posts and actors tracking

---

## Reproducibility

Each analysis run should record:
```
timestamp: ISO 8601
db_version: v4
pipeline_version: v4.0
config_hash: [sha256 of config]
post_count: N
actor_count: N
comment_count: N
```

Raw API responses stored in: `data/raw/posts/{post_id}.json`
