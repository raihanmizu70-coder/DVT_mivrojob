from fastapi import APIRouter, HTTPException, Depends, Request, Form
from typing import List
import json

from ..database import get_connection

router = APIRouter(prefix="/api/admin", tags=["admin"])

# Simple authentication check
def verify_admin(request: Request):
    # In production, use proper JWT or session auth
    # For demo, we'll use a simple check
    auth_token = request.headers.get("Authorization")
    if not auth_token or auth_token != "Bearer admin_token":
        raise HTTPException(status_code=401, detail="Unauthorized")

@router.get("/stats")
def get_admin_stats(_: Request = Depends(verify_admin)):
    conn = get_connection()
    cur = conn.cursor()
    
    # Total stats
    cur.execute("SELECT COUNT(*) as total_users FROM users")
    total_users = cur.fetchone()['total_users']
    
    cur.execute("SELECT COUNT(*) as active_tasks FROM micro_jobs WHERE status = 'active'")
    active_tasks = cur.fetchone()['active_tasks']
    
    cur.execute("""
        SELECT COUNT(*) as pending_reviews 
        FROM task_submissions 
        WHERE status = 'pending'
    """)
    pending_reviews = cur.fetchone()['pending_reviews']
    
    cur.execute("""
        SELECT COUNT(*) as pending_withdrawals 
        FROM withdrawals 
        WHERE status = 'pending'
    """)
    pending_withdrawals = cur.fetchone()['pending_withdrawals']
    
    # Today's stats
    cur.execute("""
        SELECT COUNT(*) as today_users 
        FROM users 
        WHERE DATE(created_at) = CURRENT_DATE
    """)
    today_users = cur.fetchone()['today_users']
    
    cur.execute("""
        SELECT SUM(amount) as today_revenue 
        FROM withdrawals 
        WHERE DATE(created_at) = CURRENT_DATE AND status = 'completed'
    """)
    today_revenue = cur.fetchone()['today_revenue'] or 0
    
    cur.execute("""
        SELECT COUNT(*) as today_submissions 
        FROM task_submissions 
        WHERE DATE(created_at) = CURRENT_DATE
    """)
    today_submissions = cur.fetchone()['today_submissions']
    
    cur.close()
    conn.close()
    
    return {
        "total_users": total_users,
        "active_tasks": active_tasks,
        "pending_reviews": pending_reviews,
        "pending_withdrawals": pending_withdrawals,
        "today_users": today_users,
        "today_revenue": today_revenue,
        "today_submissions": today_submissions
    }

@router.get("/submissions/pending")
def get_pending_submissions(_: Request = Depends(verify_admin)):
    conn = get_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT ts.*, u.telegram_id, u.username, u.first_name, mj.title as task_title, mj.amount
        FROM task_submissions ts
        JOIN users u ON ts.user_id = u.id
        JOIN micro_jobs mj ON ts.task_id = mj.task_id
        WHERE ts.status = 'pending'
        ORDER BY ts.created_at ASC
    """)
    
    submissions = cur.fetchall()
    cur.close()
    conn.close()
    
    return submissions

@router.post("/submissions/{submission_id}/review")
def review_submission(
    submission_id: int, 
    review_data: dict,
    _: Request = Depends(verify_admin)
):
    conn = get_connection()
    cur = conn.cursor()
    
    status = review_data.get("status")  # "success" or "rejected"
    admin_review = review_data.get("admin_review", "")
    adjusted_amount = review_data.get("adjusted_amount")
    
    if status not in ["success", "rejected"]:
        raise HTTPException(status_code=400, detail="Invalid status")
    
    # Get submission details
    cur.execute("""
        SELECT ts.*, u.id as user_id, ts.amount as original_amount
        FROM task_submissions ts
        JOIN users u ON ts.user_id = u.id
        WHERE ts.id = %s
    """, (submission_id,))
    
    submission = cur.fetchone()
    
    if not submission:
        cur.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Submission not found")
    
    # Update submission status
    amount = adjusted_amount if adjusted_amount else submission['original_amount']
    
    cur.execute("""
        UPDATE task_submissions 
        SET status = %s, 
            admin_review = %s,
            amount = %s
        WHERE id = %s
        RETURNING *
    """, (status, admin_review, amount, submission_id))
    
    updated_submission = cur.fetchone()
    
    # If approved, add amount to user's balance
    if status == "success":
        cur.execute("""
            UPDATE users 
            SET balance = balance + %s
            WHERE id = %s
        """, (amount, submission['user_id']))
    
    conn.commit()
    cur.close()
    conn.close()
    
    return updated_submission

@router.get("/withdrawals/pending")
def get_pending_withdrawals(_: Request = Depends(verify_admin)):
    conn = get_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT w.*, u.telegram_id, u.username, u.first_name
        FROM withdrawals w
        JOIN users u ON w.user_id = u.id
        WHERE w.status = 'pending'
        ORDER BY w.created_at ASC
    """)
    
    withdrawals = cur.fetchall()
    cur.close()
    conn.close()
    
    return withdrawals

@router.post("/withdrawals/{withdrawal_id}/process")
def process_withdrawal(
    withdrawal_id: int,
    process_data: dict,
    _: Request = Depends(verify_admin)
):
    conn = get_connection()
    cur = conn.cursor()
    
    status = process_data.get("status")  # "completed" or "cancelled"
    admin_note = process_data.get("admin_note", "")
    
    if status not in ["completed", "cancelled"]:
        raise HTTPException(status_code=400, detail="Invalid status")
    
    # Get withdrawal details
    cur.execute("""
        SELECT w.*, u.id as user_id
        FROM withdrawals w
        JOIN users u ON w.user_id = u.id
        WHERE w.id = %s
    """, (withdrawal_id,))
    
    withdrawal = cur.fetchone()
    
    if not withdrawal:
        cur.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Withdrawal not found")
    
    # Update withdrawal status
    cur.execute("""
        UPDATE withdrawals 
        SET status = %s,
            admin_note = %s,
            processed_at = NOW()
        WHERE id = %s
        RETURNING *
    """, (status, admin_note, withdrawal_id))
    
    updated_withdrawal = cur.fetchone()
    
    # If cancelled, return amount to user's cash wallet
    if status == "cancelled":
        cur.execute("""
            UPDATE users 
            SET cash_wallet = cash_wallet + %s
            WHERE id = %s
        """, (withdrawal['amount'], withdrawal['user_id']))
    
    conn.commit()
    cur.close()
    conn.close()
    
    return updated_withdrawal

@router.get("/users/all")
def get_all_users(
    page: int = 1,
    limit: int = 20,
    _: Request = Depends(verify_admin)
):
    conn = get_connection()
    cur = conn.cursor()
    
    offset = (page - 1) * limit
    
    cur.execute("""
        SELECT 
            u.*,
            (SELECT COUNT(*) FROM task_submissions ts WHERE ts.user_id = u.id AND ts.status = 'success') as completed_tasks,
            (SELECT COUNT(*) FROM withdrawals w WHERE w.user_id = u.id AND w.status = 'completed') as withdrawals_count,
            (SELECT COUNT(*) FROM users u2 WHERE u2.referred_by = u.refer_code) as referrals_count
        FROM users u
        ORDER BY u.created_at DESC
        LIMIT %s OFFSET %s
    """, (limit, offset))
    
    users = cur.fetchall()
    
    # Get total count for pagination
    cur.execute("SELECT COUNT(*) as total FROM users")
    total = cur.fetchone()['total']
    
    cur.close()
    conn.close()
    
    return {
        "users": users,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit
        }
    }
