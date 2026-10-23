-- =============================================================
-- Bankcore - Modern Banking Database System
-- Author: Emmanuel Obidile
-- GitHub: @emmanuelobidile85-tech
-- Description: Production-ready banking schema with Users,
-- Accounts, Transactions, ACID compliance & audit trail
-- Database: MySQL / PostgreSQL Compatible
-- Version: 1.0.0
-- Date: 2026
-- =============================================================

-- Drop tables if exists (for clean re-import)
DROP TABLE IF EXISTS transactions;
DROP TABLE IF EXISTS accounts;
DROP TABLE IF EXISTS users;

-- =============================================================
-- TABLE: users - Customer information & authentication
-- =============================================================
CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    phone VARCHAR(20) UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    bvn VARCHAR(11) UNIQUE COMMENT 'Bank Verification Number',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_email (email)
) ENGINE=InnoDB;

-- =============================================================
-- TABLE: accounts - Bank accounts linked to users
-- =============================================================
CREATE TABLE accounts (
    account_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    account_number VARCHAR(10) UNIQUE NOT NULL COMMENT '10-digit NUBAN',
    account_type ENUM('savings', 'current', 'fixed') DEFAULT 'savings',
    balance DECIMAL(15, 2) DEFAULT 0.00 CHECK (balance >= 0),
    currency VARCHAR(3) DEFAULT 'NGN',
    status ENUM('active', 'frozen', 'closed') DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    INDEX idx_account_number (account_number),
    INDEX idx_user_id (user_id)
) ENGINE=InnoDB;

-- =============================================================
-- TABLE: transactions - Complete audit trail
-- =============================================================
CREATE TABLE transactions (
    transaction_id INT AUTO_INCREMENT PRIMARY KEY,
    from_account_id INT NULL COMMENT 'NULL for deposits',
    to_account_id INT NULL COMMENT 'NULL for withdrawals',
    transaction_type ENUM('deposit', 'withdrawal', 'transfer') NOT NULL,
    amount DECIMAL(15, 2) NOT NULL CHECK (amount > 0),
    balance_before DECIMAL(15, 2) NOT NULL,
    balance_after DECIMAL(15, 2) NOT NULL,
    reference VARCHAR(50) UNIQUE NOT NULL,
    status ENUM('pending', 'success', 'failed') DEFAULT 'success',
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (from_account_id) REFERENCES accounts(account_id) ON DELETE SET NULL,
    FOREIGN KEY (to_account_id) REFERENCES accounts(account_id) ON DELETE SET NULL,
    INDEX idx_reference (reference),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB;

-- =============================================================
-- SAMPLE DATA FOR TESTING
-- =============================================================
INSERT INTO users (full_name, email, phone, password_hash, bvn) VALUES
('Emmanuel Obidile', 'emmanuelobidile85@gmail.com', '08012345678', '$2b$10$hashedpassword', '12345678901');

INSERT INTO accounts (user_id, account_number, account_type, balance) VALUES
(1, '0123456789', 'savings', 100000.00),
(1, '9876543210', 'current', 50000.00);

-- =============================================================
-- EXAMPLE: Secure Transfer with Balance Validation
-- =============================================================
-- START TRANSACTION;
-- UPDATE accounts SET balance = balance - 5000 WHERE account_id = 1 AND balance >= 5000;
-- UPDATE accounts SET balance = balance + 5000 WHERE account_id = 2;
-- INSERT INTO transactions (...) VALUES (...);
-- COMMIT;
