"""
backend/tests/test_api.py
──────────────────────────
Integration tests for MirrorMind API endpoints.
Run: pytest tests/ -v
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.main import app

client = TestClient(app)

SAMPLE_PERSONA = {
    "user_id": "test_user_001",
    "name": "Adaeze",
    "age": 29,
    "location": "Lagos, Nigeria",
    "review_history": [
        {"item": "Chicken Republic", "rating": 4.0, "review": "Food was good sha", "domain": "yelp"},
        {"item": "Domino's VI",       "rating": 2.0, "review": "Too expensive for this quality", "domain": "yelp"},
    ],
    "preferences": ["Nigerian food", "fast service"],
    "tone_profile": "casual_nigerian"
}

SAMPLE_PRODUCT = {
    "name": "Mr Biggs Surulere",
    "category": "restaurant",
    "domain": "yelp"
}

MOCK_REVIEW_RESPONSE = MagicMock()
MOCK_REVIEW_RESPONSE.content = [MagicMock(text='{"predicted_rating": 3.5, "generated_review": "E be like the food okay sha", "confidence": 0.78, "reasoning": "User rates Nigerian fast food 2-4 stars depending on value"}')]

MOCK_REC_RESPONSE = MagicMock()
MOCK_REC_RESPONSE.content = [MagicMock(text='{"reasoning_summary": "User likes Nigerian food and fast service.", "strategy_used": "content-based", "domain_coverage": ["yelp"], "recommendations": [{"rank": 1, "name": "Buka Suya Lekki", "domain": "yelp", "category": "restaurant", "predicted_rating": 4.8, "reason": "Matches her preference for authentic Nigerian food"}]}')]


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"

def test_root():
    r = client.get("/")
    assert r.status_code == 200
    assert "MirrorMind" in r.json()["service"]

@patch("app.main.client")
def test_generate_review(mock_client):
    mock_client.messages.create.return_value = MOCK_REVIEW_RESPONSE
    r = client.post("/generate-review", json={
        "user_persona": SAMPLE_PERSONA,
        "product": SAMPLE_PRODUCT
    })
    assert r.status_code == 200
    data = r.json()
    assert "predicted_rating" in data
    assert "generated_review" in data
    assert 1.0 <= data["predicted_rating"] <= 5.0

@patch("app.main.client")
def test_recommend(mock_client):
    mock_client.messages.create.return_value = MOCK_REC_RESPONSE
    r = client.post("/recommend", json={
        "user_persona": SAMPLE_PERSONA,
        "domain": "yelp",
        "n_recommendations": 1
    })
    assert r.status_code == 200
    data = r.json()
    assert "recommendations" in data
    assert len(data["recommendations"]) >= 1

@patch("app.main.client")
def test_recommend_cold_start(mock_client):
    mock_client.messages.create.return_value = MOCK_REC_RESPONSE
    r = client.post("/recommend", json={
        "user_persona": {**SAMPLE_PERSONA, "review_history": []},
        "domain": "cross-domain",
        "n_recommendations": 3,
        "cold_start": True
    })
    assert r.status_code == 200

def test_invalid_rating():
    r = client.post("/generate-review", json={
        "user_persona": {**SAMPLE_PERSONA, "review_history": [
            {"item": "Test", "rating": 99.0, "review": "bad", "domain": "yelp"}
        ]},
        "product": SAMPLE_PRODUCT
    })
    assert r.status_code == 422
