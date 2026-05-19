# OLAP

```bash
docker compose up -d
docker exec -it cinema-db psql -U admin -d cinema_db 
```

## 1. Аналитические вопросы
```text
1) Какая динамика активности пользователей по дням?
Сколько просмотров, аренд, покупок и отзывов происходит каждый день.
2) Какие фильмы и жанры самые популярные?
Какие фильмы чаще смотрят, арендуют, покупают и оценивают.
3) Сколько действий совершают пользователи?
Кто из пользователей наиболее активен.
```

## 2. Главный факт

fact_movie_events
```text
fact_movie_events

В OLTP действия лежат в разных таблицах:

viewing   — просмотр фильма
rental    — аренда фильма
purchase  — покупка фильма
review    — отзыв / оценка фильма

В OLAP объединяем их в одну таблицу фактов.
```

## 3. Зерно факта
```text
1 строка в fact_movie_events = одно действие пользователя с фильмом

Примеры строк:

Пользователь посмотрел фильм
Пользователь арендовал фильм
Пользователь купил фильм
Пользователь оставил отзыв

Зерно позволяет считать активность по дням, пользователям, фильмам, жанрам и типам действий.
```

## 4. Измерения
```text
Измерение — это таблица, которая отвечает на вопрос:
В каком разрезе мы хотим анализировать факт?

Создадим 4 измерения:

olap.dim_date   — дата события
olap.dim_user   — пользователь
olap.dim_movie  — фильм
olap.dim_genre  — жанр

Факт будет ссылаться на эти измерения.
```

## 5. Создание OLAP-схемы
```sql
CREATE SCHEMA IF NOT EXISTS olap;
```
![Screenshot 2026-05-16 at 15.45.53.png](screenshots/Screenshot%202026-05-16%20at%2015.45.53.png)
```text
Создаем отдельную схему olap, чтобы аналитические таблицы
не смешивались с OLTP-таблицами приложения.
```

```sql
-- Создание измерения дат dim_date
CREATE TABLE olap.dim_date (
                               date_id INTEGER PRIMARY KEY,
                               date_value DATE NOT NULL,
                               year INTEGER NOT NULL,
                               quarter INTEGER NOT NULL,
                               month INTEGER NOT NULL,
                               month_name TEXT NOT NULL,
                               day INTEGER NOT NULL,
                               day_of_week INTEGER NOT NULL,
                               day_name TEXT NOT NULL
);
```
![Screenshot 2026-05-16 at 15.46.07.png](screenshots/Screenshot%202026-05-16%20at%2015.46.07.png)
Вместо того чтобы каждый раз доставать год, месяц и день из timestamp, мы заранее храним эти значения.
date_id делаем в формате YYYYMMDD, например 20260516.
Так удобно соединять факт с датой.


```sql
-- Создание измерения пользователей dim_user
CREATE TABLE olap.dim_user (
                               user_id INTEGER PRIMARY KEY,
                               user_name VARCHAR(255) NOT NULL,
                               email TEXT NOT NULL,
                               role TEXT NOT NULL,
                               date_created TIMESTAMP,
                               last_login TIMESTAMP
);
```
![Screenshot 2026-05-16 at 15.46.19.png](screenshots/Screenshot%202026-05-16%20at%2015.46.19.png)

```sql
-- Создание измерения жанров dim_genre
CREATE TABLE olap.dim_genre (
                                genre_id INTEGER PRIMARY KEY,
                                genre_name TEXT NOT NULL,
                                description TEXT
);
```
![Screenshot 2026-05-16 at 15.46.29.png](screenshots/Screenshot%202026-05-16%20at%2015.46.29.png)
Это измерение позволит считать популярность по жанрам.
Например: сколько просмотров, аренд и покупок было у комедий, драм, боевиков и так далее.

```sql
-- Создание измерения фильмов dim_movie
CREATE TABLE olap.dim_movie (
                                movie_id INTEGER PRIMARY KEY,
                                title TEXT NOT NULL,
                                release_year INTEGER,
                                duration INTEGER,
                                age_rating TEXT,
                                language TEXT,
                                country TEXT,
                                director_id INTEGER,
                                director_name TEXT,
                                primary_genre_id INTEGER,
                                primary_genre_name TEXT,
                                all_genres TEXT,
                                FOREIGN KEY (primary_genre_id) REFERENCES olap.dim_genre(genre_id)
);
```
![Screenshot 2026-05-16 at 15.46.43.png](screenshots/Screenshot%202026-05-16%20at%2015.46.43.png)
В OLTP жанры вынесены отдельно через movie_genre, потому что у фильма может быть несколько жанров.
Для упрощенной OLAP-модели мы сохраняем:
1. primary_genre_id — основной жанр фильма;
2. primary_genre_name — название основного жанра;
3. all_genres — все жанры фильма одной строкой.

Это удобно для аналитических отчетов.


### Создание таблицы фактов fact_movie_events
```sql
CREATE TABLE olap.fact_movie_events (
                                        event_sk BIGSERIAL PRIMARY KEY,

                                        event_source TEXT NOT NULL,
                                        event_source_id INTEGER NOT NULL,
                                        event_natural_id TEXT NOT NULL UNIQUE,

                                        date_id INTEGER NOT NULL,
                                        user_id INTEGER NOT NULL,
                                        movie_id INTEGER NOT NULL,

                                        action_type TEXT NOT NULL,

                                        price NUMERIC,
                                        rating INTEGER,
                                        progress NUMERIC,
                                        watched_until INTEGER,
                                        device TEXT,
                                        status TEXT,
                                        is_returned BOOLEAN,
                                        is_spoiler BOOLEAN,

                                        event_timestamp TIMESTAMP NOT NULL,

                                        FOREIGN KEY (date_id) REFERENCES olap.dim_date(date_id),
                                        FOREIGN KEY (user_id) REFERENCES olap.dim_user(user_id),
                                        FOREIGN KEY (movie_id) REFERENCES olap.dim_movie(movie_id)
);
```
![Screenshot 2026-05-16 at 15.47.01.png](screenshots/Screenshot%202026-05-16%20at%2015.47.01.png)
## Заполнение OLAP-таблицы из OLTP-таблицы

```sql
-- Заполнение dim_user
INSERT INTO olap.dim_user (
    user_id,
    user_name,
    email,
    role,
    date_created,
    last_login
)
SELECT
    u.user_id,
    u.name,
    u.email,
    u.role,
    u.date_created,
    u.last_login
FROM cinema.users u;
```
![Screenshot 2026-05-16 at 15.47.51.png](screenshots/Screenshot%202026-05-16%20at%2015.47.51.png)

```sql
-- Заполнение dim_genre
INSERT INTO olap.dim_genre (
    genre_id,
    genre_name,
    description
)
SELECT
    g.genre_id,
    g.name,
    g.description
FROM cinema.genre g;
```
![Screenshot 2026-05-16 at 15.48.05.png](screenshots/Screenshot%202026-05-16%20at%2015.48.05.png)
```sql
-- Заполнение dim_movie
INSERT INTO olap.dim_movie (
    movie_id,
    title,
    release_year,
    duration,
    age_rating,
    language,
    country,
    director_id,
    director_name,
    primary_genre_id,
    primary_genre_name,
    all_genres
)
SELECT
    m.movie_id,
    m.title,
    m.release_year,
    m.duration,
    m.age_rating,
    m.language,
    m.country,
    m.director_id,
    d.name AS director_name,

    MIN(g.genre_id) AS primary_genre_id,
    MIN(g.name) AS primary_genre_name,
    STRING_AGG(g.name, ', ' ORDER BY g.name) AS all_genres

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
    m.director_id,
    d.name;
```
![Screenshot 2026-05-16 at 16.00.43.png](screenshots/Screenshot%202026-05-16%20at%2016.00.43.png)
```sql
-- Заполнение dim_date
WITH all_event_dates AS (
    SELECT purchase_date::date AS event_date
    FROM cinema.purchase
    WHERE purchase_date IS NOT NULL

    UNION ALL

    SELECT rental_date::date AS event_date
    FROM cinema.rental
    WHERE rental_date IS NOT NULL

    UNION ALL

    SELECT review_date::date AS event_date
    FROM cinema.review
    WHERE review_date IS NOT NULL

    UNION ALL

    SELECT viewing_date::date AS event_date
    FROM cinema.viewing
    WHERE viewing_date IS NOT NULL
),
     date_bounds AS (
         SELECT
             MIN(event_date) AS min_date,
             MAX(event_date) AS max_date
         FROM all_event_dates
     ),
     date_series AS (
         SELECT generate_series(
                        COALESCE((SELECT min_date FROM date_bounds), CURRENT_DATE),
                        COALESCE((SELECT max_date FROM date_bounds), CURRENT_DATE),
                        INTERVAL '1 day'
                )::date AS date_value
     )
INSERT INTO olap.dim_date (
    date_id,
    date_value,
    year,
    quarter,
    month,
    month_name,
    day,
    day_of_week,
    day_name
)
SELECT
    TO_CHAR(date_value, 'YYYYMMDD')::INTEGER AS date_id,
    date_value,
    EXTRACT(YEAR FROM date_value)::INTEGER AS year,
    EXTRACT(QUARTER FROM date_value)::INTEGER AS quarter,
    EXTRACT(MONTH FROM date_value)::INTEGER AS month,
    TO_CHAR(date_value, 'Month') AS month_name,
    EXTRACT(DAY FROM date_value)::INTEGER AS day,
    EXTRACT(ISODOW FROM date_value)::INTEGER AS day_of_week,
    TO_CHAR(date_value, 'Day') AS day_name
FROM date_series;
```
![Screenshot 2026-05-16 at 16.01.31.png](screenshots/Screenshot%202026-05-16%20at%2016.01.31.png)

```sql
-- Заполнение таблицы фактов fact_movie_events
INSERT INTO olap.fact_movie_events (
    event_source,
    event_source_id,
    event_natural_id,
    date_id,
    user_id,
    movie_id,
    action_type,
    price,
    rating,
    progress,
    watched_until,
    device,
    status,
    is_returned,
    is_spoiler,
    event_timestamp
)

SELECT
    'viewing' AS event_source,
    v.viewing_id AS event_source_id,
    'viewing_' || v.viewing_id AS event_natural_id,
    TO_CHAR(v.viewing_date::date, 'YYYYMMDD')::INTEGER AS date_id,
    v.user_id,
    v.movie_id,
    'VIEWING' AS action_type,
    NULL::NUMERIC AS price,
    NULL::INTEGER AS rating,
    v.progress,
    v.watched_until,
    v.device,
    NULL::TEXT AS status,
    NULL::BOOLEAN AS is_returned,
    NULL::BOOLEAN AS is_spoiler,
    v.viewing_date AS event_timestamp
FROM cinema.viewing v
WHERE v.viewing_date IS NOT NULL

UNION ALL

SELECT
    'rental' AS event_source,
    r.rental_id AS event_source_id,
    'rental_' || r.rental_id AS event_natural_id,
    TO_CHAR(r.rental_date::date, 'YYYYMMDD')::INTEGER AS date_id,
    r.user_id,
    r.movie_id,
    'RENTAL' AS action_type,
    r.price,
    NULL::INTEGER AS rating,
    NULL::NUMERIC AS progress,
    NULL::INTEGER AS watched_until,
    NULL::TEXT AS device,
    r.status,
    r.is_returned,
    NULL::BOOLEAN AS is_spoiler,
    r.rental_date AS event_timestamp
FROM cinema.rental r
WHERE r.rental_date IS NOT NULL

UNION ALL

SELECT
    'purchase' AS event_source,
    p.purchase_id AS event_source_id,
    'purchase_' || p.purchase_id AS event_natural_id,
    TO_CHAR(p.purchase_date::date, 'YYYYMMDD')::INTEGER AS date_id,
    p.user_id,
    p.movie_id,
    'PURCHASE' AS action_type,
    p.price,
    NULL::INTEGER AS rating,
    NULL::NUMERIC AS progress,
    NULL::INTEGER AS watched_until,
    NULL::TEXT AS device,
    NULL::TEXT AS status,
    NULL::BOOLEAN AS is_returned,
    NULL::BOOLEAN AS is_spoiler,
    p.purchase_date AS event_timestamp
FROM cinema.purchase p
WHERE p.purchase_date IS NOT NULL

UNION ALL

SELECT
    'review' AS event_source,
    rv.review_id AS event_source_id,
    'review_' || rv.review_id AS event_natural_id,
    TO_CHAR(rv.review_date::date, 'YYYYMMDD')::INTEGER AS date_id,
    rv.user_id,
    rv.movie_id,
    'REVIEW' AS action_type,
    NULL::NUMERIC AS price,
    rv.rating,
    NULL::NUMERIC AS progress,
    NULL::INTEGER AS watched_until,
    NULL::TEXT AS device,
    NULL::TEXT AS status,
    NULL::BOOLEAN AS is_returned,
    rv.is_spoiler,
    rv.review_date AS event_timestamp
FROM cinema.review rv
WHERE rv.review_date IS NOT NULL;
```
![Screenshot 2026-05-16 at 16.03.16.png](screenshots/Screenshot%202026-05-16%20at%2016.03.16.png)
```sql
-- Проверка количества строк в OLAP-таблицах
SELECT 'dim_date' AS table_name, COUNT(*) AS row_count FROM olap.dim_date
UNION ALL
SELECT 'dim_user', COUNT(*) FROM olap.dim_user
UNION ALL
SELECT 'dim_genre', COUNT(*) FROM olap.dim_genre
UNION ALL
SELECT 'dim_movie', COUNT(*) FROM olap.dim_movie
UNION ALL
SELECT 'fact_movie_events', COUNT(*) FROM olap.fact_movie_events;
```
![Screenshot 2026-05-16 at 16.03.37.png](screenshots/Screenshot%202026-05-16%20at%2016.03.37.png)

## Аналитические запросы

```sql
-- Динамика активности пользователей по дням
SELECT
    d.date_value,
    f.action_type,
    COUNT(*) AS events_count
FROM olap.fact_movie_events f
         JOIN olap.dim_date d
              ON d.date_id = f.date_id
GROUP BY
    d.date_value,
    f.action_type
ORDER BY
    d.date_value,
    f.action_type;
```
![Screenshot 2026-05-16 at 16.03.58.png](screenshots/Screenshot%202026-05-16%20at%2016.03.58.png)
Этот запрос показывает, сколько событий каждого типа было по дням.

Например:
сколько было просмотров,
сколько было аренд,
сколько было покупок,
сколько было отзывов.

Так можно увидеть динамику активности пользователей.

```sql
-- топ-10 самых популярных фильмов
SELECT
    m.movie_id,
    m.title,
    COUNT(*) AS total_events,
    COUNT(*) FILTER (WHERE f.action_type = 'VIEWING') AS views_count,
    COUNT(*) FILTER (WHERE f.action_type = 'RENTAL') AS rentals_count,
    COUNT(*) FILTER (WHERE f.action_type = 'PURCHASE') AS purchases_count,
    COUNT(*) FILTER (WHERE f.action_type = 'REVIEW') AS reviews_count,
    ROUND(AVG(f.rating) FILTER (WHERE f.action_type = 'REVIEW'), 2) AS avg_rating,
    SUM(f.price) FILTER (WHERE f.action_type IN ('RENTAL', 'PURCHASE')) AS revenue
FROM olap.fact_movie_events f
         JOIN olap.dim_movie m
              ON m.movie_id = f.movie_id
GROUP BY
    m.movie_id,
    m.title
ORDER BY
    total_events DESC
    LIMIT 10;
```
![Screenshot 2026-05-16 at 16.04.22.png](screenshots/Screenshot%202026-05-16%20at%2016.04.22.png)

Этот запрос показывает топ-10 самых популярных фильмов.

Популярность здесь считается по общему количеству действий:
просмотры + аренды + покупки + отзывы.

Дополнительно считаются:
количество просмотров,
количество аренд,
количество покупок,
количество отзывов,
средний рейтинг,
выручка от аренд и покупок.

```sql
-- Самые популярные жанры
SELECT
    g.genre_id,
    g.genre_name,
    COUNT(*) AS total_events,
    COUNT(*) FILTER (WHERE f.action_type = 'VIEWING') AS views_count,
    COUNT(*) FILTER (WHERE f.action_type = 'RENTAL') AS rentals_count,
    COUNT(*) FILTER (WHERE f.action_type = 'PURCHASE') AS purchases_count,
    COUNT(*) FILTER (WHERE f.action_type = 'REVIEW') AS reviews_count,
    SUM(f.price) FILTER (WHERE f.action_type IN ('RENTAL', 'PURCHASE')) AS revenue
FROM olap.fact_movie_events f
         JOIN olap.dim_movie m
              ON m.movie_id = f.movie_id
         LEFT JOIN olap.dim_genre g
                   ON g.genre_id = m.primary_genre_id
GROUP BY
    g.genre_id,
    g.genre_name
ORDER BY
    total_events DESC;
```
![Screenshot 2026-05-16 at 16.04.41.png](screenshots/Screenshot%202026-05-16%20at%2016.04.41.png) 
Этот запрос показывает, какие жанры дают больше всего активности.

Мы соединяем факт с фильмом, а фильм соединяем с жанром.
Так можно понять, какие жанры чаще смотрят, арендуют, покупают и оценивают.