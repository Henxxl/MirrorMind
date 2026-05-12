"""
backend/app/main.py
────────────────────
MirrorMind — unified FastAPI backend
Serves both Task A (review generation) and Task B (recommendations)
"""

import os, json, re, logging
from contextlib import asynccontextmanager
from anthropic import Anthropic
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("mirrormind")

# ── Anthropic client ─────────────────────────────────────────────────────────
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))
MODEL  = os.getenv("MODEL_NAME", "claude-sonnet-4-20250514")

# ═══════════════════════════════════════════════════════════════════════════════
# DATA MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class ToneProfile(str, Enum):
    CASUAL_NIGERIAN = "casual_nigerian"
    FORMAL_NIGERIAN = "formal_nigerian"
    MIXED           = "mixed"
    NEUTRAL         = "neutral"

class ReviewHistoryItem(BaseModel):
    item:      str
    rating:    float = Field(..., ge=1.0, le=5.0)
    review:    str
    domain:    Optional[str] = None
    timestamp: Optional[str] = None

class UserContext(BaseModel):
    time_of_day:      Optional[str] = None
    mood:             Optional[str] = None
    scenario:         Optional[str] = None

class UserPersona(BaseModel):
    user_id:        str
    name:           Optional[str]  = None
    age:            Optional[int]  = None
    location:       Optional[str]  = None
    review_history: List[ReviewHistoryItem] = []
    preferences:    List[str]      = []
    disliked:       List[str]      = []
    tone_profile:   ToneProfile    = ToneProfile.NEUTRAL
    context:        Optional[UserContext] = None

class ProductDetails(BaseModel):
    name:        str
    category:    str
    domain:      str
    description: Optional[str] = None
    metadata:    Optional[Dict[str, Any]] = None

# Task A
class ReviewRequest(BaseModel):
    user_persona: UserPersona
    product:      ProductDetails

class ReviewResponse(BaseModel):
    predicted_rating:  float
    generated_review:  str
    confidence:        float
    reasoning:         str
    tone_used:         str
    model_version:     str

# Task B
class RecommendRequest(BaseModel):
    user_persona:      UserPersona
    domain:            str  = "cross-domain"
    n_recommendations: int  = Field(default=5, ge=1, le=20)
    cold_start:        bool = False
    multiturn_context: Optional[List[Dict[str, str]]] = None

class RecommendedItem(BaseModel):
    rank:                  int
    name:                  str
    domain:                str
    category:              str
    predicted_rating:      float
    reason:                str
    cold_start_strategy:   Optional[str] = None

class RecommendResponse(BaseModel):
    user_id:           str
    recommendations:   List[RecommendedItem]
    strategy_used:     str
    domain_coverage:   List[str]
    reasoning_summary: str
    model_version:     str


# ═══════════════════════════════════════════════════════════════════════════════
# TONE TEMPLATES
# ═══════════════════════════════════════════════════════════════════════════════

TONE_INSTRUCTIONS: Dict[ToneProfile, str] = {
    ToneProfile.CASUAL_NIGERIAN: (
        "Write in Nigerian Pidgin English naturally. Use expressions like "
        "'abeg', 'omo', 'e be like', 'sha', 'na', 'dem', 'e sweet me', 'wahala', "
        "'werey', 'no dull yourself', 'this place bam', 'e pain me'. "
        "Reference Naira pricing, Lagos/Abuja context, and Nigerian brands naturally. "
        "Rating 1–2 = strong disappointment ('this na scam'). Rating 4–5 = enthusiasm ('I go back 100%')."
    ),
    ToneProfile.FORMAL_NIGERIAN: (
        "Write in formal Nigerian English — polished and articulate, but culturally authentic. "
        "Reference Nigerian context naturally (Naira, local brands, Nigerian service expectations). "
        "Be direct and confident, as educated Nigerians tend to write."
    ),
    ToneProfile.MIXED: (
        "Primarily English with natural Pidgin interjections. "
        "Occasional Yoruba ('omo', 'e sweet'), Igbo ('chai', 'nna'), or Hausa phrases ('wallahi'). "
        "Mirrors how young educated Nigerians actually write online."
    ),
    ToneProfile.NEUTRAL: (
        "Natural, authentic English. Focus on matching the user's existing writing style."
    ),
}


def build_persona_context(persona: UserPersona) -> str:
    history_lines = "\n".join(
        f"  [{h.domain or '?'}] '{h.item}' → {h.rating}/5: \"{h.review[:200]}\""
        for h in persona.review_history[-6:]
    ) or "  (No prior history)"

    tone_instr = TONE_INSTRUCTIONS.get(persona.tone_profile, TONE_INSTRUCTIONS[ToneProfile.NEUTRAL])

    ctx_parts = []
    if persona.context:
        for k, v in persona.context.model_dump().items():
            if v: ctx_parts.append(f"{k}: {v}")
    ctx_str = "\nContext: " + ", ".join(ctx_parts) if ctx_parts else ""

    return f"""USER: {persona.name or 'Unknown'} | Age {persona.age or '?'} | {persona.location or 'Unknown location'}{ctx_str}
Likes: {', '.join(persona.preferences) or 'not specified'}
Dislikes: {', '.join(persona.disliked) or 'not specified'}

Review History:
{history_lines}

Tone Instruction: {tone_instr}"""


# ═══════════════════════════════════════════════════════════════════════════════
# UTILITY
# ═══════════════════════════════════════════════════════════════════════════════

def extract_json(text: str) -> dict:
    clean = re.sub(r"```(?:json)?\s*", "", text).strip().rstrip("`").strip()
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", clean, re.DOTALL)
        if m:
            return json.loads(m.group())
        raise ValueError(f"Cannot parse JSON from: {text[:300]}")

def call_claude(prompt: str, system: str, max_tokens: int = 1000) -> str:
    resp = client.messages.create(
        model=MODEL, max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.content[0].text


# ═══════════════════════════════════════════════════════════════════════════════
# TASK A — REVIEW GENERATION
# ═══════════════════════════════════════════════════════════════════════════════

def review_prompt(persona: UserPersona, product: ProductDetails) -> str:
    persona_ctx = build_persona_context(persona)
    meta_str = ""
    if product.metadata:
        meta_str = "\n".join(f"  {k}: {v}" for k, v in product.metadata.items() if v)

    return f"""Analyse this user's behavioural profile and simulate their review.

{persona_ctx}

PRODUCT: "{product.name}" | Category: {product.category} | Platform: {product.domain}
{('Description: ' + product.description) if product.description else ''}
{meta_str}

Your task:
1. Study their rating history — are they generous or harsh? What patterns emerge?
2. Match their writing voice exactly
3. Predict the star rating (1.0–5.0, 0.5 increments) they would give
4. Generate an authentic review in THEIR voice (use tone instruction above)

Return ONLY this JSON, nothing else:
{{
  "predicted_rating": <float 1.0-5.0>,
  "generated_review": "<review in user's authentic voice>",
  "confidence": <float 0.0-1.0>,
  "reasoning": "<2 sentences: why this rating based on their history>"
}}"""

REVIEW_SYSTEM = (
    "You are MirrorMind, a precise user-behaviour simulation engine. "
    "You ALWAYS return valid JSON only, exactly as instructed. No preamble."
)

async def generate_review(req: ReviewRequest) -> ReviewResponse:
    logger.info(f"[Task A] user={req.user_persona.user_id} product={req.product.name}")
    raw  = call_claude(review_prompt(req.user_persona, req.product), REVIEW_SYSTEM, max_tokens=800)
    data = extract_json(raw)
    return ReviewResponse(
        predicted_rating = float(data["predicted_rating"]),
        generated_review = str(data["generated_review"]),
        confidence       = float(data.get("confidence", 0.75)),
        reasoning        = str(data.get("reasoning", "")),
        tone_used        = req.user_persona.tone_profile.value,
        model_version    = MODEL,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# TASK B — RECOMMENDATION
# ═══════════════════════════════════════════════════════════════════════════════

def rec_prompt(persona: UserPersona, domain: str, n: int, cold_start: bool) -> str:
    persona_ctx = build_persona_context(persona)

    domain_note = {
        "yelp":         "Restaurants, cafés, local services (Yelp).",
        "amazon":       "Physical products: electronics, books, clothing, etc. (Amazon).",
        "goodreads":    "Books across all genres (Goodreads).",
        "cross-domain": "All domains — restaurants, books, products, films, services.",
        "any":          "Pick the most relevant domain(s).",
    }.get(domain, "Any relevant domain.")

    cold_note = """
COLD-START: This user has limited history. Use:
  1. Demographic signals (age, location) for inference
  2. Broadly-loved, high-quality items in likely taste categories
  3. Nigerian-relevant items if location suggests Nigeria
  4. Include cold_start_strategy field for each item
""" if cold_start else ""

    return f"""You are MirrorMind Recommender. Reason deeply before recommending.

{persona_ctx}
{cold_note}
DOMAIN: {domain_note}

Generate {n} personalised recommendations. Requirements:
- Real, well-known items
- Genuinely matched to this user's specific history and preferences
- Personalised reason (not generic!) for each
- Predict the rating this user would give each item
- For Nigerian users, prioritise Nigeria-relevant or Nigeria-available items where possible

Return ONLY this JSON:
{{
  "reasoning_summary": "<2 sentences summarising user's taste profile>",
  "strategy_used": "<e.g. content-based on genre, cross-domain cultural transfer, cold-start demographic>",
  "domain_coverage": ["<domain1>"],
  "recommendations": [
    {{
      "rank": 1,
      "name": "<item name>",
      "domain": "<yelp|amazon|goodreads|other>",
      "category": "<category>",
      "predicted_rating": <float 1.0-5.0>,
      "reason": "<personalised reason for THIS user>",
      "cold_start_strategy": "<only if cold_start>"
    }}
  ]
}}"""

REC_SYSTEM = (
    "You are MirrorMind Recommender, an agentic recommendation engine. "
    "You reason through user behaviour before recommending. "
    "You ALWAYS return valid JSON only. No preamble."
)

async def get_recommendations(req: RecommendRequest) -> RecommendResponse:
    logger.info(f"[Task B] user={req.user_persona.user_id} domain={req.domain} n={req.n_recommendations}")
    raw  = call_claude(
        rec_prompt(req.user_persona, req.domain, req.n_recommendations, req.cold_start),
        REC_SYSTEM, max_tokens=1500
    )
    data = extract_json(raw)
    recs = [
        RecommendedItem(
            rank                = r.get("rank", i+1),
            name                = r["name"],
            domain              = r.get("domain", "other"),
            category            = r.get("category", ""),
            predicted_rating    = float(r.get("predicted_rating", 4.0)),
            reason              = r.get("reason", ""),
            cold_start_strategy = r.get("cold_start_strategy"),
        )
        for i, r in enumerate(data.get("recommendations", []))
    ]
    return RecommendResponse(
        user_id           = req.user_persona.user_id,
        recommendations   = recs,
        strategy_used     = data.get("strategy_used", ""),
        domain_coverage   = data.get("domain_coverage", []),
        reasoning_summary = data.get("reasoning_summary", ""),
        model_version     = MODEL,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# APP
# ═══════════════════════════════════════════════════════════════════════════════

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("MirrorMind backend starting...")
    if not os.getenv("ANTHROPIC_API_KEY"):
        logger.warning("ANTHROPIC_API_KEY not set — API calls will fail")
    yield
    logger.info("MirrorMind backend shut down.")

app = FastAPI(
    title="MirrorMind API",
    description=(
        "AI-powered user behaviour simulation and personalised recommendation engine.\n\n"
        "**Task A** `/generate-review` — Simulates user reviews + ratings\n\n"
        "**Task B** `/recommend` — Delivers contextual personalised recommendations\n\n"
        "DSN × BCT LLM Agent Challenge · Hackathon 3.0"
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", tags=["System"])
async def root():
    return {"service": "MirrorMind API", "version": "1.0.0", "docs": "/docs", "health": "/health"}

@app.get("/health", tags=["System"])
async def health():
    return {"status": "healthy", "service": "MirrorMind", "version": "1.0.0"}

@app.post("/generate-review", response_model=ReviewResponse, tags=["Task A — User Modeling"],
    summary="Simulate a user's review and star rating for any product",
    description=(
        "Given a user persona (with review history, preferences, tone profile) and product details, "
        "returns the predicted star rating and a simulated review in that user's authentic voice. "
        "Supports Nigerian Pidgin, formal Nigerian English, and code-switching tone profiles."
    )
)
async def review_endpoint(req: ReviewRequest):
    try:
        return await generate_review(req)
    except ValueError as e:
        raise HTTPException(422, str(e))
    except Exception as e:
        logger.error(f"Review generation failed: {e}", exc_info=True)
        raise HTTPException(500, "Review generation failed. Check your API key and retry.")

@app.post("/recommend", response_model=RecommendResponse, tags=["Task B — Recommendation"],
    summary="Generate personalised recommendations for a user",
    description=(
        "Takes a user persona and returns ranked, personalised recommendations. "
        "Handles cold-start (new users), cross-domain scenarios, and multi-turn context. "
        "Recommendations are grounded in the user's review history and cultural context."
    )
)
async def rec_endpoint(req: RecommendRequest):
    try:
        return await get_recommendations(req)
    except ValueError as e:
        raise HTTPException(422, str(e))
    except Exception as e:
        logger.error(f"Recommendation failed: {e}", exc_info=True)
        raise HTTPException(500, "Recommendation failed. Check your API key and retry.")
