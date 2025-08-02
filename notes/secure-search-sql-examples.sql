-- =====================================================
-- SQL Query Examples for Secure Similarity Search
-- Demonstrating typical operations and workflows
-- =====================================================

-- =====================================================
-- 1. CLIENT REGISTRATION AND SETUP
-- =====================================================

-- Register a new client
INSERT INTO clients (
    client_name,
    api_key_hash,
    he_context_public_key,
    he_scheme,
    poly_modulus_degree,
    scale,
    embedding_dim,
    max_embeddings_allowed
) VALUES (
    'Acme Corp',
    crypt('secret-api-key-123', gen_salt('bf')),  -- Bcrypt hash
    E'\\x0123456789ABCDEF...'::BYTEA,  -- Serialized public key
    'CKKS',
    8192,
    1099511627776,  -- 2^40
    384,
    50000
) RETURNING client_id;

-- Store LSH configuration for client
INSERT INTO lsh_configs (
    client_id,
    num_tables,
    hash_size,
    num_candidates,
    random_planes
) VALUES (
    'c47b2e8a-5d4f-4b2a-9c3d-8e7f6a5b4c3d',
    20,
    16,
    100,
    E'\\xABCDEF0123456789...'::BYTEA  -- Serialized numpy array
);

-- =====================================================
-- 2. ADDING EMBEDDINGS
-- =====================================================

-- Add an encrypted embedding with metadata
WITH new_embedding AS (
    INSERT INTO embeddings (
        client_id,
        external_id,
        encrypted_vector,
        vector_size_bytes
    ) VALUES (
        'c47b2e8a-5d4f-4b2a-9c3d-8e7f6a5b4c3d',
        'doc_12345',
        E'\\x9876543210FEDCBA...'::BYTEA,  -- Encrypted vector
        3072  -- Size in bytes
    ) RETURNING embedding_id
)
-- Add metadata
INSERT INTO embedding_metadata (embedding_id, metadata)
SELECT 
    embedding_id,
    jsonb_build_object(
        'text', 'Introduction to quantum computing and its applications',
        'category', 'technology',
        'author', 'Dr. Smith',
        'date_created', '2024-01-15',
        'tags', ARRAY['quantum', 'computing', 'physics']
    )
FROM new_embedding;

-- Batch insert LSH hashes for the embedding
INSERT INTO lsh_hashes (client_id, embedding_id, table_index, hash_value)
VALUES 
    ('c47b2e8a-5d4f-4b2a-9c3d-8e7f6a5b4c3d', 'embedding-uuid', 0, 12345),
    ('c47b2e8a-5d4f-4b2a-9c3d-8e7f6a5b4c3d', 'embedding-uuid', 1, 67890),
    ('c47b2e8a-5d4f-4b2a-9c3d-8e7f6a5b4c3d', 'embedding-uuid', 2, 34567),
    -- ... continue for all 20 tables
    ('c47b2e8a-5d4f-4b2a-9c3d-8e7f6a5b4c3d', 'embedding-uuid', 19, 98765);

-- =====================================================
-- 3. SIMILARITY SEARCH OPERATIONS
-- =====================================================

-- Find LSH candidates for a search query
WITH query_hashes AS (
    -- These would come from the client's search request
    SELECT unnest(ARRAY[11111, 22222, 33333, 44444, 55555, 
                       66666, 77777, 88888, 99999, 10101,
                       12121, 13131, 14141, 15151, 16161,
                       17171, 18181, 19191, 20201, 21211]) as hash_value,
           generate_series(0, 19) as table_index
),
candidates AS (
    SELECT 
        lh.embedding_id,
        COUNT(*) as match_count
    FROM lsh_hashes lh
    INNER JOIN query_hashes qh 
        ON lh.table_index = qh.table_index 
        AND lh.hash_value = qh.hash_value
    WHERE lh.client_id = 'c47b2e8a-5d4f-4b2a-9c3d-8e7f6a5b4c3d'
    GROUP BY lh.embedding_id
    ORDER BY match_count DESC
    LIMIT 100
)
-- Get candidate embeddings with metadata
SELECT 
    e.embedding_id,
    e.encrypted_vector,
    e.external_id,
    m.metadata,
    c.match_count
FROM candidates c
JOIN embeddings e ON c.embedding_id = e.embedding_id
LEFT JOIN embedding_metadata m ON e.embedding_id = m.embedding_id
WHERE e.is_deleted = FALSE
ORDER BY c.match_count DESC;

-- Log search request
INSERT INTO search_requests (
    client_id,
    encrypted_query,
    lsh_hashes,
    top_k,
    rerank_candidates,
    candidates_found,
    candidates_checked,
    lsh_time_ms,
    he_compute_time_ms,
    total_time_ms,
    results_returned
) VALUES (
    'c47b2e8a-5d4f-4b2a-9c3d-8e7f6a5b4c3d',
    E'\\xFEDCBA9876543210...'::BYTEA,
    ARRAY[11111, 22222, 33333, 44444, 55555, 66666, 77777, 88888, 99999, 10101,
          12121, 13131, 14141, 15151, 16161, 17171, 18181, 19191, 20201, 21211],
    10,
    100,
    87,
    87,
    45.2,
    1205.8,
    1251.0,
    20
);

-- =====================================================
-- 4. PERFORMANCE MONITORING
-- =====================================================

-- Check LSH distribution (bucket sizes)
SELECT 
    table_index,
    percentile_cont(0.5) WITHIN GROUP (ORDER BY bucket_size) as median_bucket,
    percentile_cont(0.95) WITHIN GROUP (ORDER BY bucket_size) as p95_bucket,
    MAX(bucket_size) as max_bucket,
    COUNT(*) as total_buckets
FROM lsh_bucket_sizes
WHERE client_id = 'c47b2e8a-5d4f-4b2a-9c3d-8e7f6a5b4c3d'
GROUP BY table_index
ORDER BY table_index;

-- Recent search performance analysis
SELECT 
    DATE_TRUNC('hour', created_at) as hour,
    COUNT(*) as searches,
    AVG(total_time_ms) as avg_total_ms,
    AVG(lsh_time_ms) as avg_lsh_ms,
    AVG(he_compute_time_ms) as avg_he_ms,
    AVG(candidates_checked) as avg_candidates,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY total_time_ms) as p95_total_ms
FROM search_requests
WHERE client_id = 'c47b2e8a-5d4f-4b2a-9c3d-8e7f6a5b4c3d'
    AND created_at > NOW() - INTERVAL '24 hours'
GROUP BY DATE_TRUNC('hour', created_at)
ORDER BY hour DESC;

-- =====================================================
-- 5. METADATA QUERIES
-- =====================================================

-- Search embeddings by metadata
SELECT 
    e.embedding_id,
    e.external_id,
    m.metadata->>'text' as text_content,
    m.metadata->>'category' as category,
    m.metadata->'tags' as tags
FROM embeddings e
JOIN embedding_metadata m ON e.embedding_id = m.embedding_id
WHERE e.client_id = 'c47b2e8a-5d4f-4b2a-9c3d-8e7f6a5b4c3d'
    AND e.is_deleted = FALSE
    AND m.metadata @> '{"category": "technology"}'
    AND m.metadata->'tags' ? 'quantum'
LIMIT 10;

-- Full-text search on metadata
SELECT 
    e.embedding_id,
    e.external_id,
    m.metadata->>'text' as text_content,
    ts_rank(m.search_vector, plainto_tsquery('english', 'quantum computing')) as rank
FROM embeddings e
JOIN embedding_metadata m ON e.embedding_id = m.embedding_id
WHERE e.client_id = 'c47b2e8a-5d4f-4b2a-9c3d-8e7f6a5b4c3d'
    AND e.is_deleted = FALSE
    AND m.search_vector @@ plainto_tsquery('english', 'quantum computing')
ORDER BY rank DESC
LIMIT 10;

-- =====================================================
-- 6. CACHE OPERATIONS
-- =====================================================

-- Check if query exists in cache
SELECT 
    cache_id,
    cached_results,
    hit_count
FROM search_cache
WHERE client_id = 'c47b2e8a-5d4f-4b2a-9c3d-8e7f6a5b4c3d'
    AND query_hash = SHA256(E'\\xFEDCBA9876543210...' || '10' || '100')::VARCHAR
    AND expires_at > CURRENT_TIMESTAMP;

-- Add query to cache
INSERT INTO search_cache (
    client_id,
    query_hash,
    cached_results,
    expires_at
) VALUES (
    'c47b2e8a-5d4f-4b2a-9c3d-8e7f6a5b4c3d',
    SHA256(E'\\xFEDCBA9876543210...' || '10' || '100')::VARCHAR,
    jsonb_build_array(
        jsonb_build_object(
            'embedding_id', 'uuid-1',
            'encrypted_similarity', 'base64_encoded_score',
            'metadata', '{"text": "Result 1"}'
        ),
        jsonb_build_object(
            'embedding_id', 'uuid-2',
            'encrypted_similarity', 'base64_encoded_score',
            'metadata', '{"text": "Result 2"}'
        )
    ),
    CURRENT_TIMESTAMP + INTERVAL '1 hour'
) ON CONFLICT (client_id, query_hash) 
DO UPDATE SET
    hit_count = search_cache.hit_count + 1,
    expires_at = EXCLUDED.expires_at;

-- =====================================================
-- 7. MAINTENANCE OPERATIONS
-- =====================================================

-- Soft delete old embeddings
UPDATE embeddings
SET 
    is_deleted = TRUE,
    deleted_at = CURRENT_TIMESTAMP
WHERE client_id = 'c47b2e8a-5d4f-4b2a-9c3d-8e7f6a5b4c3d'
    AND created_at < NOW() - INTERVAL '90 days'
    AND is_deleted = FALSE;

-- Clean up orphaned LSH entries
DELETE FROM lsh_hashes
WHERE embedding_id IN (
    SELECT embedding_id 
    FROM embeddings 
    WHERE is_deleted = TRUE 
        AND deleted_at < NOW() - INTERVAL '30 days'
);

-- Update client statistics
UPDATE clients
SET 
    total_embeddings = (
        SELECT COUNT(*) 
        FROM embeddings 
        WHERE client_id = clients.client_id 
            AND is_deleted = FALSE
    ),
    total_searches = (
        SELECT COUNT(*) 
        FROM search_requests 
        WHERE client_id = clients.client_id
            AND created_at > NOW() - INTERVAL '30 days'
    ),
    last_active_at = CURRENT_TIMESTAMP
WHERE client_id = 'c47b2e8a-5d4f-4b2a-9c3d-8e7f6a5b4c3d';

-- =====================================================
-- 8. ANALYTICS QUERIES
-- =====================================================

-- Client usage summary
SELECT 
    c.client_name,
    c.total_embeddings,
    c.total_searches,
    COUNT(DISTINCT e.embedding_id) as active_embeddings,
    pg_size_pretty(SUM(e.vector_size_bytes)::BIGINT) as storage_used,
    AVG(sr.total_time_ms) as avg_search_time_ms,
    MAX(c.last_active_at) as last_active
FROM clients c
LEFT JOIN embeddings e ON c.client_id = e.client_id AND e.is_deleted = FALSE
LEFT JOIN search_requests sr ON c.client_id = sr.client_id 
    AND sr.created_at > NOW() - INTERVAL '7 days'
WHERE c.is_active = TRUE
GROUP BY c.client_id, c.client_name, c.total_embeddings, c.total_searches
ORDER BY c.total_searches DESC;

-- Search patterns analysis
WITH search_patterns AS (
    SELECT 
        client_id,
        DATE_TRUNC('day', created_at) as day,
        COUNT(*) as daily_searches,
        AVG(candidates_checked) as avg_candidates,
        AVG(total_time_ms) as avg_time_ms
    FROM search_requests
    WHERE created_at > NOW() - INTERVAL '30 days'
    GROUP BY client_id, DATE_TRUNC('day', created_at)
)
SELECT 
    c.client_name,
    AVG(sp.daily_searches) as avg_daily_searches,
    MAX(sp.daily_searches) as peak_daily_searches,
    AVG(sp.avg_candidates) as overall_avg_candidates,
    AVG(sp.avg_time_ms) as overall_avg_time_ms
FROM search_patterns sp
JOIN clients c ON sp.client_id = c.client_id
GROUP BY c.client_name
ORDER BY avg_daily_searches DESC;

-- =====================================================
-- 9. SECURITY AUDIT
-- =====================================================

-- Log all operations to audit trail
INSERT INTO audit_log (
    client_id,
    action_type,
    action_details,
    ip_address,
    user_agent
) VALUES (
    'c47b2e8a-5d4f-4b2a-9c3d-8e7f6a5b4c3d',
    'EMBEDDING_ADD',
    jsonb_build_object(
        'embedding_id', 'new-embedding-uuid',
        'external_id', 'doc_12345',
        'vector_size', 3072
    ),
    '192.168.1.100'::INET,
    'SecureSearchClient/1.0'
);

-- Review recent audit activity
SELECT 
    al.action_type,
    COUNT(*) as action_count,
    COUNT(DISTINCT al.client_id) as unique_clients,
    COUNT(DISTINCT al.ip_address) as unique_ips,
    MIN(al.created_at) as first_occurrence,
    MAX(al.created_at) as last_occurrence
FROM audit_log al
WHERE al.created_at > NOW() - INTERVAL '24 hours'
GROUP BY al.action_type
ORDER BY action_count DESC;