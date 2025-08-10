## DB Server (Secure Encrypted Similarity Search)

FastAPI service responsible for storing encrypted embeddings, managing LSH structures, and performing hybrid search (LSH candidate filtering + encrypted similarity). Backed by PostgreSQL and designed for strict isolation.

### Responsibilities
- Store client registrations and HE context metadata (public parts only)
- Persist encrypted embeddings (`BYTEA`) and associated LSH hashes
- Provide `/initialize`, `/add_embedding`, `/search` endpoints
- Return encrypted similarity results that only the client can decrypt
- Maintain usage statistics and basic analytics

### Security & Isolation
- No plaintext vectors or queries are processed
- Only base64-encoded encrypted vectors/scores are transmitted
- LSH hashes are stored to enable efficient candidate selection
- API key authentication is enforced for all endpoints
- Database network is internal-only in Docker compose

### API (key endpoints)
- `POST /initialize`:
  - Input: `context_params` (public HE params), `embedding_dim`, `lsh_config`
  - Output: `client_id`, server `lsh_config`, and base64-encoded random planes for LSH
- `POST /add_embedding`:
  - Input: `client_id`, `encrypted_embedding` (base64), `lsh_hashes` (ints), optional `metadata`
  - Side effects: stores encrypted vector in `embeddings`, writes `lsh_hashes`, optional `embedding_metadata`
- `POST /search`:
  - Input: `client_id`, `encrypted_query` (base64), `lsh_hashes`, `top_k`, `rerank_candidates`
  - Process: LSH SQL to fetch candidate ids, then encrypted-similarity computation (mocked or HE service)
  - Output: `results` with `encrypted_similarity` and `metadata`, `candidates_checked`, `search_time_ms`

See `src/api/routes/secure_search.py` and `src/schemas/secure_search.py` for full definitions.

### Data model (high-level)
- `clients`: client registration, HE context metadata, usage counters
- `lsh_configs`: per-client LSH configuration + random planes (serialized)
- `embeddings`: stores encrypted vector bytes and metadata
- `lsh_hashes`: per-embedding hash values across tables
- `embedding_metadata`: JSON metadata (optional)

The target SQL schema is documented in `app/notes/secure-search-sql-schema.sql`.

### Running locally
- From `app/` project root:
  - `docker-compose up --build` (brings up postgres and db-server)
- Or run DB server standalone:
  - `cd app/db-server`
  - `python3 -m venv venv && ./venv/bin/python3 -m pip install -r requirements.txt`
  - `./venv/bin/python3 app.py`

Environment variables (examples):
- `DB_SERVER_API_KEY`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `DB_SERVER_PORT`

### Interacting with the DB server
- Use the client in `app/client` which implements the full workflow (initialize, add, search) and a robust pytest suite.
- Example via curl (see also `app/DEPLOYMENT-AZURE.md`):
  - `curl http://<host>:8001/health`

### Testing
- The DB server is best exercised end-to-end via the client suite:
  - `cd app/client`
  - `./venv/bin/python3 -m pip install -r requirements.txt`
  - `SECURE_SEARCH_SERVER_URL="http://localhost:8001" SECURE_SEARCH_STRIP_PLAINTEXT_METADATA=1 ./venv/bin/python3 -m pytest -q`

### Notes
- The provided HE service uses TenSEAL interfaces in code; production deployments should ensure proper key management and CKKS parameter tuning.
- For performance at scale, the LSH SQL candidate selection and indexing strategy can be tuned per workload. 