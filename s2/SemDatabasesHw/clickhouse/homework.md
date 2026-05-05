# ClickHouse VS PosgreSQL
```bash
# Запуск контейнеров ClickHouse и PostgreSQL
docker compose up -d
```
![Screenshot 2026-05 at 09.25.42.png](screenshots/Screenshot%202026-05%20at%2009.25.42.png)
```bash
# Подключение к ClickHouse
docker exec -it homework-clickhouse clickhouse-client -u admin --password 1234 --database homework
# Подключение к PostgreSQL
docker exec -it homework-postgres psql -U admin -d homework
```

## Задание 1 (ClickHouse)

```sql
-- Создаем необходимые таблицы из задания и наполняем данными
DROP TABLE IF EXISTS web_logs;

CREATE TABLE web_logs (
                          log_time DateTime,
                          ip String,
                          url String,
                          status_code UInt16,
                          response_size UInt64
) ENGINE = MergeTree()
ORDER BY (log_time, status_code);

INSERT INTO web_logs
SELECT
    toDateTime('2024-03-01 00:00:00') + INTERVAL number SECOND,
    concat('192.168.0.', toString(number % 50)),
    arrayElement(['/home', '/api/users', '/api/orders', '/admin', '/products'], number % 5 + 1),
    arrayElement([200, 200, 200, 404, 500, 301, 200], number % 7 + 1),
    rand() % 1000000
FROM numbers(500000);
```
![Screenshot 2026-05 at 09.26.57.png](screenshots/Screenshot%202026-05%20at%2009.26.57.png)
![Screenshot 2026-05 at 09.27.26.png](screenshots/Screenshot%202026-05%20at%2009.27.26.png)

```sql
-- 1. Топ-10 IP-адресов по количеству запросов
SELECT
    ip,
    count() AS requests
FROM web_logs
GROUP BY ip
ORDER BY requests DESC, ip
    LIMIT 10;
```
![Screenshot 2026-05 at 09.28.03.png](screenshots/Screenshot%202026-05%20at%2009.28.03.png)

```sql
--2. Процент успешных и ошибочных запросов
SELECT
    round(countIf(status_code >= 200 AND status_code < 300) / count() * 100, 2) AS success_2xx_percent,
    round(countIf(status_code >= 400 AND status_code < 600) / count() * 100, 2) AS error_4xx_5xx_percent
FROM web_logs;
```
![Screenshot 2026-05 at 09.28.32.png](screenshots/Screenshot%202026-05%20at%2009.28.32.png)
```sql
-- 3. Самый популярный URL и средний размер ответа
SELECT
    url,
    count() AS requests,
    round(avg(response_size), 2) AS avg_response_size
FROM web_logs
GROUP BY url
ORDER BY requests DESC, url
    LIMIT 1;
```
![Screenshot 2026-05 at 09.28.43.png](screenshots/Screenshot%202026-05%20at%2009.28.43.png)
```sql
-- 4. Час с наибольшим количеством ошибок 500
SELECT
    toStartOfHour(log_time) AS hour,
    count() AS errors_500
FROM web_logs
WHERE status_code = 500
GROUP BY hour
ORDER BY errors_500 DESC, hour
    LIMIT 1;
```
![Screenshot 2026-05 at 09.28.55.png](screenshots/Screenshot%202026-05%20at%2009.28.55.png)
## Задание 2
### Clickhouse

```sql
-- Создаем необходимые таблицы из задания и наполняем данными
DROP TABLE IF EXISTS sales_ch;

CREATE TABLE sales_ch (
                          sale_date DateTime,
                          product_id UInt64,
                          category String,
                          quantity UInt32,
                          price Float64,
                          customer_id UInt64
) ENGINE = MergeTree()
ORDER BY (sale_date);

INSERT INTO sales_ch
SELECT
    toDateTime('2024-01-01 00:00:00') + INTERVAL number MINUTE,
    number % 1000,
    arrayElement(['Electronics', 'Clothing', 'Food', 'Books'], number % 4 + 1),
    rand() % 10 + 1,
    round(rand() % 10000 / 100, 2),
    number % 50000
FROM numbers(1000000);
```
![Screenshot 2026-05 at 09.33.46.png](screenshots/Screenshot%202026-05%20at%2009.33.46.png)
```sql
-- Продажи за последний месяц
SELECT
count() AS sales_count,
round(sum(quantity * price), 2) AS total_sum
FROM sales_ch
WHERE sale_date >= (
SELECT max(sale_date) - INTERVAL 1 MONTH
FROM sales_ch
);
```
![Screenshot 2026-05 at 09.34.12.png](screenshots/Screenshot%202026-05%20at%2009.34.12.png)
```sql
-- Размер данных в ClickHouse
SELECT
    table,
    formatReadableSize(sum(data_compressed_bytes)) AS compressed_size,
    formatReadableSize(sum(data_uncompressed_bytes)) AS uncompressed_size,
    round(sum(data_uncompressed_bytes) / sum(data_compressed_bytes), 2) AS compression_ratio
FROM system.parts
WHERE database = 'homework'
  AND table = 'sales_ch'
  AND active
GROUP BY table;
```
![Screenshot 2026-05 at 09.34.25.png](screenshots/Screenshot%202026-05%20at%2009.34.25.png)

### PostgreSQL

```sql
-- Создаем необходимые таблицы, индексы из задания и наполняем данными
DROP TABLE IF EXISTS sales_pg;

CREATE TABLE sales_pg (
                          sale_date timestamp,
                          product_id bigint,
                          category text,
                          quantity integer,
                          price float8,
                          customer_id bigint
);

CREATE INDEX idx_sales_pg_date ON sales_pg(sale_date);
CREATE INDEX idx_sales_pg_product ON sales_pg(product_id);

INSERT INTO sales_pg
SELECT
    '2024-01-01 00:00:00'::timestamp + (n || ' minutes')::interval,
    n % 1000,
    CASE (n % 4)
        WHEN 0 THEN 'Electronics'
        WHEN 1 THEN 'Clothing'
        WHEN 2 THEN 'Food'
        ELSE 'Books'
END,
    (random() * 9 + 1)::integer,
    round((random() * 100)::numeric, 2),
    n % 50000
FROM generate_series(1, 1000000) AS n;
```
![Screenshot 2026-05 at 09.39.00.png](screenshots/Screenshot%202026-05%20at%2009.39.00.png)

```sql
-- Продажи за последний месяц
SELECT
    count(*) AS sales_count,
    round(sum(quantity * price)::numeric, 2) AS total_sum
FROM sales_pg
WHERE sale_date >= (
    SELECT max(sale_date) - interval '1 month'
FROM sales_pg
    );
```
![Screenshot 2026-05 at 09.38.27.png](screenshots/Screenshot%202026-05%20at%2009.38.27.png)
```sql
-- Размер данных в PostgreSQL
SELECT
    pg_size_pretty(pg_total_relation_size('sales_pg')) AS total_size,
    pg_size_pretty(pg_relation_size('sales_pg')) AS table_size,
    pg_size_pretty(pg_indexes_size('sales_pg')) AS indexes_size;
```
![Screenshot 2026-05 at 09.38.40.png](screenshots/Screenshot%202026-05%20at%2009.38.40.png)
## Ответы на вопросы:

1. Какая СУБД быстрее вставила 1 млн строк?
Clickhouse - 0.117 sec
PostgreSQL - 3.085
Разница:
3.085 / 0.117 = 26.37
Вывод: ClickHouse вставил 1 млн строк примерно в 26.4 раза быстрее, чем PostgreSQL.

2. Во сколько раз ClickHouse сжал данные эффективнее?
ClickHouse compressed size: 14.85 MiB
PostgreSQL total size: 102 MB
Сравнение:
102 / 14.85 = 6.87
Вывод: ClickHouse занял примерно в 6.9 раза меньше места, чем PostgreSQL.

3. Какой вывод можно сделать о выборе СУБД для аналитики?
Для аналитики лучше подходит ClickHouse. Он быстрее вставил большой объем данных и 
намного эффективнее сжал таблицу. Это важно для аналитических задач, где нужно хранить много строк, 
быстро читать большие диапазоны данных и выполнять агрегации.

4. Разница ClickHouse и PostgreSQL
ClickHouse — колоночная аналитическая СУБД. Хорошо подходит для логов,
метрик, отчетов, больших таблиц и быстрых запросов по миллионам или миллиардам строк.

PostgreSQL — строковая транзакционная СУБД. Подходит для обычных приложений, 
где важны связи между таблицами, транзакции, точечные
INSERT, UPDATE, DELETE и строгая целостность данных.