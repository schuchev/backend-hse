CREATE TABLE IF NOT EXISTS items (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    category INTEGER NOT NULL CHECK (category > 0 AND category <= 100),
    images_qty INTEGER NOT NULL CHECK (images_qty >= 0 AND images_qty <= 10)
);