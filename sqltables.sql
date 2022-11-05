CREATE TABLE users
(
    id  INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    username TEXT NOT NULL,
    hash TEXT NOT NULL
);

CREATE TABLE officers
(
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    user_id integer NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE items
(
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    name TEXT NOT NULL,
    price NUMERIC NOT NULL,
    stock INTEGER NOT NULL,
    description TEXT NOT NULL,
    specs text NOT NULL,
    category_id INTEGER NOT NULL,
    brands_id INTEGER NOT NULL,
    FOREIGN KEY (category_id) REFERENCES categories(id)
    FOREIGN KEY (brands_id) REFERENCES brands(id)
);

CREATE TABLE categories
(
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    name text NOT NULL
);

CREATE TABLE specs
(
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    name text NOT NULL,
    category_id INTEGER NOT NULL,
    FOREIGN KEY (category_id) REFERENCES categories(id)
);

CREATE TABLE brands
(
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    name text NOT NULL
);