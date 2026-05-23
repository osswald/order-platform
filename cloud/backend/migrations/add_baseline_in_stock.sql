-- Event stock baseline for test → prod reset
ALTER TABLE event_article_stock ADD COLUMN IF NOT EXISTS baseline_in_stock INTEGER;
UPDATE event_article_stock SET baseline_in_stock = in_stock WHERE baseline_in_stock IS NULL;
