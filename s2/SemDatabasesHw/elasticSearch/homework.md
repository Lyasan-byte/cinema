# ElasticSearch
```bash
# Запуск Elasticsearch в Docker
docker compose up -d
```
![Screenshot 2026-04-12 at 16.56.47.png](screenshots/Screenshot%202026-04-12%20at%2016.56.47.png)

```bash
# Проверка, что Elasticsearch запустился
curl http://localhost:9200
```
![Screenshot 2026-04-12 at 16.59.00.png](screenshots/Screenshot%202026-04-12%20at%2016.59.00.png)
```bash
# Создание индекса books
curl -X PUT "localhost:9200/books" \
  -H "Content-Type: application/json" \
  -d '{
    "mappings": {
      "properties": {
        "title": { "type": "text" },
        "author": { "type": "keyword" },
        "genre": { "type": "keyword" },
        "year": { "type": "integer" },
        "price": { "type": "float" },
        "in_stock": { "type": "boolean" }
      }
    }
  }'
```
![Screenshot 2026-04-12 at 16.59.21.png](screenshots/Screenshot%202026-04-12%20at%2016.59.21.png)
```bash
# Заполнение индекса данными
curl -X POST "localhost:9200/books/_bulk" \
  -H "Content-Type: application/json" \
  --data-binary '
{ "index": { "_id": 1 } }
{ "title": "MongoDB Basics", "author": "Ivan Petrov", "genre": "database", "year": 2022, "price": 25.5, "in_stock": true }
{ "index": { "_id": 2 } }
{ "title": "Elasticsearch Guide", "author": "Anna Smirnova", "genre": "search", "year": 2023, "price": 30.0, "in_stock": true }
{ "index": { "_id": 3 } }
{ "title": "Docker for Beginners", "author": "Ivan Petrov", "genre": "devops", "year": 2021, "price": 18.9, "in_stock": false }
{ "index": { "_id": 4 } }
{ "title": "Advanced Search Systems", "author": "Maria Volkova", "genre": "search", "year": 2024, "price": 42.0, "in_stock": true }
'
```
![Screenshot 2026-04-12 at 17.01.00.png](screenshots/Screenshot%202026-04-12%20at%2017.01.00.png)
```bash
# Обновить индекс после bulk-загрузки, чтобы документы сразу были видны в поиске
curl -X POST "localhost:9200/books/_refresh"
```
![Screenshot 2026-04-12 at 17.01.27.png](screenshots/Screenshot%202026-04-12%20at%2017.01.27.png)

## Запросы
```bash
# Запрос 1
# Поиск по названию книги
curl -X GET "localhost:9200/books/_search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "match": {
        "title": "Elasticsearch"
      }
    }
  }'

```
![Screenshot 2026-04-12 at 17.01.48.png](screenshots/Screenshot%202026-04-12%20at%2017.01.48.png)
```bash
# Запрос 2
# Фильтр по точному значению genre через term
curl -X GET "localhost:9200/books/_search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "term": {
        "genre": "search"
      }
    }
  }'

```
![Screenshot 2026-04-12 at 17.01.48.png](screenshots/Screenshot%202026-04-12%20at%2017.01.48.png)
```bash
# Запрос 3
# Поиск книг по диапазону цены через range
curl -X GET "localhost:9200/books/_search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "range": {
        "price": {
          "gte": 20,
          "lte": 35
        }
      }
    }
  }'
```
![Screenshot 2026-04-12 at 17.03.21.png](screenshots/Screenshot%202026-04-12%20at%2017.03.21.png)

```bash
# Запрос 4
# Сложный запрос через bool:
# книга должна быть по теме search,
# должна быть в наличии,
# и год выпуска должен быть не меньше 2023
curl -X GET "localhost:9200/books/_search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "bool": {
        "must": [
          { "match": { "title": "search" } }
        ],
        "filter": [
          { "term": { "in_stock": true } },
          { "range": { "year": { "gte": 2023 } } }
        ]
      }
    }
  }'
```
![Screenshot 2026-04-12 at 17.03.54.png](screenshots/Screenshot%202026-04-12%20at%2017.03.54.png)