from __future__ import annotations

import csv
import json
import os
from datetime import datetime

import psycopg2
from airflow import DAG
from airflow.operators.python import PythonOperator


DATA_DIR = "/opt/airflow/data/external"
MOVIES_CSV_PATH = f"{DATA_DIR}/movies_external.csv"
EVENTS_JSON_PATH = f"{DATA_DIR}/user_events_external.json"


def get_pg_connection():
    return psycopg2.connect(
        host=os.getenv("CINEMA_DB_HOST", "db"),
        port=os.getenv("CINEMA_DB_PORT", "5432"),
        dbname=os.getenv("CINEMA_DB_NAME", "cinema_db"),
        user=os.getenv("CINEMA_DB_USER", "admin"),
        password=os.getenv("CINEMA_DB_PASSWORD", "Mishka"),
    )


def create_metadata_tables():
    sql = """
    CREATE SCHEMA IF NOT EXISTS etl;

    CREATE TABLE IF NOT EXISTS etl.external_movie_map (
        source_name TEXT NOT NULL,
        external_movie_id TEXT NOT NULL,
        movie_id INTEGER NOT NULL,
        created_at TIMESTAMP NOT NULL DEFAULT now(),
        PRIMARY KEY (source_name, external_movie_id)
    );

    CREATE TABLE IF NOT EXISTS etl.external_event_map (
        source_name TEXT NOT NULL,
        external_event_id TEXT NOT NULL,
        event_type TEXT NOT NULL,
        target_table TEXT NOT NULL,
        target_id INTEGER NOT NULL,
        created_at TIMESTAMP NOT NULL DEFAULT now(),
        PRIMARY KEY (source_name, external_event_id)
    );
    """
    with get_pg_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)


def get_or_create_director(cur, director_name: str) -> int:
    cur.execute(
        """
        SELECT director_id
        FROM cinema.director
        WHERE name = %s
        LIMIT 1
        """,
        (director_name,),
    )
    row = cur.fetchone()
    if row:
        return row[0]

    cur.execute(
        """
        INSERT INTO cinema.director (
            name,
            birth_date,
            country,
            biography
        )
        VALUES (
            %s,
            DATE '1970-01-01',
            'Unknown',
            %s
        )
        RETURNING director_id
        """,
        (director_name, f"Loaded from external CSV source: {director_name}"),
    )
    return cur.fetchone()[0]


def get_or_create_genre(cur, genre_name: str) -> int:
    cur.execute(
        """
        SELECT genre_id
        FROM cinema.genre
        WHERE name = %s
        LIMIT 1
        """,
        (genre_name,),
    )
    row = cur.fetchone()
    if row:
        return row[0]

    cur.execute(
        """
        INSERT INTO cinema.genre (
            name,
            description
        )
        VALUES (
            %s,
            %s
        )
        RETURNING genre_id
        """,
        (genre_name, f"Loaded from external CSV source: {genre_name}"),
    )
    return cur.fetchone()[0]


def load_movies_from_csv():
    required_columns = {
        "external_movie_id",
        "title",
        "description",
        "release_year",
        "duration",
        "age_rating",
        "language",
        "country",
        "director_name",
        "genre_name",
        "price_min",
        "price_max",
        "poster_url",
    }

    with open(MOVIES_CSV_PATH, newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        missing_columns = required_columns - set(reader.fieldnames or [])
        if missing_columns:
            raise ValueError(f"CSV missing columns: {missing_columns}")
        rows = list(reader)

    if not rows:
        raise ValueError("CSV file is empty")

    with get_pg_connection() as conn:
        with conn.cursor() as cur:
            for row in rows:
                external_movie_id = row["external_movie_id"].strip()
                title = row["title"].strip()
                description = row["description"].strip()
                release_year = int(row["release_year"])
                duration = int(row["duration"])
                age_rating = row["age_rating"].strip()
                language = row["language"].strip()
                country = row["country"].strip()
                director_name = row["director_name"].strip()
                genre_name = row["genre_name"].strip()
                price_min = float(row["price_min"])
                price_max = float(row["price_max"])
                poster_url = row["poster_url"].strip()

                if not external_movie_id:
                    raise ValueError("external_movie_id is required")
                if not title:
                    raise ValueError("title is required")
                if release_year < 1888 or release_year > 2100:
                    raise ValueError(f"Invalid release_year: {release_year}")
                if duration <= 0:
                    raise ValueError(f"Invalid duration: {duration}")
                if price_min < 0 or price_max < price_min:
                    raise ValueError(f"Invalid price range: {price_min}, {price_max}")

                cur.execute(
                    """
                    SELECT movie_id
                    FROM etl.external_movie_map
                    WHERE source_name = 'movies_csv'
                      AND external_movie_id = %s
                    """,
                    (external_movie_id,),
                )
                if cur.fetchone():
                    continue

                director_id = get_or_create_director(cur, director_name)
                genre_id = get_or_create_genre(cur, genre_name)

                cur.execute(
                    """
                    INSERT INTO cinema.movie (
                        title,
                        description,
                        release_year,
                        duration,
                        age_rating,
                        language,
                        country,
                        director_id,
                        price_range,
                        poster_url
                    )
                    VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s,
                        numrange(%s, %s, '[]'),
                        %s
                    )
                    RETURNING movie_id
                    """,
                    (
                        title,
                        description,
                        release_year,
                        duration,
                        age_rating,
                        language,
                        country,
                        director_id,
                        price_min,
                        price_max,
                        poster_url,
                    ),
                )
                movie_id = cur.fetchone()[0]

                cur.execute(
                    """
                    INSERT INTO cinema.movie_genre (
                        movie_id,
                        genre_id
                    )
                    VALUES (%s, %s)
                    ON CONFLICT DO NOTHING
                    """,
                    (movie_id, genre_id),
                )

                cur.execute(
                    """
                    INSERT INTO etl.external_movie_map (
                        source_name,
                        external_movie_id,
                        movie_id
                    )
                    VALUES ('movies_csv', %s, %s)
                    """,
                    (external_movie_id, movie_id),
                )


def get_or_create_user(cur, email: str, name: str) -> int:
    cur.execute(
        """
        SELECT user_id
        FROM cinema.users
        WHERE email = %s
        LIMIT 1
        """,
        (email,),
    )
    row = cur.fetchone()
    if row:
        return row[0]

    cur.execute(
        """
        INSERT INTO cinema.users (
            name,
            email,
            password_hash,
            role,
            date_created,
            last_login,
            preferences,
            tags
        )
        VALUES (
            %s,
            %s,
            %s,
            'USER',
            now(),
            now(),
            '{}'::jsonb,
            ARRAY['external']::text[]
        )
        RETURNING user_id
        """,
        (name, email, f"external_hash_{email}"),
    )
    return cur.fetchone()[0]


def get_movie_id_by_external_id(cur, external_movie_id: str) -> int:
    cur.execute(
        """
        SELECT movie_id
        FROM etl.external_movie_map
        WHERE source_name = 'movies_csv'
          AND external_movie_id = %s
        """,
        (external_movie_id,),
    )
    row = cur.fetchone()
    if not row:
        raise ValueError(f"Movie not found for external_movie_id={external_movie_id}")
    return row[0]


def event_already_loaded(cur, external_event_id: str) -> bool:
    cur.execute(
        """
        SELECT 1
        FROM etl.external_event_map
        WHERE source_name = 'events_json'
          AND external_event_id = %s
        """,
        (external_event_id,),
    )
    return cur.fetchone() is not None


def save_event_mapping(cur, external_event_id: str, event_type: str, target_table: str, target_id: int):
    cur.execute(
        """
        INSERT INTO etl.external_event_map (
            source_name,
            external_event_id,
            event_type,
            target_table,
            target_id
        )
        VALUES ('events_json', %s, %s, %s, %s)
        ON CONFLICT DO NOTHING
        """,
        (external_event_id, event_type, target_table, target_id),
    )


def load_events_from_json():
    with open(EVENTS_JSON_PATH, encoding="utf-8") as file:
        events = json.load(file)

    if not isinstance(events, list):
        raise ValueError("JSON must contain array of events")

    allowed_event_types = {"VIEWING", "RENTAL", "PURCHASE", "REVIEW"}

    with get_pg_connection() as conn:
        with conn.cursor() as cur:
            for event in events:
                external_event_id = event.get("external_event_id")
                event_type = event.get("event_type")
                external_movie_id = event.get("external_movie_id")
                user_email = event.get("user_email")
                user_name = event.get("user_name", "External User")
                event_timestamp = event.get("event_timestamp")

                if not external_event_id:
                    raise ValueError("external_event_id is required")
                if event_type not in allowed_event_types:
                    raise ValueError(f"Invalid event_type: {event_type}")
                if not external_movie_id:
                    raise ValueError("external_movie_id is required")
                if not user_email:
                    raise ValueError("user_email is required")
                if not event_timestamp:
                    raise ValueError("event_timestamp is required")

                datetime.strptime(event_timestamp, "%Y-%m-%d %H:%M:%S")

                if event_already_loaded(cur, external_event_id):
                    continue

                movie_id = get_movie_id_by_external_id(cur, external_movie_id)
                user_id = get_or_create_user(cur, user_email, user_name)

                if event_type == "VIEWING":
                    progress = int(event.get("progress", 0))
                    watched_until = int(event.get("watched_until", 0))
                    device = event.get("device", "Unknown")
                    if progress < 0 or progress > 100:
                        raise ValueError(f"Invalid progress: {progress}")

                    cur.execute(
                        """
                        INSERT INTO cinema.viewing (
                            user_id,
                            movie_id,
                            viewing_date,
                            progress,
                            device,
                            watched_until
                        )
                        VALUES (%s, %s, %s, %s, %s, %s)
                        RETURNING viewing_id
                        """,
                        (user_id, movie_id, event_timestamp, progress, device, watched_until),
                    )
                    target_id = cur.fetchone()[0]
                    save_event_mapping(cur, external_event_id, event_type, "viewing", target_id)

                elif event_type == "RENTAL":
                    price = float(event.get("price", 0))
                    status = event.get("status", "ACTIVE")
                    is_returned = bool(event.get("is_returned", False))
                    if price < 0:
                        raise ValueError(f"Invalid rental price: {price}")

                    cur.execute(
                        """
                        INSERT INTO cinema.rental (
                            user_id,
                            movie_id,
                            rental_date,
                            return_date,
                            price,
                            status,
                            is_returned
                        )
                        VALUES (
                            %s,
                            %s,
                            %s,
                            CASE WHEN %s THEN %s::timestamp ELSE NULL END,
                            %s,
                            %s,
                            %s
                        )
                        RETURNING rental_id
                        """,
                        (
                            user_id,
                            movie_id,
                            event_timestamp,
                            is_returned,
                            event_timestamp,
                            price,
                            status,
                            is_returned,
                        ),
                    )
                    target_id = cur.fetchone()[0]
                    save_event_mapping(cur, external_event_id, event_type, "rental", target_id)

                elif event_type == "PURCHASE":
                    price = float(event.get("price", 0))
                    payment_method = event.get("payment_method", "CARD")
                    if price < 0:
                        raise ValueError(f"Invalid purchase price: {price}")

                    cur.execute(
                        """
                        INSERT INTO cinema.purchase (
                            user_id,
                            movie_id,
                            purchase_date,
                            price,
                            payment_method
                        )
                        VALUES (%s, %s, %s, %s, %s)
                        RETURNING purchase_id
                        """,
                        (user_id, movie_id, event_timestamp, price, payment_method),
                    )
                    target_id = cur.fetchone()[0]
                    save_event_mapping(cur, external_event_id, event_type, "purchase", target_id)

                elif event_type == "REVIEW":
                    rating = int(event.get("rating", 0))
                    comment = event.get("comment", "")
                    is_spoiler = bool(event.get("is_spoiler", False))
                    if rating < 1 or rating > 5:
                        raise ValueError(f"Invalid rating: {rating}")

                    cur.execute(
                        """
                        INSERT INTO cinema.review (
                            user_id,
                            movie_id,
                            rating,
                            comment,
                            review_date,
                            is_spoiler
                        )
                        VALUES (%s, %s, %s, %s, %s, %s)
                        RETURNING review_id
                        """,
                        (user_id, movie_id, rating, comment, event_timestamp, is_spoiler),
                    )
                    target_id = cur.fetchone()[0]
                    save_event_mapping(cur, external_event_id, event_type, "review", target_id)


def quality_checks_postgres():
    with get_pg_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM etl.external_movie_map WHERE source_name = 'movies_csv'")
            movies_count = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM etl.external_event_map WHERE source_name = 'events_json'")
            events_count = cur.fetchone()[0]

            if movies_count == 0:
                raise ValueError("No movies loaded from CSV")
            if events_count == 0:
                raise ValueError("No events loaded from JSON")


with DAG(
    dag_id="dag1_etl_csv_json_to_postgres",
    description="Load external CSV and JSON data into cinema PostgreSQL database",
    start_date=datetime(2026, 1, 1),
    schedule_interval=None,
    catchup=False,
    tags=["cinema", "etl", "postgres"],
) as dag:

    create_metadata_tables_task = PythonOperator(
        task_id="create_metadata_tables",
        python_callable=create_metadata_tables,
    )

    load_movies_from_csv_task = PythonOperator(
        task_id="load_movies_from_csv",
        python_callable=load_movies_from_csv,
    )

    load_events_from_json_task = PythonOperator(
        task_id="load_events_from_json",
        python_callable=load_events_from_json,
    )

    quality_checks_task = PythonOperator(
        task_id="quality_checks_postgres",
        python_callable=quality_checks_postgres,
    )

    create_metadata_tables_task >> load_movies_from_csv_task >> load_events_from_json_task >> quality_checks_task
