from __future__ import annotations

import os
from datetime import datetime

import clickhouse_connect
import psycopg2
from airflow import DAG
from airflow.operators.python import PythonOperator


def get_pg_connection():
    return psycopg2.connect(
        host=os.getenv("CINEMA_DB_HOST", "db"),
        port=os.getenv("CINEMA_DB_PORT", "5432"),
        dbname=os.getenv("CINEMA_DB_NAME", "cinema_db"),
        user=os.getenv("CINEMA_DB_USER", "admin"),
        password=os.getenv("CINEMA_DB_PASSWORD", "Mishka"),
    )


def get_clickhouse_client():
    return clickhouse_connect.get_client(
        host=os.getenv("CLICKHOUSE_HOST", "clickhouse"),
        port=int(os.getenv("CLICKHOUSE_PORT", "8123")),
        username=os.getenv("CLICKHOUSE_USER", "default"),
        password=os.getenv("CLICKHOUSE_PASSWORD", ""),
    )


def fetch_all(sql: str):
    with get_pg_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            return cur.fetchall()


def create_clickhouse_tables():
    client = get_clickhouse_client()

    client.command("CREATE DATABASE IF NOT EXISTS cinema_dw")

    client.command("""
    CREATE TABLE IF NOT EXISTS cinema_dw.dim_movies (
        movie_id Int32,
        title String,
        release_year Nullable(Int32),
        duration Nullable(Int32),
        age_rating String,
        language String,
        country String,
        director_name String,
        primary_genre_name String,
        all_genres String
    )
    ENGINE = MergeTree
    ORDER BY movie_id
    """)

    client.command("""
    CREATE TABLE IF NOT EXISTS cinema_dw.fact_movie_events (
        event_natural_id String,
        event_date Date,
        event_timestamp DateTime,
        user_id Int32,
        movie_id Int32,
        action_type String,
        price Nullable(Float64),
        rating Nullable(Int32),
        progress Nullable(Float64),
        device Nullable(String)
    )
    ENGINE = MergeTree
    ORDER BY (event_date, action_type, movie_id)
    """)

    client.command("""
    CREATE TABLE IF NOT EXISTS cinema_dw.mart_daily_activity (
        event_date Date,
        action_type String,
        primary_genre_name String,
        events_count UInt64,
        unique_users UInt64,
        movies_count UInt64,
        revenue Float64,
        avg_rating Float64
    )
    ENGINE = MergeTree
    ORDER BY (event_date, action_type, primary_genre_name)
    """)


def reload_clickhouse_from_postgres():
    client = get_clickhouse_client()

    client.command("TRUNCATE TABLE cinema_dw.dim_movies")
    client.command("TRUNCATE TABLE cinema_dw.fact_movie_events")
    client.command("TRUNCATE TABLE cinema_dw.mart_daily_activity")

    movies_sql = """
    SELECT
        m.movie_id,
        m.title,
        m.release_year,
        m.duration,
        COALESCE(m.age_rating, '') AS age_rating,
        COALESCE(m.language, '') AS language,
        COALESCE(m.country, '') AS country,
        COALESCE(d.name, '') AS director_name,
        COALESCE(MIN(g.name), '') AS primary_genre_name,
        COALESCE(STRING_AGG(g.name, ', ' ORDER BY g.name), '') AS all_genres
    FROM cinema.movie m
    LEFT JOIN cinema.director d
        ON d.director_id = m.director_id
    LEFT JOIN cinema.movie_genre mg
        ON mg.movie_id = m.movie_id
    LEFT JOIN cinema.genre g
        ON g.genre_id = mg.genre_id
    GROUP BY
        m.movie_id,
        m.title,
        m.release_year,
        m.duration,
        m.age_rating,
        m.language,
        m.country,
        d.name
    """

    facts_sql = """
    SELECT
        'viewing_' || v.viewing_id AS event_natural_id,
        v.viewing_date::date AS event_date,
        v.viewing_date AS event_timestamp,
        v.user_id,
        v.movie_id,
        'VIEWING' AS action_type,
        NULL::float AS price,
        NULL::int AS rating,
        v.progress::float AS progress,
        v.device
    FROM cinema.viewing v
    WHERE v.viewing_date IS NOT NULL

    UNION ALL

    SELECT
        'rental_' || r.rental_id AS event_natural_id,
        r.rental_date::date AS event_date,
        r.rental_date AS event_timestamp,
        r.user_id,
        r.movie_id,
        'RENTAL' AS action_type,
        r.price::float AS price,
        NULL::int AS rating,
        NULL::float AS progress,
        NULL::text AS device
    FROM cinema.rental r
    WHERE r.rental_date IS NOT NULL

    UNION ALL

    SELECT
        'purchase_' || p.purchase_id AS event_natural_id,
        p.purchase_date::date AS event_date,
        p.purchase_date AS event_timestamp,
        p.user_id,
        p.movie_id,
        'PURCHASE' AS action_type,
        p.price::float AS price,
        NULL::int AS rating,
        NULL::float AS progress,
        NULL::text AS device
    FROM cinema.purchase p
    WHERE p.purchase_date IS NOT NULL

    UNION ALL

    SELECT
        'review_' || rv.review_id AS event_natural_id,
        rv.review_date::date AS event_date,
        rv.review_date AS event_timestamp,
        rv.user_id,
        rv.movie_id,
        'REVIEW' AS action_type,
        NULL::float AS price,
        rv.rating,
        NULL::float AS progress,
        NULL::text AS device
    FROM cinema.review rv
    WHERE rv.review_date IS NOT NULL
    """

    movies = fetch_all(movies_sql)
    facts = fetch_all(facts_sql)

    if movies:
        client.insert(
            "cinema_dw.dim_movies",
            movies,
            column_names=[
                "movie_id",
                "title",
                "release_year",
                "duration",
                "age_rating",
                "language",
                "country",
                "director_name",
                "primary_genre_name",
                "all_genres",
            ],
        )

    if facts:
        client.insert(
            "cinema_dw.fact_movie_events",
            facts,
            column_names=[
                "event_natural_id",
                "event_date",
                "event_timestamp",
                "user_id",
                "movie_id",
                "action_type",
                "price",
                "rating",
                "progress",
                "device",
            ],
        )


def build_daily_activity_mart():
    client = get_clickhouse_client()

    client.command("TRUNCATE TABLE cinema_dw.mart_daily_activity")

    client.command("""
    INSERT INTO cinema_dw.mart_daily_activity
    SELECT
        f.event_date,
        f.action_type,
        ifNull(m.primary_genre_name, 'Unknown') AS primary_genre_name,
        count() AS events_count,
        uniqExact(f.user_id) AS unique_users,
        uniqExact(f.movie_id) AS movies_count,
        sumIf(ifNull(f.price, 0), f.action_type IN ('RENTAL', 'PURCHASE')) AS revenue,
        ifNull(avgIf(toFloat64(f.rating), f.action_type = 'REVIEW' AND isNotNull(f.rating)), 0) AS avg_rating
    FROM cinema_dw.fact_movie_events f
    LEFT JOIN cinema_dw.dim_movies m
        ON m.movie_id = f.movie_id
    GROUP BY
        f.event_date,
        f.action_type,
        primary_genre_name
    """)


def quality_checks_clickhouse():
    client = get_clickhouse_client()

    pg_events_count = fetch_all("""
        SELECT
            (SELECT COUNT(*) FROM cinema.viewing)
            + (SELECT COUNT(*) FROM cinema.rental)
            + (SELECT COUNT(*) FROM cinema.purchase)
            + (SELECT COUNT(*) FROM cinema.review)
    """)[0][0]

    ch_events_count = client.query(
        "SELECT count() FROM cinema_dw.fact_movie_events"
    ).result_rows[0][0]

    mart_count = client.query(
        "SELECT count() FROM cinema_dw.mart_daily_activity"
    ).result_rows[0][0]

    if pg_events_count != ch_events_count:
        raise ValueError(
            f"Events count mismatch: PostgreSQL={pg_events_count}, ClickHouse={ch_events_count}"
        )

    if mart_count == 0:
        raise ValueError("mart_daily_activity is empty")


with DAG(
    dag_id="dag2_postgres_to_clickhouse",
    description="Move cinema PostgreSQL data to ClickHouse and build analytics mart",
    start_date=datetime(2026, 1, 1),
    schedule_interval=None,
    catchup=False,
    tags=["cinema", "analytics", "clickhouse"],
) as dag:

    create_clickhouse_tables_task = PythonOperator(
        task_id="create_clickhouse_tables",
        python_callable=create_clickhouse_tables,
    )

    reload_clickhouse_task = PythonOperator(
        task_id="reload_clickhouse_from_postgres",
        python_callable=reload_clickhouse_from_postgres,
    )

    build_mart_task = PythonOperator(
        task_id="build_daily_activity_mart",
        python_callable=build_daily_activity_mart,
    )

    quality_checks_task = PythonOperator(
        task_id="quality_checks_clickhouse",
        python_callable=quality_checks_clickhouse,
    )

    create_clickhouse_tables_task >> reload_clickhouse_task >> build_mart_task >> quality_checks_task
