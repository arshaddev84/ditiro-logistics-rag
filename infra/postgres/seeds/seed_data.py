
"""
Seed a synthetic South African logistics fleet into PostgreSQL.

Requirements:
    pip install "psycopg[binary]>=3.2,<4"

Configuration:
    PG_HOST, PG_PORT, PG_DATABASE, PG_USER, PG_PASSWORD

Optional:
    DATABASE_URL

All generated records are synthetic. No live intelligence feeds are used.
The script expects the 11 tables from the logistics schema to exist.
"""

from __future__ import annotations

import hashlib
import os
from dotenv import load_dotenv
import random
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo
import psycopg
from psycopg.types.json import Jsonb

load_dotenv()


RECORD_COUNT = 20
SEED = 47
TZ = ZoneInfo("Africa/Johannesburg")
RNG = random.Random(SEED)

VEHICLE_TYPES = [
    "TAUTLINER", "REFRIGERATED", "FLATBED", "TANKER"
]
TRIP_STATUSES = [
    "PLANNED", "IN_TRANSIT", "DELAYED", "COMPLETED"
]
PRIORITIES = ["LOW", "NORMAL", "HIGH", "CRITICAL"]
RECOMMENDATION_PRIORITIES = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
SEVERITIES = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]

# Approximate synthetic waypoints along the N3 corridor.
WAYPOINTS = [
    ("Johannesburg", -26.2041, 28.0473),
    ("Heidelberg", -26.5048, 28.3592),
    ("Villiers", -27.0300, 28.6000),
    ("Warden", -27.8500, 28.9500),
    ("Harrismith", -28.2728, 29.1295),
    ("Van Reenen", -28.3710, 29.3800),
    ("Ladysmith", -28.5597, 29.7800),
    ("Estcourt", -29.0120, 29.8700),
    ("Mooi River", -29.2080, 29.9940),
    ("Howick", -29.4870, 30.2300),
    ("Pietermaritzburg", -29.6000, 30.3790),
    ("Cato Ridge", -29.7300, 30.5700),
    ("Durban", -29.8587, 31.0218),
]

NOW = datetime.now(TZ).replace(microsecond=0)


def connect() -> psycopg.Connection:
    """Connect using DATABASE_URL or standard PostgreSQL environment variables."""
    database_url = os.getenv("DATABASE_URL")

    if database_url:
        return psycopg.connect(database_url)

    password = os.getenv("PG_PASSWORD")
    if not password:
        raise RuntimeError(
            "Set PG_PASSWORD or DATABASE_URL before running this script."
        )

    return psycopg.connect(
        host=os.getenv("PG_HOST"),
        port=os.getenv("PG_PORT"),
        dbname=os.getenv("PG_DATABASE"),
        user=os.getenv("PG_USER"),
        password=password,
        connect_timeout=10,
    )


def stable_time(days_offset: int, hours_offset: int = 0) -> datetime:
    """Create repeatable timestamps anchored to the current execution hour."""
    anchor = NOW.replace(minute=0, second=0)
    return anchor + timedelta(
        days=days_offset, hours=hours_offset
    )


def synthetic_phone(index: int) -> str:
    """Return an obviously synthetic phone number."""
    return f"+27-000-000-{index:03d}"


def make_vehicles() -> list[tuple]:
    rows = []

    for i in range(1, RECORD_COUNT + 1):
        vehicle_type = VEHICLE_TYPES[(i - 1) % len(VEHICLE_TYPES)]
        location = "Durban" if i % 3 == 0 else "Johannesburg"

        status = (
            "ON_TRIP" if i <= 8
            else "MAINTENANCE" if i in (9, 10)
            else "AVAILABLE"
        )

        rows.append((
            f"VEH-{i:03d}",
            f"SYN-{i:04d}-GP",
            [
                "Volvo FH 460",
                "Scania R450",
                "Mercedes-Benz Actros 2645",
                "MAN TGX 26.480",
            ][(i - 1) % 4],
            vehicle_type,
            22000 + (i % 7) * 1000,
            Decimal(500 + (i % 7) * 20),
            status,
            location,
        ))

    return rows


def make_drivers() -> list[tuple]:
    first_names = [
        "Sipho", "Nomsa", "Thabo", "Lerato", "Pieter",
        "Zanele", "Ayanda", "Kabelo", "Musa", "Fatima",
        "Naledi", "Sibusiso", "Ayesha", "Lungile", "Daniel",
        "Nandi", "Bongani", "Karabo", "Mariam", "Themba",
    ]
    surnames = [
        "Dlamini", "Khumalo", "Mokoena", "Nkosi", "Jacobs",
        "Ndlovu", "Sithole", "Molefe", "Cele", "Daniels",
        "Mthembu", "Naidoo", "Pillay", "Botha", "Mahlangu",
        "Zulu", "Maseko", "Adams", "Mabena", "Van der Merwe",
    ]

    rows = []

    for i in range(1, RECORD_COUNT + 1):
        rows.append((
            f"DRV-{i:03d}",
            f"{first_names[i - 1]} {surnames[i - 1]}",
            "EC",
            date(2027 + i % 3, 1 + i % 12, 15),
            round(RNG.uniform(70, 99), 2),
            "ON_TRIP" if i <= 8 else "AVAILABLE",
        ))

    return rows


def make_trips() -> list[tuple]:
    rows = []
    origins = [
        "City Deep, Johannesburg",
        "Midrand, Gauteng",
        "Wadeville, Gauteng",
        "Isando, Ekurhuleni",
        "Harrismith, Free State",
    ]
    destinations = [
        "Durban Container Terminal",
        "Prospecton, Durban",
        "Cato Ridge, KwaZulu-Natal",
        "Pinetown, Durban",
        "Durban distribution centre",
    ]
    cargoes = [
        "Packaged household goods",
        "Containerised retail stock",
        "Industrial components",
        "Temperature-controlled produce",
        "Automotive components",
        "Building materials",
        "Packaged food products",
        "General merchandise",
    ]

    for i in range(1, RECORD_COUNT + 1):
        departure = stable_time(
            (i % 5) - 2,
            (i * 3) % 12,
        )
        duration = timedelta(hours=7 + (i % 6), minutes=(i * 7) % 60)
        arrival = departure + duration

        status = TRIP_STATUSES[(i - 1) % len(TRIP_STATUSES)]
        actual_departure = departure + timedelta(minutes=(i * 3) % 35)
        actual_arrival = (
            arrival + timedelta(minutes=(i * 11) % 90)
            if status == "COMPLETED"
            else None
        )

        rows.append((
            f"TRP-{1000 + i}",
            f"VEH-{i:03d}",
            f"DRV-{i:03d}",
            origins[(i - 1) % len(origins)],
            destinations[(i - 1) % len(destinations)],
            "N3",
            departure,
            arrival,
            actual_departure,
            actual_arrival,
            status,
            cargoes[(i - 1) % len(cargoes)],
            RNG.randint(8000, 24000),
            PRIORITIES[(i - 1) % len(PRIORITIES)],
            f"SYN-CUST-{7000 + i}",
        ))

    return rows


def make_telemetry() -> list[tuple]:
    rows = []

    for i in range(1, RECORD_COUNT + 1):
        waypoint = WAYPOINTS[(i * 3) % len(WAYPOINTS)]
        location, lat, lon = waypoint

        # Small deterministic coordinate variation.
        lat += RNG.uniform(-0.015, 0.015)
        lon += RNG.uniform(-0.015, 0.015)

        event_type = [
            "GPS_PING", "GPS_PING", "STOPPED",
            "HARSH_BRAKING", "GEOFENCE_DEVIATION",
            "ENGINE_WARNING",
        ][(i - 1) % 6]

        rows.append((
            900000 + i,
            f"VEH-{((i - 1) % RECORD_COUNT) + 1:03d}",
            f"TRP-{1000 + ((i - 1) % RECORD_COUNT) + 1}",
            stable_time(-((i - 1) // 5), -((i - 1) % 5) * 5),
            round(lat, 6),
            round(lon, 6),
            Decimal(str(round(RNG.uniform(0, 85), 2))),
            Decimal(str(round(RNG.uniform(15, 95), 2))),
            Decimal(str(round(RNG.uniform(78, 102), 2))),
            RNG.randint(0, 1200),
            event_type,
            "SYNTHETIC_IOT",
        ))

    return rows


def make_incidents() -> list[tuple]:
    incident_types = [
        "ROADBLOCK", "PROTEST", "SUSPICIOUS_STOP",
        "WEATHER_HAZARD", "CARGO_THEFT_REPORTED",
        "HIJACKING_REPORTED",
    ]
    verification = [
        "UNVERIFIED", "UNVERIFIED", "CORROBORATED",
        "OFFICIAL", "DISMISSED",
    ]
    rows = []

    for i in range(1, RECORD_COUNT + 1):
        location, lat, lon = WAYPOINTS[(i * 2) % len(WAYPOINTS)]
        occurred = stable_time(-((i - 1) % 4), -i)

        rows.append((
            f"INC-{9000 + i}",
            f"TRP-{1000 + i}" if i <= RECORD_COUNT else None,
            f"VEH-{i:03d}" if i <= RECORD_COUNT else None,
            occurred,
            f"Synthetic report near {location}",
            round(lat, 6),
            round(lon, 6),
            incident_types[(i - 1) % len(incident_types)],
            SEVERITIES[(i - 1) % len(SEVERITIES)],
            verification[(i - 1) % len(verification)],
            (
                f"Synthetic scenario {i}: review the reported event, "
                "check source reliability, and corroborate before action."
            ),
            "SYNTHETIC_SCENARIO_FEED",
            None,
            occurred + timedelta(hours=6),
        ))

    return rows


def make_fuel_events() -> list[tuple]:
    stations = [
        "Synthetic Truck Stop A",
        "Synthetic Truck Stop B",
        "Synthetic Highway Fuel Centre",
        "Synthetic Fleet Fuel Depot",
    ]
    rows = []

    for i in range(1, RECORD_COUNT + 1):
        vehicle_num = i
        location = WAYPOINTS[(i * 2) % len(WAYPOINTS)][0]

        rows.append((
            f"FUL-{5000 + i}",
            f"VEH-{vehicle_num:03d}",
            f"TRP-{1000 + vehicle_num}",
            stable_time(-((i - 1) % 7), -i),
            stations[(i - 1) % len(stations)],
            location,
            Decimal(str(round(RNG.uniform(100, 400), 2))),
            Decimal(str(round(RNG.uniform(21.50, 24.50), 3))),
            350000 + i * 1730,
        ))

    return rows


def make_port_observations() -> list[tuple]:
    terminals = [
        "Durban Container Terminal Pier 1",
        "Durban Container Terminal Pier 2",
        "Durban Multipurpose Terminal",
        "Durban Point Terminal",
    ]
    rows = []

    for i in range(1, RECORD_COUNT + 1):
        queue = round(RNG.uniform(0.5, 12), 2)
        congestion = (
            "SEVERE" if queue >= 9
            else "HIGH" if queue >= 6
            else "MODERATE" if queue >= 3
            else "LOW"
        )

        rows.append((
            f"PORT-{7000 + i}",
            terminals[(i - 1) % len(terminals)],
            "Port of Durban",
            stable_time(-((i - 1) // 5), -((i - 1) % 5) * 2),
            Decimal(str(queue)),
            Decimal(str(round(RNG.uniform(0, 8), 2))),
            congestion,
            "SYNTHETIC_PORT_FEED",
            Decimal(str(round(RNG.uniform(0.45, 0.95), 3))),
            True,
        ))

    return rows


DOCUMENTS = [
    (
        "N3 Driver Safety SOP",
        "SOP",
        "Follow company emergency procedures when a driver encounters a suspected security threat. Contact the control room and do not reroute solely on an unverified alert.",
        {"corridor": "N3", "topic": "driver_safety"},
    ),
    (
        "Port Delay Escalation Policy",
        "CUSTOMER_POLICY",
        "When predicted terminal queues exceed six hours, recalculate delivery ETAs and notify dispatch. Treat unverified feed estimates as uncertain.",
        {"port": "Durban", "topic": "delay_escalation"},
    ),
    (
        "Fuel Efficiency Operating Guide",
        "SOP",
        "Avoid unnecessary idling and investigate unusual fuel use against payload, terrain, traffic and distance. Do not judge drivers using one uncontextualised reading.",
        {"topic": "fuel_efficiency"},
    ),
    (
        "Incident Verification Standard",
        "SAFETY_BULLETIN",
        "Preserve the source, timestamp, location, verification status and expiry for every alert. Corroborate high-impact reports before changing a route.",
        {"topic": "risk_verification"},
    ),
    (
        "Dispatch Prioritisation Guide",
        "SOP",
        "Prioritise critical deliveries while respecting vehicle capacity, driver availability, delivery windows and safe operating limits.",
        {"topic": "dispatch"},
    ),
]


def make_documents() -> list[tuple]:
    rows = []

    for i in range(1, RECORD_COUNT + 1):
        title, document_type, content, metadata = DOCUMENTS[
            (i - 1) % len(DOCUMENTS)
        ]
        version = f"1.{(i - 1) // len(DOCUMENTS)}"
        document_id = f"DOC-{i:03d}"
        digest = hashlib.sha256(
            f"{document_id}:{version}:{content}".encode()
        ).hexdigest()

        rows.append((
            document_id,
            title,
            document_type,
            version,
            date(2026, 1, 1) + timedelta(days=i * 3),
            None,
            f"synthetic://documents/{document_id.lower()}",
            content,
            Jsonb({**metadata, "synthetic": True}),
            digest,
            True,
        ))

    return rows


def make_agent_runs() -> list[tuple]:
    rows = []

    for i in range(1, RECORD_COUNT + 1):
        started = stable_time(-((i - 1) % 3), -(i * 2))
        status = "NEEDS_REVIEW" if i % 7 == 0 else "SUCCEEDED"

        rows.append((
            f"RUN-{3000 + i}",
            f"TRP-{1000 + i}",
            "coordinator-v1",
            started,
            started + timedelta(seconds=2 + i % 10),
            status,
            f"EVT-{8000 + i}",
            "local-llm-synthetic",
            "coordinator-v1",
            None,
        ))

    return rows


def make_recommendations() -> list[tuple]:
    agents = [
        "RISK_SECURITY",
        "PORT_DELAY",
        "DISPATCH_OPTIMIZATION",
        "COORDINATOR",
    ]
    actions = [
        ("VERIFY_ALERT", "Verify the alert with an independent source."),
        ("RECALCULATE_ETA", "Refresh ETA using the latest observation."),
        ("REVIEW_SEQUENCE", "Review delivery order against current constraints."),
        ("CONTACT_DRIVER", "Contact the driver to validate the reported stop."),
        ("MONITOR_FUEL", "Compare fuel use against trip conditions."),
    ]
    rows = []

    for i in range(1, RECORD_COUNT + 1):
        action, rationale = actions[(i - 1) % len(actions)]
        priority = RECOMMENDATION_PRIORITIES[
            (i - 1) % len(RECOMMENDATION_PRIORITIES)
        ]

        rows.append((
            f"REC-{4000 + i}",
            f"RUN-{3000 + i}",
            f"TRP-{1000 + i}",
            agents[(i - 1) % len(agents)],
            action,
            priority,
            f"Synthetic recommendation {i}: {action.lower().replace('_', ' ')}",
            rationale,
            Jsonb([
                {"type": "trip", "id": f"TRP-{1000 + i}"},
                {"type": "document", "id": f"DOC-{((i - 1) % RECORD_COUNT) + 1:03d}"},
            ]),
            Decimal(str(round(RNG.uniform(100, 1500), 2))),
            Decimal(str(round(RNG.uniform(0.50, 0.95), 3))),
            "PROPOSED",
            True,
            None,
            None,
        ))

    return rows


def make_outbox_events() -> list[tuple]:
    event_types = [
        "trip.created",
        "trip.delay_detected",
        "telemetry.received",
        "incident.reported",
        "port.observation_received",
    ]
    rows = []

    for i in range(1, RECORD_COUNT + 1):
        trip_id = f"TRP-{1000 + i}"
        event_type = event_types[(i - 1) % len(event_types)]
        occurred = stable_time(-((i - 1) % 4), -i)

        rows.append((
            f"EVT-{8000 + i}",
            "trip",
            trip_id,
            event_type,
            occurred,
            Jsonb({
                "trip_id": trip_id,
                "event_type": event_type,
                "source": "synthetic-seeder",
                "is_synthetic": True,
            }),
            None,
            0,
            None,
        ))

    return rows


def insert_many(
    cursor: psycopg.Cursor,
    sql: str,
    rows: list[tuple],
) -> None:
    """Insert records efficiently; stable primary keys prevent duplicates."""
    cursor.executemany(sql, rows)


def seed() -> None:
    """Seed all 11 tables in one transaction."""
    vehicles = make_vehicles()
    drivers = make_drivers()
    trips = make_trips()
    telemetry = make_telemetry()
    incidents = make_incidents()
    fuel = make_fuel_events()
    ports = make_port_observations()
    documents = make_documents()
    runs = make_agent_runs()
    recommendations = make_recommendations()
    events = make_outbox_events()

    with connect() as connection:
        with connection.cursor() as cursor:
            # 1. Fleet reference data
            insert_many(cursor, """
                INSERT INTO vehicles (
                    vehicle_id, registration, make_model, vehicle_type,
                    capacity_kg, fuel_capacity_l, status, home_depot
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (vehicle_id) DO NOTHING
            """, vehicles)

            insert_many(cursor, """
                INSERT INTO drivers (
                    driver_id, display_name, licence_code, licence_expiry,
                    safety_score, status
                ) VALUES (%s,%s,%s,%s,%s,%s)
                ON CONFLICT (driver_id) DO NOTHING
            """, drivers)

            # 2. Trips depend on vehicles and drivers
            insert_many(cursor, """
                INSERT INTO trips (
                    trip_id, vehicle_id, driver_id, origin, destination,
                    corridor, planned_departure, planned_arrival,
                    actual_departure, actual_arrival, status,
                    cargo_description, cargo_weight_kg, delivery_priority,
                    customer_reference
                ) VALUES (
                    %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                    %s,%s,%s,%s,%s
                )
                ON CONFLICT (trip_id) DO NOTHING
            """, trips)

            # 3. Operational events
            insert_many(cursor, """
                INSERT INTO telemetry_events (
                    telemetry_id, vehicle_id, trip_id, observed_at,
                    latitude, longitude, speed_kph, fuel_level_pct,
                    engine_temp_c, idle_seconds, event_type, source
                ) OVERRIDING SYSTEM VALUE
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (telemetry_id) DO NOTHING
            """, telemetry)

            insert_many(cursor, """
                INSERT INTO security_incidents (
                    incident_id, trip_id, vehicle_id, occurred_at,
                    location_name, latitude, longitude, incident_type,
                    severity, verification_status, summary, source_name,
                    source_url, expires_at
                ) VALUES (
                    %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s
                )
                ON CONFLICT (incident_id) DO NOTHING
            """, incidents)

            insert_many(cursor, """
                INSERT INTO fuel_events (
                    fuel_event_id, vehicle_id, trip_id, occurred_at,
                    station_name, location_name, litres,
                    price_per_litre_zar, odometer_km
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (fuel_event_id) DO NOTHING
            """, fuel)

            insert_many(cursor, """
                INSERT INTO port_observations (
                    observation_id, terminal_name, port_name, observed_at,
                    estimated_queue_hours, vessel_delay_hours,
                    congestion_level, source_name, confidence, is_synthetic
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (observation_id) DO NOTHING
            """, ports)

            # 4. RAG source-document metadata
            insert_many(cursor, """
                INSERT INTO knowledge_documents (
                    document_id, title, document_type, version,
                    effective_from, effective_to, source_uri, content_text,
                    metadata, content_sha256, active
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (document_id) DO NOTHING
            """, documents)

            # 5. Agent execution history
            insert_many(cursor, """
                INSERT INTO agent_runs (
                    run_id, trip_id, coordinator_agent, started_at,
                    completed_at, status, input_event_id, model_name,
                    prompt_version, error_summary
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (run_id) DO NOTHING
            """, runs)

            insert_many(cursor, """
                INSERT INTO agent_recommendations (
                    recommendation_id, run_id, trip_id, agent_name,
                    action_type, priority, title, rationale, evidence_refs,
                    estimated_saving_zar, confidence, status,
                    requires_human_approval, reviewed_at, reviewed_by
                ) VALUES (
                    %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                    %s,%s,%s,%s,%s
                )
                ON CONFLICT (recommendation_id) DO NOTHING
            """, recommendations)

            # 6. Events waiting for publication to Redis Streams
            insert_many(cursor, """
                INSERT INTO event_outbox (
                    event_id, aggregate_type, aggregate_id, event_type,
                    occurred_at, payload, published_at, attempts, last_error
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (event_id) DO NOTHING
            """, events)

            # OVERRIDING SYSTEM VALUE bypasses identity sequence generation.
            # Advance the sequence to avoid collisions with future inserts.
            cursor.execute("""
                SELECT setval(
                    pg_get_serial_sequence(
                        'telemetry_events', 'telemetry_id'
                    ),
                    GREATEST(
                        COALESCE(
                            (SELECT MAX(telemetry_id) FROM telemetry_events),
                            1
                        ),
                        1
                    ),
                    TRUE
                )
            """)

            # Report counts from the database, not the generated lists.
            tables = [
                "vehicles", "drivers", "trips", "telemetry_events",
                "security_incidents", "fuel_events", "port_observations",
                "knowledge_documents", "agent_runs",
                "agent_recommendations", "event_outbox",
            ]

            print("\nSynthetic seed completed successfully.")
            print(f"{'Table':<28} {'Total records':>14}")
            print("-" * 44)

            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"{table:<28} {count:>14}")

        # The transaction commits automatically if no exception occurs.


if __name__ == "__main__":
    try:
        seed()
    except (psycopg.Error, RuntimeError) as exc:
        raise SystemExit(f"Seeding failed: {exc}") from exc
