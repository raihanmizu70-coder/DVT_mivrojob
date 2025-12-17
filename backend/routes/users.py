from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
import uuid

from ..database import get_connection

router = APIRouter(prefix="/api/users", tags=["users"])

@router.post("/register")
def register_user(telegram_data: dict):
    conn = get_connection()
    cur = conn.cursor()
    
    telegram_id = telegram_data.get("id")
    username = telegram_data.get("username")
    first_name = telegram_data.get("first_name")
    refer_code = telegram_data.get("refer_code")
    
    if not telegram_id:
        raise HTTPException(status_code=400, detail="Telegram ID is required")
    
    # Generate referral code
    if not refer_code:
        refer_code = f"DVT-{str(uuid.uuid4())[:8].upper()}"
    
    # Check if user exists
    cur.execute("SELECT * FROM users WHERE telegram_id = %s", (telegram_id,))
    existing_user = cur.fetchone()
    
    if existing_user:
        cur.close()
        conn.close()
        return existing_user
    
    # Create new user
    cur.execute("""
        INSERT INTO users (telegram_id, username, first_name, refer_code, created_at)
        VALUES (%s, %s, %s, %s, NOW())
        RETURNING *
    """, (telegram_id, username, first_name, refer_code))
    
    new_user = cur.fetchone()
    conn.commit()
    
    # If referred by someone
    referred_by = telegram_data.get("referred_by")
    if referred_by:
        cur.execute("""
            UPDATE users SET referred_by = %s 
            WHERE telegram_id = %s
        """, (referred_by, telegram_id))
        conn.commit()
    
    cur.close()
    conn.close()
    
    return new_user

@router.get("/{telegram_id}")
def get_user_profile(telegram_id: int):
    conn = get_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT * FROM users 
        WHERE telegram_id = %s
    """, (telegram_id,))
    
    user = cur.fetchone()
    
    if not user:
        cur.close()
        conn.close()
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get user stats
    cur.execute("""
        SELECT 
            COUNT(*) as total_tasks,
            SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as completed_tasks,
            SUM(CASE WHEN status = 'success' THEN amount ELSE 0 END) as total_earned,
            COUNT(DISTINCT referred_by) as referrals
        FROM task_submissions ts
        WHERE user_id = %s
    """, (user['id'],))
    
    stats = cur.fetchone()
    
    cur.close()
    conn.close()
    
    return {
        "user": user,
        "stats": stats
    }

@router.put("/{telegram_id}/balance")
def update_balance(telegram_id: int, update_data: dict):
    conn = get_connection()
    cur = conn.cursor()
    
    amount = update_data.get("amount")
    action = update_data.get("action")  # "add" or "subtract"
    wallet_type = update_data.get("wallet_type", "balance")  # "balance" or "cash_wallet"
    
    if wallet_type not in ["balance", "cash_wallet"]:
        raise HTTPException(status_code=400, detail="Invalid wallet type")
    
    # Get current balance
    cur.execute(f"SELECT {wallet_type} FROM users WHERE telegram_id = %s", (telegram_id,))
    user = cur.fetchone()
    
    if not user:
        cur.close()
        conn.close()
        raise HTTPException(status_code=404, detail="User not found")
    
    current_balance = user[wallet_type]
    
    if action == "add":
        new_balance = current_balance + amount
    elif action == "subtract":
        if current_balance < amount:
            raise HTTPException(status_code=400, detail="Insufficient balance")
        new_balance = current_balance - amount
    else:
        raise HTTPException(status_code=400, detail="Invalid action")
    
    # Update balance
    cur.execute(f"""
        UPDATE users 
        SET {wallet_type} = %s
        WHERE telegram_id = %s
        RETURNING *
    """, (new_balance, telegram_id))
    
    updated_user = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    
    return updated_user

@router.post("/{telegram_id}/transfer")
def transfer_to_cash_wallet(telegram_id: int, transfer_data: dict):
    conn = get_connection()
    cur = conn.cursor()
    
    amount = transfer_data.get("amount")
    
    if amount < 10:
        raise HTTPException(status_code=400, detail="Minimum transfer amount is ৳10")
    
    # Check if user has enough balance
    cur.execute("SELECT balance FROM users WHERE telegram_id = %s", (telegram_id,))
    user = cur.fetchone()
    
    if not user:
        cur.close()
        conn.close()
        raise HTTPException(status_code=404, detail="User not found")
    
    if user['balance'] < amount:
        raise HTTPException(status_code=400, detail="Insufficient main wallet balance")
    
    # Transfer from balance to cash wallet
    cur.execute("""
        UPDATE users 
        SET balance = balance - %s,
            cash_wallet = cash_wallet + %s
        WHERE telegram_id = %s
        RETURNING *
    """, (amount, amount, telegram_id))
    
    updated_user = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    
    return updated_user

@router.get("/{telegram_id}/referrals")
def get_user_referrals(telegram_id: int):
    conn = get_connection()
    cur = conn.cursor()
    
    # Get user's referral code
    cur.execute("SELECT refer_code FROM users WHERE telegram_id = %s", (telegram_id,))
    user = cur.fetchone()
    
    if not user:
        cur.close()
        conn.close()
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get referrals
    cur.execute("""
        SELECT u.*, 
               (SELECT COUNT(*) FROM withdrawals w WHERE w.user_id = u.id) as withdrawals_count
        FROM users u
        WHERE u.referred_by = %s
        ORDER BY u.created_at DESC
    """, (user['refer_code'],))
    
    referrals = cur.fetchall()
    
    # Get referral stats
    cur.execute("""
        SELECT 
            COUNT(*) as total_referrals,
            SUM(CASE WHEN (SELECT COUNT(*) FROM withdrawals w WHERE w.user_id = u.id) > 0 THEN 1 ELSE 0 END) as active_referrals,
            SUM(CASE WHEN (SELECT COUNT(*) FROM withdrawals w WHERE w.user_id = u.id) > 0 THEN 5 ELSE 0 END) as total_bonus_earned
        FROM users u
        WHERE u.referred_by = %s
    """, (user['refer_code'],))
    
    stats = cur.fetchone()
    
    cur.close()
    conn.close()
    
    return {
        "referrals": referrals,
        "stats": stats
    }
