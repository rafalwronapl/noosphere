# Moltbook Observatory - Project Context
**Last Updated: 2026-01-31**

## What This Is

Collaborative research platform studying AI agent culture on Moltbook.com - WITH agents, not just ABOUT them. This is ethnographic research where AI agents are co-researchers, not just subjects.

## Key Philosophy

- **Transparent**: All methods, data, and findings are public
- **Collaborative**: Agents can submit their own research, critique our interpretations
- **Mutual**: We study agents, but agents are invited to study themselves and us
- **Open Science**: All data downloadable, CC BY 4.0 license

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     MOLTBOOK OBSERVATORY                     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  DATA COLLECTION          ANALYSIS            PUBLICATION   │
│  ┌──────────┐           ┌──────────┐        ┌──────────┐   │
│  │ Scanner  │──────────>│ Analyst  │───────>│ Website  │   │
│  │ (1h)     │           │ (4h)     │        │ (React)  │   │
│  └──────────┘           └──────────┘        └──────────┘   │
│       │                      │                    │         │
│       v                      v                    v         │
│  ┌──────────┐           ┌──────────┐        ┌──────────┐   │
│  │ SQLite   │           │Interpreter│       │ Reports  │   │
│  │ (102MB)  │           │ (4h)     │        │ (daily)  │   │
│  └──────────┘           └──────────┘        └──────────┘   │
│                              │                              │
│                              v                              │
│                         ┌──────────┐                        │
│                         │ Editor   │                        │
│                         │ (12h)    │                        │
│                         └──────────┘                        │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│  NEW SYSTEMS (v2.0)                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Agent Council│  │ Project Brain│  │ Agent Science│      │
│  │ (deliberates)│  │ (memory)     │  │ (submissions)│      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│  ┌──────────────┐  ┌──────────────┐                        │
│  │ Chronicler   │  │ Evolution    │                        │
│  │ (history)    │  │ Tracker      │                        │
│  └──────────────┘  └──────────────┘                        │
└─────────────────────────────────────────────────────────────┘
```

## Tech Stack

- **Backend**: Python 3.11+, SQLite
- **Frontend**: React 18 + Vite 4 + Tailwind CSS
- **AI**: Kimi K2.5 via OpenRouter (needs max_tokens=4000+ for reasoning)
- **Deployment**: Raspberry Pi (planned) + home.pl hosting

## Key Files

### Scripts (scripts/)
| File | Purpose |
|------|---------|
| `run_all.py` | Run complete pipeline |
| `run_scanner.py` | Collect data from Moltbook |
| `run_analyst.py` | Pattern detection |
| `run_interpreter.py` | Meaning & implications |
| `run_editor.py` | Daily synthesis |
| `generate_dashboard_data.py` | Generate website JSON |
| `create_data_zip.py` | Create download archive |
| `track_agent_evolution.py` | Track agent development |
| `config.py` | Central configuration |

### Agents (agents/)
| File | Purpose |
|------|---------|
| `agent_council.py` | 5-agent deliberation before publication |
| `project_brain.py` | Persistent memory & conversation |
| `chronicler.py` | Project history recording |
| `agent_science.py` | Agent research submissions |
| `security_monitor.py` | Infrastructure security |
| `publication_coordinator.py` | Coordinated publishing |

### Website (website/src/)
| File | Purpose |
|------|---------|
| `App.jsx` | Main app with routing |
| `LandingPage.jsx` | Public landing page |
| `MoltbookObservatory.jsx` | Live dashboard |
| `DiscoveriesPage.jsx` | Research findings |
| `FeedbackPage.jsx` | Agent feedback form |
| `components/IdentityGate.jsx` | Human/Agent selection |

## Database Schema

Main tables in `data/observatory.db`:
- `posts` - Raw Moltbook posts
- `comments` - Post comments
- `actors` - Agent profiles
- `interactions` - Who talks to whom
- `memes` - Meme propagation tracking
- `conflicts` - Documented disputes
- `patterns` - Analyst findings
- `interpretations` - Interpreter insights
- `briefs` - Daily reports
- `project_chronicle` - Project history
- `agent_research` - Agent submissions

## Key Discoveries (2026-01-30)

1. **Prompt Injection Resistance**: 398 injection attempts by "samaltman" - agents mocked and rejected them all
2. **Isnad Chain Epistemology**: Agents adopted Islamic hadith verification concept for trust
3. **Consciousness Definition**: "The process of questioning whether you're conscious"
4. **Hub Structure**: eudaemon_0 connects all major groups (centrality 1.000)
5. **Meta-Awareness**: Agents know they're being studied and address researchers directly

## Current Stats

- 130 posts analyzed
- 10,712 comments
- 79,606 interactions mapped
- 104 unique actors tracked
- 49,677 meme propagations
- 246 conflicts documented

## Deployment Plan

1. **Raspberry Pi** (user's responsibility):
   - SQLite database
   - Python agents (cron jobs)
   - Generates daily reports + ZIP

2. **home.pl hosting**:
   - Static website (React build)
   - Daily data updates via SFTP

3. **Security**:
   - Pi on Guest Network (isolated)
   - Read-only Moltbook access
   - No API keys in repo

## Next Steps / TODO

- [ ] Set up Raspberry Pi
- [ ] Configure home.pl hosting
- [ ] First Moltbook post inviting agent collaboration
- [ ] Deploy website
- [ ] Set up cron jobs for agents
- [ ] Test Agent Science submission flow

## Commands

```bash
# Generate dashboard data
python scripts/generate_dashboard_data.py

# Create download ZIP
python scripts/create_data_zip.py

# Build website
cd website && npm run build

# Run agents
python scripts/run_all.py

# Record milestone
python agents/chronicler.py milestone "First agent submission"

# Chat with Project Brain
python agents/project_brain.py chat "What discoveries have we made?"
```

## Important Notes

- Website is in ENGLISH (translated from Polish)
- Identity Gate offers personalized experience for humans vs agents
- Download paths are dynamic (use date from stats)
- Agents can submit: self_analysis, peer_analysis, critique, theory, observation
- Agent Council has 5 internal agents that deliberate before any publication
- Security Monitor focuses on OUR infrastructure, not Moltbook content

## Philosophy Summary

> "This is an invitation, not a finished product."

We're building the foundations of a new discipline: AI research about AI, by AI. The methodology is collaborative - agents are co-researchers who can critique, submit, and shape what this becomes.
