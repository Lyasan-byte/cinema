## RANGE-секционирование
```sql
-- Создание таблицы и секций
CREATE TABLE cinema.review_p_range (
                                       LIKE cinema.review INCLUDING DEFAULTS INCLUDING CONSTRAINTS
) PARTITION BY RANGE (review_date);

CREATE TABLE cinema.review_p_range_2024
    PARTITION OF cinema.review_p_range
    FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');

CREATE TABLE cinema.review_p_range_2025
    PARTITION OF cinema.review_p_range
    FOR VALUES FROM ('2025-01-01') TO ('2026-01-01');

CREATE TABLE cinema.review_p_range_2026
    PARTITION OF cinema.review_p_range
    FOR VALUES FROM ('2026-01-01') TO ('2027-01-01');

CREATE TABLE cinema.review_p_range_default
    PARTITION OF cinema.review_p_range DEFAULT;

CREATE INDEX idx_review_p_range_movie_date
    ON cinema.review_p_range (movie_id, review_date);

INSERT INTO cinema.review_p_range
SELECT *
FROM cinema.review;

ANALYZE cinema.review_p_range;
```
![Screenshot 2026-03 at 16.38.00.png](screenshots/Screenshot%202026-03%20at%2016.38.00.png)
```sql
-- Запрос для проверки
EXPLAIN (ANALYZE, BUFFERS)
SELECT review_id, movie_id, rating, review_date
FROM cinema.review_p_range
WHERE review_date >= TIMESTAMP '2025-01-01'
  AND review_date <  TIMESTAMP '2026-01-01'
  AND movie_id = 10;
```
![Screenshot 2026-03 at 16.41.31.png](screenshots/Screenshot%202026-03%20at%2016.41.31.png)
1. Есть ли partition pruning?
   Да, есть. В плане видна только одна партиция — review_p_range_2025. 
PostgreSQL указывает, что партиции, отсечённые pruning,
не показываются в EXPLAIN, поэтому появление только одной партиции означает, что остальные были исключены. 

2. Сколько партиций участвует в плане?
   Одна партиция. Это review_p_range_2025. Другие партиции в плане отсутствуют, следовательно, они не участвовали в выполнении запроса.

3. Используется ли индекс?
   Да, индекс используется. Это видно по типу узла Index Scan using review_p_range_2025_movie_id_review_date_idx.

## LIST-секционирование

```sql
-- Создание таблицы и партиций
CREATE TABLE cinema.movie_p_list (
                                    LIKE cinema.movie INCLUDING DEFAULTS INCLUDING CONSTRAINTS
) PARTITION BY LIST (language);

CREATE TABLE cinema.movie_p_list_en
   PARTITION OF cinema.movie_p_list
   FOR VALUES IN ('English');

CREATE TABLE cinema.movie_p_list_ru
   PARTITION OF cinema.movie_p_list
   FOR VALUES IN ('Russian');

CREATE TABLE cinema.movie_p_list_fr
   PARTITION OF cinema.movie_p_list
   FOR VALUES IN ('French');

CREATE TABLE cinema.movie_p_list_other
   PARTITION OF cinema.movie_p_list DEFAULT;

CREATE INDEX idx_movie_p_list_title
   ON cinema.movie_p_list (title);

INSERT INTO cinema.movie_p_list
SELECT *
FROM cinema.movie;

ANALYZE cinema.movie_p_list;
```
![Screenshot 2026-03 at 16.57.11.png](screenshots/Screenshot%202026-03%20at%2016.57.11.png)

```sql
-- Запрос для проверки
EXPLAIN (ANALYZE, BUFFERS)
SELECT movie_id, title, language
FROM cinema.movie_p_list
WHERE language = 'English'
  AND title = 'Movie_1000';
```
![Screenshot 2026-03 at 17.02.14.png](screenshots/Screenshot%202026-03%20at%2017.02.14.png)

1. Есть ли partition pruning?
   Да. В плане видна только одна партиция — movie_p_list_en. 
Для LIST это означает, что по значению language = 'English' PostgreSQL отбросил остальные партиции.

2. Сколько партиций участвует в плане?
   Одна партиция — movie_p_list_en.

3. Используется ли индекс?
   Да. Это видно по узлу Index Scan using movie_p_list_en_title_idx. Индекс используется для условия title = 'Movie_1000'.

## HASH-секционирование

```sql
-- Создание таблицы и партиций
CREATE TABLE cinema.users_p_hash (
                                    LIKE cinema.users INCLUDING DEFAULTS INCLUDING CONSTRAINTS
) PARTITION BY HASH (user_id);

CREATE TABLE cinema.users_p_hash_0
   PARTITION OF cinema.users_p_hash
   FOR VALUES WITH (MODULUS 4, REMAINDER 0);

CREATE TABLE cinema.users_p_hash_1
   PARTITION OF cinema.users_p_hash
   FOR VALUES WITH (MODULUS 4, REMAINDER 1);

CREATE TABLE cinema.users_p_hash_2
   PARTITION OF cinema.users_p_hash
   FOR VALUES WITH (MODULUS 4, REMAINDER 2);

CREATE TABLE cinema.users_p_hash_3
   PARTITION OF cinema.users_p_hash
   FOR VALUES WITH (MODULUS 4, REMAINDER 3);

CREATE INDEX idx_users_p_hash_user_id
   ON cinema.users_p_hash (user_id);

INSERT INTO cinema.users_p_hash
SELECT *
FROM cinema.users;

ANALYZE cinema.users_p_hash;
```
![Screenshot 2026-03 at 17.06.49.png](screenshots/Screenshot%202026-03%20at%2017.06.49.png)

```sql
-- Запрос для проверки
EXPLAIN (ANALYZE, BUFFERS)
SELECT user_id, name, email
FROM cinema.users_p_hash
WHERE user_id = 42;
```
![Screenshot 2026-03 at 17.12.31.png](screenshots/Screenshot%202026-03%20at%2017.12.31.png)

Есть ли partition pruning?
Да. В плане участвует только одна партиция — users_p_hash_2, остальные hash-партиции были отсечены.

Сколько партиций участвует в плане?
Одна партиция из четырёх — users_p_hash_2.

Используется ли индекс?
Да. Это видно по узлу Index Scan using users_p_hash_2_user_id_idx.

## Секционирование и физическая репликация

```bash
# Сначала подключаемся к реплике:
docker exec -it pg-replica1 psql -U admin -d cinema_db
```
![Screenshot 2026-03 at 17.25.44.png](screenshots/Screenshot%202026-03%20at%2017.25.44.png)

```sql
-- Проверка наличия самих секционированных таблиц:
SELECT schemaname, tablename
FROM pg_tables
WHERE schemaname = 'cinema'
  AND tablename IN ('review_p_range', 'movie_p_list', 'users_p_hash')
ORDER BY tablename;
```
![Screenshot 2026-03 at 17.22.40.png](screenshots/Screenshot%202026-03%20at%2017.22.40.png)

```sql
-- Смотрим сами партиции
SELECT
   inhparent::regclass AS parent_table,
   inhrelid::regclass AS partition_table
FROM pg_inherits
WHERE inhparent::regclass::text IN (
    'cinema.review_p_range',
    'cinema.movie_p_list',
    'cinema.users_p_hash'
)
ORDER BY parent_table, partition_table;
```
![Screenshot 2026-03 at 17.23.23.png](screenshots/Screenshot%202026-03%20at%2017.23.23.png)

На физической реплике было проверено наличие секционированных 
таблиц cinema.review_p_range, cinema.movie_p_list и cinema.users_p_hash.

Почему физическая репликация “не знает” про секции?
Физическая репликация PostgreSQL не “знает” про секции как про отдельный логический объект, 
потому что она работает не на уровне таблиц и строк, 
а на уровне WAL-записей и физических изменений файлов кластера.

## Логическая репликация и секционирование publish_via_partition_root = on / off

### publish_via_partition_root = off
```bash
# Сначала подключаемся к Publisher (pg-primary):
docker exec -it pg-primary psql -U admin -d cinema_db
```
```sql
--Создаем тестовую таблицу:
CREATE SCHEMA IF NOT EXISTS cinema;

CREATE TABLE cinema.lr_root_off (
                                   id   integer NOT NULL,
                                   d    date    NOT NULL,
                                   note text,
                                   PRIMARY KEY (id, d)
) PARTITION BY RANGE (d);

CREATE TABLE cinema.lr_root_off_2025
   PARTITION OF cinema.lr_root_off
   FOR VALUES FROM ('2025-01-01') TO ('2026-01-01');

CREATE TABLE cinema.lr_root_off_2026
   PARTITION OF cinema.lr_root_off
   FOR VALUES FROM ('2026-01-01') TO ('2027-01-01');

CREATE PUBLICATION pub_lr_off
FOR TABLE cinema.lr_root_off
WITH (publish = 'insert', publish_via_partition_root = false);
```
![Screenshot 2026-03 at 17.36.07.png](screenshots/Screenshot%202026-03%20at%2017.36.07.png)

```bash
# Сначала подключаемся к Subscriber (pg-logical-sub):
docker exec -it pg-logical-sub psql -U admin -d cinema_db
```

```sql
--Так как DDL не реплицируется, ту же структуру надо создать руками.
CREATE SCHEMA IF NOT EXISTS cinema;
CREATE TABLE cinema.lr_root_off (
                                   id   integer NOT NULL,
                                   d    date    NOT NULL,
                                   note text,
                                   PRIMARY KEY (id, d)
) PARTITION BY RANGE (d);

CREATE TABLE cinema.lr_root_off_2025
   PARTITION OF cinema.lr_root_off
   FOR VALUES FROM ('2025-01-01') TO ('2026-01-01');

CREATE TABLE cinema.lr_root_off_2026
   PARTITION OF cinema.lr_root_off
   FOR VALUES FROM ('2026-01-01') TO ('2027-01-01');

CREATE SUBSCRIPTION sub_lr_off
CONNECTION 'host=primary port=5432 dbname=cinema_db user=admin password=Mishka'
PUBLICATION pub_lr_off
WITH (copy_data = false);
```
![Screenshot 2026-03 at 17.38.34.png](screenshots/Screenshot%202026-03%20at%2017.38.34.png)

```sql
--Проверка На publisher
INSERT INTO cinema.lr_root_off VALUES (1, DATE '2025-06-01', 'root insert off');
INSERT INTO cinema.lr_root_off_2026 VALUES (2, DATE '2026-03-10', 'leaf insert off');
```
![Screenshot 2026-03 at 17.40.29.png](screenshots/Screenshot%202026-03%20at%2017.40.29.png)
```sql
--На subscriber
SELECT tableoid::regclass AS where_landed, *
FROM cinema.lr_root_off
ORDER BY id;
```
![Screenshot 2026-03 at 17.42.01.png](screenshots/Screenshot%202026-03%20at%2017.42.01.png)
Вывод: строки попали в партиции subscriber:
cinema.lr_root_off_2025
cinema.lr_root_off_2026
### publish_via_partition_root = on

```sql
--Publisher (pg-primary)
CREATE TABLE cinema.lr_root_on (
                                  id   integer NOT NULL,
                                  d    date    NOT NULL,
                                  note text,
                                  PRIMARY KEY (id, d)
) PARTITION BY RANGE (d);

CREATE TABLE cinema.lr_root_on_2025
   PARTITION OF cinema.lr_root_on
   FOR VALUES FROM ('2025-01-01') TO ('2026-01-01');

CREATE TABLE cinema.lr_root_on_2026
   PARTITION OF cinema.lr_root_on
   FOR VALUES FROM ('2026-01-01') TO ('2027-01-01');

CREATE PUBLICATION pub_lr_on
FOR TABLE cinema.lr_root_on
WITH (publish = 'insert', publish_via_partition_root = true);
```
![Screenshot 2026-03 at 18.03.49.png](screenshots/Screenshot%202026-03%20at%2018.03.49.png)

```sql
--Subscriber (pg-logical-sub)
CREATE TABLE cinema.lr_root_on (
                                  id   integer NOT NULL,
                                  d    date    NOT NULL,
                                  note text,
                                  PRIMARY KEY (id, d)
);

CREATE SUBSCRIPTION sub_lr_on
CONNECTION 'host=primary port=5432 dbname=cinema_db user=admin password=Mishka'
PUBLICATION pub_lr_on
WITH (copy_data = false);
```
![Screenshot 2026-03 at 18.05.37.png](screenshots/Screenshot%202026-03%20at%2018.05.37.png)
```sql
--Проверка На publisher
INSERT INTO cinema.lr_root_on VALUES (1, DATE '2025-07-01', 'root insert on');
INSERT INTO cinema.lr_root_on_2026 VALUES (2, DATE '2026-04-01', 'leaf insert on');
```
![Screenshot 2026-03 at 18.08.01.png](screenshots/Screenshot%202026-03%20at%2018.08.01.png)

```sql
--На subscriber
SELECT *
FROM cinema.lr_root_on
ORDER BY id;
```
![Screenshot 2026-03 at 18.08.25.png](screenshots/Screenshot%202026-03%20at%2018.08.25.png)

Обе строки появятся в обычной таблице cinema.lr_root_on на subscriber, 
хотя на publisher одна из них была вставлена прямо в leaf partition. 
Это и демонстрирует режим publish_via_partition_root = on 
subscriber получает изменения как изменения root table.
## Шардирование через postgres_fdw

```bash
# Изменили docker-compose.yml и запускаем
docker compose up -d shard1 shard2 router
```
![Screenshot 2026-03 at 18.53.14.png](screenshots/Screenshot%202026-03%20at%2018.53.14.png)
```sql
--Создаем таблицы на shard1 и shard2
--shard1
docker exec -it pg-shard1 psql -U admin -d cinema_shard1

CREATE SCHEMA IF NOT EXISTS cinema;

DROP TABLE IF EXISTS cinema.users_shard;

CREATE TABLE cinema.users_shard (
                                   user_id integer NOT NULL,
                                   name text NOT NULL,
                                   email text NOT NULL
);

CREATE INDEX users_shard_user_id_idx ON cinema.users_shard(user_id);

INSERT INTO cinema.users_shard (user_id, name, email)
SELECT
   g,
   'User_' || g,
   'user' || g || '@shard1.test'
FROM generate_series(1, 100000) AS g;
```
![Screenshot 2026-03 at 19.03.51.png](screenshots/Screenshot%202026-03%20at%2019.03.51.png)

```sql
--shard2
docker exec -it pg-shard2 psql -U admin -d cinema_shard2

CREATE SCHEMA IF NOT EXISTS cinema;

DROP TABLE IF EXISTS cinema.users_shard;

CREATE TABLE cinema.users_shard (
                                   user_id integer NOT NULL,
                                   name text NOT NULL,
                                   email text NOT NULL
);

CREATE INDEX users_shard_user_id_idx ON cinema.users_shard(user_id);

INSERT INTO cinema.users_shard (user_id, name, email)
SELECT
   g,
   'User_' || g,
   'user' || g || '@shard2.test'
FROM generate_series(100001, 200000) AS g;
```
![Screenshot 2026-03 at 19.05.51.png](screenshots/Screenshot%202026-03%20at%2019.05.51.png)

### Настройка router через postgres_fdw
```bash
docker exec -it pg-router psql -U admin -d cinema_router
```
```sql
--Создаем foreign servers и user mappings
CREATE SCHEMA IF NOT EXISTS cinema;
CREATE EXTENSION IF NOT EXISTS postgres_fdw;

CREATE SERVER shard1_srv
FOREIGN DATA WRAPPER postgres_fdw
OPTIONS (
    host 'shard1',
    port '5432',
    dbname 'cinema_shard1',
    use_remote_estimate 'true'
);

CREATE SERVER shard2_srv
FOREIGN DATA WRAPPER postgres_fdw
OPTIONS (
    host 'shard2',
    port '5432',
    dbname 'cinema_shard2',
    use_remote_estimate 'true'
);

CREATE USER MAPPING FOR CURRENT_USER
SERVER shard1_srv
OPTIONS (user 'admin', password 'Mishka');

CREATE USER MAPPING FOR CURRENT_USER
SERVER shard2_srv
OPTIONS (user 'admin', password 'Mishka');
```
![Screenshot 2026-03 at 19.12.33.png](screenshots/Screenshot%202026-03%20at%2019.12.33.png)

```sql
-- Создаём router parent и foreign partitions:
CREATE TABLE cinema.users_router (
                                    user_id integer NOT NULL,
                                    name text NOT NULL,
                                    email text NOT NULL
) PARTITION BY RANGE (user_id);

CREATE FOREIGN TABLE cinema.users_shard1_ft
PARTITION OF cinema.users_router
FOR VALUES FROM (1) TO (100001)
SERVER shard1_srv
OPTIONS (
    schema_name 'cinema',
    table_name 'users_shard'
);

CREATE FOREIGN TABLE cinema.users_shard2_ft
PARTITION OF cinema.users_router
FOR VALUES FROM (100001) TO (200001)
SERVER shard2_srv
OPTIONS (
    schema_name 'cinema',
    table_name 'users_shard'
);
```
![Screenshot 2026-03 at 19.14.21.png](screenshots/Screenshot%202026-03%20at%2019.14.21.png)

#### Простой запрос на все данные, который задевает оба шарда:
```sql
EXPLAIN (VERBOSE)
SELECT user_id, name, email
FROM cinema.users_router
WHERE user_id BETWEEN 99998 AND 100003;
```
![Screenshot 2026-03 at 19.16.20.png](screenshots/Screenshot%202026-03%20at%2019.16.20.png)

Узел Append означает, что PostgreSQL объединяет результаты нескольких дочерних 
узлов в один поток результата. В данном случае router собирает строки из двух источников.

Два узла Foreign Scan показывают, что запрос был отправлен на оба шарда: 
users_shard1_ft и users_shard2_ft, потому что
часть значений находится на первом шарде, часть — на втором.

Строки Remote SQL показывают SQL-запросы, которые postgres_fdw отправил
на удалённые PostgreSQL-серверы. postgres_fdw предназначен для доступа к таблицам
внешних PostgreSQL-серверов, а в EXPLAIN VERBOSE можно увидеть удалённые запросы,
реально выполняемые на шардах.

#### Простой запрос на один шард
```sql
EXPLAIN (VERBOSE)
SELECT user_id, name, email
FROM cinema.users_router
WHERE user_id = 42;
```
![Screenshot 2026-03 at 19.20.53.png](screenshots/Screenshot%202026-03%20at%2019.20.53.png)
В плане присутствует только один Foreign Scan на users_shard1_ft. 
Это означает, что router выполнил запрос только на одном шарде.
Причина — partition pruning: по значению ключа user_id PostgreSQL
определил единственную подходящую партицию и исключил остальные.