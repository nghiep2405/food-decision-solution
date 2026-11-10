PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS restaurants (
    id TEXT PRIMARY KEY,
    external_provider TEXT,
    external_id TEXT,
    name TEXT NOT NULL,
    address_line TEXT,
    ward TEXT,
    district TEXT,
    city TEXT NOT NULL,
    latitude REAL NOT NULL CHECK (latitude BETWEEN -90 AND 90),
    longitude REAL NOT NULL CHECK (longitude BETWEEN -180 AND 180),
    phone TEXT,
    rating REAL CHECK (rating IS NULL OR rating BETWEEN 0 AND 5),
    review_count INTEGER CHECK (review_count IS NULL OR review_count >= 0),
    price_level INTEGER CHECK (price_level IS NULL OR price_level BETWEEN 1 AND 4),
    data_status TEXT NOT NULL CHECK (
        data_status IN ('verified', 'unverified', 'stale', 'partial')
    ),
    source_name TEXT NOT NULL,
    source_url TEXT,
    collected_at TEXT NOT NULL,
    updated_at TEXT,
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    UNIQUE (external_provider, external_id)
);

CREATE TABLE IF NOT EXISTS restaurant_hours (
    id TEXT PRIMARY KEY,
    restaurant_id TEXT NOT NULL REFERENCES restaurants(id) ON DELETE CASCADE,
    weekday INTEGER NOT NULL CHECK (weekday BETWEEN 0 AND 6),
    open_time TEXT,
    close_time TEXT,
    crosses_midnight INTEGER NOT NULL DEFAULT 0 CHECK (crosses_midnight IN (0, 1)),
    status TEXT NOT NULL CHECK (status IN ('known', 'closed', 'unknown')),
    source_name TEXT NOT NULL,
    updated_at TEXT,
    UNIQUE (restaurant_id, weekday)
);

CREATE TABLE IF NOT EXISTS restaurant_tags (
    id TEXT PRIMARY KEY,
    restaurant_id TEXT NOT NULL REFERENCES restaurants(id) ON DELETE CASCADE,
    tag_type TEXT NOT NULL CHECK (
        tag_type IN ('cuisine', 'flavor', 'dish_category', 'occasion', 'diet')
    ),
    tag_value TEXT NOT NULL,
    source TEXT NOT NULL,
    confidence REAL CHECK (confidence IS NULL OR confidence BETWEEN 0 AND 1),
    UNIQUE (restaurant_id, tag_type, tag_value)
);

CREATE TABLE IF NOT EXISTS menu_assets (
    id TEXT PRIMARY KEY,
    restaurant_id TEXT NOT NULL REFERENCES restaurants(id) ON DELETE CASCADE,
    asset_type TEXT NOT NULL CHECK (asset_type IN ('image', 'text', 'structured')),
    local_path TEXT,
    source_url TEXT,
    source_type TEXT NOT NULL CHECK (
        source_type IN ('restaurant_provided', 'provider', 'public_image', 'manual_sample', 'synthetic_fixture')
    ),
    captured_at TEXT,
    checksum TEXT,
    processing_status TEXT NOT NULL CHECK (
        processing_status IN ('pending', 'processing', 'processed', 'failed')
    ),
    created_at TEXT NOT NULL,
    UNIQUE (checksum)
);

CREATE TABLE IF NOT EXISTS ocr_runs (
    id TEXT PRIMARY KEY,
    menu_asset_id TEXT NOT NULL REFERENCES menu_assets(id) ON DELETE CASCADE,
    method TEXT NOT NULL CHECK (method IN ('visual', 'text_pipeline')),
    model_version TEXT NOT NULL,
    prompt_version TEXT,
    raw_text TEXT,
    raw_response_path TEXT,
    structured_json_path TEXT,
    confidence REAL CHECK (confidence IS NULL OR confidence BETWEEN 0 AND 1),
    latency_ms INTEGER CHECK (latency_ms IS NULL OR latency_ms >= 0),
    status TEXT NOT NULL CHECK (status IN ('pending', 'completed', 'failed')),
    error_message TEXT,
    processed_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS menu_versions (
    id TEXT PRIMARY KEY,
    restaurant_id TEXT NOT NULL REFERENCES restaurants(id) ON DELETE CASCADE,
    menu_asset_id TEXT REFERENCES menu_assets(id) ON DELETE SET NULL,
    ocr_run_id TEXT REFERENCES ocr_runs(id) ON DELETE SET NULL,
    source_type TEXT NOT NULL CHECK (
        source_type IN ('structured', 'restaurant_provided', 'ocr_visual', 'ocr_text_pipeline', 'synthetic_fixture')
    ),
    verification_status TEXT NOT NULL CHECK (
        verification_status IN ('verified', 'unverified', 'outdated', 'unknown')
    ),
    confidence REAL CHECK (confidence IS NULL OR confidence BETWEEN 0 AND 1),
    effective_at TEXT,
    created_at TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 0 CHECK (is_active IN (0, 1)),
    notes TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_active_menu_per_restaurant
ON menu_versions(restaurant_id)
WHERE is_active = 1;

CREATE TABLE IF NOT EXISTS menu_items (
    id TEXT PRIMARY KEY,
    menu_version_id TEXT NOT NULL REFERENCES menu_versions(id) ON DELETE CASCADE,
    category TEXT,
    original_name TEXT NOT NULL,
    normalized_name TEXT NOT NULL,
    description TEXT,
    availability TEXT NOT NULL DEFAULT 'unknown' CHECK (
        availability IN ('available', 'unavailable', 'unknown')
    ),
    confidence REAL CHECK (confidence IS NULL OR confidence BETWEEN 0 AND 1),
    verification_status TEXT NOT NULL CHECK (
        verification_status IN ('verified', 'unverified', 'outdated', 'unknown')
    ),
    source_line TEXT
);

CREATE TABLE IF NOT EXISTS menu_item_variants (
    id TEXT PRIMARY KEY,
    menu_item_id TEXT NOT NULL REFERENCES menu_items(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    price INTEGER CHECK (price IS NULL OR price >= 0),
    price_min INTEGER CHECK (price_min IS NULL OR price_min >= 0),
    price_max INTEGER CHECK (price_max IS NULL OR price_max >= 0),
    currency TEXT NOT NULL DEFAULT 'VND',
    confidence REAL CHECK (confidence IS NULL OR confidence BETWEEN 0 AND 1),
    verification_status TEXT NOT NULL CHECK (
        verification_status IN ('verified', 'unverified', 'outdated', 'unknown')
    ),
    CHECK (price_min IS NULL OR price_max IS NULL OR price_min <= price_max)
);

CREATE TABLE IF NOT EXISTS reviews (
    id TEXT PRIMARY KEY,
    restaurant_id TEXT NOT NULL REFERENCES restaurants(id) ON DELETE CASCADE,
    external_review_id TEXT,
    rating REAL CHECK (rating IS NULL OR rating BETWEEN 0 AND 5),
    text TEXT,
    created_at TEXT,
    author_hash TEXT,
    author_review_count INTEGER CHECK (author_review_count IS NULL OR author_review_count >= 0),
    helpful_count INTEGER CHECK (helpful_count IS NULL OR helpful_count >= 0),
    language TEXT,
    source_name TEXT NOT NULL,
    source_url TEXT,
    collected_at TEXT NOT NULL,
    data_status TEXT NOT NULL CHECK (
        data_status IN ('verified', 'unverified', 'stale', 'partial')
    )
);

CREATE TABLE IF NOT EXISTS review_analysis_runs (
    id TEXT PRIMARY KEY,
    restaurant_id TEXT NOT NULL REFERENCES restaurants(id) ON DELETE CASCADE,
    method TEXT NOT NULL CHECK (
        method IN ('text_similarity', 'metadata_anomaly', 'combined')
    ),
    model_version TEXT NOT NULL,
    prompt_version TEXT,
    analyzed_count INTEGER NOT NULL CHECK (analyzed_count >= 0),
    risk_level TEXT CHECK (risk_level IS NULL OR risk_level IN ('low', 'medium', 'high')),
    confidence REAL CHECK (confidence IS NULL OR confidence BETWEEN 0 AND 1),
    evidence_status TEXT NOT NULL CHECK (
        evidence_status IN ('sufficient', 'insufficient_evidence')
    ),
    signals_json TEXT NOT NULL DEFAULT '[]',
    agent_explanation TEXT,
    metrics_json TEXT,
    latency_ms INTEGER CHECK (latency_ms IS NULL OR latency_ms >= 0),
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS decision_runs (
    id TEXT PRIMARY KEY,
    mode TEXT NOT NULL CHECK (mode IN ('direct', 'recommendation')),
    search_context_json TEXT NOT NULL,
    candidate_source TEXT NOT NULL CHECK (candidate_source IN ('local', 'external', 'auto')),
    candidate_ids_json TEXT NOT NULL DEFAULT '[]',
    ranked_result_json TEXT,
    model_version TEXT,
    prompt_version TEXT,
    latency_ms INTEGER CHECK (latency_ms IS NULL OR latency_ms >= 0),
    status TEXT NOT NULL CHECK (status IN ('pending', 'completed', 'failed')),
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS feedback_submissions (
    id TEXT PRIMARY KEY,
    decision_run_id TEXT REFERENCES decision_runs(id) ON DELETE SET NULL,
    actor_type TEXT NOT NULL CHECK (actor_type IN ('user', 'restaurant_owner')),
    target_type TEXT NOT NULL CHECK (
        target_type IN ('restaurant', 'menu_item', 'price', 'location', 'result_relevance', 'review_warning')
    ),
    target_id TEXT NOT NULL,
    feedback_type TEXT NOT NULL,
    description TEXT,
    evidence_path TEXT,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (
        status IN ('pending', 'accepted', 'rejected', 'merged')
    ),
    submitted_at TEXT NOT NULL,
    reviewed_at TEXT,
    resolution_note TEXT
);

CREATE INDEX IF NOT EXISTS idx_restaurants_location
ON restaurants(latitude, longitude);

CREATE INDEX IF NOT EXISTS idx_restaurant_tags_value
ON restaurant_tags(tag_type, tag_value);

CREATE INDEX IF NOT EXISTS idx_menu_items_normalized_name
ON menu_items(normalized_name);

CREATE INDEX IF NOT EXISTS idx_reviews_restaurant_created
ON reviews(restaurant_id, created_at);

CREATE INDEX IF NOT EXISTS idx_review_analysis_restaurant_created
ON review_analysis_runs(restaurant_id, created_at);

CREATE INDEX IF NOT EXISTS idx_decision_runs_created
ON decision_runs(created_at);

CREATE INDEX IF NOT EXISTS idx_feedback_status
ON feedback_submissions(status, submitted_at);
