# Cassandra

```bash
# Запуск кластера Cassandra из двух нод
docker compose up -d
```
![Screenshot 2026-05 at 10.15.21.png](screenshots/Screenshot%202026-05%20at%2010.15.21.png)
```bash
# Подключение к первой ноде Cassandra
docker exec -it cassandra-node1 cqlsh
```
![Screenshot 2026-05 at 10.15.35.png](screenshots/Screenshot%202026-05%20at%2010.15.35.png)
## Задание 1: Инициализация БД с репликацией

```sql
-- Создание keyspace university с фактором репликации 2
CREATE KEYSPACE university
WITH replication = {
    'class': 'SimpleStrategy',
    'replication_factor': 2
};
```
```sql
-- Выбор keyspace
USE university;
-- Проверка keyspace
DESCRIBE KEYSPACE university;
```
![Screenshot 2026-05 at 10.17.04.png](screenshots/Screenshot%202026-05%20at%2010.17.04.png)

## Задание 2: Создание таблицы и данных
```sql
-- Создание таблицы student_grades
CREATE TABLE student_grades (
                                student_id uuid,
                                created_at timestamp,
                                subject text,
                                grade int,
                                PRIMARY KEY (student_id, created_at)
);
```
![Screenshot 2026-05 at 10.17.36.png](screenshots/Screenshot%202026-05%20at%2010.17.36.png)
```sql
-- Сгенерируем айди стундентов для последующей работы с ними
SELECT uuid() FROM system.local;
SELECT uuid() FROM system.local;
```
![Screenshot 2026-05 at 10.17.47.png](screenshots/Screenshot%202026-05%20at%2010.17.47.png)
```sql
-- Две оценки для первого студента
INSERT INTO student_grades (student_id, created_at, subject, grade)
VALUES (039aadde-b4fa-44ed-ba9b-57db4593a289, '2026-05-01 10:00:00', 'Databases', 95);

INSERT INTO student_grades (student_id, created_at, subject, grade)
VALUES (039aadde-b4fa-44ed-ba9b-57db4593a289, '2026-05-01 11:00:00', 'Algorithms', 88);

-- Две оценки для второго студента
INSERT INTO student_grades (student_id, created_at, subject, grade)
VALUES (b37cbba0-9438-4112-ab45-cde49c3015d7, '2026-05-01 10:30:00', 'Databases', 91);

INSERT INTO student_grades (student_id, created_at, subject, grade)
VALUES (b37cbba0-9438-4112-ab45-cde49c3015d7, '2026-05-01 11:30:00', 'Networks', 84);
-- Проверка данных
SELECT * FROM student_grades;
```
![Screenshot 2026-05 at 10.19.21.png](screenshots/Screenshot%202026-05%20at%2010.19.21.png)


## Задание 3: Проверка распределения данных (Partitioning)
```sql
-- Найти UUID студентов
SELECT student_id FROM student_grades;
```
![Screenshot 2026-05 at 10.18.58.png](screenshots/Screenshot%202026-05%20at%2010.18.58.png)
```bash
# Команды для получения ip нод с данными каждого UUID
docker exec -it cassandra-node1 nodetool getendpoints university student_grades 039aadde-b4fa-44ed-ba9b-57db4593a289
docker exec -it cassandra-node1 nodetool getendpoints university student_grades b37cbba0-9438-4112-ab45-cde49c3015d7
```
![Screenshot 2026-05 at 10.20.33.png](screenshots/Screenshot%202026-05%20at%2010.20.33.png)
Так как у keyspace стоит replication_factor = 2, 
Cassandra хранит данные на двух нодах. 
Поэтому для каждого UUID отображается два endpoint-адреса.

## Задание 4: Работа с фильтрацией

```sql
-- Запрос по неключевому полю
SELECT * FROM student_grades
WHERE subject = 'Databases';
```
![Screenshot 2026-05 at 10.21.00.png](screenshots/Screenshot%202026-05%20at%2010.21.00.png)
Ошибка возникает потому, что subject не входит в ключ таблицы. 
Cassandra не может эффективно искать по этому полю без указания partition key.
```sql
-- Запрос с ALLOW FILTERING
SELECT * FROM student_grades
WHERE subject = 'Databases'
    ALLOW FILTERING;
```
![Screenshot 2026-05 at 10.21.16.png](screenshots/Screenshot%202026-05%20at%2010.21.16.png)
ALLOW FILTERING разрешает Cassandra просканировать данные и отфильтровать 
строки после чтения. В реальных больших таблицах такой запрос может быть очень медленным.

Вывод
В Cassandra данные распределяются по нодам на основе Partition Key. 
В этой таблице partition key — это student_id, поэтому все оценки одного студента хранятся в одной партиции. 
Благодаря replication_factor = 2 каждая партиция хранится на двух нодах.

Cassandra хорошо подходит для распределенного хранения данных и 
быстрых запросов по заранее продуманным ключам. Но она плохо подходит для произвольной фильтрации по 
любым полям, поэтому структуру таблиц нужно проектировать под конкретные запросы.