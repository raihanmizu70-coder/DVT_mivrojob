from fastapi import APIRouter, HTTPException, Depends
from typing import List
from datetime import datetime

from ..database import get_connection

router = APIRouter(prefix="/api/withdrawals", tags=["withdrawals"])

@router.get("/user/{telegram_id}")
def get_user_withdrawals(telegram_id: int):
    conn = get_connection()
    cur = conn.cursor()
    
    # Get user id
    cur.execute("SELECT id FROM users WHERE telegram_id = %s", (telegram_id,))
    user = cur.fetchone()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get withdrawals
    cur.execute("""
        SELECT * FROM withdrawals 
        WHERE user_id = %s 
        ORDER BY created_at DESC
        LIMIT 50
    """, (user['id'],))
    
    withdrawals = cur.fetchall()
    cur.close()
    conn.close()
    
    return withdrawals

@router.get("/calculate/{telegram_id}")
def calculate_withdrawal(telegram_id: int, amount: float):
    conn = get_connection()
    cur = conn.cursor()
    
    # Check if it's first withdrawal
    cur.execute("""
        SELECT 
            (SELECT COUNT(*) FROM withdrawals w 
             WHERE w.user_id = u.id) as withdraw_count
        FROM users u 
        WHERE u.telegram_id = %s
    """, (telegram_id,))
    
    result = cur.fetchone()
    
    if not result:
        cur.close()
        conn.close()
        raise HTTPException(status_code=404, detail="User not found")
    
    is_first = result['withdraw_count'] == 0
    
    # Calculate charges
    service_charge = amount * 0.10
    fixed_fee = 10 if is_first else 0
    total_charges = service_charge + fixed_fee
    net_amount = amount - total_charges
    
    cur.close()
    conn.close()
    
    return {
        "amount": amount,
        "is_first_withdrawal": is_first,
        "charges": {
            "service_charge": service_charge,
            "fixed_fee": fixed_fee,
            "total_charges": total_charges
        },
        "net_amount": net_amount,
        "you_will_receive": net_amount
    }

@router.post("/request/{telegram_id}")
def request_withdrawal(telegram_id: int, request_data: dict):
    conn = get_connection()
    cur = conn.cursor()
    
    amount = request_data.get("amount")
    method = request_data.get("method")
    account_number = request_data.get("account_number")
    
    # Validate amount
    if amount < 100:
        raise HTTPException(status_code=400, detail="Minimum withdrawal is ৳100")
    
    if amount % 100 != 0:
        raise HTTPException(status_code=400, detail="Amount must be in multiples of ৳100")
    
    # Get user info
    cur.execute("""
        SELECT 
            u.id,
            u.cash_wallet,
            (SELECT COUNT(*) FROM withdrawals w WHERE w.user_id = u.id) as withdraw_count
        FROM users u 
        WHERE u.telegram_id = %s
    """, (telegram_id,))
    
    user = cur.fetchone()
    
    if not user:
        cur.close()
        conn.close()
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check balance
    if user['cash_wallet'] < amount:
        raise HTTPException(status_code=400, detail="Insufficient cash wallet balance")
    
    # Calculate charges
    is_first = user['withdraw_count'] == 0
    service_charge = amount * 0.10
    fixed_fee = 10 if is_first else 0
    total_charges = service_charge + fixed_fee
    net_amount = amount - total_charges
    
    # Generate withdrawal ID
    from datetime import datetime
    import uuid
    withdraw_id = f"WD-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:4].upper()}"
    
    # Create withdrawal request
    cur.execute("""
        INSERT INTO withdrawals (
            user_id, amount, net_amount, charges, method, 
            account_number, is_first_withdrawal, status, created_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, 'pending', NOW())
        RETURNING *
    """, (
        user['id'], amount, net_amount, total_charges, 
        method, account_number, is_first
    ))
    
    withdrawal = cur.fetchone()
    
    # Deduct from cash wallet
    cur.execute("""
        UPDATE users 
        SET cash_wallet = cash_wallet - %s
        WHERE id = %s
    """, (amount, user['id']))
    
    conn.commit()
    
    # TODO: Send notification to admin via Telegram bot
    
    cur.close()
    conn.close()
    
    return {
        "success": True,
        "withdrawal": withdrawal,
        "message": "Withdrawal request submitted successfully"
    }

@router.get("/methods")
def get_withdrawal_methods():
    return {
        "methods": [
            {"id": "bkash", "name": "bKash", "icon": "💰", "min_amount": 100},
            {"id": "nagad", "name": "Nagad", "icon": "💸", "min_amount": 100},
            {"id": "rocket", "name": "Rocket", "icon": "🚀", "min_amount": 100}
        ]
    }

@router.get("/rules")
def get_withdrawal_rules():
    return {
        "rules": {
            "minimum_amount": 100,
            "amount_multiples": 100,
            "first_withdrawal_charge": "10% + ৳10 fixed fee",
            "regular_withdrawal_charge": "10% only",
            "processing_time": "24-48 hours",
            "available_methods": ["bKash", "Nagad", "Rocket"]
        },
        "examples": {
            "first_withdrawal": {
                "৳100": "You get ৳80 (৳10 + ৳10 fee)",
                "৳300": "You get ৳260 (৳30 + ৳10 fee)",
                "৳500": "You get ৳440 (৳50 + ৳10 fee)"
            },
            "regular_withdrawal": {
                "৳100": "You get ৳90",
                "৳300": "You get ৳270",
                "৳500": "You get ৳450"
            }
        }
    }
