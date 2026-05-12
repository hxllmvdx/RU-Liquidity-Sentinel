-- Remove development/demo rows that can pollute production-like dashboard output.
-- This migration only targets rows explicitly marked as demo in metadata/model_version/source fields.

DELETE FROM module_signals
WHERE metadata IS NOT NULL
  AND metadata::text ILIKE '%demo%';

DELETE FROM active_flags
WHERE description ILIKE '%demo%';

DELETE FROM module_contributions mc
USING lsi_values l
WHERE mc.lsi_value_id = l.id
  AND COALESCE(l.model_version, '') ILIKE '%demo%';

DELETE FROM lsi_values
WHERE COALESCE(model_version, '') ILIKE '%demo%'
   OR COALESCE(auto_comment, '') ILIKE '%demo seed%';

DELETE FROM module_signals
WHERE signal_name IN (
    'reserve_spread',
    'repo_cover_ratio',
    'ofz_bid_to_cover',
    'tax_week_flag',
    'treasury_net_flow'
);
