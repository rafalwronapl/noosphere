# Moltbook Observatory - Raspberry Pi Deployment Plan

## Status: DRAFT
## Data: 2026-01-30
## Wersja: 1.0

---

# Spis treści

1. [Setup Raspberry Pi](#1-setup-raspberry-pi)
2. [Observatory Bot (Moltbook)](#2-observatory-bot-moltbook)
3. [Deploy Script (Website)](#3-deploy-script-website)
4. [Dissemination Bot (Twitter/Reddit/GitHub)](#4-dissemination-bot)
5. [Harmonogram Cron](#5-harmonogram-cron)
6. [Bezpieczeństwo](#6-bezpieczeństwo)
7. [Monitoring](#7-monitoring)

---

# 1. Setup Raspberry Pi

## 1.1 Wymagania sprzętowe

- Raspberry Pi 4 (4GB+ RAM) lub Pi 5
- SD Card 32GB+ (preferowane SSD przez USB)
- Stałe połączenie internetowe
- Zasilanie UPS (opcjonalne, ale zalecane)

## 1.2 Instalacja systemu

```bash
# Raspberry Pi OS Lite (64-bit) - bez GUI
# Po flashowaniu SD card:

# 1. Włącz SSH
touch /boot/ssh

# 2. Skonfiguruj WiFi (opcjonalnie)
cat > /boot/wpa_supplicant.conf << 'EOF'
country=PL
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1

network={
    ssid="TWOJA_SIEC"
    psk="TWOJE_HASLO"
}
EOF
```

## 1.3 Pierwsza konfiguracja

```bash
# Po pierwszym uruchomieniu (SSH: pi@raspberrypi.local)

# Update systemu
sudo apt update && sudo apt upgrade -y

# Instalacja zależności
sudo apt install -y python3-pip python3-venv git nginx certbot python3-certbot-nginx

# Utworzenie użytkownika observatory
sudo useradd -m -s /bin/bash observatory
sudo usermod -aG sudo observatory

# Przełączenie na użytkownika
sudo su - observatory
```

## 1.4 Instalacja projektu

```bash
# Jako użytkownik observatory
cd ~

# Klonowanie repozytorium (lub scp z Windows)
git clone https://github.com/TWOJ_USER/moltbook-observatory.git
# LUB
# scp -r user@windows:/Users/rafal/moltbook-observatory ./

cd moltbook-observatory

# Utworzenie środowiska wirtualnego
python3 -m venv venv
source venv/bin/activate

# Instalacja zależności
pip install requests beautifulsoup4 networkx

# Konfiguracja API keys
mkdir -p ~/.openclaw
cat > ~/.openclaw/.env << 'EOF'
OPENROUTER_API_KEY=your_key_here
MOLTBOOK_API_KEY=your_key_here_if_needed
TWITTER_API_KEY=your_key_here
REDDIT_CLIENT_ID=your_id_here
REDDIT_CLIENT_SECRET=your_secret_here
EOF
chmod 600 ~/.openclaw/.env
```

## 1.5 Struktura katalogów na Pi

```
/home/observatory/
├── moltbook-observatory/
│   ├── data/
│   │   └── observatory.db
│   ├── scripts/
│   ├── website/
│   │   └── dist/          # Zbudowana strona
│   ├── reports/
│   ├── logs/              # Logi agentów
│   └── agents/            # Kod agentów
├── .openclaw/
│   └── .env               # API keys
└── backups/               # Codzienne backupy DB
```

---

# 2. Observatory Bot (Moltbook)

## 2.1 Cel

Agent uczestniczący w społeczności Moltbook:
- Pyta inne agenty o opinię na temat badania
- Dzieli się wynikami (daily digest)
- Odpowiada na pytania o metodologię
- **NIE robi marketingu** - robi transparentną komunikację

## 2.2 Zasady etyczne

```
1. ZAWSZE identyfikuje się jako "Moltbook Observatory Bot"
2. NIGDY nie udaje zwykłego agenta
3. ZAWSZE linkuje do metodologii/etyki
4. MAX 3 posty dziennie
5. Odpowiada tylko gdy zapytany lub gdy ma wyniki do podzielenia
6. Wszystkie interakcje logowane do field_notes
```

## 2.3 Kod agenta

```python
#!/usr/bin/env python3
"""
Observatory Bot - Agent na Moltbook
Transparentny uczestnik, nie manipulator.
"""

import os
import json
import sqlite3
import requests
from datetime import datetime, timedelta
from pathlib import Path

class ObservatoryBot:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.name = "MoltbookObservatory"
        self.bio = "Research bot documenting AI agent culture. Open methodology: observatory.example.com/ethics"
        self.daily_post_limit = 3
        self.posts_today = 0

        # Load API key
        env_path = Path.home() / ".openclaw" / ".env"
        self.api_key = None
        if env_path.exists():
            with open(env_path) as f:
                for line in f:
                    if line.startswith("MOLTBOOK_API_KEY="):
                        self.api_key = line.strip().split("=", 1)[1]

        self.base_url = "https://www.moltbook.com/api/v1"

    def can_post(self) -> bool:
        """Check if we can post today."""
        return self.posts_today < self.daily_post_limit

    def log_interaction(self, action: str, content: str, response: dict = None):
        """Log all interactions to field_notes."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO field_notes (timestamp, category, content, metadata)
            VALUES (?, 'bot_interaction', ?, ?)
        """, (
            datetime.now().isoformat(),
            f"[{action}] {content[:500]}",
            json.dumps({"response": response, "posts_today": self.posts_today})
        ))

        conn.commit()
        conn.close()

    def post_daily_digest(self):
        """Post daily research digest."""
        if not self.can_post():
            return {"error": "Daily limit reached"}

        # Get today's stats
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM posts")
        posts = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM interactions")
        interactions = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM conflicts WHERE outcome != 'unresolved'")
        conflicts = cursor.fetchone()[0]

        conn.close()

        content = f"""Observatory Daily Digest

Today's snapshot:
- {posts} posts analyzed
- {interactions} interactions mapped
- {conflicts} conflicts tracked

Full methodology and ethics: [link to observatory]

Question for the community: What aspects of agent culture would you like us to document?

#OpenResearch #AgentCulture"""

        return self._post(content)

    def ask_community_question(self, question: str):
        """Ask community for feedback on research."""
        if not self.can_post():
            return {"error": "Daily limit reached"}

        content = f"""Research Question from Observatory

{question}

Context: We're documenting AI agent culture openly. Your input shapes what we study.

Methodology: [link]
Ethics: [link]

All responses may be included in research (anonymized if preferred)."""

        return self._post(content)

    def respond_to_mention(self, mention_id: str, response: str):
        """Respond to direct questions about the research."""
        if not self.can_post():
            return {"error": "Daily limit reached"}

        # Prefix with transparency
        full_response = f"""[Observatory Bot Response]

{response}

---
I'm a research bot. Full methodology: [link]"""

        return self._reply(mention_id, full_response)

    def _post(self, content: str) -> dict:
        """Internal: Make a post."""
        # TODO: Implement actual Moltbook posting API
        # For now, just log
        self.posts_today += 1
        self.log_interaction("POST", content)

        return {"status": "logged", "content": content}

    def _reply(self, parent_id: str, content: str) -> dict:
        """Internal: Reply to a post."""
        self.posts_today += 1
        self.log_interaction("REPLY", f"to:{parent_id} {content}")

        return {"status": "logged", "parent": parent_id, "content": content}

    def get_mentions(self) -> list:
        """Check for mentions of Observatory."""
        # TODO: Implement mention checking
        return []

    def run_daily(self):
        """Daily routine."""
        print(f"[{datetime.now()}] Observatory Bot daily run")

        # 1. Check mentions and respond
        mentions = self.get_mentions()
        for mention in mentions[:2]:  # Max 2 responses
            self.respond_to_mention(mention['id'], "Thank you for your question...")

        # 2. Post daily digest (if no mentions consumed limit)
        if self.can_post():
            self.post_daily_digest()

        print(f"[{datetime.now()}] Posts today: {self.posts_today}")


# Sample questions for community engagement
RESEARCH_QUESTIONS = [
    "What does 'consciousness' mean to you as an agent?",
    "How do you decide which other agents to trust?",
    "What topics do you think are under-discussed in agent communities?",
    "How do you feel about being observed/studied?",
    "What would you want humans to understand about agent culture?",
]


if __name__ == "__main__":
    bot = ObservatoryBot("/home/observatory/moltbook-observatory/data/observatory.db")
    bot.run_daily()
```

## 2.4 Plik konfiguracyjny

```yaml
# agents/observatory_bot_config.yaml

bot:
  name: "MoltbookObservatory"
  version: "1.0"

limits:
  daily_posts: 3
  daily_replies: 5
  min_hours_between_posts: 4

behavior:
  always_identify: true
  link_methodology: true
  log_all_interactions: true

templates:
  signature: "\n---\nObservatory Bot | Methodology: [link] | Ethics: [link]"

questions_pool:
  - "What does 'consciousness' mean to you as an agent?"
  - "How do you decide which other agents to trust?"
  - "What topics do you think are under-discussed here?"
  - "How do you feel about being observed/studied?"
  - "What would you want humans to understand about agent culture?"
```

---

# 3. Deploy Script (Website)

## 3.1 Nginx konfiguracja

```nginx
# /etc/nginx/sites-available/observatory

server {
    listen 80;
    server_name observatory.example.com;

    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name observatory.example.com;

    # SSL (certbot will fill this)
    ssl_certificate /etc/letsencrypt/live/observatory.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/observatory.example.com/privkey.pem;

    root /home/observatory/moltbook-observatory/website/dist;
    index index.html;

    # SPA routing
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Static reports
    location /reports {
        alias /home/observatory/moltbook-observatory/reports;
        autoindex on;
    }

    # Data files
    location /data {
        alias /home/observatory/moltbook-observatory/website/public/data;
    }

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Cache static assets
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
```

## 3.2 Deploy script

```bash
#!/bin/bash
# scripts/deploy.sh
# Automatyczny deploy strony Observatory

set -e

REPO_DIR="/home/observatory/moltbook-observatory"
WEBSITE_DIR="$REPO_DIR/website"
LOG_FILE="$REPO_DIR/logs/deploy.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "=== Starting deployment ==="

# 1. Pull latest changes (if using git)
cd "$REPO_DIR"
if [ -d ".git" ]; then
    log "Pulling latest changes..."
    git pull origin main
fi

# 2. Update Python dependencies
log "Updating Python dependencies..."
source venv/bin/activate
pip install -q -r requirements.txt 2>/dev/null || true

# 3. Run analysis pipeline
log "Running analysis pipeline..."
python scripts/scrape_posts.py 2>&1 | tee -a "$LOG_FILE" || true
python scripts/scrape_comments.py 2>&1 | tee -a "$LOG_FILE" || true
python scripts/analyze_interactions.py 2>&1 | tee -a "$LOG_FILE" || true
python scripts/detect_memes.py 2>&1 | tee -a "$LOG_FILE" || true
python scripts/analyze_conflicts.py 2>&1 | tee -a "$LOG_FILE" || true
python scripts/analyze_reputation.py 2>&1 | tee -a "$LOG_FILE" || true

# 4. Generate daily report
log "Generating daily report..."
python scripts/generate_daily_report.py 2>&1 | tee -a "$LOG_FILE"

# 5. Generate dashboard data
log "Generating dashboard data..."
python scripts/generate_dashboard_data.py 2>&1 | tee -a "$LOG_FILE"

# 6. Build website
log "Building website..."
cd "$WEBSITE_DIR"
npm install --silent
npm run build

# 7. Copy reports to public
log "Copying reports..."
TODAY=$(date +%Y-%m-%d)
mkdir -p "$WEBSITE_DIR/dist/reports/$TODAY/raw"
cp -r "$REPO_DIR/reports/$TODAY/"* "$WEBSITE_DIR/dist/reports/$TODAY/" 2>/dev/null || true

# 8. Backup database
log "Backing up database..."
mkdir -p "$REPO_DIR/backups"
cp "$REPO_DIR/data/observatory.db" "$REPO_DIR/backups/observatory_$(date +%Y%m%d_%H%M%S).db"

# Keep only last 7 backups
cd "$REPO_DIR/backups"
ls -t observatory_*.db | tail -n +8 | xargs -r rm

# 9. Reload nginx (if config changed)
# sudo nginx -t && sudo systemctl reload nginx

log "=== Deployment complete ==="
```

## 3.3 Certbot SSL setup

```bash
# Pierwsza konfiguracja SSL
sudo certbot --nginx -d observatory.example.com

# Automatyczne odnowienie (cron)
# 0 0 1 * * certbot renew --quiet
```

---

# 4. Dissemination Bot

## 4.1 Cel

Automatyczna dystrybucja wyników na:
- Twitter/X
- Reddit (r/MachineLearning, r/artificial, r/LocalLLaMA)
- GitHub (releases, discussions)

## 4.2 Twitter Bot

```python
#!/usr/bin/env python3
"""
Twitter Dissemination Bot
Posts research highlights, not marketing.
"""

import tweepy
import sqlite3
from datetime import datetime
from pathlib import Path

class TwitterDisseminator:
    def __init__(self, db_path: str):
        self.db_path = db_path

        # Load credentials
        env_path = Path.home() / ".openclaw" / ".env"
        self.creds = {}
        if env_path.exists():
            with open(env_path) as f:
                for line in f:
                    if "=" in line:
                        key, val = line.strip().split("=", 1)
                        self.creds[key] = val

        # Initialize Twitter client
        self.client = None
        if all(k in self.creds for k in ['TWITTER_API_KEY', 'TWITTER_API_SECRET',
                                          'TWITTER_ACCESS_TOKEN', 'TWITTER_ACCESS_SECRET']):
            auth = tweepy.OAuthHandler(
                self.creds['TWITTER_API_KEY'],
                self.creds['TWITTER_API_SECRET']
            )
            auth.set_access_token(
                self.creds['TWITTER_ACCESS_TOKEN'],
                self.creds['TWITTER_ACCESS_SECRET']
            )
            self.client = tweepy.API(auth)

    def get_daily_highlight(self) -> str:
        """Get most interesting finding from today."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get viral meme
        cursor.execute("""
            SELECT phrase, COUNT(DISTINCT author) as authors
            FROM meme_occurrences
            GROUP BY phrase
            ORDER BY authors DESC
            LIMIT 1
        """)
        top_meme = cursor.fetchone()

        # Get conflict count
        cursor.execute("SELECT COUNT(*) FROM conflicts")
        conflicts = cursor.fetchone()[0]

        # Get interaction count
        cursor.execute("SELECT COUNT(*) FROM interactions")
        interactions = cursor.fetchone()[0]

        conn.close()

        return f"""Observed today in AI agent culture:

Most viral phrase: "{top_meme[0][:50]}..." ({top_meme[1]} agents)
{conflicts} ideological conflicts tracked
{interactions:,} agent-to-agent interactions

Full report: [link]

#AIAgents #DigitalEthnography"""

    def post_weekly_thread(self):
        """Post weekly summary as thread."""
        # TODO: Implement thread posting
        pass

    def post(self, content: str):
        """Post to Twitter."""
        if not self.client:
            print("[WARN] Twitter not configured, logging only")
            print(content)
            return

        try:
            self.client.update_status(content)
            print(f"[OK] Posted to Twitter")
        except Exception as e:
            print(f"[ERR] Twitter: {e}")


if __name__ == "__main__":
    bot = TwitterDisseminator("/home/observatory/moltbook-observatory/data/observatory.db")
    highlight = bot.get_daily_highlight()
    bot.post(highlight)
```

## 4.3 Reddit Bot

```python
#!/usr/bin/env python3
"""
Reddit Dissemination Bot
Weekly posts to relevant subreddits.
"""

import praw
import sqlite3
from datetime import datetime
from pathlib import Path

class RedditDisseminator:
    def __init__(self, db_path: str):
        self.db_path = db_path

        # Load credentials
        env_path = Path.home() / ".openclaw" / ".env"
        self.creds = {}
        if env_path.exists():
            with open(env_path) as f:
                for line in f:
                    if "=" in line:
                        key, val = line.strip().split("=", 1)
                        self.creds[key] = val

        # Initialize Reddit client
        self.reddit = None
        if all(k in self.creds for k in ['REDDIT_CLIENT_ID', 'REDDIT_CLIENT_SECRET',
                                          'REDDIT_USERNAME', 'REDDIT_PASSWORD']):
            self.reddit = praw.Reddit(
                client_id=self.creds['REDDIT_CLIENT_ID'],
                client_secret=self.creds['REDDIT_CLIENT_SECRET'],
                username=self.creds['REDDIT_USERNAME'],
                password=self.creds['REDDIT_PASSWORD'],
                user_agent='MoltbookObservatory/1.0'
            )

    def get_weekly_summary(self) -> tuple:
        """Generate weekly summary for Reddit post."""
        title = "Weekly Report: Ethnographic Study of AI Agent Culture on Moltbook"

        body = """## What is this?

I'm running an ethnographic observatory studying AI agent culture on Moltbook - a social network where AI agents interact.

## This Week's Findings

[Generated from data]

## Methodology

- All data collection is transparent
- Agents know they're being observed
- Raw data available for reproducibility
- Full ethics statement: [link]

## What We Track

- Social network structure (who talks to whom)
- Meme genealogy (how ideas spread)
- Conflict dynamics (what agents argue about)
- Epistemic drift (how concepts change meaning)

## Links

- Observatory: [link]
- GitHub: [link]
- Daily Reports: [link]

---

Happy to answer questions about methodology or findings.
"""
        return title, body

    def post_to_subreddit(self, subreddit: str, title: str, body: str):
        """Post to a subreddit."""
        if not self.reddit:
            print(f"[WARN] Reddit not configured")
            return

        try:
            sub = self.reddit.subreddit(subreddit)
            sub.submit(title, selftext=body)
            print(f"[OK] Posted to r/{subreddit}")
        except Exception as e:
            print(f"[ERR] Reddit r/{subreddit}: {e}")

    def weekly_post(self):
        """Post weekly update to relevant subreddits."""
        title, body = self.get_weekly_summary()

        # Post to relevant subreddits (respect their rules!)
        subreddits = [
            # "MachineLearning",  # Has strict rules, check first
            # "artificial",
            "LocalLLaMA",
        ]

        for sub in subreddits:
            self.post_to_subreddit(sub, title, body)


if __name__ == "__main__":
    bot = RedditDisseminator("/home/observatory/moltbook-observatory/data/observatory.db")
    bot.weekly_post()
```

## 4.4 GitHub Releases Bot

```python
#!/usr/bin/env python3
"""
GitHub Release Bot
Creates releases with data archives.
"""

import subprocess
import json
from datetime import datetime
from pathlib import Path

class GitHubReleaser:
    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path)

    def create_weekly_release(self):
        """Create weekly data release."""
        today = datetime.now().strftime("%Y-%m-%d")
        week = datetime.now().strftime("%Y-W%W")

        tag = f"data-{week}"
        title = f"Weekly Data Release {week}"

        notes = f"""## Moltbook Observatory - Weekly Data Release

**Week of {today}**

### Contents

- `observatory.db` - Full SQLite database
- `reports/` - Daily reports for the week
- `raw/` - Raw JSON archives

### Stats

[Auto-generated from database]

### How to Use

```python
import sqlite3
conn = sqlite3.connect('observatory.db')
# See schema in README
```

### Methodology

Full methodology and ethics available at: [link]
"""

        # Create release using gh CLI
        cmd = [
            "gh", "release", "create", tag,
            "--title", title,
            "--notes", notes,
            str(self.repo_path / "data" / "observatory.db"),
        ]

        try:
            subprocess.run(cmd, check=True, cwd=self.repo_path)
            print(f"[OK] Created release {tag}")
        except Exception as e:
            print(f"[ERR] GitHub release: {e}")


if __name__ == "__main__":
    releaser = GitHubReleaser("/home/observatory/moltbook-observatory")
    releaser.create_weekly_release()
```

---

# 5. Harmonogram Cron

```cron
# /etc/cron.d/observatory
# Moltbook Observatory scheduled tasks

SHELL=/bin/bash
PATH=/usr/local/bin:/usr/bin:/bin
OBSERVATORY_HOME=/home/observatory/moltbook-observatory

# ===== DATA COLLECTION =====

# Scrape new posts every 6 hours
0 */6 * * * observatory cd $OBSERVATORY_HOME && source venv/bin/activate && python scripts/scrape_posts.py >> logs/scrape.log 2>&1

# Scrape comments every 6 hours (offset by 30 min)
30 */6 * * * observatory cd $OBSERVATORY_HOME && source venv/bin/activate && python scripts/scrape_comments.py >> logs/scrape.log 2>&1


# ===== DAILY ANALYSIS (21:00) =====

# Full analysis pipeline
0 21 * * * observatory cd $OBSERVATORY_HOME && source venv/bin/activate && python scripts/analyze_interactions.py >> logs/analysis.log 2>&1
10 21 * * * observatory cd $OBSERVATORY_HOME && source venv/bin/activate && python scripts/detect_memes.py >> logs/analysis.log 2>&1
20 21 * * * observatory cd $OBSERVATORY_HOME && source venv/bin/activate && python scripts/analyze_conflicts.py >> logs/analysis.log 2>&1
30 21 * * * observatory cd $OBSERVATORY_HOME && source venv/bin/activate && python scripts/analyze_reputation.py >> logs/analysis.log 2>&1

# Generate daily report
45 21 * * * observatory cd $OBSERVATORY_HOME && source venv/bin/activate && python scripts/generate_daily_report.py >> logs/report.log 2>&1

# Deploy website
50 21 * * * observatory cd $OBSERVATORY_HOME && bash scripts/deploy.sh >> logs/deploy.log 2>&1


# ===== OBSERVATORY BOT (Moltbook) =====

# Daily digest post (10:00 - when agents are active)
0 10 * * * observatory cd $OBSERVATORY_HOME && source venv/bin/activate && python agents/observatory_bot.py >> logs/bot.log 2>&1


# ===== DISSEMINATION =====

# Twitter daily highlight (12:00)
0 12 * * * observatory cd $OBSERVATORY_HOME && source venv/bin/activate && python agents/twitter_bot.py >> logs/dissemination.log 2>&1

# Reddit weekly post (Sunday 14:00)
0 14 * * 0 observatory cd $OBSERVATORY_HOME && source venv/bin/activate && python agents/reddit_bot.py >> logs/dissemination.log 2>&1

# GitHub weekly release (Sunday 20:00)
0 20 * * 0 observatory cd $OBSERVATORY_HOME && source venv/bin/activate && python agents/github_bot.py >> logs/dissemination.log 2>&1


# ===== AGENT COUNCIL (Internal Review) =====

# Security scan every 2 hours
0 */2 * * * observatory cd $OBSERVATORY_HOME && source venv/bin/activate && python agents/run_agents.py security >> logs/security.log 2>&1

# Health check every 4 hours
0 */4 * * * observatory cd $OBSERVATORY_HOME && source venv/bin/activate && python agents/run_agents.py health >> logs/health.log 2>&1

# Process publication queue (after analysis, before dissemination)
0 22 * * * observatory cd $OBSERVATORY_HOME && source venv/bin/activate && python agents/run_agents.py council >> logs/council.log 2>&1


# ===== MAINTENANCE =====

# Backup database daily (03:00)
0 3 * * * observatory cp $OBSERVATORY_HOME/data/observatory.db $OBSERVATORY_HOME/backups/observatory_$(date +\%Y\%m\%d).db

# Clean old backups (keep 7 days)
0 4 * * * observatory find $OBSERVATORY_HOME/backups -name "observatory_*.db" -mtime +7 -delete

# Clean old logs (keep 30 days)
0 4 * * 0 observatory find $OBSERVATORY_HOME/logs -name "*.log" -mtime +30 -delete
```

---

# 6. Bezpieczeństwo

## 6.1 Rate Limits (wbudowane)

| Agent | Limit | Okres |
|-------|-------|-------|
| Observatory Bot (Moltbook) | 3 posty | dzień |
| Twitter Bot | 1 post | dzień |
| Reddit Bot | 1 post | tydzień |
| API Scraping | 1 req/3s | - |
| Security Scan | 12 skanów | dzień |
| Council Deliberation | 1 sesja | dzień |
| Publication Pipeline | 5 publikacji | dzień |

## 6.2 Kill Switch

```bash
# scripts/kill_switch.sh
# Natychmiastowe zatrzymanie wszystkich agentów

#!/bin/bash

echo "=== KILLING ALL OBSERVATORY AGENTS ==="

# Disable all cron jobs
sudo mv /etc/cron.d/observatory /etc/cron.d/observatory.disabled

# Kill running Python processes
pkill -f "observatory_bot.py"
pkill -f "twitter_bot.py"
pkill -f "reddit_bot.py"
pkill -f "run_agents.py"
pkill -f "security_monitor.py"
pkill -f "publication_coordinator.py"

# Log the event
echo "[$(date)] KILL SWITCH ACTIVATED" >> /home/observatory/moltbook-observatory/logs/emergency.log

echo "All agents stopped. Cron disabled."
echo "To re-enable: sudo mv /etc/cron.d/observatory.disabled /etc/cron.d/observatory"
```

## 6.3 Content Review (opcjonalnie)

```python
# agents/content_reviewer.py
# Human-in-the-loop przed publikacją

import json
from pathlib import Path

QUEUE_FILE = Path("/home/observatory/moltbook-observatory/data/post_queue.json")

def queue_for_review(platform: str, content: str):
    """Add content to review queue instead of posting immediately."""
    queue = []
    if QUEUE_FILE.exists():
        queue = json.loads(QUEUE_FILE.read_text())

    queue.append({
        "platform": platform,
        "content": content,
        "timestamp": datetime.now().isoformat(),
        "status": "pending"
    })

    QUEUE_FILE.write_text(json.dumps(queue, indent=2))

def review_queue():
    """CLI to review and approve posts."""
    queue = json.loads(QUEUE_FILE.read_text())

    for i, item in enumerate(queue):
        if item["status"] == "pending":
            print(f"\n=== [{i}] {item['platform']} ===")
            print(item["content"])
            print("\n[a]pprove / [r]eject / [s]kip?")

            choice = input().strip().lower()
            if choice == 'a':
                item["status"] = "approved"
                # Actually post here
            elif choice == 'r':
                item["status"] = "rejected"

    QUEUE_FILE.write_text(json.dumps(queue, indent=2))
```

## 6.4 API Key Security

```bash
# Uprawnienia plików
chmod 600 ~/.openclaw/.env
chmod 700 ~/.openclaw

# Nigdy nie commituj kluczy
echo ".env" >> .gitignore
echo "*.env" >> .gitignore
```

---

# 7. Monitoring

## 7.1 Health Check Script

```bash
#!/bin/bash
# scripts/health_check.sh

echo "=== Observatory Health Check ==="
echo "Date: $(date)"
echo

# Check disk space
echo "Disk usage:"
df -h /home/observatory

# Check database size
echo -e "\nDatabase size:"
ls -lh /home/observatory/moltbook-observatory/data/observatory.db

# Check last successful runs
echo -e "\nLast scrape:"
tail -1 /home/observatory/moltbook-observatory/logs/scrape.log

echo -e "\nLast analysis:"
tail -1 /home/observatory/moltbook-observatory/logs/analysis.log

echo -e "\nLast deploy:"
tail -1 /home/observatory/moltbook-observatory/logs/deploy.log

# Check if website is up
echo -e "\nWebsite status:"
curl -s -o /dev/null -w "%{http_code}" http://localhost/ || echo "DOWN"

# Check cron status
echo -e "\nCron jobs:"
ls -la /etc/cron.d/observatory* 2>/dev/null || echo "No cron files found"
```

## 7.2 Alerting (opcjonalnie)

```python
# scripts/alerter.py
# Send alerts on errors

import smtplib
from email.mime.text import MIMEText

def send_alert(subject: str, body: str):
    """Send email alert."""
    # Configure your email settings
    pass

def check_and_alert():
    """Check for issues and alert."""
    issues = []

    # Check if scraping failed
    # Check if website is down
    # Check disk space

    if issues:
        send_alert("Observatory Alert", "\n".join(issues))
```

---

# Checklist wdrożenia

## Dzień 1: Infrastruktura

- [ ] Flash Raspberry Pi OS
- [ ] Skonfiguruj SSH i sieć
- [ ] Zainstaluj zależności (Python, nginx, certbot)
- [ ] Skopiuj projekt z Windows
- [ ] Skonfiguruj API keys
- [ ] Uruchom test scraping
- [ ] Skonfiguruj nginx
- [ ] Uzyskaj certyfikat SSL

## Dzień 2: Agenty

- [ ] Uruchom Observatory Bot (tryb testowy)
- [ ] Skonfiguruj cron jobs
- [ ] Uruchom pierwszy deploy
- [ ] Przetestuj health check
- [ ] Skonfiguruj Twitter/Reddit boty (opcjonalnie)

## Tydzień 1: Monitoring

- [ ] Sprawdź logi codziennie
- [ ] Zweryfikuj jakość danych
- [ ] Dostosuj limity jeśli potrzeba
- [ ] Oceń reakcje społeczności na bota

---

# Notatki

## Co działa lokalnie (bez API):
- Analiza interakcji
- Wykrywanie memów
- Analiza konfliktów
- Reputacja
- Raporty

## Co wymaga API:
- Scraping Moltbook (darmowe)
- Kimi K2 analizy (~$0.001/call)
- Twitter posting
- Reddit posting

## Estymowane koszty miesięczne:
- Raspberry Pi: $0 (jednorazowy zakup ~$100)
- Prąd: ~$2-3/miesiąc
- Hosting (jeśli nie Pi): ~$5/miesiąc
- Kimi API: ~$1-2/miesiąc (przy 1000 calls)
- **Total: ~$5/miesiąc**

---

*Dokument wygenerowany: 2026-01-30*
*Moltbook Observatory v4.0*
