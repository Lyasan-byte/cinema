## Physical streaming replication
![Screenshot 2026-03 at 19.26.00.png](screenshots/Screenshot%202026-03%20at%2019.26.00.png)

```bash
# Настроили docker-compose.yml
# Сначала запускаем только primary:
docker compose up -d primary

# Добавляем строку в pg_hba.conf внутри контейнера:
docker exec -it pg-primary bash

echo "host replication replicator 0.0.0.0/0 md5" >> /var/lib/postgresql/data/pg_hba.conf
echo "host all all 0.0.0.0/0 md5" >> /var/lib/postgresql/data/pg_hba.conf

# Перезагружаем конфиг:
psql -U admin -d cinema_db -c "SELECT pg_reload_conf();"
```
```bash
# Поднимаем все 3 instance
docker compose up -d
# Проверка контейнеров:
docker ps
```
![Screenshot 2026-03 at 16.04.22.png](screenshots/Screenshot%202026-03%20at%2016.04.22.png)

```bash
# Подключение к primary
docker exec -it pg-primary psql -U admin -d cinema_db
```
```sql
-- Проверить, что это primary (На primary должно быть: f)
SELECT pg_is_in_recovery();
```
![Screenshot 2026-03 at 15.11.23.png](screenshots/Screenshot%202026-03%20at%2015.11.23.png)

```sql
-- Создать тестовую таблицу на primary
CREATE TABLE replication_test (
                                  id SERIAL PRIMARY KEY,
                                  message TEXT NOT NULL
);
```
![Screenshot 2026-03 at 15.11.29.png](screenshots/Screenshot%202026-03%20at%2015.11.29.png)


```sql
-- Вставить данные на primary
INSERT INTO replication_test (message)
VALUES ('hello from primary');
-- Проверить на primary
SELECT * FROM replication_test;
```
![Screenshot 2026-03 at 15.11.36.png](screenshots/Screenshot%202026-03%20at%2015.11.36.png)

```bash
# Подключение к replica1
docker exec -it pg-replica1 psql -U admin -d cinema_db
```
```sql
-- Проверить, что это replica (На реплике должно быть: t)
SELECT pg_is_in_recovery();
```
![Screenshot 2026-03 at 15.11.46.png](screenshots/Screenshot%202026-03%20at%2015.11.46.png)

```sql
-- Проверить наличие строки
SELECT * FROM replication_test;
```
![Screenshot 2026-03 at 15.11.51.png](screenshots/Screenshot%202026-03%20at%2015.11.51.png)
```sql
-- Попробовать вставить на реплике (должна быть ошибка)
INSERT INTO replication_test (message)
VALUES ('try insert on replica1');
```
![Screenshot 2026-03 at 15.11.56.png](screenshots/Screenshot%202026-03%20at%2015.11.56.png)

```bash
# Подключение к replica2
docker exec -it pg-replica2 psql -U admin -d cinema_db
```
```sql
-- Проверить наличие строки
SELECT pg_is_in_recovery();
SELECT * FROM replication_test;
```
![Screenshot 2026-03 at 15.12.10.png](screenshots/Screenshot%202026-03%20at%2015.12.10.png)


## Анализ replication lag

```bash
# Окно 1 — мониторинг
docker exec -it pg-primary psql -U admin -d cinema_db
```
```sql
SELECT application_name,
state,
sync_state,
write_lag,
flush_lag,
replay_lag,
pg_wal_lsn_diff(pg_current_wal_lsn(), replay_lsn) AS byte_lag
FROM pg_stat_replication;
```
![Screenshot 2026-03 at 15.39.21.png](screenshots/Screenshot%202026-03%20at%2015.39.21.png)

До INSERT  byte_lag = 0 у обоих реплик, это значит, что данные не отстают друг от друга
```sql
-- Нагрузка на primary (300_000 строк)
CREATE TABLE IF NOT EXISTS load_test (
                                         id SERIAL PRIMARY KEY,
                                         payload TEXT NOT NULL,
                                         created_at TIMESTAMP DEFAULT now()
    );

INSERT INTO load_test (payload)
SELECT repeat(md5(random()::text), 20)
FROM generate_series(1, 300000);
```
![Screenshot 2026-03 at 15.43.11.png](screenshots/Screenshot%202026-03%20at%2015.43.11.png)

```bash
# Проверка на реплике
docker exec -it pg-replica1 psql -U admin -d cinema_db
```
```sql
SELECT count(*) FROM load_test;
```
![Screenshot 2026-03 at 15.48.39.png](screenshots/Screenshot%202026-03%20at%2015.48.39.png)

Данные сразу дошли до реплики, это подтверждает byte_lag = 0 на primary
![Screenshot 2026-03 at 15.51.33.png](screenshots/Screenshot%202026-03%20at%2015.51.33.png)

## Logical replication
```bash
# Перезапускаем с новыми настройками в docker-compose.yml
docker compose up -d
```
![Screenshot 2026-03 at 16.13.36.png](screenshots/Screenshot%202026-03%20at%2016.13.36.png)

```bash
# Разрешаем подключение в pg_hba.conf на publisher
docker exec -it pg-primary bash

echo "host all admin 0.0.0.0/0 md5" >> /var/lib/postgresql/data/pg_hba.conf
psql -U admin -d cinema_db -c "SELECT pg_reload_conf();"
exit
```

# Показать, что данные реплицируются
```bash
# На publisher создать таблицу и publication
docker exec -it pg-primary psql -U admin -d cinema_db
```
```sql
CREATE TABLE logical_test (
id INT PRIMARY KEY,
message TEXT NOT NULL
);

CREATE PUBLICATION demo_pub FOR TABLE logical_test;
```
![Screenshot 2026-03 at 16.19.03.png](screenshots/Screenshot%202026-03%20at%2016.19.03.png)

```bash
# На subscriber создаем такую же таблицу (Схема не реплицируется, поэтому таблица на subscriber должна быть создана заранее.)
docker exec -it pg-logical-sub psql -U admin -d cinema_db

CREATE TABLE logical_test (
    id INT PRIMARY KEY,
    message TEXT NOT NULL
);
```
![Screenshot 2026-03 at 16.23.28.png](screenshots/Screenshot%202026-03%20at%2016.23.28.png)

```bash
# На subscriber создаем subscription
docker exec -it pg-logical-sub psql -U admin -d cinema_db

CREATE SUBSCRIPTION demo_sub
CONNECTION 'host=primary port=5432 dbname=cinema_db user=admin password=Mishka'
PUBLICATION demo_pub;
```
![Screenshot 2026-03 at 16.48.23.png](screenshots/Screenshot%202026-03%20at%2016.48.23.png)
CREATE SUBSCRIPTION создаёт подписку на publication и запускает initial copy существующих данных, 
а затем начинает применять последующие изменения в реальном времени.

# Проверка данных
```bash
# На publisher:
docker exec -it pg-primary psql -U admin -d cinema_db

INSERT INTO logical_test (id, message)
VALUES (1, 'hello logical replication');
SELECT * FROM logical_test;
```
![Screenshot 2026-03 at 16.50.32.png](screenshots/Screenshot%202026-03%20at%2016.50.32.png)

```bash
# На subscriber:
docker exec -it pg-logical-sub psql -U admin -d cinema_db

SELECT * FROM logical_test;
```
![Screenshot 2026-03 at 16.51.48.png](screenshots/Screenshot%202026-03%20at%2016.51.48.png)


# Показать, что DDL не реплицируется
```bash
# Изменим схему только на publisher
docker exec -it pg-primary psql -U admin -d cinema_db

ALTER TABLE logical_test ADD COLUMN note TEXT;
\d logical_test
```
![Screenshot 2026-03 at 16.54.40.png](screenshots/Screenshot%202026-03%20at%2016.54.40.png)

```bash
# На subscriber:
docker exec -it pg-logical-sub psql -U admin -d cinema_db

\d logical_test
```
![Screenshot 2026-03 at 16.56.12.png](screenshots/Screenshot%202026-03%20at%2016.56.12.png)
-на publisher у таблицы есть note
-на subscriber колонки note нет

Это и есть требуемая проверка: DDL не реплицируется.

## Проверка REPLICA IDENTITY
Publication реплицирует UPDATE и DELETE только если 
у таблицы есть replica identity. По умолчанию это primary key; 
можно использовать другой подходящий unique index или REPLICA IDENTITY FULL.
Если таблица без replica identity добавлена в publication, то INSERT пройдёт, 
а последующие UPDATE/DELETE на publisher вызовут ошибку.

```bash
# Таблица без PK на publisher:
docker exec -it pg-primary psql -U admin -d cinema_db

CREATE TABLE no_pk_test (
    a INT,
    b TEXT
);

ALTER PUBLICATION demo_pub ADD TABLE no_pk_test;
```
![Screenshot 2026-03 at 17.29.54.png](screenshots/Screenshot%202026-03%20at%2017.29.54.png)

```bash
# На subscriber:
docker exec -it pg-logical-sub psql -U admin -d cinema_db

CREATE TABLE no_pk_test (
    a INT,
    b TEXT
);
```
![Screenshot 2026-03 at 17.30.28.png](screenshots/Screenshot%202026-03%20at%2017.30.28.png)
```bash
# INSERT будет работать на publisher:
docker exec -it pg-primary psql -U admin -d cinema_db

INSERT INTO no_pk_test (a, b) VALUES (1, 'first');
SELECT * FROM no_pk_test;
```
![Screenshot 2026-03 at 17.32.49.png](screenshots/Screenshot%202026-03%20at%2017.32.49.png)
```bash
# На subscriber:
docker exec -it pg-logical-sub psql -U admin -d cinema_db

SELECT * FROM no_pk_test;
```
![Screenshot 2026-03 at 20.38.40.png](screenshots/Screenshot%202026-03%20at%2020.38.40.png)
## UPDATE (должна быть ошибка, так как нет REPLICA IDENTITY)

```bash
# На publisher:
docker exec -it pg-primary psql -U admin -d cinema_db

UPDATE no_pk_test
SET b = 'updated'
WHERE a = 1;
```
![Screenshot 2026-03 at 20.41.09.png](screenshots/Screenshot%202026-03%20at%2020.41.09.png)

### Чтобы это исправить на publisher и subscriber можно выставить:
```sql
ALTER TABLE no_pk_test REPLICA IDENTITY FULL;
```
## Проверка replication status
Для logical replication PostgreSQL рекомендует смотреть 
pg_stat_subscription на subscriber.
```bash
# На subscriber:
docker exec -it pg-logical-sub psql -U admin -d cinema_db

SELECT subname,
       pid,
       relid::regclass,
       received_lsn,
       latest_end_lsn,
       latest_end_time
FROM pg_stat_subscription;
```
![Screenshot 2026-03 at 20.45.27.png](screenshots/Screenshot%202026-03%20at%2020.45.27.png)

## Как пригодятся pg_dump / pg_restore
Logical replication не реплицирует DDL и схему, поэтому 
pg_dump --schema-only удобен, чтобы быстро создать на subscriber 
совместимую схему до создания subscription.
