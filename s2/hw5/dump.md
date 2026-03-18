## Dump только структуры базы

**Шаг 1: Создать папку для бэкапов**

```bash
mkdir -p ~/cinema-backups
```

**Шаг 2: Создать дамп внутри контейнера**

```bash
docker exec cinema-db pg_dump -U admin -d cinema_db \
  --schema-only \
  --format=plain \
  -f /tmp/cinema_schema.sql
```

**Шаг 3: Скопировать файл на Mac**

```bash
docker cp cinema-db:/tmp/cinema_schema.sql ~/cinema-backups/cinema_schema.sql
```bash
```
![Screenshot at 09.08.10.png](screenshots/Screenshot%20at%2009.08.10.png)

**Шаг 4: Проверить что файл создан**

```bash
ls -lh ~/cinema-backups/cinema_schema.sql
```
![Screenshot at 08.59.42.png](screenshots/Screenshot%20at%2008.59.42.png)

**Шаг 5: Создать новую базу для восстановления**
```bash
docker exec cinema-db psql -U admin -d postgres -c "CREATE DATABASE cinema_schema_only;"
```
![Screenshot at 08.59.48.png](screenshots/Screenshot%20at%2008.59.48.png)

**Шаг 6: Скопировать файл обратно в контейнер**
```bash
docker cp ~/cinema-backups/cinema_schema.sql cinema-db:/tmp/cinema_schema.sql
```
![Screenshot at 08.59.53.png](screenshots/Screenshot%20at%2008.59.53.png)

**Шаг 7: Восстановить структуру в новую базу**
```bash
docker exec cinema-db psql -U admin -d cinema_schema_only -f /tmp/cinema_schema.sql
```


**Шаг 8: Проверить что данных нет (только структура)**
```bash
docker exec cinema-db psql -U admin -d cinema_schema_only -c "
SELECT
'users' as table_name, COUNT(*) as rows FROM cinema.users
UNION ALL
SELECT 'movie', COUNT(*) FROM cinema.movie
UNION ALL
SELECT 'review', COUNT(*) FROM cinema.review;
"
```
![Screenshot at 09.00.23.png](screenshots/Screenshot%20at%2009.00.23.png)

## Dump одной таблицы


**Шаг 1: Создать дамп полной таблицы (структура + данные)**
```bash
# Внутри контейнера
docker exec cinema-db pg_dump -U admin -d cinema_db \
--table=review \
--format=custom \
-f /tmp/cinema_review_table.dump

# Скопировать на Mac
docker cp cinema-db:/tmp/cinema_review_table.dump ~/cinema-backups/cinema_review_table.dump
```

**Шаг 2: Создать дамп только структуры таблицы**
```bash
# Внутри контейнера
docker exec cinema-db pg_dump -U admin -d cinema_db \
--table=review \
--schema-only \
--format=plain \
-f /tmp/cinema_review_schema.sql

# Скопировать на Mac
docker cp cinema-db:/tmp/cinema_review_schema.sql ~/cinema-backups/cinema_review_schema.sql
```

**Шаг 3: Создать дамп только данных таблицы**
```bash
# Внутри контейнера
docker exec cinema-db pg_dump -U admin -d cinema_db \
--table=review \
--data-only \
--format=plain \
-f /tmp/cinema_review_data.sql

# Скопировать на Mac
docker cp cinema-db:/tmp/cinema_review_data.sql ~/cinema-backups/cinema_review_data.sql
```
**Шаг 4: Проверить все файлы**
```bash
ls -lh ~/cinema-backups/
```
![Screenshot at 09.31.13.png](screenshots/Screenshot%20at%2009.31.13.png)

**Шаг 5: Создать новую базу для таблицы**
```bash
docker exec cinema-db psql -U admin -d postgres -c "CREATE DATABASE cinema_review_only;"
```

**Шаг 6: Восстановить таблицу в новую базу**
```bash
# Скопировать файл в контейнер
docker cp ~/cinema-backups/cinema_review_table.dump cinema-db:/tmp/cinema_review_table.dump

# Восстановить
docker exec cinema-db pg_restore -U admin -d cinema_review_only /tmp/cinema_review_table.dump
```
**Шаг 7: Проверить восстановление**
```bash
docker exec cinema-db psql -U admin -d cinema_review_only -c "
SELECT
COUNT(*) as review_count,
MIN(rating) as min_rating,
MAX(rating) as max_rating
FROM cinema.review;
"
```
![Screenshot at 09.33.27.png](screenshots/Screenshot%20at%2009.33.27.png)