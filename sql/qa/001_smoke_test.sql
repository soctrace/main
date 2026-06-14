SELECT current_database() AS db, current_user AS usr;

SELECT schema_name
FROM information_schema.schemata
WHERE schema_name IN ('raw', 'staging', 'core', 'marts', 'qa')
ORDER BY schema_name;