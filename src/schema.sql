CREATE TABLE file_inventory (
	sclk INTEGER,
	file_name TEXT PRIMARY KEY,
	file_type TEXT, 
	file_path TEXT
);
CREATE TABLE sample_registry (
	sclk INTEGER PRIMARY KEY,
	sample_name INTEGER, 
	target_id TEXT, 
	nominal_sol INTEGER
, scan_type TEXT);
CREATE TABLE processing_status (
	sclk INTEGER PRIMARY KEY,
	raw_spectra_ready INTEGER DEFAULT 0,
	raw_abundance_ready INTEGER DEFAULT 0,
	metadata_ready INTEGER DEFAULT 0,	
	molar_ready INTEGER DEFAULT 0, 
	is_processed INTEGER DEFAULT 0
, analysis_ready INTEGER, mapping_created INTEGER);
CREATE TABLE classification_definitions 
(
mineral_id INTEGER PRIMARY KEY AUTOINCREMENT,
mineral_name TEXT NOT NULL,
priority_rank INT NOT NULL
);
CREATE TABLE sqlite_sequence(name,seq);
CREATE TABLE mineral_rules
(
rule_id INTEGER PRIMARY KEY AUTOINCREMENT,
mineral_id INTEGER NOT NULL,
group_id TEXT NOT NULL,
parameter TEXT NOT NULL,
min_val REAL,
max_val REAL,
FOREIGN KEY (mineral_id) REFERENCES classification_definitions(mineral_id)
);
