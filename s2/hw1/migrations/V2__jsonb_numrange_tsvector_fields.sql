-- Новое JSONB поле для предпочтений пользователя
ALTER TABLE cinema.users
ADD COLUMN IF NOT EXISTS preferences JSONB;

-- Ограничение на рейтинг
ALTER TABLE cinema.review
ADD CONSTRAINT chk_review_rating CHECK (rating BETWEEN 1 AND 10);

-- Новое поле типа NUMRANGE для хранения диапазона цен,
-- поле типа TSVECTOR для эффективного полнотекстового поиска по описанию фильма.
ALTER TABLE cinema.movie
ADD COLUMN IF NOT EXISTS price_range NUMRANGE,
ADD COLUMN IF NOT EXISTS description_ts TSVECTOR;