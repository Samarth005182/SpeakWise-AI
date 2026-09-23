-- Safe to run repeatedly: Will NOT wipe or delete existing data!

CREATE DATABASE IF NOT EXISTS speakwise;

USE speakwise;

-- =========================
-- 1. USERS TABLE
-- =========================
CREATE TABLE IF NOT EXISTS users (
    user_id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL
);

-- =========================
-- 2. SESSIONS TABLE
-- =========================
CREATE TABLE IF NOT EXISTS sessions (
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
-- 3. TAKES TABLE
-- =========================
CREATE TABLE IF NOT EXISTS takes (
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
-- 4. VIEW PERSISTED DATA
-- =========================
SELECT * FROM users;
SELECT * FROM sessions;
SELECT * FROM takes;
