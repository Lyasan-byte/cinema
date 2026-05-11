# Очереди
```bash
docker compose up -d
docker exec -it cinema-db psql -U admin -d cinema_db 
```
![Screenshot 2026-05 at 14.50.28.png](screenshots/Screenshot%202026-05%20at%2014.50.28.png)
## 1. Создание таблицы очереди
```sql
CREATE TYPE task_status AS ENUM ('READY', 'RUNNING', 'COMPLETED', 'FAILED');

CREATE TABLE queue_business_events (
                                       event_id BIGSERIAL PRIMARY KEY,
                                       event_type TEXT NOT NULL,
                                       payload JSONB NOT NULL,
                                       created_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE tasks (
                       task_id BIGSERIAL PRIMARY KEY,

                       task_type TEXT NOT NULL,
                       payload JSONB NOT NULL,

                       priority INTEGER NOT NULL DEFAULT 0,
                       status task_status NOT NULL DEFAULT 'READY',

                       attempts INTEGER NOT NULL DEFAULT 0,
                       max_attempts INTEGER NOT NULL DEFAULT 5,

                       created_at TIMESTAMP NOT NULL DEFAULT now(),
                       scheduled_at TIMESTAMP NOT NULL DEFAULT now(),
                       started_at TIMESTAMP,
                       completed_at TIMESTAMP,
                       failed_at TIMESTAMP,
                       updated_at TIMESTAMP NOT NULL DEFAULT now(),

                       locked_by TEXT,
                       last_error TEXT
);
```
![Screenshot 2026-05 at 14.50.47.png](screenshots/Screenshot%202026-05%20at%2014.50.47.png)

```sql
-- Добавление индексов
CREATE INDEX idx_tasks_ready_pick
    ON tasks (priority DESC, scheduled_at ASC, created_at ASC)
    WHERE status = 'READY';

CREATE INDEX idx_tasks_status_created
    ON tasks (status, created_at);

CREATE INDEX idx_tasks_completed_at
    ON tasks (completed_at);

CREATE INDEX idx_tasks_priority_started
    ON tasks (priority, started_at);
```
![Screenshot 2026-05 at 14.51.14.png](screenshots/Screenshot%202026-05%20at%2014.51.14.png)
## Борьба с Bloat:
```sql
-- Настройка autovacuum для таблицы (ДОПОЛНИТЕЛЬНОЕ ЗАДАНИЕ)
ALTER TABLE tasks SET (
    autovacuum_vacuum_scale_factor = 0.01,
    autovacuum_analyze_scale_factor = 0.01,
    autovacuum_vacuum_threshold = 50,
    autovacuum_analyze_threshold = 50
    );
```
![Screenshot 2026-05 at 14.51.25.png](screenshots/Screenshot%202026-05%20at%2014.51.25.png)

## Создаем Java-проект в папке postgres-queue-hw


### Запускаем worker-1 в первом терминале 
```bash
cd postgres-queue-hw
```

```bash
DB_URL='jdbc:postgresql://localhost:5433/cinema_db?currentSchema=cinema,public' \
DB_USER=admin \
DB_PASSWORD=Mishka \
mvn -q exec:java -Dexec.mainClass=com.lays.queue.QueueApp -Dexec.args="worker worker-1"
```
![Screenshot 2026-05 at 15.56.13.png](screenshots/Screenshot%202026-05%20at%2015.56.13.png)
### Запускаем worker-2 во втором терминале
```bash
cd postgres-queue-hw
```

```bash
JAVA_TOOL_OPTIONS="-Duser.timezone=UTC" \
DB_URL='jdbc:postgresql://localhost:5433/cinema_db?currentSchema=cinema,public' \
DB_USER=admin \
DB_PASSWORD=Mishka \
mvn -q exec:java -Dexec.mainClass=com.lays.queue.QueueApp -Dexec.args="worker worker-2"
```
![Screenshot 2026-05 at 15.39.19.png](screenshots/Screenshot%202026-05%20at%2015.39.19.png)

### Запускаем monitor в третьем терминале
```bash
cd postgres-queue-hw
mkdir -p logs
```

```bash
JAVA_TOOL_OPTIONS="-Duser.timezone=UTC" \
DB_URL='jdbc:postgresql://localhost:5433/cinema_db?currentSchema=cinema,public' \
DB_USER=admin \
DB_PASSWORD=Mishka \
mvn -q exec:java -Dexec.mainClass=com.lays.queue.QueueApp -Dexec.args="monitor" | tee logs/monitor.csv
```
![Screenshot 2026-05 at 15.40.10.png](screenshots/Screenshot%202026-05%20at%2015.40.10.png)

### Запускаем producer в четвертом терминале

```bash
cd postgres-queue-hw
```

```bash
# Сначала можно запустить 100 задач в секунду
JAVA_TOOL_OPTIONS="-Duser.timezone=UTC" \
DB_URL='jdbc:postgresql://localhost:5433/cinema_db?currentSchema=cinema,public' \
DB_USER=admin \
DB_PASSWORD=Mishka \
mvn -q exec:java -Dexec.mainClass=com.lays.queue.QueueApp -Dexec.args="producer 100"
```
![Screenshot 2026-05 at 15.40.58.png](screenshots/Screenshot%202026-05%20at%2015.40.58.png)
```bash
# Далее пробуем 300 задач в секунду
JAVA_TOOL_OPTIONS="-Duser.timezone=UTC" \
DB_URL='jdbc:postgresql://localhost:5433/cinema_db?currentSchema=cinema,public' \
DB_USER=admin \
DB_PASSWORD=Mishka \
mvn -q exec:java -Dexec.mainClass=com.lays.queue.QueueApp -Dexec.args="producer 300"
```
![Screenshot 2026-05 at 15.41.44.png](screenshots/Screenshot%202026-05%20at%2015.41.44.png)
### Проверяем лаг очереди

```bash
docker exec -it cinema-db psql -U admin -d cinema_db
```

```sql
SELECT now() - MIN(created_at) AS queue_lag
FROM tasks
WHERE status = 'READY'
AND scheduled_at <= now();
```
![Screenshot 2026-05 at 15.42.12.png](screenshots/Screenshot%202026-05%20at%2015.42.12.png)

```text
Самая старая задача в статусе READY ожидает обработки примерно 1 минуту 15 секунд.
Это означает, что очередь действительно начала накапливаться: producer создает 
задачи быстрее, чем два worker-а успевают их обрабатывать. Этот показатель и 
является лагом очереди: чем он больше, тем дольше задачи ждут выполнения.
```
### Проверяем количество задач по статусам

```sql
SELECT status, COUNT(*) AS count
FROM tasks
GROUP BY status
ORDER BY status;
```
![Screenshot 2026-05 at 15.42.26.png](screenshots/Screenshot%202026-05%20at%2015.42.26.png)

```text
В очереди находится 17693 задачи в статусе READY, то есть они уже 
созданы producer-ом, но еще не обработаны.
В статусе RUNNING находятся 2 задачи, что соответствует двум запущенным 
worker-ам: каждый worker в конкретный момент времени обрабатывает одну задачу.
В статусе COMPLETED находится 763 задачи, то есть они уже успешно обработаны.

Этот результат показывает, что очередь работает как буфер: при высокой нагрузке 
задачи не теряются, а накапливаются в таблице tasks.
```
### Проверяем throughput

```sql
SELECT COUNT(*) AS completed_last_second
FROM tasks
WHERE status = 'COMPLETED'
  AND completed_at >= now() - interval '1 second';
```
![Screenshot 2026-05 at 15.42.40.png](screenshots/Screenshot%202026-05%20at%2015.42.40.png)

```text
За последнюю секунду оба worker-а суммарно обработали 5 задач. 
Это текущая пропускная способность системы в момент измерения.
```

### Проверяем, что priority 100 выполняется быстрее
```sql
SELECT
    priority,
    COUNT(*) AS started_count,
    ROUND(AVG(EXTRACT(EPOCH FROM (started_at - created_at)))::numeric, 3) AS avg_wait_seconds,
    ROUND(percentile_cont(0.5) WITHIN GROUP (
        ORDER BY EXTRACT(EPOCH FROM (started_at - created_at))
    )::numeric, 3) AS median_wait_seconds
FROM tasks
WHERE started_at IS NOT NULL
GROUP BY priority
ORDER BY priority DESC;
```
![Screenshot 2026-05 at 15.43.01.png](screenshots/Screenshot%202026-05%20at%2015.43.01.png)

```text
В результате видно, что worker-ы почти полностью заняты 
приоритетными задачами: было начато 1155 задач с priority 100 
и только 2 задачи с priority 0. Это показывает, что при высокой 
нагрузке критические задачи вытесняют обычные и обрабатываются раньше них.

Важно: в этом конкретном замере среднее ожидание у priority = 0 
маленьким не потому, что обычные задачи быстрее, а потому что их было обработано 2 штуки.
```

### Проверяем retry
```sql
SELECT
    task_id,
    task_type,
    priority,
    status,
    attempts,
    scheduled_at,
    last_error
FROM tasks
WHERE attempts > 0
ORDER BY attempts DESC, scheduled_at DESC
    LIMIT 20;
```
![Screenshot 2026-05 at 15.43.30.png](screenshots/Screenshot%202026-05%20at%2015.43.30.png)


```text
Этот результат подтверждает работу retry-механизма. 
Некоторые задачи завершились ошибкой, поэтому worker:

увеличил поле attempts;
вернул задачу в статус READY;
записал ошибку в last_error;
перенес scheduled_at в будущее.
```

### Проверяем bloat
```sql
SELECT
    relname,
    n_live_tup,
    n_dead_tup,
    vacuum_count,
    autovacuum_count,
    last_vacuum,
    last_autovacuum
FROM pg_stat_user_tables
WHERE relname = 'tasks';
```
![Screenshot 2026-05 at 15.43.46.png](screenshots/Screenshot%202026-05%20at%2015.43.46.png)

```text
До ручного VACUUM в таблице tasks было примерно 43156 живых строк и 696 мертвых строк.

Мертвые строки появляются из-за особенностей PostgreSQL MVCC: 
при частых UPDATE старые версии строк не удаляются сразу. В очереди 
это особенно заметно, потому что каждая задача несколько раз меняет статус
```

### Запускаем ручной VACUUM ANALYZE
```sql
VACUUM (ANALYZE, VERBOSE) tasks;
-- После этого еще раз проверяем bloat
SELECT
    relname,
    n_live_tup,
    n_dead_tup,
    vacuum_count,
    autovacuum_count,
    last_vacuum,
    last_autovacuum
FROM pg_stat_user_tables
WHERE relname = 'tasks';
```
![Screenshot 2026-05 at 15.44.08.png](screenshots/Screenshot%202026-05%20at%2015.44.08.png)

```text
Ручной VACUUM ANALYZE очистил таблицу от мертвых строк и 
обновил статистику планировщика запросов.
То есть после очистки в таблице остались только 
актуальные строки, а мертвые версии были убраны.
```