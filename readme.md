# 🏦 Bankcore - Core Banking System

> A production-ready REST API for secure banking transactions, built with Node.js, Python & MySQL.

**Live Demo:** `localhost:3000` | **Author:** Emmanuel Obidile - Backend Engineer | Lagos, NG
**GitHub:** emmanuelobidile85-tech | **Stack:** Node.js, Express, Python Flask, MySQL

### 🔥 Why This Project Will Get Me Hired

This is not tutorial code. I implemented real banking logic used by Paystack & Flutterwave:
- **ACID Transactions** with `COMMIT/ROLLBACK` - money never disappears
- **FOR UPDATE Lock** - prevents double-spending / race condition
- **Audit Trail** - logs balance_before & balance_after for every transfer
- **DECIMAL(15,2)** - no floating point error, no kobo lost
- **Security:** Helmet, CORS, parameterized queries (no SQL injection)

### 🛠️ Tech Stack
Node.js, Express.js, Python Flask, MySQL 8.0, REST API, Git

### 🚀 How To Run
```bash
git clone https://github.com/emmanuelobidile85-tech/bankcore.git
cd bankcore
npm install
# setup your .env with DB credentials
mysql -u root -p < schema.sql
npm start
