## Добавление тестовых данных 

Файл 1: ~/cinema-seeds/01_genres.sql
```sql
-- Жанры фильмов (идемпотентный)
INSERT INTO cinema.genre (name, description)
VALUES
('Action', 'Exciting sequences'),
('Comedy', 'Humorous content'),
('Drama', 'Serious narrative'),
('Horror', 'Frightening content'),
('Sci-Fi', 'Futuristic concepts')
ON CONFLICT (name) DO NOTHING;
```
Запустить Seed (Проверка Идемпотентности)
```bash
docker exec -i cinema-db psql -U admin -d cinema_db < ~/cinema-seeds/01_genres.sql
```
### Два запуска дают одиннаковый результат(идемпотентность)
![Screenshot at 10.08.56.png](screenshots/Screenshot%20at%2010.08.56.png)


Файл 2: ~/cinema-seeds/02_users.sql
```sql
-- Тестовые пользователи (идемпотентный по email)
INSERT INTO cinema.users (name, email, password_hash, subscription_status)
VALUES
('Test User 1', 'test1@seed.com', 'hash123', 'active'),
('Test User 2', 'test2@seed.com', 'hash123', 'active'),
('Test User 3', 'test3@seed.com', 'hash123', 'trial')
ON CONFLICT (email) DO NOTHING;
```
Запустить Seed (Проверка Идемпотентности)
```bash
docker exec -i cinema-db psql -U admin -d cinema_db < ~/cinema-seeds/02_users.sql
```
### Два запуска дают одиннаковый результат(идемпотентность)
![Screenshot at 10.08.46.png](screenshots/Screenshot%20at%2010.08.46.png)

Файл 3: ~/cinema-seeds/03_reviews.sql
```sql
-- Отзывы (идемпотентный по user_id + movie_id)
INSERT INTO cinema.review (user_id, movie_id, rating, comment)
VALUES
(1, 1, 5, 'Seed review 1'),
(2, 2, 4, 'Seed review 2'),
(3, 3, 5, 'Seed review 3')
ON CONFLICT (user_id, movie_id) DO NOTHING;
```

Запустить Seed (Проверка Идемпотентности)
```bash
docker exec -i cinema-db psql -U admin -d cinema_db < ~/cinema-seeds/03_reviews.sql
```
### Два запуска дают одиннаковый результат(идемпотентность)
![Screenshot at 10.09.36.png](screenshots/Screenshot%20at%2010.09.36.png)



