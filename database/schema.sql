CREATE DATABASE IF NOT EXISTS campusconnect
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE campusconnect;

CREATE TABLE IF NOT EXISTS students (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    name VARCHAR(80) NOT NULL,
    email VARCHAR(160) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    college VARCHAR(120) NOT NULL DEFAULT '',
    course VARCHAR(100) NOT NULL DEFAULT '',
    study_year VARCHAR(40) NOT NULL DEFAULT '',
    bio VARCHAR(500) NOT NULL DEFAULT '',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_students_email (email),
    KEY idx_students_name (name),
    KEY idx_students_college (college),
    KEY idx_students_course (course)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS student_skills (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    student_id BIGINT UNSIGNED NOT NULL,
    skill VARCHAR(80) NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_student_skill (student_id, skill),
    KEY idx_skill (skill),
    CONSTRAINT fk_skills_student FOREIGN KEY (student_id)
      REFERENCES students(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS student_interests (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    student_id BIGINT UNSIGNED NOT NULL,
    interest VARCHAR(100) NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_student_interest (student_id, interest),
    KEY idx_interest (interest),
    CONSTRAINT fk_interests_student FOREIGN KEY (student_id)
      REFERENCES students(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS collaboration_requests (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    sender_id BIGINT UNSIGNED NOT NULL,
    receiver_id BIGINT UNSIGNED NOT NULL,
    message VARCHAR(500) NOT NULL DEFAULT '',
    status ENUM('pending', 'accepted', 'rejected') NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_request_pair (sender_id, receiver_id),
    KEY idx_requests_receiver_status (receiver_id, status),
    KEY idx_requests_sender_status (sender_id, status),
    CONSTRAINT fk_request_sender FOREIGN KEY (sender_id)
      REFERENCES students(id) ON DELETE CASCADE,
    CONSTRAINT fk_request_receiver FOREIGN KEY (receiver_id)
      REFERENCES students(id) ON DELETE CASCADE,
    CONSTRAINT chk_request_different_students CHECK (sender_id <> receiver_id)
) ENGINE=InnoDB;


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
