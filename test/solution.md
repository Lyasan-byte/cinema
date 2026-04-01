## Задание 1. Оптимизация простого запроса
```sql
--План до изменений
EXPLAIN (ANALYZE, BUFFERS)

        SELECT id, user_id, amount, created_at
FROM exam_events
WHERE user_id = 4242
AND created_at >= TIMESTAMP '2025-03-10 00:00:00'
AND created_at < TIMESTAMP '2025-03-11 00:00:00';
```
![Screenshot 2026-04-01 at 09.17.24.png](screenshots/Screenshot%202026-04-01%20at%2009.17.24.png)

CREATE INDEX idx_exam_events_user_id_created_at
ON exam_events (user_id, created_at);

![Screenshot 2026-04-01 at 09.18.35.png](screenshots/Screenshot%202026-04-01%20at%2009.18.35.png)

До создания нового индекса используется Seq Scan, потому что в таблице нет индекса по user_id и created_at, а существующие индексы по status и amount к этому условию не подходят.
Хеш-индекс idx_exam_events_amount_hash не помогает, потому что фильтра по amount нет.
После создания индекса (user_id, created_at) план улучшается
Нужно ли делать ANALYZE после создания индекса?
Не обязательно. Планировщик начинает видеть индекс сразу после CREATE INDEX, а статистика по распределению значений столбцов у него уже есть после выполненного ранее ANALYZE.

## Задание 2. Анализ и улучшение JOIN-запроса


```sql
--План до изменений
EXPLAIN (ANALYZE, BUFFERS)
SELECT u.id, u.country, o.amount, o.created_at
FROM exam_users u
         JOIN exam_orders o ON o.user_id = u.id
WHERE u.country = 'JP'
  AND o.created_at >= TIMESTAMP '2025-03-01 00:00:00'
  AND o.created_at < TIMESTAMP '2025-03-08 00:00:00';
```
![Screenshot 2026-04-01 at 09.21.46.png](screenshots/Screenshot%202026-04-01%20at%2009.21.46.png)

Улучшение

CREATE INDEX idx_exam_orders_created_at_user_id
ON exam_orders (created_at, user_id);

```sql
--План до изменений
EXPLAIN (ANALYZE, BUFFERS)
SELECT u.id, u.country, o.amount, o.created_at
FROM exam_users u
         JOIN exam_orders o ON o.user_id = u.id
WHERE u.country = 'JP'
  AND o.created_at >= TIMESTAMP '2025-03-01 00:00:00'
  AND o.created_at < TIMESTAMP '2025-03-08 00:00:00';
```

![Screenshot 2026-04-01 at 09.22.59.png](screenshots/Screenshot%202026-04-01%20at%2009.22.59.png)

До изменений планировщик выбирает Hash Join из за равенства по ключу o.user_id = u.id, а после фильтрации по стране и диапазону дат остаются средние по размеру наборы строк.

Существующий индекс idx_exam_orders_created_at полезен частично: он помогает отфильтровать заказы по диапазону дат, но не учитывает ключ соединения user_id. Индекс idx_exam_users_name для этого запроса практически бесполезен, потому что фильтрация идет по country, а не по name.

После создания индекса (created_at, user_id) план улучшается за счет более удобного доступа к exam_orders. Но в результате cost запроса не изменился.

Что означает преобладание shared hit или shared read в BUFFERS?
Если преобладает shared hit, значит нужные страницы уже были в shared buffers PostgreSQL, и запрос в основном работал из памяти. Если преобладает shared read, значит страниц пришлось больше читать с диска, и запрос тратил больше времени на I/O.

## Задание 3. MVCC и очистка
```sql
SELECT xmin, xmax, ctid, id, title, qty
FROM exam_mvcc_items
ORDER BY id;

UPDATE exam_mvcc_items
SET qty = qty + 5
WHERE id = 1;

SELECT xmin, xmax, ctid, id, title, qty
FROM exam_mvcc_items
ORDER BY id;

DELETE FROM exam_mvcc_items
WHERE id = 2;

SELECT xmin, xmax, ctid, id, title, qty
FROM exam_mvcc_items
ORDER BY id;
```
![Screenshot 2026-04-01 at 09.29.14.png](screenshots/Screenshot%202026-04-01%20at%2009.29.14.png)

![Screenshot 2026-04-01 at 09.29.53.png](screenshots/Screenshot%202026-04-01%20at%2009.29.53.png)

Что было до изменений
У всех строк одинаковый xmin = 751, то есть они были созданы одной транзакцией.
xmax = 0 означает что актуальны 
ctid показывает физическое расположение версии строки в таблице.
Что изменилось после UPDATE
Для строки id = 1:

qty изменилось с 10 на 15;
xmin изменился с 751 на 810;
ctid изменился с (0,1) на (0,4).
Объяснение
PostgreSQL не перезаписал строку на месте, а создал новую версию строки.
Новая версия получила новый xmin = 810, потому что она была создана уже другой транзакцией UPDATE.
Новый ctid = (0,4) показывает, что это уже другой физический tuple в таблице.

Почему старой строки не видно
Старая версия строки с id = 1 осталась в таблице физически, 
но обычный SELECT ее уже не показывает, потому что для текущей транзакции видимой является только новая версия.

Почему UPDATE в MVCC — не простое перезаписывание
Если бы строка просто перезаписывалась на месте, это ломало бы механизм снимков данных для других транзакций.
UPDATE создает новую версию строки, а старая остается до тех пор, пока не станет ненужной и не будет очищена.

После DELETE у версии строки записывается xmax — идентификатор транзакции удаления.
Для текущих запросов такая строка считается удаленной, поэтому SELECT ее уже не возвращает.
Физическая очистка произойдет позже, когда VACUUM удалит мертвые версии строк.

Сравнение VACUUM, autovacuum и VACUUM FULL
VACUUM очищает мертвые версии строк, которые остались после UPDATE и DELETE.
Освобождает место для повторного использования, но обычно не уменьшает сам файл таблицы на диске.

autovacuum — нужен для того, чтобы таблицы не разрастались из-за мусора и чтобы планировщик строил корректные планы.

VACUUM FULL полностью переписывает таблицу и реально может уменьшить ее размер на диске.
Tребует полной блокировки таблицы на время выполнения.

Какой механизм может полностью блокировать таблицу
VACUUM FULL

## Задание 4. Блокировки строк
эксперимент 1 Первый терминал
![Screenshot 2026-04-01 at 09.38.15.png](screenshots/Screenshot%202026-04-01%20at%2009.38.15.png)
Второй терминал
![Screenshot 2026-04-01 at 09.38.22.png](screenshots/Screenshot%202026-04-01%20at%2009.38.22.png)

эксперимент 2 Первый терминал
![Screenshot 2026-04-01 at 09.41.44.png](screenshots/Screenshot%202026-04-01%20at%2009.41.44.png)

Второй терминал
![Screenshot 2026-04-01 at 09.41.52.png](screenshots/Screenshot%202026-04-01%20at%2009.41.52.png)

Пояснение
В первом эксперименте UPDATE в сессии B будет ждать завершения транзакции A потому что 
FOR SHARE ставит разделяемую блокировку строки, а UPDATE хочет взять более сильную блокировку на изменение этой же строки, и возникает конфликт.

Во втором эксперименте UPDATE в сессии B тоже будет ждать. Но FOR UPDATE более сильная блокировка

Чем FOR SHARE отличается от FOR UPDATE?
FOR SHARE строку можно читать с блокировкой совместного доступа, но нельзя параллельно менять. Это более слабый режим, чем FOR UPDATE.
у FOR UPDATE конфликтов больше. 

Почему обычный SELECT ведет себя иначе?
Благодаря MVCC он читает снимок данных и обычно не мешает UPDATE, как и UPDATE не мешает обычному чтению.

Где использовать FOR UPDATE в прикладных сценариях?
там, где важна защита от гонок

## Задание 5. Секционирование и partition pruning
Создание секционированной таблицы
DROP TABLE IF EXISTS exam_measurements CASCADE;

CREATE TABLE exam_measurements (
city_id INTEGER NOT NULL,
log_date DATE NOT NULL,
peaktemp INTEGER,
unitsales INTEGER
) PARTITION BY RANGE (log_date);

Создание секций
CREATE TABLE exam_measurements_2025_01
PARTITION OF exam_measurements
FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');

CREATE TABLE exam_measurements_2025_02
PARTITION OF exam_measurements
FOR VALUES FROM ('2025-02-01') TO ('2025-03-01');

CREATE TABLE exam_measurements_2025_03
PARTITION OF exam_measurements
FOR VALUES FROM ('2025-03-01') TO ('2025-04-01');

CREATE TABLE exam_measurements_default
PARTITION OF exam_measurements
DEFAULT;

Перенос данных


INSERT INTO exam_measurements (city_id, log_date, peaktemp, unitsales)
SELECT city_id, log_date, peaktemp, unitsales
FROM exam_measurements_src;

ANALYZE exam_measurements;

План для запроса по диапазону даты
EXPLAIN (ANALYZE, BUFFERS)
SELECT city_id, log_date, unitsales
FROM exam_measurements
WHERE log_date >= DATE '2025-02-01'
AND log_date < DATE '2025-03-01';
![Screenshot 2026-04-01 at 09.49.37.png](screenshots/Screenshot%202026-04-01%20at%2009.49.37.png)
Ожидаемо в плане участвует только февральская секция

План для запроса по city_id
EXPLAIN (ANALYZE, BUFFERS)
SELECT city_id, log_date, unitsales
FROM exam_measurements
WHERE city_id = 10;

![Screenshot 2026-04-01 at 09.51.52.png](screenshots/Screenshot%202026-04-01%20at%2009.51.52.png)

Ожидаемо будет Append по всем секциям

Пояснение
Для запроса с фильтром по log_date pruning есть. 
Планировщик видит условие по ключу секционирования и понимает, 
что диапазон целиком попадает только в февральскую секцию, поэтому остальные секции можно не читать.
Для запроса с фильтром только по city_id pruning нет, так как city_id не является ключом секционирования

Сколько секций участвует?
В первом запросе — одна секция, февральская.
Во втором запросе — все четыре секции

Связан ли pruning напрямую с обычным индексом?
Нет. Индекс может ускорить поиск внутри уже выбранной секции, но сам по себе pruning не включает.

Зачем нужна секция DEFAULT?
Она нужна для строк, которые не попадают ни в январский, ни в февральский, ни в мартовский диапазон.