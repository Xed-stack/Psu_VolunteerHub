-- Explicit additive review migration. Back up and select the intended database first.
-- No source facts, reviews, or user records are deleted or backfilled.
DELIMITER $$
DROP PROCEDURE IF EXISTS migrate_finding_review_storage$$
CREATE PROCEDURE migrate_finding_review_storage()
BEGIN
 DECLARE user_type VARCHAR(64);
 DECLARE campus_type VARCHAR(64);
 DECLARE event_type VARCHAR(64);
 IF DATABASE() IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Select the existing application database first'; END IF;
 SELECT MAX(COLUMN_TYPE) INTO user_type FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='users' AND COLUMN_NAME='id';
 SELECT MAX(COLUMN_TYPE) INTO campus_type FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='campuses' AND COLUMN_NAME='id';
 SELECT MAX(COLUMN_TYPE) INTO event_type FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='events' AND COLUMN_NAME='id';
 IF user_type IS NULL OR campus_type IS NULL OR event_type IS NULL OR user_type NOT REGEXP '^(tinyint|smallint|mediumint|int|bigint)' OR campus_type NOT REGEXP '^(tinyint|smallint|mediumint|int|bigint)' OR event_type NOT REGEXP '^(tinyint|smallint|mediumint|int|bigint)' THEN
  SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Existing integer user, campus and activity primary keys are required';
 END IF;
 IF EXISTS(SELECT 1 FROM information_schema.TABLES WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='finding_reviews') AND (SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='finding_reviews' AND COLUMN_NAME IN ('id','finding_key','campus_id','event_id','year','activity_date','period_start','period_end','finding_type','status','fingerprint','snapshot','scope','assessment','recommendation','closure_reason','actor_id','version','created_at','updated_at')) <> 20 THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Existing review storage is incomplete; inspect before retrying'; END IF;
 IF EXISTS(SELECT 1 FROM information_schema.TABLES WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='finding_review_events') AND (SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='finding_review_events' AND COLUMN_NAME IN ('id','review_id','campus_id','actor_id','actor_name','action','content','created_at')) <> 8 THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Existing review storage is incomplete; inspect before retrying'; END IF;
 IF EXISTS(SELECT 1 FROM information_schema.TABLES WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='finding_reviews') AND NOT EXISTS(SELECT INDEX_NAME FROM information_schema.STATISTICS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='finding_reviews' GROUP BY INDEX_NAME HAVING MAX(NON_UNIQUE)=0 AND COUNT(*)=1 AND MAX(COLUMN_NAME)='finding_key') THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Review storage requires a unique finding key; inspect before retrying'; END IF;
 SET @review_ddl=CONCAT('CREATE TABLE IF NOT EXISTS finding_reviews (
	id INTEGER NOT NULL AUTO_INCREMENT,
	finding_key VARCHAR(64) NOT NULL,
	','campus_id ',campus_type,',
	','event_id ',event_type,',
	year INTEGER NOT NULL,
	activity_date DATETIME,
	period_start DATE,
	period_end DATE,
	finding_type VARCHAR(40) NOT NULL,
	status VARCHAR(24) NOT NULL,
	fingerprint VARCHAR(64) NOT NULL,
	snapshot JSON NOT NULL,
	scope JSON NOT NULL,
	assessment TEXT NOT NULL,
	recommendation VARCHAR(40) NOT NULL,
	closure_reason VARCHAR(40) NOT NULL,
	','actor_id ',user_type,',
	version INTEGER NOT NULL,
	created_at DATETIME NOT NULL,
	updated_at DATETIME NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (finding_key),
	FOREIGN KEY(campus_id) REFERENCES campuses (id),
	FOREIGN KEY(event_id) REFERENCES events (id) ON DELETE SET NULL,
	FOREIGN KEY(actor_id) REFERENCES users (id) ON DELETE SET NULL,
	INDEX ix_finding_reviews_campus_id (campus_id),
	INDEX ix_finding_reviews_status (status),
	INDEX ix_finding_reviews_event_id (event_id),
	INDEX ix_finding_reviews_year (year)
) ENGINE=InnoDB');
 PREPARE review_statement FROM @review_ddl; EXECUTE review_statement; DEALLOCATE PREPARE review_statement;
 SET @review_ddl=CONCAT('CREATE TABLE IF NOT EXISTS finding_review_events (
	id INTEGER NOT NULL AUTO_INCREMENT,
	review_id INTEGER NOT NULL,
	','campus_id ',campus_type,',
	','actor_id ',user_type,',
	actor_name VARCHAR(100) NOT NULL,
	action VARCHAR(32) NOT NULL,
	content JSON NOT NULL,
	created_at DATETIME NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(review_id) REFERENCES finding_reviews (id),
	FOREIGN KEY(campus_id) REFERENCES campuses (id),
	FOREIGN KEY(actor_id) REFERENCES users (id) ON DELETE SET NULL,
	INDEX ix_finding_review_events_campus_id (campus_id),
	INDEX ix_finding_review_events_action (action),
	INDEX ix_finding_review_events_created_at (created_at),
	INDEX ix_finding_review_events_review_id (review_id)
) ENGINE=InnoDB');
 PREPARE review_statement FROM @review_ddl; EXECUTE review_statement; DEALLOCATE PREPARE review_statement;
END$$
CALL migrate_finding_review_storage()$$
DROP PROCEDURE migrate_finding_review_storage$$
DELIMITER ;
