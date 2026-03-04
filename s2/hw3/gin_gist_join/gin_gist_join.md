## Создание GIN индексов

```sql
CREATE INDEX idx_users_preferences_gin
    ON cinema.users USING gin (preferences);

CREATE INDEX idx_movie_description_ts_gin
    ON cinema.movie USING gin (description_ts);

CREATE INDEX idx_users_tags_gin
    ON cinema.users USING gin (tags);

-- Запрос 1: JSONB containment (@>)
EXPLAIN (ANALYZE, BUFFERS)
SELECT user_id, name, email, preferences
FROM cinema.users
WHERE preferences @> '{"theme": "dark"}';
```
![Screenshot at 19.31.57.png](screenshots/Screenshot%20at%2019.31.57.png)

```sql
-- Запрос 2: JSONB key exists (?)
EXPLAIN (ANALYZE, BUFFERS)
SELECT user_id, name, preferences
FROM cinema.users
WHERE preferences ? 'lang' 
AND user_id > 250000; 
```   
![Screenshot at 19.46.16.png](screenshots/Screenshot%20at%2019.46.16.png)

```sql
-- Запрос 3: Full-text search (@@)
EXPLAIN (ANALYZE, BUFFERS)
SELECT movie_id, title, description
FROM cinema.movie
WHERE description_ts @@ to_tsquery('english', 'epic');
```
![Screenshot at 19.49.19.png](screenshots/Screenshot%20at%2019.49.19.png)
```sql
-- Запрос 4: JSONB multiple keys (@>)
EXPLAIN (ANALYZE, BUFFERS)
SELECT user_id, name, preferences
FROM cinema.users
WHERE preferences @> '{"theme": "dark", "lang": "en"}';
```
![Screenshot at 19.41.43.png](screenshots/Screenshot%20at%2019.41.43.png)
```sql
-- Запрос 5: Array containment (@>)
EXPLAIN (ANALYZE, BUFFERS)
SELECT user_id, name, tags
FROM cinema.users
WHERE tags @> ARRAY['action'];
```
![Screenshot at 13.58.43.png](screenshots/Screenshot%20at%2013.58.43.png)

## Создание GiST индексов
```sql
CREATE INDEX idx_movie_price_range_gist ON cinema.movie USING gist (price_range);
CREATE INDEX idx_movie_description_ts_gist ON cinema.movie USING gist (description_ts);

-- Запрос 1: Range overlap (&&)
EXPLAIN (ANALYZE, BUFFERS)
SELECT movie_id, title, price_range
FROM cinema.movie
WHERE price_range && numrange(5.99, 7);
```
![Screenshot at 20.02.59.png](screenshots/Screenshot%20at%2020.02.59.png)
```sql
-- Запрос 2: Range contains (@>)
EXPLAIN (ANALYZE, BUFFERS)
SELECT movie_id, title, price_range
FROM cinema.movie
WHERE price_range @> 35.99;
```
![Screenshot at 19.58.02.png](screenshots/Screenshot%20at%2019.58.02.png)
```sql
-- Запрос 3: Range is contained (<@)
EXPLAIN (ANALYZE, BUFFERS)
SELECT movie_id, title, price_range
FROM cinema.movie
WHERE numrange(33, 35) <@ price_range;
```
![Screenshot at 19.59.38.png](screenshots/Screenshot%20at%2019.59.38.png)
```sql
-- Запрос 4: Range strictly left of (<<)
EXPLAIN (ANALYZE, BUFFERS)
SELECT movie_id, title, price_range
FROM cinema.movie
WHERE price_range << numrange(8, 9);
```
![Screenshot at 07.25.30.png](screenshots/Screenshot%20at%2007.25.30.png)
```sql
-- Запрос 5: Full-text search с GiST (@@)
EXPLAIN (ANALYZE, BUFFERS)
SELECT movie_id, title, description
FROM cinema.movie
WHERE description_ts @@ to_tsquery('english', 'adventure | drama');
```
![Screenshot at 20.04.42.png](screenshots/Screenshot%20at%2020.04.42.png)

## JOIN
```sql
-- Запрос 1
EXPLAIN (ANALYZE, BUFFERS)
SELECT
u.user_id,
u.name,
u.email,
r.rental_id,
r.rental_date,
r.price
FROM cinema.users u
LEFT JOIN cinema.rental r ON u.user_id = r.user_id
WHERE u.user_id BETWEEN 1 AND 1000
LIMIT 100;
```
**РЕЗУЛЬТАТ:** Nested Loop, так как количество строк небольшое 
(благодаря фильтрации и LIMIT)

![Screenshot  at 20.27.01.png](screenshots/Screenshot%20%20at%2020.27.01.png)
```sql
-- Запрос 2
EXPLAIN (ANALYZE, BUFFERS)
SELECT
r.review_id,
r.user_id,
u.name AS user_name,
u.email,
r.rating,
r.comment
FROM cinema.review r
INNER JOIN cinema.users u ON r.user_id = u.user_id
WHERE r.rating >= 3;
```
**РЕЗУЛЬТАТ:** Hash Join, так как соединяем две большие таблицы без сортировки

![Screenshot at 20.40.42.png](screenshots/Screenshot%20at%2020.40.42.png)
```sql
-- Запрос 3
EXPLAIN (ANALYZE, BUFFERS)
SELECT
m.movie_id,
m.title,
g.genre_id,
g.name AS genre_name
FROM cinema.movie        AS m
JOIN cinema.movie_genre  AS mg
ON mg.movie_id = m.movie_id
JOIN cinema.genre        AS g
ON g.genre_id = mg.genre_id
WHERE m.release_year BETWEEN 1990 AND 2020
ORDER BY m.movie_id, g.genre_id;
```
**РЕЗУЛЬТАТ:** Nested Loop, несмотря на то, 
что данные уже отсортированны по ключу и оператор "=", 
планировщик считает его эффективнее Merge Join

![Screenshot at 07.03.24.png](screenshots/Screenshot%20at%2007.03.24.png)
```sql
-- Запрос 4
EXPLAIN (ANALYZE, BUFFERS)
SELECT
r.review_id,
r.user_id,
r.rating,
r.review_date,
m.movie_id,
m.title,
m.release_year
FROM cinema.review AS r
JOIN cinema.movie  AS m
ON r.movie_id = m.movie_id
WHERE
r.review_date > CURRENT_DATE - INTERVAL '365 days'
AND m.release_year >= 2000;
```
**РЕЗУЛЬТАТ:** Hash Join, так как соединяем две большие таблицы без сортировки

![Screenshot at 06.45.21.png](screenshots/Screenshot%20at%2006.45.21.png)
```sql
-- Запрос 5
EXPLAIN (ANALYZE, BUFFERS)
SELECT
p.purchase_id,
p.user_id,
p.price,
m.movie_id,
m.title,
m.price_range
FROM cinema.purchase AS p
JOIN cinema.movie    AS m
ON p.price <@ m.price_range   
WHERE p.price BETWEEN 10 AND 12;
```
**РЕЗУЛЬТАТ:** Nested Loop, так как это НЕ оператор равенства, 
следовательно Hash/Merge Join не могут быть построены

![Screenshot at 06.48.00.png](screenshots/Screenshot%20at%2006.48.00.png)