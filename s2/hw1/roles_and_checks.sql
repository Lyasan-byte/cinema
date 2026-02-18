-- СОЗДАНИЕ РОЛЕЙ
-- Роль 1: Только чтение
CREATE ROLE cinema_reader WITH LOGIN PASSWORD 'reader_cinema';
GRANT CONNECT ON DATABASE cinema_db TO cinema_reader;
GRANT USAGE ON SCHEMA cinema TO cinema_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA cinema TO cinema_reader;

-- Роль 2: Чтение + вставка
CREATE ROLE cinema_editor WITH LOGIN PASSWORD 'editor_cinema';
GRANT CONNECT ON DATABASE cinema_db TO cinema_editor;
GRANT USAGE ON SCHEMA cinema TO cinema_editor;
GRANT SELECT, INSERT ON ALL TABLES IN SCHEMA cinema TO cinema_editor;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA cinema TO cinema_editor;

-- Роль 3: Полный доступ
CREATE ROLE cinema_admin WITH LOGIN PASSWORD 'secret_admin_cinema';
GRANT CONNECT ON DATABASE cinema_db TO cinema_admin;
GRANT ALL PRIVILEGES ON SCHEMA cinema TO cinema_admin;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA cinema TO cinema_admin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA cinema TO cinema_admin;


-- ПРОВЕРКА РОЛЕЙ
-- Role: Cinema Reader
-- Должно РАБОТАТЬ:
SELECT * FROM cinema.users LIMIT 5;
-- Должно ВЫЗВАТЬ ОШИБКУ:
INSERT INTO cinema.users (name, email, password_hash, role)
VALUES ('Test', 'test@test.com', 'hash', 'user');

-- Role: Cinema Editor (Select + Insert)
-- Должно РАБОТАТЬ:
SELECT * FROM cinema.users LIMIT 5;

INSERT INTO cinema.users (name, email, password_hash, role)
VALUES ('Editor Test', 'editor@test.com', 'hash', 'user');
-- Должно ВЫЗВАТЬ ОШИБКУ:
DELETE FROM cinema.users WHERE user_id = 1;

-- Role: Cinema Admin
-- Должно ВСЁ РАБОТАТЬ:
SELECT * FROM cinema.users LIMIT 5;

INSERT INTO cinema.users (name, email, password_hash, role)
VALUES ('Admin Test', 'admin@test.com', 'hash', 'admin');
DELETE FROM cinema.users WHERE email = 'admin@test.com';
