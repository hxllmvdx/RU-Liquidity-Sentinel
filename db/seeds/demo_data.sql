INSERT INTO data_sources (source_code, name, source_type)
VALUES
    ('cbr_repo', 'CBR Repo Auctions', 'public_api'),
    ('minfin_ofz', 'Minfin OFZ Placements', 'public_site')
ON CONFLICT (source_code) DO NOTHING;
