CREATE INDEX idx_trials_nct_number ON trials(nct_number);
EXPLAIN SELECT * FROM trials WHERE nct_number='NCT10000042';
