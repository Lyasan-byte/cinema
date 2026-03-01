-- Запрос 1.1: Оператор >
EXPLAIN
SELECT movie_id, title, release_year
FROM cinema.movie
WHERE release_year > 2024;
-- БЕЗ ИНДЕКСОВ
![Screenshot 2026-02-26 at 08.26.19.png](screenshots/Screenshot%202026-02-26%20at%2008.26.19.png)
-- B-tree индекс
![Screenshot 2026-02-26 at 08.35.23.png](screenshots/Screenshot%202026-02-26%20at%2008.35.23.png)

-- 1.2
EXPLAIN (ANALYZE, BUFFERS)
SELECT movie_id, title, release_year
FROM cinema.movie
WHERE release_year > 2024;
-- БЕЗ ИНДЕКСОВ
![Screenshot 2026-02-26 at 08.27.13.png](screenshots/Screenshot%202026-02-26%20at%2008.27.13.png)
-- B-tree индекс
![Screenshot 2026-02-26 at 08.37.15.png](screenshots/Screenshot%202026-02-26%20at%2008.37.15.png)

-- Запрос 2.1: Оператор <
EXPLAIN
SELECT rental_id, user_id, price
FROM cinema.rental
WHERE price < 7.00;
-- БЕЗ ИНДЕКСОВ
![Screenshot 2026-02-26 at 08.28.12.png](screenshots/Screenshot%202026-02-26%20at%2008.28.12.png)
-- B-tree индекс
![Screenshot 2026-02-26 at 08.38.09.png](screenshots/Screenshot%202026-02-26%20at%2008.38.09.png)

-- 2.2
EXPLAIN (ANALYZE, BUFFERS)
SELECT rental_id, user_id, price
FROM cinema.rental
WHERE price < 7.00;
-- БЕЗ ИНДЕКСОВ
![Screenshot 2026-02-26 at 08.28.31.png](screenshots/Screenshot%202026-02-26%20at%2008.28.31.png)
-- B-tree индекс
![Screenshot 2026-02-26 at 08.38.46.png](screenshots/Screenshot%202026-02-26%20at%2008.38.46.png)

-- Запрос 3.1: Оператор =
EXPLAIN
SELECT user_id, name, email
FROM cinema.users
WHERE email = 'user12345@cinema.test';
-- БЕЗ ИНДЕКСОВ
![Screenshot 2026-02-26 at 08.29.11.png](screenshots/Screenshot%202026-02-26%20at%2008.29.11.png)
-- B-tree индекс
![Screenshot 2026-02-26 at 08.39.01.png](screenshots/Screenshot%202026-02-26%20at%2008.39.01.png)
-- Hash индекс
![Screenshot 2026-02-26 at 08.46.26.png](screenshots/Screenshot%202026-02-26%20at%2008.46.26.png)

-- 3.2
EXPLAIN (ANALYZE, BUFFERS)
SELECT user_id, name, email
FROM cinema.users
WHERE email = 'user12345@cinema.test';
-- БЕЗ ИНДЕКСОВ
![Screenshot 2026-02-26 at 08.29.38.png](screenshots/Screenshot%202026-02-26%20at%2008.29.38.png)
-- B-tree индекс
![Screenshot 2026-02-26 at 08.41.27.png](screenshots/Screenshot%202026-02-26%20at%2008.41.27.png)
-- Hash индекс
![Screenshot 2026-02-26 at 08.49.00.png](screenshots/Screenshot%202026-02-26%20at%2008.49.00.png)

-- Запрос 4: Оператор %like
EXPLAIN
SELECT actor_id, name
FROM cinema.actor
WHERE name LIKE '%_123';
-- БЕЗ ИНДЕКСОВ
![Screenshot 2026-02-26 at 08.30.16.png](screenshots/Screenshot%202026-02-26%20at%2008.30.16.png)
-- B-tree индекс
![Screenshot 2026-02-26 at 08.42.27.png](screenshots/Screenshot%202026-02-26%20at%2008.42.27.png)

-- 4.2
EXPLAIN (ANALYZE, BUFFERS)
SELECT actor_id, name
FROM cinema.actor
WHERE name LIKE '%_123';
-- БЕЗ ИНДЕКСОВ
![Screenshot 2026-02-26 at 08.30.43.png](screenshots/Screenshot%202026-02-26%20at%2008.30.43.png)
-- B-tree индекс
![Screenshot 2026-02-26 at 08.42.52.png](screenshots/Screenshot%202026-02-26%20at%2008.42.52.png)

-- Запрос 5: Оператор IN
EXPLAIN
SELECT review_id, user_id, movie_id, rating
FROM cinema.review
WHERE rating = 10;
-- БЕЗ ИНДЕКСОВ
![Screenshot 2026-02-26 at 08.31.25.png](screenshots/Screenshot%202026-02-26%20at%2008.31.25.png)
-- B-tree индекс
![Screenshot 2026-02-26 at 08.43.21.png](screenshots/Screenshot%202026-02-26%20at%2008.43.21.png)

-- 5.2
EXPLAIN (ANALYZE, BUFFERS)
SELECT review_id, user_id, movie_id, rating
FROM cinema.review
WHERE rating = 10;
-- БЕЗ ИНДЕКСОВ
![Screenshot 2026-02-26 at 08.31.53.png](screenshots/Screenshot%202026-02-26%20at%2008.31.53.png)
-- B-tree индекс
![Screenshot 2026-02-26 at 08.43.46.png](screenshots/Screenshot%202026-02-26%20at%2008.43.46.png)

**РЕЗУЛЬТАТ**

**1 запрос**
Без индекса: Parallel Seq Scan, Execution time: 40 ms, Cost: 10713
B tree индекс: Bitmap Heat Scan, Execution time: 3 ms, Cost: 3991

**2 запрос**
Без индекса: Parallel Seq Scan, Execution time: 0.8 ms
Postgres не использовал b-tree индекс

**3 запрос**
Без индекса: Parallel Seq Scan, Execution time: 24 ms, Cost: 9525
B tree индекс: Index Scan, Execution time: 3 ms, Cost: 8.44
Hash индекс: Index Scan, Execution time: 2 ms, Cost: 8.02

**4 запрос**
Без индекса: Parallel Seq Scan, Execution time: 16 ms
Postgres не использовал b-tree индекс

**5 запрос**
Без индекса: Seq Scan, Execution time: 22 ms, Cost: 5362
B tree индекс: Bitmap Heat Scan, Execution time: 13 ms, Cost: 2836