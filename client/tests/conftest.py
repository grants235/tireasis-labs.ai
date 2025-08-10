import os
import random
import string
from typing import Dict, List, Tuple

import pytest

# Ensure src is importable when running from client dir
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from src.secure_search_client import SecureSearchTestClient


def _env(name: str, default: str) -> str:
    return os.getenv(name, default)


@pytest.fixture(scope="session")
def server_url() -> str:
    # Prefer explicit SECURE_SEARCH_SERVER_URL, fall back to default within client
    return _env("SECURE_SEARCH_SERVER_URL", "")


@pytest.fixture(scope="session")
def api_key() -> str:
    # DB_SERVER_API_KEY is what the server expects
    return _env("DB_SERVER_API_KEY", _env("SECURE_SEARCH_API_KEY", ""))


@pytest.fixture(scope="function")
def make_client(server_url: str, api_key: str):
    def _factory() -> SecureSearchTestClient:
        # Instantiate with env if provided; otherwise SecureSearchTestClient uses its defaults
        kwargs = {}
        if server_url:
            kwargs["server_url"] = server_url
        if api_key:
            kwargs["api_key"] = api_key
        client = SecureSearchTestClient(**kwargs) if kwargs else SecureSearchTestClient()
        return client
    return _factory


def generate_synthetic_sentences(
    total: int,
    category_mix: Dict[str, float],
    seed: int = 1337,
) -> List[Dict[str, str]]:
    """
    Generate synthetic sentences across categories according to a probability mix.
    Returns list of dicts with keys: id, text, category, topic.
    """
    rng = random.Random(seed)

    category_topics = {
        "technology": ["AI", "machine learning", "cryptography", "distributed systems", "cloud"],
        "science": ["neuroscience", "genetics", "physics", "chemistry", "biology"],
        "business": ["entrepreneurship", "marketing", "finance", "operations", "strategy"],
        "health": ["wellness", "mental health", "telemedicine", "cardiology", "nutrition"],
        "education": ["e-learning", "STEM", "pedagogy", "curriculum", "assessment"],
    }

    # Normalize mix
    total_weight = sum(category_mix.values()) or 1.0
    categories = list(category_mix.keys())
    weights = [category_mix[c] / total_weight for c in categories]

    def rand_id(prefix: str = "sent") -> str:
        return f"{prefix}_" + "".join(rng.choices(string.ascii_lowercase + string.digits, k=8))

    sentences: List[Dict[str, str]] = []
    for _ in range(total):
        category = rng.choices(categories, weights=weights, k=1)[0]
        topic = rng.choice(category_topics.get(category, [category]))
        extra = rng.choice([
            "trends", "applications", "methods", "benchmarks", "best practices",
            "ethical considerations", "deployments", "workflows", "pipelines", "research"
        ])
        text = f"An overview of {topic} in {category} discussing {extra} and practical use cases."
        sentences.append({
            "id": rand_id(),
            "text": text,
            "category": category,
            "topic": topic,
        })

    return sentences


@pytest.fixture(scope="session")
def dataset_small() -> List[Dict[str, str]]:
    return generate_synthetic_sentences(
        total=int(os.getenv("SECURE_SEARCH_TEST_SMALL", "20")),
        category_mix={"technology": 0.6, "science": 0.4},
        seed=101,
    )


@pytest.fixture(scope="session")
def dataset_medium() -> List[Dict[str, str]]:
    return generate_synthetic_sentences(
        total=int(os.getenv("SECURE_SEARCH_TEST_MEDIUM", "60")),
        category_mix={"technology": 0.2, "science": 0.2, "business": 0.2, "health": 0.2, "education": 0.2},
        seed=202,
    )


@pytest.fixture(scope="session")
def dataset_large() -> List[Dict[str, str]]:
    return generate_synthetic_sentences(
        total=int(os.getenv("SECURE_SEARCH_TEST_LARGE", "120")),
        category_mix={"health": 0.5, "education": 0.3, "business": 0.2},
        seed=303,
    ) 