# Neo4j

```bash
# Запуск Neo4j в Docker
docker compose up -d
```
![Screenshot 2026-04-12 at 17.17.56.png](screenshots/Screenshot%202026-04-12%20at%2017.17.56.png)

```bash
# Открыть Neo4j Browser
# В браузере перейти по адресу:
http://localhost:7474
```
![Screenshot 2026-04-12 at 17.29.34.png](screenshots/Screenshot%202026-04-12%20at%2017.29.34.png)
```sql
--Создание пользователей
CREATE (alex:User {name: "Alex"}),
       (maria:User {name: "Maria"}),
       (john:User {name: "John"})
```
![Screenshot 2026-04-12 at 17.31.05.png](screenshots/Screenshot%202026-04-12%20at%2017.31.05.png)
```sql
--Создание фильмов
CREATE (inception:Movie {title: "Inception"}),
       (matrix:Movie {title: "The Matrix"})
```
![Screenshot 2026-04-12 at 17.31.20.png](screenshots/Screenshot%202026-04-12%20at%2017.31.20.png)
```sql
--Создание связи friendship между Alex и Maria
MATCH (a:User {name: "Alex"}), (m:User {name: "Maria"})
CREATE (a)-[:FRIENDS]->(m)
```
![Screenshot 2026-04-12 at 17.31.50.png](screenshots/Screenshot%202026-04-12%20at%2017.31.50.png)
```sql
--Создание связи WATCHED между Alex и фильмом Inception
MATCH (a:User {name: "Alex"}), (i:Movie {title: "Inception"})
CREATE (a)-[:WATCHED {rating: 5}]->(i)
```
![Screenshot 2026-04-12 at 17.32.07.png](screenshots/Screenshot%202026-04-12%20at%2017.32.07.png)
```sql
--Добавим еще один просмотренный фильм другом Алекса:
--Maria посмотрела The Matrix
MATCH (m:User {name: "Maria"}), (film:Movie {title: "The Matrix"})
CREATE (m)-[:WATCHED {rating: 4}]->(film)
```
![Screenshot 2026-04-12 at 17.32.24.png](screenshots/Screenshot%202026-04-12%20at%2017.32.24.png)
## Запросы
### Cypher
```sql
--Найти всех друзей Алекса
MATCH (:User {name: "Alex"})-[:FRIENDS]->(friend:User)
RETURN friend
```
![Screenshot 2026-04-12 at 17.32.48.png](screenshots/Screenshot%202026-04-12%20at%2017.32.48.png)

```sql
--Найти фильмы, которые смотрели друзья Алекса, но не смотрел сам Алекс
MATCH (:User {name: "Alex"})-[:FRIENDS]->(friend:User)-[:WATCHED]->(movie:Movie)
WHERE NOT EXISTS {
  MATCH (:User {name: "Alex"})-[:WATCHED]->(movie)
}
RETURN movie.title
```
![Screenshot 2026-04-12 at 17.33.07.png](screenshots/Screenshot%202026-04-12%20at%2017.33.07.png)
### SQL
```sql
--Пример SQL-запроса для поиска друзей Алекса:
SELECT u2.name
FROM users u1
JOIN friends f ON u1.id = f.user_id
JOIN users u2 ON f.friend_id = u2.id
WHERE u1.name = 'Alex';
```

```sql
SELECT DISTINCT m.title
FROM users alex
JOIN friends f ON alex.id = f.user_id
JOIN users friend ON f.friend_id = friend.id
JOIN watched w1 ON friend.id = w1.user_id
JOIN movies m ON w1.movie_id = m.id
WHERE alex.name = 'Alex'
AND NOT EXISTS (
  SELECT 1
  FROM watched w2
  WHERE w2.user_id = alex.id
    AND w2.movie_id = m.id
);
```

Сравнение сложности запросов
В Neo4j такие запросы писать проще, потому что связи между объектами уже являются частью модели данных.
В SQL нужно явно соединять таблицы через JOIN, поэтому запрос получается длиннее и сложнее для чтения.
Для графовых задач, где много связей “пользователь-друг-фильм”, Cypher обычно нагляднее.
Для табличных данных и обычной бизнес-логики SQL чаще привычнее и универсальнее.
