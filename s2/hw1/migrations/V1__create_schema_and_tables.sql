CREATE SCHEMA IF NOT EXISTS cinema;

-- Таблица users
CREATE TABLE cinema.users (
                              user_id INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
                              name VARCHAR(255) NOT NULL,
                              email TEXT NOT NULL,
                              password_hash TEXT NOT NULL,
                              role TEXT NOT NULL,
                              date_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                              last_login TIMESTAMP
);

-- Таблица actor
CREATE TABLE cinema.actor (
                              actor_id INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
                              name TEXT NOT NULL,
                              birth_date DATE,
                              country TEXT,
                              biography TEXT
);

-- Таблица director
CREATE TABLE cinema.director (
                                 director_id INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
                                 name TEXT NOT NULL,
                                 birth_date DATE,
                                 country TEXT,
                                 biography TEXT
);

-- Таблица genre
CREATE TABLE cinema.genre (
                              genre_id INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
                              name TEXT NOT NULL,
                              description TEXT
);

-- Таблица movie
CREATE TABLE cinema.movie (
                              movie_id INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
                              title TEXT NOT NULL,
                              description TEXT,
                              release_year INTEGER,
                              duration INTEGER,
                              age_rating TEXT,
                              language TEXT,
                              country TEXT,
                              director_id INTEGER REFERENCES cinema.director(director_id)
);

-- Таблица family_group
CREATE TABLE cinema.family_group (
                                     group_id INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
                                     group_name TEXT NOT NULL,
                                     owner_id INTEGER NOT NULL,
                                     created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица family_member
CREATE TABLE cinema.family_member (
                                      member_id INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
                                      family_group_id INTEGER NOT NULL REFERENCES cinema.family_group(group_id),
                                      user_id INTEGER NOT NULL REFERENCES cinema.users(user_id),
                                      role TEXT NOT NULL
);

-- Таблица movie_actor (связь многие-ко-многим)
CREATE TABLE cinema.movie_actor (
                                    movie_id INTEGER NOT NULL REFERENCES cinema.movie(movie_id),
                                    actor_id INTEGER NOT NULL REFERENCES cinema.actor(actor_id),
                                    PRIMARY KEY (movie_id, actor_id)
);

-- Таблица movie_genre (связь многие-ко-многим)
CREATE TABLE cinema.movie_genre (
                                    movie_id INTEGER NOT NULL REFERENCES cinema.movie(movie_id),
                                    genre_id INTEGER NOT NULL REFERENCES cinema.genre(genre_id),
                                    PRIMARY KEY (movie_id, genre_id)
);

-- Таблица purchase
CREATE TABLE cinema.purchase (
                                 purchase_id INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
                                 user_id INTEGER NOT NULL REFERENCES cinema.users(user_id),
                                 movie_id INTEGER NOT NULL REFERENCES cinema.movie(movie_id),
                                 purchase_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                 price NUMERIC NOT NULL,
                                 payment_method TEXT NOT NULL
);

-- Таблица rental
CREATE TABLE cinema.rental (
                               rental_id INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
                               user_id INTEGER NOT NULL REFERENCES cinema.users(user_id),
                               movie_id INTEGER NOT NULL REFERENCES cinema.movie(movie_id),
                               rental_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                               return_date TIMESTAMP,
                               price NUMERIC NOT NULL,
                               status TEXT NOT NULL,
                               is_returned BOOLEAN DEFAULT false
);

-- Таблица review
CREATE TABLE cinema.review (
                               review_id INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
                               user_id INTEGER NOT NULL REFERENCES cinema.users(user_id),
                               movie_id INTEGER NOT NULL REFERENCES cinema.movie(movie_id),
                               rating INTEGER NOT NULL,
                               comment TEXT,
                               review_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                               is_spoiler BOOLEAN DEFAULT false
);

-- Таблица subscription
CREATE TABLE cinema.subscription (
                                     subscription_id INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
                                     user_id INTEGER NOT NULL REFERENCES cinema.users(user_id),
                                     plan_type TEXT NOT NULL,
                                     price NUMERIC NOT NULL,
                                     start_date TIMESTAMP NOT NULL,
                                     end_date TIMESTAMP NOT NULL,
                                     status TEXT NOT NULL
);

-- Таблица viewing
CREATE TABLE cinema.viewing (
                                viewing_id INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
                                user_id INTEGER NOT NULL REFERENCES cinema.users(user_id),
                                movie_id INTEGER NOT NULL REFERENCES cinema.movie(movie_id),
                                viewing_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                                progress NUMERIC,
                                device TEXT NOT NULL,
                                watched_until INTEGER
);
