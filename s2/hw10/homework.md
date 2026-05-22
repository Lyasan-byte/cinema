# Airflow

## 1. ETL-сценарий

ИСТОЧНИКИ ДАННЫХ

1) CSV-файл отвечает за справочные данные: фильмы, режиссеры, жанры.
```text
movies_external.csv содержит дополнительные фильмы.

Этот файл будет пополнять таблицы проекта:

cinema.director
cinema.genre
cinema.movie
cinema.movie_genre
```

2) JSON-файл

```text
user_events_external.json содержит события пользователей.

В нем есть события типов:

VIEWING   — просмотр
RENTAL    — аренда
PURCHASE  — покупка
REVIEW    — отзыв

Этот файл будет пополнять таблицы проекта:

cinema.users
cinema.viewing
cinema.rental
cinema.purchase
cinema.review

Событие из JSON ссылается на фильм, который был загружен из CSV.
```


```bash
# Инициализация Airflow (Создается служебная база Airflow.
#    Выполняется миграция метаданных Airflow.
#    Создается пользователь для входа в Airflow UI:
#    логин airflow
#    пароль airflow
# )
docker compose up airflow-init
```
![Screenshot 2026-05-20 at 11.40.24.png](screenshots/Screenshot%202026-05-20%20at%2011.40.24.png)

```bash
# Запуск всех контейнеров
docker compose up -d
```
![Screenshot 2026-05-20 at 11.41.04.png](screenshots/Screenshot%202026-05-20%20at%2011.41.04.png)
Docker Compose поднимает несколько сервисов: PostgreSQL основного проекта,
ClickHouse для аналитики, отдельную PostgreSQL-БД для метаданных Airflow,
webserver Airflow и scheduler Airflow.

http://localhost:8080 
![Screenshot 2026-05-20 at 11.42.38.png](screenshots/Screenshot%202026-05-20%20at%2011.42.38.png)
![Screenshot 2026-05-20 at 11.43.13.png](screenshots/Screenshot%202026-05-20%20at%2011.43.13.png)
### DAG1

В DAG 1 задачи идут так:

```text
create_metadata_tables
↓
load_movies_from_csv
↓
load_events_from_json
↓
quality_checks_postgres
```
![Screenshot 2026-05-20 at 11.45.19.png](screenshots/Screenshot%202026-05-20%20at%2011.45.19.png)
![Screenshot 2026-05-20 at 11.46.14.png](screenshots/Screenshot%202026-05-20%20at%2011.46.14.png)

DAG 1 реализует ETL-сценарий.
Сначала создаются служебные mapping-таблицы для идемпотентности.
Затем Airflow читает CSV-файл с фильмами, режиссерами и жанрами и загружает эти данные в PostgreSQL.
После этого Airflow читает JSON-файл с пользовательскими событиями и загружает
просмотры, аренды, покупки и отзывы в соответствующие таблицы проекта.
В конце выполняются проверки качества данных.


Проверка PostgreSQL после DAG 1
```bash
docker exec -it cinema-db psql -U admin -d cinema_db
```
![Screenshot 2026-05-20 at 11.47.28.png](screenshots/Screenshot%202026-05-20%20at%2011.47.28.png)
```sql
-- Проверка служебных таблиц ETL:
SELECT COUNT(*) FROM etl.external_movie_map;
SELECT COUNT(*) FROM etl.external_event_map;
```
![Screenshot 2026-05-20 at 11.47.45.png](screenshots/Screenshot%202026-05-20%20at%2011.47.45.png)
```sql
-- Проверка таблиц проекта(смотрим загруженные фильмы)
SELECT
    emm.external_movie_id,
    m.movie_id,
    m.title
FROM etl.external_movie_map emm
         JOIN cinema.movie m
              ON m.movie_id = emm.movie_id
ORDER BY emm.external_movie_id
    LIMIT 20;
```
![Screenshot 2026-05-20 at 11.49.53.png](screenshots/Screenshot%202026-05-20%20at%2011.49.53.png)
После выполнения DAG 1 в PostgreSQL появились данные из внешних источников. 

### DAG2
![Screenshot 2026-05-20 at 13.19.12.png](screenshots/Screenshot%202026-05-20%20at%2013.19.12.png)

```bash
# Проверить ClickHouse после DAG 2
docker exec -it cinema-clickhouse clickhouse-client
```
![Screenshot 2026-05-20 at 13.19.12.png](screenshots/Screenshot%202026-05-20%20at%2013.19.12.png)
```sql
SHOW DATABASES;
```
![Screenshot 2026-05-20 at 13.19.32.png](screenshots/Screenshot%202026-05-20%20at%2013.19.32.png)
```sql
-- Проверка таблиц
SHOW TABLES FROM cinema_dw;
```
![Screenshot 2026-05-20 at 13.19.45.png](screenshots/Screenshot%202026-05-20%20at%2013.19.45.png)
```sql
-- Проверка количества строк
SELECT count()
FROM cinema_dw.dim_movies;

SELECT count()
FROM cinema_dw.fact_movie_events;

SELECT count()
FROM cinema_dw.mart_daily_activity;
```
![Screenshot 2026-05-20 at 13.20.27.png](screenshots/Screenshot%202026-05-20%20at%2013.20.27.png)
```sql
-- Витрина данных
SELECT *
FROM cinema_dw.mart_daily_activity
ORDER BY event_date, action_type, primary_genre_name
    LIMIT 30;
```
![Screenshot 2026-05-20 at 13.21.06.png](screenshots/Screenshot%202026-05-20%20at%2013.21.06.png)

# ОТЧЕТ

### 1. Какие источники данных выбраны

Первый источник — CSV-файл movies_external.csv.
Он содержит дополнительные фильмы, режиссеров и жанры.

Второй источник — JSON-файл user_events_external.json.
Он содержит пользовательские события: просмотры, аренды, покупки и отзывы.

CSV и JSON связаны между собой через поле external_movie_id.
Это позволяет событиям из JSON ссылаться на фильмы, которые были загружены из CSV.

### 2. Какие таблицы проекта пополняются

CSV-файл пополняет таблицы основной PostgreSQL-БД проекта:

cinema.director — режиссеры;
cinema.genre — жанры;
cinema.movie — фильмы;
cinema.movie_genre — связь фильмов и жанров.

JSON-файл пополняет таблицы:

cinema.users — пользователи;
cinema.viewing — просмотры;
cinema.rental — аренды;
cinema.purchase — покупки;
cinema.review — отзывы.

### 3. Как устроен DAG 1

Задачи DAG 1:

1. create_metadata_tables
   Создает служебные таблицы etl.external_movie_map и etl.external_event_map.
   Они нужны для идемпотентности.

2. load_movies_from_csv
   Читает CSV-файл movies_external.csv.
   Из него загружаются режиссеры, жанры, фильмы и связи фильмов с жанрами.

3. load_events_from_json
   Читает JSON-файл user_events_external.json.
   Из него загружаются пользователи и пользовательские события: просмотры, аренды, покупки и отзывы.

4. quality_checks_postgres
   Проверяет, что фильмы и события действительно были загружены.

### 4. Как устроен DAG 2

Задачи DAG 2:

1. create_clickhouse_tables
   Создает базу cinema_dw и таблицы в ClickHouse.

2. reload_clickhouse_from_postgres
   Очищает ClickHouse-таблицы и заново загружает данные из PostgreSQL.

3. build_daily_activity_mart
   Строит аналитическую витрину mart_daily_activity.

4. quality_checks_clickhouse
   Проверяет, что количество событий в PostgreSQL и ClickHouse совпадает, а витрина не пустая.

### 5. Какие таблицы создаются в ClickHouse

1. cinema_dw.dim_movies
   Измерение фильмов.
   Содержит информацию о фильмах, режиссерах, основном жанре и списке всех жанров.

2. cinema_dw.fact_movie_events
   Таблица фактов пользовательских событий.
   В нее объединяются просмотры, аренды, покупки и отзывы.

3. cinema_dw.mart_daily_activity
   Аналитическая витрина активности пользователей.

### 6. Какая аналитическая витрина построена

1 строка = один день + один тип действия + один основной жанр фильма.

Витрина позволяет анализировать активность пользователей по дням, типам действий и жанрам.

### 7. Какие метрики считаются

events_count — количество событий;
unique_users — количество уникальных пользователей;
movies_count — количество уникальных фильмов;
revenue — выручка от аренд и покупок;
avg_rating — средняя оценка по отзывам.

### 8. Как обеспечена идемпотентность

В DAG 1 идемпотентность обеспечена служебными mapping-таблицами:

etl.external_movie_map;
etl.external_event_map.

Они хранят соответствие между внешними id из CSV/JSON и внутренними id в базе проекта.

Если DAG 1 запустить повторно, уже загруженные фильмы и события не будут созданы повторно.

В DAG 2 идемпотентность обеспечена полной перезагрузкой ClickHouse-таблиц.
Перед загрузкой выполняется TRUNCATE TABLE, после чего данные заново загружаются из PostgreSQL.

Поэтому повторный запуск DAG 2 приводит ClickHouse к одному и тому же состоянию.

### 9. Какие проверки качества данных реализованы

В DAG 1 реализованы следующие проверки качества данных:

CSV содержит обязательные колонки;
CSV не пустой;
external_movie_id не пустой;
title не пустой;
release_year находится в корректном диапазоне;
duration больше 0;
price_min и price_max корректные;
JSON является массивом событий;
event_type входит в допустимый список: VIEWING, RENTAL, PURCHASE, REVIEW;
progress находится от 0 до 100;
rating находится от 1 до 5;
для каждого события из JSON найден фильм из CSV.

В DAG 2 реализованы проверки:

количество событий в PostgreSQL совпадает с количеством событий в ClickHouse;
аналитическая витрина mart_daily_activity не пустая.


### 10. Как запустить проект

1. Склонировать проект
2. Запустить PostgreSQL-контейнер командой docker compose up -d db.
3. Создать OLTP-схему cinema и таблицы проекта.
4. Выполнить docker compose config.
5. Выполнить docker compose up airflow-init.
6. Выполнить docker compose up -d.
7. Открыть Airflow UI по адресу http://localhost:8080.
8. Войти под airflow / airflow.
9. Запустить dag1_etl_csv_json_to_postgres.
10. После успешного выполнения DAG 1 запустить dag2_postgres_to_clickhouse.
11. Проверить данные в PostgreSQL и ClickHouse.

