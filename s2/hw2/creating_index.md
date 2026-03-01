-- B-TREE Indexes
CREATE INDEX idx_movie_release_year_btree ON cinema.movie USING btree (release_year);
CREATE INDEX idx_rental_price_btree ON cinema.rental USING btree (price);
CREATE INDEX idx_users_email_btree ON cinema.users USING btree (email);
CREATE INDEX idx_actor_name_btree ON cinema.actor USING btree (name);
CREATE INDEX idx_review_rating_btree ON cinema.review USING btree (rating);

-- Создание Hash индексов (только для оператора =)
CREATE INDEX idx_users_email_hash ON cinema.users USING hash (email);