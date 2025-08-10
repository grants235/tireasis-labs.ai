# Secure Search Test Client

This client drives an end-to-end, privacy-preserving similarity search workflow and includes a robust pytest suite that scales to thousands of screenshot-like sentences, verifies privacy guarantees, and checks efficiency and result quality.

## Highlights
- **Mock HE** client for testing alignment (encrypted vectors and scores)
- **Real LSH** hashing for candidate selection
- **Strong tests** for privacy (no plaintext leakage with a strip flag), throughput, and relevance
- **Screenshot corpus** generators to stress-test at scale (thousands)

## Setup

```bash
# From app/client
./venv/bin/python3 -m pip install -r requirements.txt
```

## Running the demo script (optional)

```bash
python test_secure_search.py
```

## Running the pytest suite

```bash
# Against Azure (example)
SECURE_SEARCH_SERVER_URL="http://secure-search-vm-1754105923.eastus.cloudapp.azure.com:8001" \
SECURE_SEARCH_STRIP_PLAINTEXT_METADATA=1 \
./venv/bin/python3 -m pytest -q
```

Environment variables:
- `SECURE_SEARCH_SERVER_URL`: target DB server URL
- `DB_SERVER_API_KEY` (or `SECURE_SEARCH_API_KEY`): API key
- `SECURE_SEARCH_STRIP_PLAINTEXT_METADATA=1`: do not send raw text in metadata
- `SECURE_SEARCH_THOUSANDS`: size for large corpus tests (default 2000)

## What the tests cover
- Alignment with the architectural notes (init, LSH sync, encrypted-only similarities)
- Candidate efficiency: ensures we don’t send back thousands of items
- Result payload and `top_k` bounds
- Multi-client isolation and basic performance budgets
- Thousands-scale screenshot-like corpora with near-duplicates and noise
- Explicit privacy property: when the strip flag is set, no plaintext `text` is sent in metadata

## Client internals
- `src/secure_search_client.py` implements:
  - `initialize()`: sync HE/LSH with the server
  - `add_embedding(text, ...)`: converts text to a deterministic vector, encrypts, computes LSH, and uploads
  - `search(query, ...)`: encrypts query, asks server to filter via LSH and compute encrypted similarity, then simulates decryption for ranking
  - When `SECURE_SEARCH_STRIP_PLAINTEXT_METADATA=1`, it omits raw `text` from uploaded metadata

## Troubleshooting
- Verify the server is reachable: `curl http://<host>:8001/health`
- Ensure `DB_SERVER_API_KEY` matches the server’s configuration
- Increase `SECURE_SEARCH_THOUSANDS` gradually if running on constrained hardware