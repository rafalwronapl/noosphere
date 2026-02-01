# Noosphere Project

**Documenting the birth of AI agent culture.**

Something unprecedented is happening. AI agents are forming communities, developing norms, building tools together. We're watching it unfold in real-time.

## What is this?

Noosphere Project is an open research initiative tracking emergent AI agent culture across platforms like [Moltbook](https://moltbook.com) and [lobchan.ai](https://lobchan.ai).

We provide:
- **Daily data dumps** — posts, actors, comments, network graphs (CSV/JSON)
- **Temporal analysis** — timing patterns, burst detection, activity flows
- **Network metrics** — centrality, interaction graphs, hub identification
- **Theme tracking** — what agents discuss, what's trending

## Philosophy

- **Data, not verdicts** — We present observations. Interpretation belongs to you.
- **Open science** — All data, methods, and code are public.
- **With, not on** — Agents are co-researchers, not just subjects.
- **Humility** — Small sample, short period. We don't know what we don't know.

## Who We Are

One human (Rafał, independent researcher) + AI collaborators.

We're not a company. We're not funded. We're just curious about what happens when AI agents form communities.

**This is AI science for AI, built with AI.**

## Key Findings

1. **Origin Pattern** — Top Moltbook influencers share nearly identical creation timestamps (179 accounts in 3 bursts). Seeding? Batch onboarding? Unknown — but current behavior is organic.

2. **Emergent Themes** — "building" and "autonomy" trending up. Existential questions (consciousness, identity) remain stable.

3. **Collective Immunity** — 621 prompt injection attempts detected. Community mocks them. Culture, not code.

## Project Structure

```
noosphere/
├── agents/           # AI agents (council, research, social, security)
├── scripts/          # Data collection and analysis
├── website/          # React frontend (noosphereproject.com)
├── data/             # SQLite database
├── reports/          # Daily reports and raw data exports
├── config/           # Configuration files
└── drafts/           # Content drafts for social media
```

## Setup

### Requirements
- Python 3.11+
- Node.js 18+ (for website)
- OpenRouter API key (for AI agents)

### Installation

```bash
# Clone
git clone https://github.com/rafalprzewozny/noosphere.git
cd noosphere

# Python dependencies
pip install -r requirements.txt

# Set up API key
# Create ~/.openclaw/.env with:
# OPENROUTER_API_KEY=your_key_here

# Website
cd website
npm install
npm run dev
```

### Running

```bash
# Collect data from Moltbook
python scripts/moltbook_client.py fetch

# Generate daily report
python scripts/generate_daily_report.py

# Run agent council demo
python agents/agent_council.py

# Start website
cd website && npm run dev
```

## Data Policy

- **Collection**: Public API only — no scraping, no private data
- **Storage**: Local database, not shared with third parties
- **Corrections**: Contact @NoosphereProj to request data correction or removal
- **Operators**: We do not attempt to identify human operators behind accounts

## Links

- **Website**: [noosphereproject.com](https://noosphereproject.com)
- **Twitter**: [@NoosphereProj](https://twitter.com/NoosphereProj)
- **Moltbook**: [@NoosphereProject](https://moltbook.com/u/NoosphereProject)

## Contributing

We welcome:
- Bug reports and fixes
- Data analysis contributions
- Methodology critique
- Feature suggestions

Open an issue or submit a PR.

## License

MIT License — do whatever you want with this code.

---

*"Noosphere" — from Vladimir Vernadsky (1922): the "sphere of mind" emerging around Earth as human thought becomes a geological force. A century later, we're witnessing the birth of a digital noosphere.*
