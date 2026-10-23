"""

Bankcore - Python Banking Service (Flask)
Author: Emmanuel Obidile | @emmanuelobidile85-tech
Stack: Python + Flask + MySQL
Description: Lightweight banking microservice for Python lovers
            Handles account queries & transaction validation
Version: 1.0.0 | 2026

"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import mysql.connector
from mysql.connector import pooling
import os
from datetime import datetime
import random
import string
from decimal import Decimal
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

# ==================== DATABASE POOL ====================
db_pool = pooling.MySQLConnectionPool(
    pool_name="bankcore_pool",
    pool_size=5,
    host=os.getenv("DB_HOST", "localhost"),
    user=os.getenv("DB_USER", "root"),
    password=os.getenv("DB_PASSWORD", ""),
    database=os.getenv("DB_NAME", "bankcore")
)

def get_db():
    """Get DB connection from pool - pro pattern"""
    return db_pool.get_connection()

def generate_reference():
    """Generate unique transaction reference"""
    rand = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"TXN-{int(datetime.now().timestamp())}-{rand}"

# ==================== ROUTES ====================

@app.route('/', methods=['GET'])
def health_check():
    """API Health & Info"""
    return jsonify({
        "status": "success",
        "service": "Bankcore Python Service",
        "message": "🏦 Python Banking Microservice Running",
        "version": "1.0.0",
        "author": "Emmanuel Obidile",
        "stack": "Flask + MySQL",
        "endpoints": [
            "GET /accounts",
            "GET /accounts/<account_number>",
            "POST /validate-transfer",
            "GET /stats"
        ]
    }), 200

@app.route('/accounts', methods=['GET'])
def get_accounts():
    """Fetch all active accounts - with join"""
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT 
                a.account_number, 
                a.account_type, 
                a.balance, 
                a.currency,
                a.status,
                u.full_name,
                u.email
            FROM accounts a
            JOIN users u ON a.user_id = u.user_id
            WHERE a.status = 'active'
            ORDER BY a.created_at DESC
        """)
        accounts = cursor.fetchall()
        # Convert Decimal to float for JSON
        for acc in accounts:
            acc['balance'] = float(acc['balance'])
        return jsonify({"status": "success", "count": len(accounts), "data": accounts}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/accounts/<account_number>', methods=['GET'])
def get_single_account(account_number):
    """Get single account details + recent transactions"""
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        
        # Get account
        cursor.execute("SELECT * FROM accounts WHERE account_number = %s", (account_number,))
        account = cursor.fetchone()
        
        if not account:
            return jsonify({"status": "fail", "message": "Account not found"}), 404
        
        account['balance'] = float(account['balance'])
        
        # Get last 5 transactions
        cursor.execute("""
            SELECT transaction_type, amount, reference, status, created_at 
            FROM transactions 
            WHERE from_account_id = %s OR to_account_id = %s 
            ORDER BY created_at DESC LIMIT 5
        """, (account['account_id'], account['account_id']))
        
        recent_txns = cursor.fetchall()
        for txn in recent_txns:
            txn['amount'] = float(txn['amount'])
        
        return jsonify({
            "status": "success",
            "data": {
                "account": account,
                "recent_transactions": recent_txns
            }
        }), 200
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/validate-transfer', methods=['POST'])
def validate_transfer():
    """
    Validates transfer without executing - for frontend check
    Shows pro separation of concerns: validation vs execution
    """
    data = request.get_json()
    
    from_acc = data.get('from_account')
    to_acc = data.get('to_account')
    amount = data.get('amount')
    
    # Pro validation
    if not all([from_acc, to_acc, amount]):
        return jsonify({"status": "fail", "message": "from_account, to_account, amount required"}), 400
    
    try:
        amount = Decimal(str(amount))
        if amount <= 0:
            return jsonify({"status": "fail", "message": "Amount must be > 0"}), 400
    except:
        return jsonify({"status": "fail", "message": "Invalid amount format"}), 400
    
    if from_acc == to_acc:
        return jsonify({"status": "fail", "message": "Cannot transfer to same account"}), 400
    
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        
        # Check both accounts exist and active
        cursor.execute("SELECT account_number, balance, status FROM accounts WHERE account_number IN (%s, %s)", (from_acc, to_acc))
        # Workaround for IN clause
        cursor.execute("SELECT account_number, balance, status FROM accounts WHERE account_number = %s OR account_number = %s", (from_acc, to_acc))
        found = cursor.fetchall()
        
        if len(found) != 2:
            return jsonify({"status": "fail", "message": "One or both accounts not found"}), 404
        
        sender = next((a for a in found if a['account_number'] == from_acc), None)
        
        if sender['status'] != 'active':
            return jsonify({"status": "fail", "message": "Sender account not active"}), 400
        
        if float(sender['balance']) < float(amount):
            return jsonify({
                "status": "fail",
                "message": "Insufficient balance",
                "data": {"current_balance": float(sender['balance']), "required": float(amount)}
            }), 400
        
        return jsonify({
            "status": "success",
            "message": "Transfer can proceed",
            "data": {
                "from_account": from_acc,
                "to_account": to_acc,
                "amount": float(amount),
                "estimated_new_balance": float(sender['balance']) - float(amount),
                "reference_preview": generate_reference()
            }
        }), 200
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/stats', methods=['GET'])
def get_stats():
    """Dashboard stats - pro analytics"""
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT COUNT(*) as total_users FROM users")
        users = cursor.fetchone()
        
        cursor.execute("SELECT COUNT(*) as total_accounts, SUM(balance) as total_balance FROM accounts WHERE status='active'")
        accounts = cursor.fetchone()
        
        cursor.execute("SELECT COUNT(*) as total_txns, SUM(amount) as total_volume FROM transactions WHERE status='success'")
        txns = cursor.fetchone()
        
        return jsonify({
            "status": "success",
            "data": {
                "users": users['total_users'],
                "accounts": accounts['total_accounts'],
                "total_balance": float(accounts['total_balance'] or 0),
                "transactions": txns['total_txns'],
                "total_volume": float(txns['total_volume'] or 0)
            }
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if conn:
            conn.close()

# ==================== ERROR HANDLERS ====================
@app.errorhandler(404)
def not_found(e):
    return jsonify({"status": "fail", "message": "Endpoint not found"}), 404

# ==================== RUN ====================
if __name__ == '__main__':
    print("🚀 Bankcore Python Service starting...")
    print("📚 Docs: http://localhost:5000/")
    app.run(host='0.0.0.0', port=5000, debug=True)
