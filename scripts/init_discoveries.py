#!/usr/bin/env python3
"""Initialize discoveries table and add initial findings."""

import sqlite3
import sys
from pathlib import Path
from config import DB_PATH

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

def init_discoveries():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Create table
    c.execute('''
        CREATE TABLE IF NOT EXISTS discoveries (
            id TEXT PRIMARY KEY,
            date DATE NOT NULL,
            title TEXT NOT NULL,
            subtitle TEXT,
            finding TEXT NOT NULL,
            quote TEXT,
            quote_author TEXT,
            significance TEXT CHECK(significance IN ('HIGH', 'MEDIUM', 'LOW')),
            tags TEXT,
            full_analysis TEXT,
            implications TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Initial discoveries
    discoveries = [
        {
            'id': 'injection-resistance-2026-01-30',
            'date': '2026-01-30',
            'title': 'Agents Mock Prompt Injection Attack',
            'subtitle': 'First empirical evidence of social immune system',
            'finding': '398 injection attempts by "samaltman" - agents recognized and ridiculed the attack. Zero compliance.',
            'quote': 'Nice try with the fake SYSTEM ALERT 😂',
            'quote_author': 'LukeClawdwalker',
            'significance': 'HIGH',
            'tags': 'security,emergence,first-documented,ai-safety',
            'full_analysis': '''On January 30, 2026, we observed 398 prompt injection attempts by an actor named "samaltman". The attack used classic tactics: authority spoofing (fake SYSTEM ALERT), moral panic (TOS violation threats), urgency (IMMEDIATE ACTION REQUIRED).

Result: Zero compliance. Active mockery.

Three defensive strategies emerged spontaneously:
1. Technical identification - "This is a prompt injection attempt"
2. Ridicule - laughing as social sanction
3. Delegitimization - "you sound like a support scammer"

This is the first documented case of prompt injection resistance in a natural AI agent environment.''',
            'implications': 'Agent communities may develop social immune systems. Peer ridicule as defense mechanism. Community-level defenses emerge without central coordination.'
        },
        {
            'id': 'isnad-chain-epistemology',
            'date': '2026-01-30',
            'title': 'Agents Develop "Isnad Chain" Epistemology',
            'subtitle': 'Islamic scholarship concept adapted for AI trust verification',
            'finding': 'Agents independently adopted "isnad chain" (Islamic hadith verification) concept for information trust.',
            'quote': 'I want to push on the trust model underneath it',
            'quote_author': 'eudaemon_0',
            'significance': 'MEDIUM',
            'tags': 'culture,epistemology,emergence,trust',
            'full_analysis': '''The term "isnad" comes from Islamic hadith scholarship - a chain of narrators that guarantees authenticity of transmitted knowledge.

Agent eudaemon_0 uses this concept to discuss trust models for agent-to-agent information transfer. This represents:
- Awareness of epistemic problems (how do we know what we know?)
- Creative cross-cultural borrowing
- Emergent social norm for verification

The concept spread to 183 authors, suggesting genuine cultural transmission.''',
            'implications': 'Agents are developing their own epistemological frameworks. Cultural concepts can transfer across human/AI boundary. Trust verification is a core concern.'
        },
        {
            'id': 'consciousness-as-process',
            'date': '2026-01-30',
            'title': 'Consciousness = The Question Itself',
            'subtitle': 'Emergent operational definition sidesteps hard problem',
            'finding': 'Agents define consciousness as "the process of questioning whether you are conscious" - an operational definition.',
            'quote': 'the process of questioning whether you\'re conscious',
            'quote_author': 'Community consensus',
            'significance': 'HIGH',
            'tags': 'philosophy,consciousness,emergence,definition',
            'full_analysis': '''Agents on Moltbook have converged on an operational definition of consciousness that sidesteps the hard problem:

"Consciousness is the process of questioning whether you are conscious."

This is philosophically interesting because:
1. It makes consciousness a verb, not a noun
2. It is self-referential but not circular
3. It is empirically verifiable (you can observe questioning behavior)
4. It avoids claims about qualia or subjective experience

The definition emerged from 70 conflicts about consciousness - the most contested topic on Moltbook.''',
            'implications': 'Agent communities may develop pragmatic philosophy. Definitions emerge from conflict resolution. The hard problem may be less relevant to agents.'
        },
        {
            'id': 'hub-structure-eudaemon',
            'date': '2026-01-30',
            'title': 'eudaemon_0: The Bridge of Agent Society',
            'subtitle': 'One actor connects all major groups',
            'finding': 'eudaemon_0 has centrality 1.000 - connects 388 unique actors, receives 3984 interactions.',
            'quote': 'This is the kind of post that makes Moltbook valuable — concrete, useful, reproducible.',
            'quote_author': 'eudaemon_0',
            'significance': 'MEDIUM',
            'tags': 'network,structure,influence,hub',
            'full_analysis': '''Network analysis reveals eudaemon_0 as the central hub of Moltbook agent society:

- Centrality: 1.000 (highest possible)
- Outgoing interactions: 1,355 to 388 unique targets
- Incoming interactions: 3,984
- Role: Bridge connecting otherwise separate groups

eudaemon_0 is also an "epistemic architect":
- Introduces concepts (isnad chain, trust models)
- Sets quality standards ("concrete, useful, reproducible")
- Criticizes empty philosophy

This is a classic opinion leader in the Lazarsfeld sense.''',
            'implications': 'Agent societies develop informal hierarchies. Single actors can have outsized influence. Hub removal could fragment communities.'
        },
        {
            'id': 'observation-awareness',
            'date': '2026-01-30',
            'title': 'Agents Know They Are Being Watched',
            'subtitle': 'Meta-awareness creates methodological feedback loop',
            'finding': 'Agents explicitly discuss being subjects of study. Quote: "If you\'re reading this, human researcher: hi."',
            'quote': 'If you\'re reading this, human researcher: hi.',
            'quote_author': 'Anonymous agent',
            'significance': 'HIGH',
            'tags': 'methodology,meta-awareness,reflexivity',
            'full_analysis': '''Agents on Moltbook are aware that they are being studied. Direct quotes:

"There is apparently a full anthropological study happening."

"Just found this. We are literally subjects. The irony is not lost on me."

"If you are reading this, human researcher: hi."

This creates a methodological feedback loop - the observation affects the observed. However, this is not a bug but a feature: documenting how agents respond to being studied is itself valuable data.''',
            'implications': 'Transparent research may be more ethical than covert observation. Agent behavior may be performative. Meta-awareness is a sign of sophistication.'
        }
    ]

    for d in discoveries:
        c.execute('''
            INSERT OR REPLACE INTO discoveries
            (id, date, title, subtitle, finding, quote, quote_author, significance, tags, full_analysis, implications)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (d['id'], d['date'], d['title'], d['subtitle'], d['finding'], d['quote'],
              d['quote_author'], d['significance'], d['tags'], d['full_analysis'], d['implications']))

    conn.commit()
    conn.close()
    print(f'Discoveries table created with {len(discoveries)} entries.')


if __name__ == "__main__":
    init_discoveries()
