# InfluxDB

## Задание 1. Установка и запуск InfluxDB

```bash
# Запуск InfluxDB
docker compose up -d
```
![Screenshot 2026-05 at 10.51.18.png](screenshots/Screenshot%202026-05%20at%2010.51.18.png)
После запуска InfluxDB доступен в браузере:
http://localhost:8086

## Задание 2. Создание базы через веб-интерфейс
![Screenshot 2026-05 at 10.53.46.png](screenshots/Screenshot%202026-05%20at%2010.53.46.png)
## Задание 3. Наполнение данными промышленных датчиков

```bash
curl -XPOST "http://localhost:8086/api/v2/write?org=university&bucket=sensors&precision=s" \
--header "Authorization: Token my-super-token" \
--header "Content-Type: text/plain; charset=utf-8" \
--data-binary "
current,motor_id=M-1001,type=induction,load=high value=145.5
current,motor_id=M-1001,type=induction,load=high value=151.2
current,motor_id=M-1002,type=synchronous,load=medium value=98.4
current,motor_id=M-1002,type=synchronous,load=medium value=104.7
pressure,pipe_id=MP-01,section=main,zone=A value=4.2
pressure,pipe_id=MP-01,section=main,zone=A value=4.8
pressure,pipe_id=MP-02,section=backup,zone=B value=3.6
pressure,pipe_id=MP-02,section=backup,zone=B value=3.9
temperature,sensor_id=T-01,zone=A,equipment=boiler value=82.5
temperature,sensor_id=T-01,zone=A,equipment=boiler value=86.3
temperature,sensor_id=T-02,zone=B,equipment=pump value=61.4
temperature,sensor_id=T-02,zone=B,equipment=pump value=65.1
vibration,motor_id=M-1001,axis=x,zone=A value=2.4
vibration,motor_id=M-1001,axis=x,zone=A value=3.1
vibration,motor_id=M-1002,axis=y,zone=B value=1.7
vibration,motor_id=M-1002,axis=y,zone=B value=2.2
"
```
![Screenshot 2026-05 at 11.00.07.png](screenshots/Screenshot%202026-05%20at%2011.00.07.png)
## Задание 4. Базовые запросы
```bash
# 1. Просмотреть все данные за последние 30 минут
from(bucket: "sensors")
|> range(start: -30m)
```
![Screenshot 2026-05 at 11.05.09.png](screenshots/Screenshot%202026-05%20at%2011.05.09.png)
```bash
# 2. Посмотреть измерения только одного датчика
Например, данные по электродвигателю M-1001:

from(bucket: "sensors")
  |> range(start: -30m)
  |> filter(fn: (r) => r.motor_id == "M-1001")
```
![Screenshot 2026-05 at 11.05.44.png](screenshots/Screenshot%202026-05%20at%2011.05.44.png)
```bash
# 3. Максимальное значение на одном датчике
from(bucket: "sensors")
  |> range(start: -30m)
  |> filter(fn: (r) => r.motor_id == "M-1001")
  |> max()
```
![Screenshot 2026-05 at 11.06.01.png](screenshots/Screenshot%202026-05%20at%2011.06.01.png)
```bash
# 4. Среднее значение на датчике
   from(bucket: "sensors")
   |> range(start: -30m)
   |> filter(fn: (r) => r.motor_id == "M-1001")
   |> mean()
```
![Screenshot 2026-05 at 11.06.41.png](screenshots/Screenshot%202026-05%20at%2011.06.41.png)

```bash
5. Аналитический запрос с фильтром по значению: высокий ток
   from(bucket: "sensors")
   |> range(start: -30m)
   |> filter(fn: (r) => r._measurement == "current")
   |> filter(fn: (r) => r._value > 140)
```
![Screenshot 2026-05 at 11.06.58.png](screenshots/Screenshot%202026-05%20at%2011.06.58.png)
```bash
6. Аналитический запрос с фильтром по значению: высокое давление
   from(bucket: "sensors")
   |> range(start: -30m)
   |> filter(fn: (r) => r._measurement == "pressure")
   |> filter(fn: (r) => r._value > 4.5)
```
![Screenshot 2026-05 at 11.07.32.png](screenshots/Screenshot%202026-05%20at%2011.07.32.png)

```bash
7. Аналитический запрос с фильтром по значению: высокая температура
   from(bucket: "sensors")
   |> range(start: -30m)
   |> filter(fn: (r) => r._measurement == "temperature")
   |> filter(fn: (r) => r._value > 80)
```
![Screenshot 2026-05 at 11.07.47.png](screenshots/Screenshot%202026-05%20at%2011.07.47.png)
```bash
8. Запрос на агрегацию данных
   Среднее значение по каждому измерению за последние 30 минут:

from(bucket: "sensors")
|> range(start: -30m)
|> group(columns: ["_measurement"])
|> mean()
```
![Screenshot 2026-05 at 11.08.12.png](screenshots/Screenshot%202026-05%20at%2011.08.12.png)
## Задание 5. Dashboard с графиками

График 1. Ток электродвигателей 
Motor Current

from(bucket: "sensors")
|> range(start: -30m)
|> filter(fn: (r) => r._measurement == "current")
|> aggregateWindow(every: 1m, fn: mean, createEmpty: false)

![Screenshot 2026-05 at 11.10.36.png](screenshots/Screenshot%202026-05%20at%2011.10.36.png)


График 2. Давление в трубопроводах
Pipeline Pressure

from(bucket: "sensors")
|> range(start: -30m)
|> filter(fn: (r) => r._measurement == "pressure")
|> aggregateWindow(every: 1m, fn: mean, createEmpty: false

![Screenshot 2026-05 at 11.11.36.png](screenshots/Screenshot%202026-05%20at%2011.11.36.png)

Вывод
InfluxDB подходит для хранения временных рядов: показаний датчиков, метрик, 
логов оборудования и мониторинга. Данные записываются в формате line protocol,
где есть измерение, теги и значение. 
Через Flux можно быстро фильтровать данные по времени, датчику и значению, 
а также строить агрегации и dashboard-графики.