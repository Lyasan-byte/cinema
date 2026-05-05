# Redis

```bash
# Запуск Redis в Docker
docker compose up -d
```
![Screenshot 2026-04-12 at 18.49.35.png](screenshots/Screenshot%202026-04-12%20at%2018.49.35.png)
```bash
# Подключение к redis-cli
docker exec -it redis redis-cli
```

## Задание 1. Hash — данные о студентах

```bash
# Создаем студента 1
HSET student:1 name "Alex" group "CS-101" gpa "4.5"

# Создаем студента 2
HSET student:2 name "Maria" group "CS-102" gpa "4.8"

# Создаем студента 3
HSET student:3 name "John" group "CS-103" gpa "4.2"
```
![Screenshot 2026-04-12 at 18.52.38.png](screenshots/Screenshot%202026-04-12%20at%2018.52.38.png)
```bash
# Проверяем, что данные записались
HGETALL student:1
HGETALL student:2
HGETALL student:3
```
![Screenshot 2026-04-12 at 18.52.48.png](screenshots/Screenshot%202026-04-12%20at%2018.52.48.png)
## Задание 2. Sorted Set — лидерборд по GPA

```bash
# Создаем рейтинг студентов по GPA
ZADD students:gpa 4.5 "Alex" 4.8 "Maria" 4.2 "John"

# Выводим топ-3 по убыванию GPA
ZREVRANGE students:gpa 0 2 WITHSCORES
```
![Screenshot 2026-04-12 at 18.53.22.png](screenshots/Screenshot%202026-04-12%20at%2018.53.22.png)
## Задание 3. List — очередь задач
```bash
# Добавляем 5 задач в очередь
RPUSH tasks "Task 1" "Task 2" "Task 3" "Task 4" "Task 5"

# Проверяем очередь
LRANGE tasks 0 -1
```
![Screenshot 2026-04-12 at 18.54.10.png](screenshots/Screenshot%202026-04-12%20at%2018.54.10.png)

```bash
# Забираем 3 задачи из очереди по принципу FIFO
LPOP tasks
LPOP tasks
LPOP tasks
# Смотрим, что осталось в очереди
LRANGE tasks 0 -1
```
![Screenshot 2026-04-12 at 18.54.15.png](screenshots/Screenshot%202026-04-12%20at%2018.54.15.png)

## Задание 4. TTL — время жизни ключа

```bash
# Создаем ключ с TTL 10 секунд
SET temp:key "temporary value" EX 10

# Сразу проверяем оставшееся время жизни
TTL temp:key

# Получаем значение ключа
GET temp:key
```
![Screenshot 2026-04-12 at 18.55.16.png](screenshots/Screenshot%202026-04-12%20at%2018.55.16.png)
```bash
# Через 10 секунд cнова проверяем TTL
TTL temp:key

# Пробуем получить значение после истечения времени
GET temp:key
```
![Screenshot 2026-04-12 at 18.55.21.png](screenshots/Screenshot%202026-04-12%20at%2018.55.21.png)
## Задание 5. Транзакция MULTI/EXEC

```bash
# Сначала проверим текущие GPA
HGET student:1 gpa
HGET student:2 gpa
```
![Screenshot 2026-04-12 at 18.56.08.png](screenshots/Screenshot%202026-04-12%20at%2018.56.08.png)
```bash
# Начинаем транзакцию
MULTI

# Уменьшаем GPA студента 1 на 1
HINCRBYFLOAT student:1 gpa -1

# Увеличиваем GPA студента 2 на 1
HINCRBYFLOAT student:2 gpa 1

# Выполняем транзакцию
EXEC
```
![Screenshot 2026-04-12 at 18.56.14.png](screenshots/Screenshot%202026-04-12%20at%2018.56.14.png)
```bash
# Проверяем результат после транзакции
HGET student:1 gpa
HGET student:2 gpa
```
![Screenshot 2026-04-12 at 18.56.19.png](screenshots/Screenshot%202026-04-12%20at%2018.56.19.png)