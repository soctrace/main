CREATE UNIQUE INDEX IF NOT EXISTS ux_mijas_features_panel
    ON marts.mijas_features_panel (seccion_id, anio, election_id);

CREATE INDEX IF NOT EXISTS ix_mijas_features_panel_anio
    ON marts.mijas_features_panel (anio);

CREATE INDEX IF NOT EXISTS ix_mijas_features_panel_sigla_ganadora
    ON marts.mijas_features_panel (sigla_ganadora);

CREATE INDEX IF NOT EXISTS ix_mijas_features_panel_income_quintile
    ON marts.mijas_features_panel (income_quintile);
