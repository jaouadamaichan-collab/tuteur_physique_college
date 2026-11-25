-- ════════════════════════════════════════════════════════════
-- 🗄️  Tuteur Physique-Chimie IA Collège — Table Supabase
-- ════════════════════════════════════════════════════════════
-- À exécuter dans Supabase → SQL Editor → New Query → Run
-- Peut être relancé sans risque (ne supprime aucune donnée).
--
-- Sécurité : les élèves sont mineurs. La table n'a AUCUNE politique d'accès
-- public : seule la clé secrète (sb_secret_… ou service_role), stockée dans les
-- secrets Streamlit, peut lire et écrire. La clé publique (anon / publishable)
-- n'a accès à rien.

CREATE TABLE IF NOT EXISTS sessions_physique_college (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    eleve_nom     TEXT NOT NULL,
    classe        TEXT DEFAULT '',
    programme     TEXT DEFAULT '',
    chapitre      TEXT DEFAULT '',
    objectif      TEXT DEFAULT '',
    temps         TEXT DEFAULT '',
    nb_exercices  INTEGER DEFAULT 0,
    nb_echanges   INTEGER DEFAULT 0,
    phase_finale  TEXT DEFAULT '',
    bilan         TEXT DEFAULT '',
    messages      JSONB DEFAULT '[]'::jsonb,
    date_session  TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_sessions_physique_college_eleve ON sessions_physique_college (eleve_nom);
CREATE INDEX IF NOT EXISTS idx_sessions_physique_college_date  ON sessions_physique_college (date_session DESC);

ALTER TABLE sessions_physique_college ENABLE ROW LEVEL SECURITY;

-- Supprime l'ancienne politique ouverte si elle a été créée par une version précédente de ce script.
DROP POLICY IF EXISTS "allow_all_physique_college" ON sessions_physique_college;
