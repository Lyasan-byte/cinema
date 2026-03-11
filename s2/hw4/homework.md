## xmin, xmax, ctid, t_infomask
```sql
CREATE EXTENSION IF NOT EXISTS pageinspect;

-- Создаём тестового пользователя
INSERT INTO cinema.users (name, email, password_hash, role, date_created)
VALUES ('MVCC_Original', 'mvcc_test@cinema.local', md5('test123'), 'user', NOW())
RETURNING user_id, ctid;
```
![Screenshot at 13.47.03.png](screenshots/Screenshot%20at%2013.47.03.png)
```sql
-- Терминал 1 — начинаем транзакцию и смотрим исходное состояние
BEGIN;
-- 1. Смотрим xmin, xmax, ctid
SELECT
    ctid,
    xmin,
    xmax,
    name,
    email,
    'ДО UPDATE' AS этап
FROM cinema.users
WHERE user_id = 300005;
```
![Screenshot at 13.48.02.png](screenshots/Screenshot%20at%2013.48.02.png)
```sql
-- 2. Смотрим t_infomask 
SELECT
    lp AS кортеж,
    t_infomask,
    (t_infomask & 1024) != 0 AS xmin_committed,
(t_infomask & 4096) != 0 AS xmax_committed,
(t_infomask & 8192) != 0 AS row_updated
FROM heap_page_items(get_raw_page('cinema.users', 4))  -- блок
WHERE lp = 2; -- кортеж
```
![Screenshot  at 13.48.11.png](screenshots/Screenshot%20%20at%2013.48.11.png)
t_infomask 2307 - нет флага HEAP_UPDATED => оригинальная версия
```sql
--Терминал 1 — обновляем строку
UPDATE cinema.users
SET name = 'MVCC_Updated_v2', last_login = NOW()
WHERE user_id = 300005;
-- 1. Смотрим xmin, xmax, ctid
SELECT
    ctid,
    xmin,
    xmax,
    name,
    email,
    'ПОСЛЕ UPDATE (до COMMIT)' AS этап
FROM cinema.users
WHERE user_id = 300005;
```
![Screenshot at 13.53.07.png](screenshots/Screenshot%20at%2013.53.07.png)

```sql
-- 2. Смотрим t_infomask для НОВОГО ctid
SELECT
    lp AS кортеж,
    t_infomask,
    (t_infomask & 1024) != 0 AS xmin_committed,
    (t_infomask & 4096) != 0 AS xmax_committed,
    (t_infomask & 8192) != 0 AS row_updated
FROM heap_page_items(get_raw_page('cinema.users', 4))  
WHERE lp = 5; 
```
![Screenshot at 13.55.03.png](screenshots/Screenshot%20at%2013.55.03.png)
t_infomask 10243 - новая версия

```sql
-- Терминал 2
-- 1. Читаем строку (видим СТАРУЮ версию)
SELECT
    ctid,
    xmin,
    xmax,
    name,
    email,
    'Терминал 2 ДО COMMIT Т1' AS этап
FROM cinema.users
WHERE user_id = 300005;
```
![Screenshot at 13.56.05.png](screenshots/Screenshot%20at%2013.56.05.png)`

```sql
-- 2. Смотрим t_infomask
SELECT 
    lp AS кортеж,
    t_infomask,
    (t_infomask & 1024) != 0 AS xmin_committed,
    (t_infomask & 4096) != 0 AS xmax_committed,
    (t_infomask & 8192) != 0 AS row_updated
FROM heap_page_items(get_raw_page('cinema.users', 4))
WHERE lp = 2;
```
![Screenshot at 13.58.13.png](screenshots/Screenshot%20at%2013.58.13.png)
t_infomask 259 - старая версия
```sql
-- Терминал 2 — попытка обновления (заблокировано)
BEGIN;

UPDATE cinema.users 
SET email = 'conflict@blocked.local' 
WHERE user_id = 300005;
```
![Screenshot at 13.58.01.png](screenshots/Screenshot%20at%2013.58.01.png)

```sql
-- Терминал 1 — завершаем транзакцию
COMMIT;
```
![Screenshot  at 13.59.34.png](screenshots/Screenshot%20%20at%2013.59.34.png)

```sql
-- Терминал 2 - Смотрим финальное состояние (видим обновленную строку)
SELECT
    ctid,
    xmin,
    xmax,
    name,
    email,
    'Терминал 2 ПОСЛЕ COMMIT Т1' AS этап
FROM cinema.users
WHERE user_id = 300005;
```
![Screenshot at 14.01.05.png](screenshots/Screenshot%20at%2014.01.05.png)

```sql
-- Терминал 2 - Смотрим финальное состояние у обновленной строки
SELECT
    lp AS кортеж,
    t_infomask,
    (t_infomask & 1024) != 0 AS xmin_committed,
    (t_infomask & 4096) != 0 AS xmax_committed,
    (t_infomask & 8192) != 0 AS row_updated
FROM heap_page_items(get_raw_page('cinema.users', 4))
WHERE lp = 5;
```
![Screenshot 14.02.04.png](screenshots/Screenshot%2014.02.04.png)
t_infomask 10499 - новая версия видна всем

## DEADLOCK
```sql
-- Создаём две тестовые строки
INSERT INTO cinema.users (name, email, password_hash, role, date_created)
VALUES 
    ('Deadlock_User_A', 'deadlock_a@test.local', md5('test'), 'user', NOW()),
    ('Deadlock_User_B', 'deadlock_b@test.local', md5('test'), 'user', NOW())
RETURNING user_id, name;
```
![Screenshot at 14.13.44.png](screenshots/Screenshot%20at%2014.13.44.png)
```sql
-- Терминал 1 — начинаем транзакцию и блокируем строку A
BEGIN;

UPDATE cinema.users
SET name = 'T1_Locks_A'
WHERE user_id = 300006;
-- Строка A заблокирована Терминалом 1
```
![Screenshot at 14.25.53.png](screenshots/Screenshot%20at%2014.25.53.png)
```sql
-- Терминал 2 — начинаем транзакцию и блокируем строку B
BEGIN;

UPDATE cinema.users 
SET name = 'T2_Locks_B' 
WHERE user_id = 300007;  
-- Строка B заблокирована Терминалом 2
```
![Screenshot at 14.26.04.png](screenshots/Screenshot%20at%2014.26.04.png)
```sql
-- Терминал 1 — пытается обновить строку B
UPDATE cinema.users 
SET name = 'T1_Wants_B' 
WHERE user_id = 300007;  
-- Запрос ЗАВИСНЕТ — Терминал 1 ждёт, пока Терминал 2 освободит строку B
```
![Screenshot at 14.27.23.png](screenshots/Screenshot%20at%2014.27.23.png)
```sql
-- Терминал 2 — пытается обновить строку A
UPDATE cinema.users 
SET name = 'T2_Wants_A' 
WHERE user_id = 300006;  

-- ДЕДЛОК! PostgreSQL обнаружит циклическую зависимость
-- Одна из транзакций будет ОТКАЧЕНА с ошибкой:
```
![Screenshot at 14.27.54.png](screenshots/Screenshot%20at%2014.27.54.png)
```sql
-- Проверяем, что строки существуют и не заблокированы
SELECT user_id, name, email 
FROM cinema.users 
WHERE user_id IN (300006, 300007);
```
![Screenshot at 14.28.05.png](screenshots/Screenshot%20at%2014.28.05.png)
```sql
1. Терминал 1 заблокировал строку A (user_id = 300006)
2. Терминал 2 заблокировал строку B (user_id = 300007)
3. Терминал 1 попытался заблокировать строку B — ЗАВИС (ожидание)
4. Терминал 2 попытался заблокировать строку A — ДЕДЛОК!

PostgreSQL обнаружил циклическую зависимость:
T1 → ждёт B → которую держит T2
T2 → ждёт A → которую держит T1

Результат: Одна транзакция (T2) была принудительно откатана с ошибкой.
```

## Режимы блокировки на уровне строк
```sql
-- Создаём тестовую строку
INSERT INTO cinema.users (name, email, password_hash, role, date_created)
VALUES ('Lock_Test_User', 'lock_test@cinema.local', md5('test'), 'user', NOW())
RETURNING user_id, ctid;
```
![Screenshot at 14.41.16.png](screenshots/Screenshot%20at%2014.41.16.png)
```sql
-- Терминал 1 — FOR UPDATE
BEGIN;

SELECT * FROM cinema.users
WHERE user_id = 300008
FOR UPDATE;
-- Строка заблокирована для ВСЕХ других транзакций
```
 
```sql
-- Терминал 2 — тестируем конфликты

BEGIN;

-- Вариант 1: FOR UPDATE (должен ЗАВИСНУТЬ)
SELECT * FROM cinema.users 
WHERE user_id = 300008 
FOR UPDATE;
```
![Screenshot at 14.43.23.png](screenshots/Screenshot%20at%2014.43.23.png)
```sql
-- Вариант 2: FOR NO KEY UPDATE (должен ЗАВИСНУТЬ)
SELECT * FROM cinema.users 
WHERE user_id = 300008 
FOR NO KEY UPDATE;
```
![Screenshot at 14.43.23.png](screenshots/Screenshot%20at%2014.43.23.png)

```sql
-- Вариант 3: FOR SHARE (должен ЗАВИСНУТЬ)
SELECT * FROM cinema.users 
WHERE user_id = 300008 
FOR SHARE;
```
![Screenshot at 14.43.23.png](screenshots/Screenshot%20at%2014.43.23.png)
```sql
-- Вариант 4: FOR KEY SHARE (должен ЗАВИСНУТЬ)
SELECT * FROM cinema.users 
WHERE user_id = 300008 
FOR KEY SHARE;
```
![Screenshot at 14.43.23.png](screenshots/Screenshot%20at%2014.43.23.png)
```sql
-- Вариант 5: Обычный UPDATE (должен ЗАВИСНУТЬ)
UPDATE cinema.users 
SET name = 'Blocked_Update' 
WHERE user_id = 300008;
```
![Screenshot at 14.43.23.png](screenshots/Screenshot%20at%2014.43.23.png)
```sql
-- Вариант 6: Обычный SELECT (НЕ заблокируется)
SELECT * FROM cinema.users 
WHERE user_id = 300008;
```
![Screenshot at 14.48.30.png](screenshots/Screenshot%20at%2014.48.30.png)

## Очистка данных

```sql
-- Создаём тестовую таблицу
CREATE TABLE IF NOT EXISTS cinema.vacuum_test (
      id SERIAL PRIMARY KEY,
      name TEXT,
      data TEXT,
      created_at TIMESTAMP DEFAULT NOW()
 );

-- Заполняем 1000 строк
INSERT INTO cinema.vacuum_test (name, data)
SELECT
    'User_' || g,
    repeat('x', 1000)  
FROM generate_series(1, 1000) AS g;
```

```sql
-- Статистика таблицы ДО обновлений
SELECT 
    relname AS таблица,
    n_live_tup AS живые_строки,
    n_dead_tup AS мёртвые_строки,
    last_vacuum AS последний_vacuum,
    last_autovacuum AS последний_autovacuum
FROM pg_stat_user_tables 
WHERE relname = 'vacuum_test';
```
![Screenshot at 15.07.58.png](screenshots/Screenshot%20at%2015.07.58.png)
```sql
-- Обновляем все строки (создаём 1000 dead tuples)
UPDATE cinema.vacuum_test 
SET 
    name = 'Updated_' || id,
    created_at = NOW();
```

```sql
-- Статистика ПОСЛЕ UPDATE (до VACUUM)
SELECT 
    relname AS таблица,
    n_live_tup AS живые_строки,
    n_dead_tup AS мёртвые_строки,
    pg_size_pretty(pg_relation_size('cinema.vacuum_test')) AS размер_таблицы
FROM pg_stat_user_tables 
WHERE relname = 'vacuum_test';
```
![Screenshot  at 15.08.27.png](screenshots/Screenshot%20%20at%2015.08.27.png)
```sql
-- Запускаем ручную очистку
VACUUM cinema.vacuum_test;
```
![Screenshot  at 15.08.42.png](screenshots/Screenshot%20%20at%2015.08.42.png)
```sql
-- Проверяем статистику ПОСЛЕ VACUUM
SELECT
    relname AS таблица,
    n_live_tup AS живые_строки,
    n_dead_tup AS мёртвые_строки,
    pg_size_pretty(pg_relation_size('cinema.vacuum_test')) AS размер_таблицы,
    last_vacuum AS последний_vacuum
FROM pg_stat_user_tables
WHERE relname = 'vacuum_test';
```
![Screenshot at 15.17.54.png](screenshots/Screenshot%20at%2015.17.54.png)