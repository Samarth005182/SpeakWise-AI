DROP DATABASE IF EXISTS speakwise;

CREATE DATABASE speakwise;

USE speakwise;

DROP USER IF EXISTS 'speakwise_user'@'localhost';

CREATE USER 'speakwise_user'@'localhost'
IDENTIFIED BY 'SpeakWise@123';

GRANT ALL PRIVILEGES
ON speakwise.*
TO 'speakwise_user'@'localhost';

FLUSH PRIVILEGES;


-- =========================
-- USERS
-- =========================

CREATE TABLE users (
    user_id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL
);


-- =========================
-- SESSIONS
-- =========================

CREATE TABLE sessions (
    session_id INT PRIMARY KEY AUTO_INCREMENT,

    user_id INT NOT NULL,

    category VARCHAR(100) NOT NULL,
    topic_name VARCHAR(255) NOT NULL,
    speaking_time INT NOT NULL,

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id)
        REFERENCES users(user_id)
        ON DELETE CASCADE
);


-- =========================
-- TAKES
-- =========================

CREATE TABLE takes (
    take_id INT PRIMARY KEY AUTO_INCREMENT,

    session_id INT NOT NULL,

    audio_path VARCHAR(500),
    video_path VARCHAR(500),

    transcription TEXT,
    report TEXT,

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (session_id)
        REFERENCES sessions(session_id)
        ON DELETE CASCADE
);


-- =========================
-- CHECK DATA
-- =========================

SELECT * FROM users;

SELECT * FROM sessions;

SELECT * FROM takes;