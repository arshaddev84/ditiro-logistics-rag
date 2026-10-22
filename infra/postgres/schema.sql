CREATE TABLE vehicles (
    vehicle_id TEXT PRIMARY KEY,
    registration TEXT UNIQUE NOT NULL,
    make_model TEXT NOT NULL,
    vehicle_type TEXT NOT NULL,
    capacity_kg INTEGER NOT NULL CHECK (capacity_kg > 0),
    fuel_capacity_l NUMERIC(8, 2) NOT NULL CHECK (fuel_capacity_l > 0),
    status TEXT NOT NULL CHECK (
        status IN (
            'AVAILABLE',
            'ON_TRIP',
            'MAINTENANCE',
            'OFFLINE'
        )
    ),
    home_depot TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE drivers (
    driver_id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    licence_code TEXT NOT NULL,
    licence_expiry DATE NOT NULL,
    safety_score NUMERIC(5, 2) NOT NULL CHECK (
        safety_score BETWEEN 0 AND 100
    ),
    status TEXT NOT NULL CHECK (
        status IN (
            'AVAILABLE',
            'ON_TRIP',
            'OFF_DUTY',
            'SUSPENDED'
        )
    )
);

CREATE TABLE trips (
    trip_id TEXT PRIMARY KEY,
    vehicle_id TEXT NOT NULL REFERENCES vehicles (vehicle_id),
    driver_id TEXT NOT NULL REFERENCES drivers (driver_id),
    origin TEXT NOT NULL,
    destination TEXT NOT NULL,
    corridor TEXT NOT NULL DEFAULT 'N3',
    planned_departure TIMESTAMPTZ NOT NULL,
    planned_arrival TIMESTAMPTZ NOT NULL,
    actual_departure TIMESTAMPTZ,
    actual_arrival TIMESTAMPTZ,
    status TEXT NOT NULL CHECK (
        status IN (
            'PLANNED',
            'IN_TRANSIT',
            'DELAYED',
            'COMPLETED',
            'CANCELLED'
        )
    ),
    cargo_description TEXT NOT NULL,
    cargo_weight_kg INTEGER NOT NULL CHECK (cargo_weight_kg > 0),
    delivery_priority TEXT NOT NULL CHECK (
        delivery_priority IN (
            'LOW',
            'NORMAL',
            'HIGH',
            'CRITICAL'
        )
    ),
    customer_reference TEXT UNIQUE NOT NULL,
    CHECK (
        planned_arrival > planned_departure
    )
);

CREATE TABLE telemetry_events (
    telemetry_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    vehicle_id TEXT NOT NULL REFERENCES vehicles (vehicle_id),
    trip_id TEXT REFERENCES trips (trip_id),
    observed_at TIMESTAMPTZ NOT NULL,
    latitude NUMERIC(9, 6) NOT NULL CHECK (latitude BETWEEN -90 AND 90),
    longitude NUMERIC(9, 6) NOT NULL CHECK (
        longitude BETWEEN -180 AND 180
    ),
    speed_kph NUMERIC(6, 2) NOT NULL CHECK (speed_kph >= 0),
    fuel_level_pct NUMERIC(5, 2) CHECK (
        fuel_level_pct BETWEEN 0 AND 100
    ),
    engine_temp_c NUMERIC(5, 2),
    idle_seconds INTEGER NOT NULL DEFAULT 0 CHECK (idle_seconds >= 0),
    event_type TEXT NOT NULL CHECK (
        event_type IN (
            'GPS_PING',
            'STOPPED',
            'HARSH_BRAKING',
            'GEOFENCE_DEVIATION',
            'ENGINE_WARNING'
        )
    ),
    source TEXT NOT NULL DEFAULT 'SYNTHETIC_IOT'
);

CREATE TABLE security_incidents (
    incident_id TEXT PRIMARY KEY,
    trip_id TEXT REFERENCES trips (trip_id),
    vehicle_id TEXT REFERENCES vehicles (vehicle_id),
    occurred_at TIMESTAMPTZ NOT NULL,
    location_name TEXT NOT NULL,
    latitude NUMERIC(9, 6),
    longitude NUMERIC(9, 6),
    incident_type TEXT NOT NULL,
    severity TEXT NOT NULL CHECK (
        severity IN (
            'LOW',
            'MEDIUM',
            'HIGH',
            'CRITICAL'
        )
    ),
    verification_status TEXT NOT NULL CHECK (
        verification_status IN (
            'UNVERIFIED',
            'CORROBORATED',
            'OFFICIAL',
            'DISMISSED'
        )
    ),
    summary TEXT NOT NULL,
    source_name TEXT NOT NULL,
    source_url TEXT,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE fuel_events (
    fuel_event_id TEXT PRIMARY KEY,
    vehicle_id TEXT NOT NULL REFERENCES vehicles (vehicle_id),
    trip_id TEXT REFERENCES trips (trip_id),
    occurred_at TIMESTAMPTZ NOT NULL,
    station_name TEXT NOT NULL,
    location_name TEXT NOT NULL,
    litres NUMERIC(8, 2) NOT NULL CHECK (litres > 0),
    price_per_litre_zar NUMERIC(8, 3) NOT NULL CHECK (price_per_litre_zar > 0),
    total_cost_zar NUMERIC(10, 2) GENERATED ALWAYS AS (
        ROUND(
            litres * price_per_litre_zar,
            2
        )
    ) STORED,
    odometer_km INTEGER CHECK (odometer_km >= 0)
);

CREATE TABLE port_observations (
    observation_id TEXT PRIMARY KEY,
    terminal_name TEXT NOT NULL,
    port_name TEXT NOT NULL,
    observed_at TIMESTAMPTZ NOT NULL,
    estimated_queue_hours NUMERIC(6, 2) NOT NULL CHECK (estimated_queue_hours >= 0),
    vessel_delay_hours NUMERIC(6, 2) CHECK (vessel_delay_hours >= 0),
    congestion_level TEXT NOT NULL CHECK (
        congestion_level IN (
            'LOW',
            'MODERATE',
            'HIGH',
            'SEVERE'
        )
    ),
    source_name TEXT NOT NULL,
    confidence NUMERIC(4, 3) NOT NULL CHECK (confidence BETWEEN 0 AND 1),
    is_synthetic BOOLEAN NOT NULL DEFAULT TRUE
);

-- Metadata for documents whose chunks and embeddings
-- will be stored in Qdrant.
CREATE TABLE knowledge_documents (
    document_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    document_type TEXT NOT NULL,
    version TEXT NOT NULL,
    effective_from DATE,
    effective_to DATE,
    source_uri TEXT,
    content_text TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::JSONB,
    content_sha256 TEXT NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE agent_runs (
    run_id TEXT PRIMARY KEY,
    trip_id TEXT REFERENCES trips (trip_id),
    coordinator_agent TEXT NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    status TEXT NOT NULL CHECK (
        status IN (
            'QUEUED',
            'RUNNING',
            'SUCCEEDED',
            'FAILED',
            'NEEDS_REVIEW'
        )
    ),
    input_event_id TEXT,
    model_name TEXT NOT NULL,
    prompt_version TEXT NOT NULL,
    error_summary TEXT,
    CHECK (
        completed_at IS NULL
        OR completed_at >= started_at
    )
);

CREATE TABLE agent_recommendations (
    recommendation_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES agent_runs (run_id),
    trip_id TEXT REFERENCES trips (trip_id),
    agent_name TEXT NOT NULL CHECK (
        agent_name IN (
            'RISK_SECURITY',
            'PORT_DELAY',
            'DISPATCH_OPTIMIZATION',
            'COORDINATOR'
        )
    ),
    action_type TEXT NOT NULL,
    priority TEXT NOT NULL CHECK (
        priority IN (
            'INFO',
            'LOW',
            'MEDIUM',
            'HIGH',
            'CRITICAL'
        )
    ),
    title TEXT NOT NULL,
    rationale TEXT NOT NULL,
    evidence_refs JSONB NOT NULL DEFAULT '[]'::JSONB,
    estimated_saving_zar NUMERIC(12, 2),
    confidence NUMERIC(4, 3) NOT NULL CHECK (confidence BETWEEN 0 AND 1),
    status TEXT NOT NULL CHECK (
        status IN (
            'PROPOSED',
            'APPROVED',
            'REJECTED',
            'EXECUTED',
            'EXPIRED'
        )
    ),
    requires_human_approval BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    reviewed_at TIMESTAMPTZ,
    reviewed_by TEXT
);

-- Transactional outbox for reliable Redis event publishing.
CREATE TABLE event_outbox (
    event_id TEXT PRIMARY KEY,
    aggregate_type TEXT NOT NULL,
    aggregate_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    payload JSONB NOT NULL,
    published_at TIMESTAMPTZ,
    attempts INTEGER NOT NULL DEFAULT 0 CHECK (attempts >= 0),
    last_error TEXT
);

-- Query performance indexes
CREATE INDEX idx_trips_status_departure ON trips (status, planned_departure);

CREATE INDEX idx_telemetry_vehicle_time ON telemetry_events (vehicle_id, observed_at DESC);

CREATE INDEX idx_telemetry_trip_time ON telemetry_events (trip_id, observed_at DESC);

CREATE INDEX idx_incidents_time_severity ON security_incidents (occurred_at DESC, severity);

CREATE INDEX idx_incidents_verification ON security_incidents (
    verification_status,
    expires_at
);

CREATE INDEX idx_fuel_vehicle_time ON fuel_events (vehicle_id, occurred_at DESC);

CREATE INDEX idx_port_terminal_time ON port_observations (
    terminal_name,
    observed_at DESC
);

CREATE INDEX idx_knowledge_metadata ON knowledge_documents USING GIN (metadata);

CREATE INDEX idx_recommendations_status ON agent_recommendations (
    status,
    priority,
    created_at DESC
);

CREATE INDEX idx_outbox_pending ON event_outbox (occurred_at)
WHERE
    published_at IS NULL;