# MongoDB

```bash
# Запуск и подключение
docker compose up -d
docker exec -it homework-mongodb mongosh -u admin -p 1234 --authenticationDatabase admin
```
![Screenshot 2026-04-12 at 12.54.34.png](screenshots/Screenshot%202026-04-12%20at%2012.54.34.png)
![Screenshot 2026-04-12 at 13.10.27.png](screenshots/Screenshot%202026-04-12%20at%2013.10.27.png)

```js
// Создание и выбор базы данных
use("university")
```
![Screenshot 2026-04-12 at 13.10.39.png](screenshots/Screenshot%202026-04-12%20at%2013.10.39.png)
```js
// Создание коллекции students и добавление документов
// Здесь есть вложенный JSON-объект contacts и массив skills
db.students.insertMany([
    {
        _id: ObjectId("661900000000000000000001"),
        name: "Anna Petrova",
        age: 20,
        group: "CS-101",
        contacts: {
            email: "anna@example.com",
            phone: "+1-111-111"
        },
        skills: ["MongoDB", "JavaScript", "Docker"]
    },
    {
        _id: ObjectId("661900000000000000000002"),
        name: "Ivan Sidorov",
        age: 22,
        group: "CS-102",
        contacts: {
            email: "ivan@example.com",
            phone: "+1-222-222"
        },
        skills: ["Python", "SQL"]
    },
    {
        _id: ObjectId("661900000000000000000003"),
        name: "Maria Kozlova",
        age: 21,
        group: "CS-101",
        contacts: {
            email: "maria@example.com",
            phone: "+1-333-333"
        },
        skills: ["C++", "Linux"]
    }
])
```
![Screenshot 2026-04-12 at 13.11.07.png](screenshots/Screenshot%202026-04-12%20at%2013.11.07.png)


```js
// Создание коллекции courses и добавление документов
db.courses.insertMany([
    {
        _id: ObjectId("662900000000000000000001"),
        title: "Databases",
        teacher: "Dr. Brown",
        credits: 5,
        schedule: {
            day: "Monday",
            room: "A-201"
        }
    },
    {
        _id: ObjectId("662900000000000000000002"),
        title: "Backend Development",
        teacher: "Prof. Wilson",
        credits: 4,
        schedule: {
            day: "Wednesday",
            room: "B-105"
        }
    },
    {
        _id: ObjectId("662900000000000000000003"),
        title: "Algorithms",
        teacher: "Dr. Green",
        credits: 6,
        schedule: {
            day: "Friday",
            room: "C-310"
        }
    }
])
```
![Screenshot 2026-04-12 at 13.11.27.png](screenshots/Screenshot%202026-04-12%20at%2013.11.27.png)

```js
// Создание коллекции enrollments и добавление документов
// Здесь studentId и courseId связаны с другими коллекциями через ObjectId
db.enrollments.insertMany([
  {
    _id: ObjectId("663900000000000000000001"),
    studentId: ObjectId("661900000000000000000001"),
    courseId: ObjectId("662900000000000000000001"),
    semester: "2026 Spring",
    grade: 88
  },
  {
    _id: ObjectId("663900000000000000000002"),
    studentId: ObjectId("661900000000000000000001"),
    courseId: ObjectId("662900000000000000000002"),
    semester: "2026 Spring",
    grade: 91
  },
  {
    _id: ObjectId("663900000000000000000003"),
    studentId: ObjectId("661900000000000000000002"),
    courseId: ObjectId("662900000000000000000003"),
    semester: "2026 Spring",
    grade: 84
  },
  {
    _id: ObjectId("663900000000000000000004"),
    studentId: ObjectId("661900000000000000000003"),
    courseId: ObjectId("662900000000000000000001"),
    semester: "2026 Spring",
    grade: 95
  }
])
```
![Screenshot 2026-04-12 at 13.11.37.png](screenshots/Screenshot%202026-04-12%20at%2013.11.37.png)

## Запросы

```js
// FIND 1
// Найти всех студентов из группы CS-101
db.students.find({ group: "CS-101" })
```
![Screenshot 2026-04-12 at 13.11.51.png](screenshots/Screenshot%202026-04-12%20at%2013.11.51.png)
```js
// FIND 2 с projection
// Показать только name, age и skills у студентов старше или равных 21 году
db.students.find(
{ age: { $gte: 21 } },
{ _id: 0, name: 1, age: 1, skills: 1 }
)
```
![Screenshot 2026-04-12 at 13.12.13.png](screenshots/Screenshot%202026-04-12%20at%2013.12.13.png)
```js
// UPDATE 1
// Обновить возраст студента Ivan Sidorov
db.students.updateOne(
{ name: "Ivan Sidorov" },
{ $set: { age: 23 } }
)
```
![Screenshot 2026-04-12 at 13.12.25.png](screenshots/Screenshot%202026-04-12%20at%2013.12.25.png)
```js
// UPDATE 2
// Добавить category = "elective" всем курсам, у которых credits меньше 5
db.courses.updateMany(
{ credits: { $lt: 5 } },
{ $set: { category: "elective" } }
)
```
![Screenshot 2026-04-12 at 13.12.34.png](screenshots/Screenshot%202026-04-12%20at%2013.12.34.png)
```js
// AGGREGATE
// Посчитать среднюю оценку по группам студентов
db.enrollments.aggregate([
  {
    $lookup: {
      from: "students",
      localField: "studentId",
      foreignField: "_id",
      as: "student"
    }
  },
  {
    $unwind: "$student"
  },
  {
    $group: {
      _id: "$student.group",
      averageGrade: { $avg: "$grade" },
      studentsCount: { $sum: 1 }
    }
  },
  {
    $project: {
      _id: 0,
      group: "$_id",
      averageGrade: { $round: ["$averageGrade", 2] },
      studentsCount: 1
    }
  }
])
```
![Screenshot 2026-04-12 at 13.12.46.png](screenshots/Screenshot%202026-04-12%20at%2013.12.46.png)