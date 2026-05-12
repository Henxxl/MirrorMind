# 🪞 MirrorMind

> AI that thinks like your users — simulates reviews, predicts ratings, and recommends what they'll want next.

**DSN × BCT LLM Agent Challenge · Hackathon 3.0**

---

## What is MirrorMind?

MirrorMind is a dual-agent AI system built on Claude (Anthropic) that:

- **Simulates user reviews** — given a user's past review history and a new product, generates the review and star rating that user would give, in their authentic voice
- **Delivers personalised recommendations** — reasons through a user's behavioural profile before recommending items they'll genuinely love
- **Contextualises for Nigerian users** — supports Naija Pidgin, formal Nigerian English, and code-switching tone profiles

## Project Structure

```
MirrorMind/
├── README.md
├── docker-compose.yml          ← Run everything with one command
├── .env.example                ← Copy to .env, add your API key
│
├── frontend/
│   └── index.html              ← Full interactive web app (open in browser)
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app/
│   │   └── main.py             ← FastAPI app: /generate-review + /recommend
│   └── tests/
│       └── test_api.py
│
└── docs/
    └── MirrorMind_Solution_Paper.md   ← 6-page technical write-up
```

---

## Quick Start

### Option 1 — Open the frontend directly (no server needed)

Just open `frontend/index.html` in your browser. The app runs entirely in-browser using the Anthropic API directly (you'll need to set `API_BASE` in the JS if you want to use the backend instead).

### Option 2 — Full stack with Docker

```bash
# 1. Clone and configure
cp .env.example .env
# Edit .env — add your ANTHROPIC_API_KEY

# 2. Run
docker-compose up --build

# Backend API:  http://localhost:8000
# API Docs:     http://localhost:8000/docs
# Frontend:     http://localhost:3000
```

### Option 3 — Backend only (local dev)

```bash
cd backend
pip install -r requirements.txt
export ANTHROPIC_API_KEY=your_key_here
uvicorn app.main:app --reload --port 8000
```

---

## API Reference

### POST `/generate-review` — Task A: User Modelling

Simulates the review + rating a specific user would give to a product.

```bash
curl -X POST http://localhost:8000/generate-review \
  -H "Content-Type: application/json" \
  -d '{
    "user_persona": {
      "user_id": "user_001",
      "name": "Chioma",
      "age": 27,
      "location": "Lagos, Nigeria",
      "review_history": [
        {"item": "Chicken Republic Lekki", "rating": 4.0,
         "review": "Jollof rice was on point but wait time too long abeg", "domain": "yelp"}
      ],
      "preferences": ["spicy food", "fast service", "value for money"],
      "tone_profile": "casual_nigerian"
    },
    "product": {
      "name": "Mr Biggs Victoria Island",
      "category": "restaurant",
      "domain": "yelp"
    }
  }'
```

**Response:**
```json
{
  "predicted_rating": 3.5,
  "generated_review": "Hmm this Mr Biggs sha... e be like dem dey try but e no reach the level wey...",
  "confidence": 0.81,
  "reasoning": "User rates fast food 2–4 stars based on value/speed ratio...",
  "tone_used": "casual_nigerian",
  "model_version": "claude-sonnet-4-20250514"
}
```

---

### POST `/recommend` — Task B: Recommendation

Delivers personalised recommendations for a user, with cold-start and cross-domain support.

```bash
curl -X POST http://localhost:8000/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "user_persona": {
      "user_id": "user_002",
      "name": "Emeka",
      "location": "Abuja, Nigeria",
      "review_history": [
        {"item": "Things Fall Apart", "rating": 5.0, "review": "Achebe is a legend", "domain": "goodreads"},
        {"item": "Half of a Yellow Sun", "rating": 5.0, "review": "Chimamanda never misses", "domain": "goodreads"}
      ],
      "preferences": ["African literature", "historical fiction"],
      "tone_profile": "formal_nigerian"
    },
    "domain": "cross-domain",
    "n_recommendations": 5,
    "cold_start": false
  }'
```

---

## Tone Profiles

| Value | Description |
|-------|-------------|
| `casual_nigerian` | Nigerian Pidgin — "abeg", "omo", "e be like", "e sweet me" |
| `formal_nigerian` | Standard Nigerian English — polished, professional, culturally grounded |
| `mixed` | Code-switching — English + Pidgin + Yoruba/Igbo/Hausa interjections |
| `neutral` | Standard English, style-matched to history |

---

## Running Tests

```bash
cd backend
pip install -r requirements.txt
pytest tests/ -v
```

---

## Datasets

- **Yelp**: https://www.yelp.com/dataset
- **Amazon Reviews 2023**: https://amazon-reviews-2023.github.io/
- **Goodreads**: https://mengtingwan.github.io/data/goodreads.html

---

## Solution Paper

See `docs/MirrorMind_Solution_Paper.md` for the full 6-page technical write-up covering architecture, experiments, ablation studies, and future work.

---

## Tech Stack

- **LLM**: Claude (claude-sonnet-4-20250514) via Anthropic API
- **Backend**: FastAPI + Pydantic + Uvicorn (Python 3.11)
- **Frontend**: Vanilla HTML/CSS/JS (zero dependencies, works offline)
- **Containerisation**: Docker + Docker Compose
- **Tests**: Pytest + FastAPI TestClient

---

*Built for DSN × BCT Hackathon 3.0 · May 2026*
