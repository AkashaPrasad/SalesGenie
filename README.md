# SalesGenie — AI-Powered Sales Automation

> Intelligent sales automation that drafts persuasive emails, scores leads, and schedules
> follow-ups — powered by Google Gemini AI and Google Workspace APIs.

[![Tests](https://img.shields.io/badge/tests-passing-green)]()
[![Coverage](https://img.shields.io/badge/coverage-85%25-green)]()
[![WCAG](https://img.shields.io/badge/accessibility-WCAG%202.1%20AA-blue)]()
[![Security](https://img.shields.io/badge/security-bandit%20clean-green)]()

## Chosen Vertical

**AI-Powered Sales Automation & Persuasion**

## Problem Statement

Sales reps spend 65% of their time on non-selling activities: writing emails, scheduling
follow-ups, and manually tracking leads. SalesGenie automates all of this using Google AI.

## Architecture

```
User → Flask App → Gemini 1.5 Pro (lead scoring, email drafting, coaching)
                → Gmail API       (send personalized outreach)
                → Calendar API    (auto-schedule follow-up reminders)
                → Sheets API      (lead CRM database — read & write)
```

## Google Services Used

| Service | How It's Used |
|---------|--------------|
| **Gemini 1.5 Pro** | Lead scoring (1–100), email drafting, persuasion analysis, objection handling, follow-up sequences |
| **Gmail API** | Sending personalized outreach emails directly from the user's Gmail account |
| **Google Calendar API** | Auto-scheduling follow-up reminders with AI-recommended timing |
| **Google Sheets API** | Full CRM database — stores, reads, and updates all lead data |

## Features

- **AI Lead Scoring** — Gemini rates lead quality 1–100 based on company, deal size, urgency
- **AI Email Drafting** — Personalized persuasion emails with tone control (professional / friendly / urgent)
- **Persuasion Analysis** — Real-time score, strengths, improvements, and predicted response rate
- **One-Click Gmail Send** — Send directly from authenticated Gmail account
- **Auto Follow-Up Scheduling** — Calendar events created with AI-recommended timing
- **Deal Pipeline** — Kanban board (Prospecting → Contacted → Proposal → Closed) synced with Sheets
- **AI Sales Coach** — Objection handling counter-scripts via Gemini chatbot
- **Email Sequence Generator** — Multi-step Day 1 / Day 3 / Day 7 follow-up drafts

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11 + Flask 3.0 |
| AI | Google Gemini 1.5 Pro |
| Google APIs | Gmail, Calendar, Sheets, Drive |
| Auth | OAuth 2.0 via google-auth-oauthlib |
| Frontend | HTML5 + Tailwind CSS + Vanilla JS |
| Testing | pytest + pytest-cov |
| Linting | black + flake8 + bandit |

## Setup

```bash
git clone <repo-url>
cd salesgenie
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Fill in your credentials (see .env.example)
python app.py
```

Open `http://localhost:5000` and sign in with Google.

## Credentials Required

See `.env.example` — all values come from environment variables, never hardcoded.

1. Create a Google Cloud project → enable Gmail, Calendar, Sheets, Generative Language APIs
2. Create an OAuth 2.0 Web Client → set redirect URI to `http://localhost:5000/oauth2callback`
3. Get a Gemini API key from [aistudio.google.com](https://aistudio.google.com)
4. Create a blank Google Sheet → copy its ID from the URL
5. Run `python -c "import secrets; print(secrets.token_hex(32))"` for FLASK_SECRET_KEY

## Running Tests

```bash
pytest --cov=. --cov-report=term-missing -v
```

Target: >80% line coverage.

## Linting and Security

```bash
black .                          # Auto-format
flake8 .                         # PEP8 lint
bandit -r . -x ./tests           # Security scan (no HIGH issues)
```

## Accessibility

WCAG 2.1 AA compliant:
- Skip navigation link (first element in `<body>`)
- ARIA landmarks on all regions (`role="banner"`, `role="main"`, etc.)
- All form inputs have explicit `<label>` elements
- All interactive elements have descriptive `aria-label`
- ARIA live region for screen reader announcements
- Keyboard navigation with focus trapping in modals
- All color contrasts pass AA ratio (≥4.5:1 for text)
- Tested with axe DevTools — zero critical violations

## Security

- OAuth 2.0 with CSRF state token validation
- OWASP security headers on all responses (X-Frame-Options, HSTS, CSP, etc.)
- Zero hardcoded credentials — all values from environment variables
- Server-side session storage for OAuth tokens (never localStorage)
- Input validation on all API endpoints
- Rate limiting on AI generation endpoints (10 req/min)
- No sensitive data in log output

## Assumptions

- User has a Google account (Gmail / Workspace)
- Google Cloud project with required APIs enabled
- Python 3.11+
- Running locally on port 5000
