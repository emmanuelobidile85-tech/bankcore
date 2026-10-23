// =============================================================
// Bankcore - Core Banking Backend API
// Author: Emmanuel Obidile | @emmanuelobidile85-tech
// Stack: Node.js + Express + MySQL
// Description: Secure banking API with ACID transactions
// Version: 1.0.0
// =============================================================

const express = require('express');
const mysql = require('mysql2/promise');
const cors = require('cors');
const helmet = require('helmet');
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 3000;

// ==================== MIDDLEWARES ====================
app.use(helmet()); // Security headers
app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Request logger - Pro debugging
app.use((req, res, next) => {
    console.log(`[${new Date().toISOString()}] ${req.method} ${req.path}`);
    next();
});

// ==================== DATABASE CONFIG ====================
const dbConfig = {
    host: process.env.DB_HOST || 'localhost',
    user: process.env.DB_USER || 'root',
    password: process.env.DB_PASSWORD || '',
    database: process.env.DB_NAME || 'bankcore',
    waitForConnections: true,
    connectionLimit: 10,
    queueLimit: 0
};

const pool = mysql.createPool(dbConfig);

// Test DB connection
(async () => {
    try {
        const conn = await pool.getConnection();
        console.log('✅ MySQL Connected - Bankcore DB Ready');
        conn.release();
    } catch (err) {
        console.error('❌ DB Connection Failed:', err.message);
    }
})();

// ==================== HELPER: Generate Reference ====================
const generateReference = () => `TXN-${Date.now()}-${Math.random().toString(36).substr(2, 6).toUpperCase()}`;

// ==================== ROUTES ====================

// Health check
app.get('/', (req, res) => {
    res.json({
        status: 'success',
        message: '🏦 Bankcore API is running - Secure Banking System',
        version: '1.0.0',
        author: 'Emmanuel Obidile',
        endpoints: ['/accounts', '/transfer', '/transactions/:accountNumber']
    });
});

// Get all accounts with user info
app.get('/accounts', async (req, res) => {
    try {
        const [rows] = await pool.query(`
            SELECT a.account_number, a.account_type, a.balance, a.status, u.full_name, u.email
            FROM accounts a
            JOIN users u ON a.user_id = u.user_id
            WHERE a.status = 'active'
        `);
        res.json({ status: 'success', data: rows });
    } catch (err) {
        res.status(500).json({ status: 'error', message: err.message });
    }
});

// Get single account balance
app.get('/accounts/:accountNumber', async (req, res) => {
    try {
        const [rows] = await pool.query(
            'SELECT * FROM accounts WHERE account_number = ?',
            [req.params.accountNumber]
        );
        if (!rows.length) return res.status(404).json({ status: 'fail', message: 'Account not found' });
        res.json({ status: 'success', data: rows[0] });
    } catch (err) {
        res.status(500).json({ status: 'error', message: err.message });
    }
});

// ==================== SECURE TRANSFER - ACID COMPLIANT ====================
app.post('/transfer', async (req, res) => {
    const { from_account, to_account, amount, description } = req.body;

    // Validation - Pro level
    if (!from_account || !to_account || !amount) {
        return res.status(400).json({ status: 'fail', message: 'from_account, to_account, amount are required' });
    }
    if (from_account === to_account) {
        return res.status(400).json({ status: 'fail', message: 'Cannot transfer to same account' });
    }
    if (amount <= 0) {
        return res.status(400).json({ status: 'fail', message: 'Amount must be greater than 0' });
    }

    const connection = await pool.getConnection();
    try {
        await connection.beginTransaction();

        // 1. Lock and check sender account (FOR UPDATE prevents race condition)
        const [sender] = await connection.query(
            'SELECT * FROM accounts WHERE account_number = ? FOR UPDATE',
            [from_account]
        );
        if (!sender.length) throw new Error('Sender account not found');
        if (sender[0].balance < amount) throw new Error('Insufficient balance');
        if (sender[0].status !== 'active') throw new Error('Sender account is not active');

        // 2. Lock and check receiver
        const [receiver] = await connection.query(
            'SELECT * FROM accounts WHERE account_number = ? FOR UPDATE',
            [to_account]
        );
        if (!receiver.length) throw new Error('Receiver account not found');
        if (receiver[0].status !== 'active') throw new Error('Receiver account is not active');

        const senderBefore = parseFloat(sender[0].balance);
        const receiverBefore = parseFloat(receiver[0].balance);
        const reference = generateReference();

        // 3. Debit sender
        await connection.query(
            'UPDATE accounts SET balance = balance - ? WHERE account_number = ?',
            [amount, from_account]
        );

        // 4. Credit receiver
        await connection.query(
            'UPDATE accounts SET balance = balance + ? WHERE account_number = ?',
            [amount, to_account]
        );

        // 5. Log transaction - Audit trail
        await connection.query(
            `INSERT INTO transactions 
            (from_account_id, to_account_id, transaction_type, amount, balance_before, balance_after, reference, description) 
            VALUES (?, ?, 'transfer', ?, ?, ?, ?, ?)`,
            [
                sender[0].account_id,
                receiver[0].account_id,
                amount,
                senderBefore,
                senderBefore - amount,
                reference,
                description || `Transfer to ${to_account}`
            ]
        );

        await connection.commit();

        res.json({
            status: 'success',
            message: 'Transfer successful',
            data: { reference, from_account, to_account, amount, new_balance: senderBefore - amount }
        });

    } catch (err) {
        await connection.rollback();
        res.status(400).json({ status: 'fail', message: err.message });
    } finally {
        connection.release();
    }
});

// Get transaction history
app.get('/transactions/:accountNumber', async (req, res) => {
    try {
        const [account] = await pool.query('SELECT account_id FROM accounts WHERE account_number = ?', [req.params.accountNumber]);
        if (!account.length) return res.status(404).json({ status: 'fail', message: 'Account not found' });

        const [txns] = await pool.query(
            'SELECT * FROM transactions WHERE from_account_id = ? OR to_account_id = ? ORDER BY created_at DESC LIMIT 50',
            [account[0].account_id, account[0].account_id]
        );
        res.json({ status: 'success', count: txns.length, data: txns });
    } catch (err) {
        res.status(500).json({ status: 'error', message: err.message });
    }
});

// ==================== ERROR HANDLER ====================
app.use((req, res) => {
    res.status(404).json({ status: 'fail', message: `Route ${req.originalUrl} not found` });
});

// ==================== START SERVER ====================
app.listen(PORT, () => {
    console.log(`🚀 Bankcore Server running on http://localhost:${PORT}`);
    console.log(`📚 Docs: http://localhost:${PORT}/`);
});

module.exports = app;
