-- users — 300 000 строк
INSERT INTO cinema.users (
    name, email, password_hash, role,
    date_created, last_login, preferences
)
SELECT
    'User_' || g AS name,
    'user' || g || '@cinema.test' AS email,
    md5(g::text) AS password_hash,
    ('{user,premium,admin}'::text[])[1 + (g % 3)] AS role,  -- низкая селективность (3 значения)
    CURRENT_DATE - (random() * 1095)::int,  -- равномерное: до 3 лет назад
    CASE WHEN random() > 0.2 THEN
    CURRENT_TIMESTAMP - (random() * 730)::int * '1 day'::interval END, -- 20% NULL
    jsonb_build_object(
        'theme', CASE WHEN g % 2 = 0 THEN 'dark' ELSE 'light' END,
        'lang', CASE WHEN g % 3 = 0 THEN 'en' WHEN g % 3 = 1 THEN 'ru' ELSE 'es' END,
        'notifications', (g % 4 != 0)  -- JSONB с разными типами
    ) AS preferences  -- JSONB
FROM generate_series(1, 300000) AS g;

-- actor — 250 000 строк
INSERT INTO cinema.actor (name, birth_date, country, biography)
SELECT
    'Actor_' || g,
    CURRENT_DATE - (random() * 29200)::int,  -- равномерное распределение дат
    ('{USA,UK,France,Germany,Russia}'::text[])[1 + (random()*4)::int],  -- низкая селективность (5 значений)
    CASE WHEN random() > 0.15 THEN 'Biography of actor ' || g END  -- 15% NULL
FROM generate_series(1, 250000) AS g;

-- movie — 250 000 строк
INSERT INTO cinema.movie (
    title, description, release_year, duration,
    age_rating, language, country, poster_url,
    price_range, description_ts
)
SELECT
    'Movie_' || g AS title,  -- высокая селективность
    'Plot of movie ' || g || '. Adventure, drama, and more.' AS description,
    1950 + (random() * 75)::int AS release_year,  -- диапазонные значения (годы)
    60 + (random() * 180)::int AS duration,       -- диапазонные значения (минуты)
    ('{G,PG,PG-13,R,NC-17}'::text[])[1 + (random()*4)::int] AS age_rating,  -- низкая селективность (5 значений)
    'English' AS language,
    'USA' AS country,
    CASE WHEN random() > 0.1 THEN 'https://cinema/poster' || g || '.jpg' END AS poster_url,  -- 10% NULL
    numrange(
        (5.99 + random()*10)::numeric,
        (15.99 + random()*20)::numeric
    ) AS price_range,  -- диапазонный тип (NUMRANGE)
    to_tsvector('english', 'Plot of movie ' || g || '. Adventure, drama, and more.') AS description_ts  -- полнотекст
FROM generate_series(1, 250000) AS g;

-- review — 250 000 строк
INSERT INTO cinema.review (user_id, movie_id, rating, comment, review_date, is_spoiler)
SELECT
    -- Сильно неравномерное распределение: 70% отзывов от 10% пользователей
    CASE
        WHEN random() < 0.7 THEN 1 + (random()*30000)::int   -- активные (первые 30k)
        ELSE 1 + (random()*300000)::int                     -- остальные
END AS user_id,
    1 + (random()*250000)::int AS movie_id,
    (g % 10 + 1) AS rating,  -- диапазон 1–10
    CASE WHEN random() > 0.2 THEN 'Great film!' END AS comment,  -- 20% NULL
    CURRENT_DATE - (random() * 730)::int AS review_date,
    (random() > 0.9) AS is_spoiler
FROM generate_series(1, 250000) AS g;