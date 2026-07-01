-- Ingredients and composite article stock (Postgres)

ALTER TABLE organisations ADD COLUMN IF NOT EXISTS ingredients_enabled BOOLEAN NOT NULL DEFAULT FALSE;

CREATE TABLE IF NOT EXISTS ingredients (
    id SERIAL PRIMARY KEY,
    organisation_id INTEGER NOT NULL REFERENCES organisations(id) ON DELETE CASCADE,
    name VARCHAR NOT NULL,
    unit VARCHAR(32),
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);
CREATE INDEX IF NOT EXISTS ix_ingredients_organisation_id ON ingredients (organisation_id);

CREATE TABLE IF NOT EXISTS article_ingredient_links (
    base_article_id INTEGER NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
    ingredient_id INTEGER NOT NULL REFERENCES ingredients(id) ON DELETE CASCADE,
    amount NUMERIC(12, 3) NOT NULL DEFAULT 1,
    sort_order INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (base_article_id, ingredient_id)
);

CREATE TABLE IF NOT EXISTS event_ingredient_stock (
    event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    ingredient_id INTEGER NOT NULL REFERENCES ingredients(id) ON DELETE CASCADE,
    monitor_stock BOOLEAN NOT NULL DEFAULT FALSE,
    in_stock NUMERIC(12, 3),
    baseline_in_stock NUMERIC(12, 3),
    PRIMARY KEY (event_id, ingredient_id)
);
