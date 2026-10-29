-- CampusConnect chat feature migration
-- Run this script against your existing campusconnect database.
-- It preserves current students and collaboration requests.

USE campusconnect;

CREATE TABLE IF NOT EXISTS chat_messages (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    collaboration_request_id BIGINT UNSIGNED NOT NULL,
    sender_id BIGINT UNSIGNED NOT NULL,
    message TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_chat_request_message (collaboration_request_id, id),
    KEY idx_chat_sender (sender_id),
    CONSTRAINT fk_chat_request FOREIGN KEY (collaboration_request_id)
      REFERENCES collaboration_requests(id) ON DELETE CASCADE,
    CONSTRAINT fk_chat_sender FOREIGN KEY (sender_id)
      REFERENCES students(id) ON DELETE CASCADE
) ENGINE=InnoDB;

SHOW TABLES;
