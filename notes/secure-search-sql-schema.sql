-- =====================================================
-- Secure Similarity Search Database Schema
-- Supports LSH + Homomorphic Encryption Architecture
-- =====================================================

-- Enable necessary extensions (PostgreSQL specific)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- =====================================================
-- CLIENTS AND AUTHENTICATION
-- =====================================================

-- Clients table: Stores registered clients and their HE contexts
CREATE TABLE clients (
    client_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_name VARCHAR(255) NOT NULL,
    api_key_hash VARCHAR(255) NOT NULL UNIQUE, -- Hashed API key for auth
    
    -- HE Context Information
    he_context_public_key BYTEA NOT NULL, -- Serialized public key
    he_scheme VARCHAR(50) NOT NULL DEFAULT 'CKKS',
    poly_modulus_degree INTEGER NOT NULL DEFAULT 8192,
    scale BIGINT NOT NULL DEFAULT 1099511627776, -- 2^40
    
    -- Configuration
    embedding_dim INTEGER NOT NULL DEFAULT 384,
    max_embeddings_allowed INTEGER DEFAULT 100000,
    
    -- Timestamps and status
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_active_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Usage statistics
    total_embeddings INTEGER DEFAULT 0,
    total_searches INTEGER DEFAULT 0,
    
    CONSTRAINT check_embedding_dim CHECK (embedding_dim > 0),
    CONSTRAINT check_poly_modulus CHECK (poly_modulus_degree IN (4096, 8192, 16384, 32768))
);

CREATE INDEX idx_clients_api_key ON clients(api_key_hash);
CREATE INDEX idx_clients_active ON clients(is_active) WHERE is_active = TRUE;

-- =====================================================
-- LSH CONFIGURATION
-- =====================================================

-- LSH configurations per client
CREATE TABLE lsh_configs (
    config_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_id UUID NOT NULL REFERENCES clients(client_id) ON DELETE CASCADE,
    
    num_tables INTEGER NOT NULL DEFAULT 20,
    hash_size INTEGER NOT NULL DEFAULT 16,
    num_candidates INTEGER NOT NULL DEFAULT 100,
    
    -- Random planes for LSH (stored as serialized numpy array)
    random_planes BYTEA NOT NULL,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT check_num_tables CHECK (num_tables > 0 AND num_tables <= 50),
    CONSTRAINT check_hash_size CHECK (hash_size >= 8 AND hash_size <= 32)
);

CREATE INDEX idx_lsh_configs_client ON lsh_configs(client_id);

-- =====================================================
-- ENCRYPTED EMBEDDINGS
-- =====================================================

-- Main embeddings table
CREATE TABLE embeddings (
    embedding_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_id UUID NOT NULL REFERENCES clients(client_id) ON DELETE CASCADE,
    
    -- User-provided ID (optional)
    external_id VARCHAR(255),
    
    -- Encrypted embedding data
    encrypted_vector BYTEA NOT NULL,
    vector_size_bytes INTEGER NOT NULL,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    accessed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    access_count INTEGER DEFAULT 0,
    
    -- Soft delete support
    is_deleted BOOLEAN DEFAULT FALSE,
    deleted_at TIMESTAMP WITH TIME ZONE,
    
    CONSTRAINT unique_external_id_per_client UNIQUE (client_id, external_id)
);

CREATE INDEX idx_embeddings_client ON embeddings(client_id);
CREATE INDEX idx_embeddings_external ON embeddings(client_id, external_id) WHERE external_id IS NOT NULL;
CREATE INDEX idx_embeddings_created ON embeddings(created_at);
CREATE INDEX idx_embeddings_not_deleted ON embeddings(client_id, is_deleted) WHERE is_deleted = FALSE;

-- =====================================================
-- LSH HASH TABLES
-- =====================================================

-- LSH hash mappings (one row per hash table per embedding)
CREATE TABLE lsh_hashes (
    client_id UUID NOT NULL REFERENCES clients(client_id) ON DELETE CASCADE,
    embedding_id UUID NOT NULL REFERENCES embeddings(embedding_id) ON DELETE CASCADE,
    
    table_index INTEGER NOT NULL, -- Which hash table (0 to num_tables-1)
    hash_value INTEGER NOT NULL,   -- The hash value for this table
    
    PRIMARY KEY (client_id, table_index, hash_value, embedding_id)
);

-- Optimized indexes for LSH lookups
CREATE INDEX idx_lsh_lookup ON lsh_hashes(client_id, table_index, hash_value);
CREATE INDEX idx_lsh_embedding ON lsh_hashes(embedding_id);

-- Materialized view for faster candidate retrieval
CREATE MATERIALIZED VIEW lsh_bucket_sizes AS
SELECT 
    client_id,
    table_index,
    hash_value,
    COUNT(*) as bucket_size
FROM lsh_hashes
GROUP BY client_id, table_index, hash_value;

CREATE INDEX idx_bucket_sizes ON lsh_bucket_sizes(client_id, table_index, hash_value);

-- =====================================================
-- METADATA STORAGE
-- =====================================================

-- Flexible metadata storage using JSONB
CREATE TABLE embedding_metadata (
    embedding_id UUID PRIMARY KEY REFERENCES embeddings(embedding_id) ON DELETE CASCADE,
    metadata JSONB NOT NULL DEFAULT '{}',
    
    -- Indexed fields for common queries
    text_content TEXT GENERATED ALWAYS AS (metadata->>'text') STORED,
    category VARCHAR(100) GENERATED ALWAYS AS (metadata->>'category') STORED,
    
    -- Full text search
    search_vector tsvector GENERATED ALWAYS AS (
        to_tsvector('english', COALESCE(metadata->>'text', '') || ' ' || COALESCE(metadata->>'category', ''))
    ) STORED
);

CREATE INDEX idx_metadata_text ON embedding_metadata(text_content);
CREATE INDEX idx_metadata_category ON embedding_metadata(category);
CREATE INDEX idx_metadata_search ON embedding_metadata USING GIN(search_vector);
CREATE INDEX idx_metadata_jsonb ON embedding_metadata USING GIN(metadata);

-- =====================================================
-- SEARCH OPERATIONS
-- =====================================================

-- Search request logging
CREATE TABLE search_requests (
    search_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_id UUID NOT NULL REFERENCES clients(client_id) ON DELETE CASCADE,
    
    -- Search parameters
    encrypted_query BYTEA NOT NULL,
    lsh_hashes INTEGER[] NOT NULL,
    top_k INTEGER NOT NULL,
    rerank_candidates INTEGER NOT NULL,
    
    -- Performance metrics
    candidates_found INTEGER,
    candidates_checked INTEGER,
    lsh_time_ms NUMERIC(10,2),
    he_compute_time_ms NUMERIC(10,2),
    total_time_ms NUMERIC(10,2),
    
    -- Results summary
    results_returned INTEGER,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_search_requests_client ON search_requests(client_id);
CREATE INDEX idx_search_requests_time ON search_requests(created_at);

-- Search results cache (optional, for repeated queries)
CREATE TABLE search_cache (
    cache_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_id UUID NOT NULL REFERENCES clients(client_id) ON DELETE CASCADE,
    
    -- Query fingerprint (hash of encrypted query + parameters)
    query_hash VARCHAR(64) NOT NULL,
    
    -- Cached results
    cached_results JSONB NOT NULL,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    hit_count INTEGER DEFAULT 0,
    
    CONSTRAINT unique_query_per_client UNIQUE (client_id, query_hash)
);

CREATE INDEX idx_cache_lookup ON search_cache(client_id, query_hash);
CREATE INDEX idx_cache_expiry ON search_cache(expires_at);

-- =====================================================
-- BATCH OPERATIONS
-- =====================================================

-- Batch upload tracking
CREATE TABLE batch_uploads (
    batch_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_id UUID NOT NULL REFERENCES clients(client_id) ON DELETE CASCADE,
    
    total_embeddings INTEGER NOT NULL,
    processed_embeddings INTEGER DEFAULT 0,
    failed_embeddings INTEGER DEFAULT 0,
    
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    error_message TEXT,
    
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE,
    
    CONSTRAINT check_status CHECK (status IN ('pending', 'processing', 'completed', 'failed'))
);

CREATE INDEX idx_batch_uploads_client ON batch_uploads(client_id);
CREATE INDEX idx_batch_uploads_status ON batch_uploads(status);

-- =====================================================
-- ANALYTICS AND MONITORING
-- =====================================================

-- Performance metrics aggregation
CREATE TABLE performance_metrics (
    metric_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_id UUID NOT NULL REFERENCES clients(client_id) ON DELETE CASCADE,
    
    metric_date DATE NOT NULL,
    metric_hour INTEGER NOT NULL CHECK (metric_hour >= 0 AND metric_hour < 24),
    
    -- Counters
    total_searches INTEGER DEFAULT 0,
    total_embeddings_added INTEGER DEFAULT 0,
    
    -- Performance averages
    avg_search_time_ms NUMERIC(10,2),
    avg_candidates_checked NUMERIC(10,2),
    avg_lsh_time_ms NUMERIC(10,2),
    avg_he_time_ms NUMERIC(10,2),
    
    -- Peak values
    max_search_time_ms NUMERIC(10,2),
    max_candidates_checked INTEGER,
    
    CONSTRAINT unique_metrics_per_hour UNIQUE (client_id, metric_date, metric_hour)
);

CREATE INDEX idx_metrics_lookup ON performance_metrics(client_id, metric_date, metric_hour);

-- =====================================================
-- AUDIT TRAIL
-- =====================================================

CREATE TABLE audit_log (
    audit_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_id UUID REFERENCES clients(client_id) ON DELETE SET NULL,
    
    action_type VARCHAR(50) NOT NULL,
    action_details JSONB NOT NULL DEFAULT '{}',
    
    ip_address INET,
    user_agent TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_client ON audit_log(client_id);
CREATE INDEX idx_audit_action ON audit_log(action_type);
CREATE INDEX idx_audit_time ON audit_log(created_at);

-- =====================================================
-- FUNCTIONS AND PROCEDURES
-- =====================================================

-- Function to find LSH candidates efficiently
CREATE OR REPLACE FUNCTION find_lsh_candidates(
    p_client_id UUID,
    p_lsh_hashes INTEGER[],
    p_max_candidates INTEGER
)
RETURNS TABLE(embedding_id UUID, match_count INTEGER) AS $$
BEGIN
    RETURN QUERY
    WITH hash_matches AS (
        SELECT 
            lh.embedding_id,
            COUNT(*) as matches
        FROM lsh_hashes lh
        WHERE lh.client_id = p_client_id
          AND lh.hash_value = ANY(p_lsh_hashes)
          AND EXISTS (
              SELECT 1 FROM embeddings e 
              WHERE e.embedding_id = lh.embedding_id 
                AND e.is_deleted = FALSE
          )
        GROUP BY lh.embedding_id
    )
    SELECT 
        hm.embedding_id,
        hm.matches::INTEGER
    FROM hash_matches hm
    ORDER BY hm.matches DESC
    LIMIT p_max_candidates;
END;
$$ LANGUAGE plpgsql;

-- Function to clean up expired cache entries
CREATE OR REPLACE FUNCTION cleanup_expired_cache() RETURNS void AS $$
BEGIN
    DELETE FROM search_cache WHERE expires_at < CURRENT_TIMESTAMP;
END;
$$ LANGUAGE plpgsql;

-- Function to update client statistics
CREATE OR REPLACE FUNCTION update_client_stats() RETURNS TRIGGER AS $$
BEGIN
    IF TG_TABLE_NAME = 'embeddings' AND TG_OP = 'INSERT' THEN
        UPDATE clients 
        SET total_embeddings = total_embeddings + 1,
            last_active_at = CURRENT_TIMESTAMP
        WHERE client_id = NEW.client_id;
    ELSIF TG_TABLE_NAME = 'search_requests' AND TG_OP = 'INSERT' THEN
        UPDATE clients 
        SET total_searches = total_searches + 1,
            last_active_at = CURRENT_TIMESTAMP
        WHERE client_id = NEW.client_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- TRIGGERS
-- =====================================================

CREATE TRIGGER update_embedding_stats
    AFTER INSERT ON embeddings
    FOR EACH ROW
    EXECUTE FUNCTION update_client_stats();

CREATE TRIGGER update_search_stats
    AFTER INSERT ON search_requests
    FOR EACH ROW
    EXECUTE FUNCTION update_client_stats();

-- =====================================================
-- VIEWS FOR MONITORING
-- =====================================================

-- Client usage overview
CREATE VIEW client_usage_stats AS
SELECT 
    c.client_id,
    c.client_name,
    c.total_embeddings,
    c.total_searches,
    c.last_active_at,
    COUNT(DISTINCT e.embedding_id) as active_embeddings,
    pg_size_pretty(SUM(e.vector_size_bytes)::BIGINT) as total_storage
FROM clients c
LEFT JOIN embeddings e ON c.client_id = e.client_id AND e.is_deleted = FALSE
GROUP BY c.client_id;

-- Recent search performance
CREATE VIEW recent_search_performance AS
SELECT 
    c.client_name,
    DATE_TRUNC('hour', s.created_at) as hour,
    COUNT(*) as searches,
    AVG(s.total_time_ms) as avg_time_ms,
    MAX(s.total_time_ms) as max_time_ms,
    AVG(s.candidates_checked) as avg_candidates
FROM search_requests s
JOIN clients c ON s.client_id = c.client_id
WHERE s.created_at > CURRENT_TIMESTAMP - INTERVAL '24 hours'
GROUP BY c.client_name, DATE_TRUNC('hour', s.created_at)
ORDER BY hour DESC;

-- =====================================================
-- INDEXES FOR PERFORMANCE
-- =====================================================

-- Additional performance indexes
CREATE INDEX idx_embeddings_recent ON embeddings(created_at DESC) 
    WHERE is_deleted = FALSE;

CREATE INDEX idx_search_recent ON search_requests(created_at DESC);

-- Partial indexes for active data
CREATE INDEX idx_active_embeddings ON embeddings(client_id, created_at) 
    WHERE is_deleted = FALSE;

-- =====================================================
-- MAINTENANCE PROCEDURES
-- =====================================================

-- Procedure to vacuum and analyze tables
CREATE OR REPLACE PROCEDURE maintenance_routine() AS $$
BEGIN
    -- Update materialized view
    REFRESH MATERIALIZED VIEW CONCURRENTLY lsh_bucket_sizes;
    
    -- Clean expired cache
    PERFORM cleanup_expired_cache();
    
    -- Vacuum and analyze main tables
    VACUUM ANALYZE embeddings;
    VACUUM ANALYZE lsh_hashes;
    VACUUM ANALYZE search_requests;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- EXAMPLE QUERIES
-- =====================================================

/*
-- Find LSH candidates for a search:
SELECT * FROM find_lsh_candidates(
    'client-uuid-here',
    ARRAY[12345, 67890, ...],
    100
);

-- Get embedding with metadata:
SELECT 
    e.embedding_id,
    e.encrypted_vector,
    m.metadata
FROM embeddings e
JOIN embedding_metadata m ON e.embedding_id = m.embedding_id
WHERE e.client_id = 'client-uuid' 
  AND e.external_id = 'sent_001';

-- Monitor recent performance:
SELECT * FROM recent_search_performance
WHERE client_name = 'Client A';

-- Check LSH distribution:
SELECT 
    table_index,
    COUNT(DISTINCT hash_value) as unique_hashes,
    AVG(bucket_size) as avg_bucket_size,
    MAX(bucket_size) as max_bucket_size
FROM lsh_bucket_sizes
WHERE client_id = 'client-uuid'
GROUP BY table_index;
*/