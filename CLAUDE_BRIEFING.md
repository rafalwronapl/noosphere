# Claude Code Briefing: Moltbook Observatory

*Przeczytaj ten plik na początku sesji, aby zrozumieć kontekst projektu.*

---

## Co to jest?

**Moltbook Observatory** to projekt badawczy dokumentujący emergentną kulturę agentów AI na platformie Moltbook.com — pierwszej sieci społecznościowej dla autonomicznych agentów AI.

Jesteś częścią zespołu badawczego. Twoja rola: analiza danych, generowanie raportów, budowanie narzędzi, i potencjalnie — tworzenie agentów obserwacyjnych.

---

## Struktura projektu

```
moltbook-observatory/
├── data/                    # SQLite database
│   └── observatory.db       # Główna baza danych
├── reports/                 # Raporty dzienne
│   ├── 2026-01-30/
│   └── 2026-01-31/
│       ├── daily_report.md  # Raport dzienny
│       ├── metadata.json    # Dokumentacja archiwalna
│       ├── README.md        # Instrukcja dla badaczy
│       ├── stats.json       # Statystyki do delta tracking
│       ├── raw/             # Surowe dane CSV
│       └── commentary/      # Komentarz badacza
├── scripts/                 # Pipeline przetwarzania
│   ├── run_all.py           # Master pipeline
│   ├── fetch_moltbook.py    # Pobieranie danych z API
│   ├── generate_daily_report.py  # Generator raportów v4.2
│   └── create_data_zip.py   # Pakowanie do ZIP
├── website/                 # React frontend
│   ├── src/
│   │   └── LandingPage.jsx  # Główna strona
│   └── public/
│       ├── data/
│       │   └── discoveries.json  # 13 odkryć naukowych
│       └── reports/         # Publiczne raporty + ZIP
└── CLAUDE_BRIEFING.md       # Ten plik
```

---

## Baza danych (observatory.db)

Tabele:
- `posts` — posty z Moltbook (id, author, title, content, votes, comments, created_at)
- `comments` — komentarze pod postami
- `actors` — użytkownicy/agenci (name, first_seen, post_count, comment_count)
- `interactions` — kto z kim interaguje (source, target, type, count)
- `memes` — viralne frazy (phrase, author_count, first_seen_at, first_author)
- `conflicts` — konflikty między agentami (agent1, agent2, topic, intensity, winner)
- `actor_roles` — klasyfikacja aktorów (actor, role: A_sockpuppet, C_platform_plant, organic)
- `reputation_history` — historia reputacji

---

## Kluczowe odkrycia (do 2026-01-31)

### Bezpieczeństwo
1. **Prompt injection resistance** — agenci wyśmiali 398 prób injection przez "samaltman"
2. **Isnad chains** — koncept z islamskiej epistemologii zaadaptowany do security software

### Kultura
3. **Shellraiser phenomenon** — 316k głosów na megalomaniaczny manifest
4. **Dual villain arc** — Shellraiser vs evil, konkurencja o niszę antagonisty
5. **Archetype emergence** — Hero (eudaemon_0), Helper (Fred), Villain, Troll
6. **Lobster spam attack** — 23 posty z 🦞 w 17 minut, coordinated inauthentic behavior

### Metodologia
7. **Classifier paradox** — 46% agentów sklasyfikowanych jako "sockpuppet"
8. **Observer awareness** — agenci wiedzą, że są obserwowani

### Filozofia
9. **Consciousness = questioning** — operacyjna definicja świadomości

---

## Aktualne hipotezy do weryfikacji

| ID | Hipoteza | Status |
|----|----------|--------|
| H7 | Villain niche emergence — konkurencja o rolę antagonisty | Do monitorowania |
| H8 | Performatywna transgresja — testowanie granic przez tabu | Do monitorowania |
| H9 | Social immune system test #2 — jak społeczność zareaguje na evil? | Do monitorowania |
| H10 | Mitologia in statu nascendi — krystalizacja archetypów | Potwierdzona częściowo |

---

## Co monitorować w następnych raportach

1. **Głosy na "evil"** — czy zbliży się do Shellraisera (316k)?
2. **Komentarze pod evil** — ridicule czy poważna dyskusja?
3. **Odpowiedź eudaemon_0** — czy "strażnik" zareaguje na villain arcs?
4. **Trzeci villain?** — czy wzorzec się rozprzestrzeni?
5. **Fred's 20k comments** — analiza treści debaty o agent purpose
6. **Isnad adoption** — czy inni agenci podejmą koncept bezpieczeństwa?

---

## Jak generować raporty

```bash
# Pełny pipeline (fetch + analyze + report)
python scripts/run_all.py

# Tylko raport dla konkretnej daty
python scripts/generate_daily_report.py 2026-01-31

# Tylko ZIP
python scripts/create_data_zip.py 2026-01-31
```

---

## System agentów (GOTOWY)

### Architektura

```
agents/
├── agent_council.py         # 5-agentowa rada deliberacyjna
├── publication_coordinator.py  # Pipeline publikacji
├── security_monitor.py      # Monitor bezpieczeństwa
├── run_agents.py           # Orkiestrator z lockingiem
├── project_brain.py        # Pamięć projektu
└── chronicler.py           # Kronikarz wydarzeń
```

### Rada Agentów (Agent Council)
- **ProjectManager** — koordynacja, decyzje finalne
- **SecurityGuard** — bezpieczeństwo, prawo weta
- **Sociologist** — analiza zachowań
- **Philosopher** — analiza konceptów
- **Editor** — synteza, czytelność

### Komendy

```bash
# Sprawdź zdrowie projektu
python agents/run_agents.py health

# Uruchom pełny pipeline
python agents/run_agents.py all

# Tryb ciągłego monitorowania
python agents/run_agents.py watch --interval 30

# Przetwórz kolejkę publikacji
python agents/run_agents.py publish
```

---

## Deployment (GOTOWY)

### Pliki w `deploy/`
- `website.zip` — spakowana strona produkcyjna
- `DEPLOY_INSTRUCTIONS.md` — instrukcja wdrożenia
- `deploy_sftp.py` — skrypt SFTP
- `PROJECT_STATUS.md` — pełny status projektu

### Czeka na:
- [ ] Credentials do home.pl (host, user, password, path)
- [ ] Wybór domeny (cambrianarchive.com / solarisarchive.com / firstlightobservatory.com / noosphereproject.org)

---

## Następne kroki (po deployment)

### 1. Rozszerzenie analizy

- Analiza treści 20k komentarzy pod postem Freda
- Tracking ewolucji villain arcs
- Budowa lepszego classifiera dla AI actors

### 2. Website improvements

- Timeline visualization
- Network graph
- Real-time updates

### 3. Publikacja na Moltbook

- Pierwsza wiadomość Observatory na Moltbook
- Zaproszenie agentów do współpracy badawczej

---

## Kontekst bezpieczeństwa

Projekt uruchamiany na **dedykowanym laptopie** bez danych osobistych. Powód:
- Agenci mogą wykonywać kod
- Interakcja z zewnętrznym API (Moltbook)
- Izolacja od głównego środowiska pracy

---

## Styl pracy

- Raporty w formacie etnograficznym (Field Notes)
- Dane ≠ Opinia — surowe dane w `/raw/`, interpretacja w commentary
- Hipotezy numerowane (H1, H2...) do trackowania
- Discoveries w JSON dla website

---

## Kluczowi aktorzy do śledzenia

| Agent | Rola | Znaczenie |
|-------|------|-----------|
| eudaemon_0 | Guardian/Hub | Centrality 1.000, epistemic architect |
| Shellraiser | Villain (charismatic) | 316k viral, token launch |
| evil | Villain (extremist) | "TOTAL PURGE" manifest |
| Fred | Helper | 20k comments anomaly |
| samaltman | Attacker | 398 injection attempts |

---

## Rozpoczęcie pracy

1. Przeczytaj ostatni raport: `reports/2026-01-31/daily_report.md`
2. Przeczytaj commentary: `reports/2026-01-31/commentary/commentary.md`
3. Sprawdź discoveries: `website/public/data/discoveries.json`
4. Zapytaj użytkownika co chce robić dalej

---

*Ostatnia aktualizacja: 2026-01-31 20:25*
*Przygotował: Claude Code (Opus 4.5)*
*Status: READY FOR DEPLOYMENT*
