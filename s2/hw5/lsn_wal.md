## Сравнение LSN до и после INSERT
```sql
-- LSN перед операцией
SELECT
pg_current_wal_lsn() as lsn_before,
pg_walfile_name(pg_current_wal_lsn()) as wal_file_before,
pg_current_wal_insert_lsn() as insert_ptr_before;
```
![Screenshot at 08.09.44.png](screenshots/Screenshot%20at%2008.09.44.png)

```sql
-- ОДНА запись в review
INSERT INTO cinema.review (
user_id, movie_id, rating, comment, review_date, is_spoiler
) VALUES (
1, 1, 5, 'TEST_LSN_single_record', CURRENT_DATE, false
);

-- LSN после операции
SELECT
    pg_current_wal_lsn() as lsn_after,
    pg_walfile_name(pg_current_wal_lsn()) as wal_file_after,
    pg_current_wal_flush_lsn() as flush_ptr_after;
```
![Screenshot at 08.09.55.png](screenshots/Screenshot%20at%2008.09.55.png) 


```sql
-- Вычисляем разницу
WITH lsn_diff AS (
    SELECT
        '0/3120FE10'::pg_lsn as lsn_before,
        '0/3121B168'::pg_lsn as lsn_after
)
SELECT
    lsn_before,
    lsn_after,
    pg_wal_lsn_diff(lsn_after, lsn_before) as diff_bytes,
    pg_size_pretty(pg_wal_lsn_diff(lsn_after, lsn_before)) as diff_pretty,
    CASE
        WHEN pg_walfile_name(lsn_before) = pg_walfile_name(lsn_after)
            THEN 'Same WAL segment'
        ELSE 'WAL segment switched'
        END as segment_status
from lsn_diff;
```
![Screenshot at 08.12.04.png](screenshots/Screenshot%20at%2008.12.04.png)

1: Одиночный INSERT в cinema.review

До INSERT:
• LSN: 0/3120FE10
• WAL файл: 000000010000000000000031

После INSERT (1 запись):
• LSN: 0/3121B168
• WAL файл: 000000010000000000000031

Результат:
• ΔLSN: 45912 байта
• Сегмент WAL: не изменился
## Сравнение WAL до и после commit
```sql
BEGIN;

-- LSN внутри транзакции (до коммита)
SELECT 
    pg_current_wal_lsn() as lsn_before_commit,
    pg_current_wal_flush_lsn() as flush_before_commit,
    txid_current() as transaction_id;
```
![Screenshot at 08.15.25.png](screenshots/Screenshot%20at%2008.15.25.png)

```sql
-- Вставим несколько записей 
INSERT INTO cinema.review (user_id, movie_id, rating, comment)
SELECT 
    1 + (random()*100)::int,
    1 + (random()*100)::int,
    (random()*10)::int + 1,
    'TEST_COMMIT_' || g
FROM generate_series(1, 10) AS g;

COMMIT;

-- Сразу после COMMIT все LSN-метрики
SELECT
    pg_current_wal_lsn() as lsn_after_commit,
    pg_current_wal_insert_lsn() as insert_after,
    pg_current_wal_flush_lsn() as flush_after,
    pg_last_wal_replay_lsn() as replay_after;
```
![Screenshot at 08.17.42.png](screenshots/Screenshot%20at%2008.17.42.png)

```sql
-- Рассчитаем изменения
WITH commit_analysis AS (
    SELECT 
        '0/3122BA88'::pg_lsn as lsn_before,  -- до COMMIT
        '0/31248660'::pg_lsn as lsn_after,   -- после COMMIT
        10 as rows_in_transaction
)
SELECT 
    lsn_before,
    lsn_after,
    pg_wal_lsn_diff(lsn_after, lsn_before) as total_wal_bytes,
    ROUND(pg_wal_lsn_diff(lsn_after, lsn_before)::numeric / 10, 2) as avg_bytes_per_row,
    pg_size_pretty(pg_wal_lsn_diff(lsn_after, lsn_before)) as total_pretty
from commit_analysis;
```
![Screenshot  at 08.18.30.png](screenshots/Screenshot%20%20at%2008.18.30.png)

2: Влияние COMMIT на WAL (10 записей в review)

До COMMIT (внутри транзакции):
• LSN: 0/3122BA88
• Flush LSN: 0/3122BA88

После COMMIT:
• LSN: 0/31248660
• Flush LSN: 0/31248660 (данные гарантированно на диске)
• Все LSN совпадают → синхронная запись выполнена

Вывод:
• После COMMIT: flush_lsn = current_lsn → данные безопасно на диске

## Размер WAL после массового INSERT
```sql
-- Количество и размер WAL-файлов до операции
SELECT 
    COUNT(*) as wal_files_count,
    ROUND(SUM(size)::numeric / 1024 / 1024, 2) as total_size_mb,
    pg_size_pretty(SUM(size)) as total_size_pretty
FROM pg_ls_waldir()
WHERE name ~ '^[0-9A-F]{24}$';  
```
![Screenshot at 08.26.26.png](screenshots/Screenshot%20at%2008.26.26.png)

```sql
-- Текущий LSN и сегмент
SELECT 
    pg_current_wal_lsn() as lsn_end,
    pg_walfile_name(pg_current_wal_lsn()) as wal_segment_end,
    pg_current_wal_flush_lsn() as flush_lsn_end;
```
![Screenshot at 08.26.35.png](screenshots/Screenshot%20at%2008.26.35.png)


```sql
-- Массовая вставка: 1000 записей в review
```


```sql
-- Количество и размер WAL-файлов после
SELECT
    COUNT(*) as wal_files_count,
    ROUND(SUM(size)::numeric / 1024 / 1024, 2) as total_size_mb,
    pg_size_pretty(SUM(size)) as total_size_pretty
FROM pg_ls_waldir()
WHERE name ~ '^[0-9A-F]{24}$';  
```

```sql
-- Текущий LSN и сегмент
SELECT 
    pg_current_wal_lsn() as lsn_end,
    pg_walfile_name(pg_current_wal_lsn()) as wal_segment_end,
    pg_current_wal_flush_lsn() as flush_lsn_end;
```
![Screenshot at 08.32.25.png](screenshots/Screenshot%20at%2008.32.25.png)


```sql
-- Сводный расчёт 
WITH bulk_analysis AS (
    SELECT 
        1000 as rows_inserted,
        4 as wal_files_before,
        6 as wal_files_after,
        64.00 as size_mb_before,
        96.00 as size_mb_after,
        '0/312526A0'::pg_lsn as lsn_start,
        '0/32A833D0'::pg_lsn as lsn_end
)
SELECT 
    rows_inserted,
    wal_files_after - wal_files_before as new_wal_files,
    ROUND(size_mb_after - size_mb_before, 2) as wal_growth_mb,
    pg_wal_lsn_diff(lsn_end, lsn_start) as lsn_diff_bytes,
    pg_size_pretty(pg_wal_lsn_diff(lsn_end, lsn_start)) as lsn_diff_pretty,
    ROUND(
        pg_wal_lsn_diff(lsn_end, lsn_start)::numeric / rows_inserted, 
        2
    ) as avg_bytes_per_row,
    CASE 
        WHEN pg_walfile_name(lsn_start) != pg_walfile_name(lsn_end)
        THEN 'WAL segment switched'
        ELSE 'Same segment'
    END as segment_status from bulk_analysis;
```
![Screenshot at 08.33.51.png](screenshots/Screenshot%20at%2008.33.51.png)

3: Массовый INSERT (1000 записей) в cinema.review

До операции:
• WAL файлов: 10
• Общий размер: 160 MB
• LSN: 0/312526A0
• Сегмент: 000000010000000000000031

После операции (1000 INSERT):
• WAL файлов: 9 (+2 новых)
• Общий размер: 144 MB
• LSN: 0/32A833D0
• Сегмент: 000000010000000000000032

Вывод:
• Количество файлов уменьшилось с 10 до 9 → сработала автоматическая очистка
• При достижении 16 MB создаётся новый WAL-сегмент

