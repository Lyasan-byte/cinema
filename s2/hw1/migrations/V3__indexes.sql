-- Индексы для ускорения частых запросов

-- 1. Индекс по дате регистрации пользователей
CREATE INDEX IF NOT EXISTS idx_users_date_created ON cinema.users (date_created);

-- 2. Индекс по роли пользователя (низкая селективность, частая фильтрация)
CREATE INDEX IF NOT EXISTS idx_users_role ON cinema.users (role);

-- 3. Индекс по году выпуска фильма (частая фильтрация)
CREATE INDEX IF NOT EXISTS idx_movie_release_year ON cinema.movie (release_year);

-- 4. Композитный индекс: страна + язык (для поиска по региону)
CREATE INDEX IF NOT EXISTS idx_movie_country_language ON cinema.movie (country, language);

-- 5. Индекс по рейтингу отзывов (для сортировки "лучшие фильмы")
CREATE INDEX IF NOT EXISTS idx_review_rating ON cinema.review (rating DESC);

-- 6. Индекс по пользователю в отзывах (чтобы быстро найти все отзывы пользователя)
CREATE INDEX IF NOT EXISTS idx_review_user_id ON cinema.review (user_id);

-- 7. Индекс по фильму в отзывах (чтобы быстро получить все отзывы к фильму)
CREATE INDEX IF NOT EXISTS idx_review_movie_id ON cinema.review (movie_id);

-- 8. Частичный индекс: только активные аренды (для быстрого поиска текущих аренд)
CREATE INDEX IF NOT EXISTS idx_rental_active ON cinema.rental (rental_id)
WHERE status = 'active' AND is_returned = false;

-- 9. Индекс по дате просмотра (для аналитики поведения)
CREATE INDEX IF NOT EXISTS idx_viewing_date ON cinema.viewing (viewing_date);

-- 10. GIN-индекс для полнотекстового поиска для TSVECTOR
CREATE INDEX IF NOT EXISTS idx_movie_description_ts ON cinema.movie USING GIN (description_ts);