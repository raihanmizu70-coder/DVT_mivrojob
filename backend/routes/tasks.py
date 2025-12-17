from fastapi import APIRouter, HTTPException, Depends
from typing import List
import uuid
from datetime import datetime

from ..database import get_connection
from ..models import MicroJob

router = APIRouter(prefix="/api/tasks", tags=["tasks"])

@router.get("/", response_model=List[dict])
def get_all_tasks(status: str = "active", limit: int = 50):
    conn = get_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT * FROM micro_jobs 
        WHERE status = %s 
        ORDER BY created_at DESC 
        LIMIT %s
    """, (status, limit))
    
    tasks = cur.fetchall()
    cur.close()
    conn.close()
    
    return tasks

@router.get("/{task_id}")
def get_task(task_id: str):
    conn = get_connection()
    cur = conn.cursor()
    
    cur.execute("SELECT * FROM micro_jobs WHERE task_id = %s", (task_id,))
    task = cur.fetchone()
    
    cur.close()
    conn.close()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return task

@router.post("/")
def create_task(task_data: dict):
    conn = get_connection()
    cur = conn.cursor()
    
    task_id = f"MJ-{str(uuid.uuid4())[:8].upper()}"
    
    cur.execute("""
        INSERT INTO micro_jobs (task_id, title, description, cpa_link, amount, 
                               max_submissions, daily_limit, admin_id, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
        RETURNING *
    """, (
        task_id, 
        task_data.get("title"),
        task_data.get("description"),
        task_data.get("cpa_link"),
        task_data.get("amount", 3.0),
        task_data.get("max_submissions", 100),
        task_data.get("daily_limit", 3),
        1  # admin_id
    ))
    
    new_task = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    
    return new_task

@router.put("/{task_id}")
def update_task(task_id: str, task_data: dict):
    conn = get_connection()
    cur = conn.cursor()
    
    # Build update query dynamically
    updates = []
    values = []
    
    for key, value in task_data.items():
        if key in ["title", "description", "cpa_link", "amount", "status", "max_submissions", "daily_limit"]:
            updates.append(f"{key} = %s")
            values.append(value)
    
    if not updates:
        raise HTTPException(status_code=400, detail="No valid fields to update")
    
    values.append(task_id)
    
    query = f"""
        UPDATE micro_jobs 
        SET {', '.join(updates)}
        WHERE task_id = %s
        RETURNING *
    """
    
    cur.execute(query, values)
    updated_task = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    
    if not updated_task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return updated_task

@router.delete("/{task_id}")
def delete_task(task_id: str):
    conn = get_connection()
    cur = conn.cursor()
    
    cur.execute("DELETE FROM micro_jobs WHERE task_id = %s RETURNING *", (task_id,))
    deleted_task = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    
    if not deleted_task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return {"message": "Task deleted successfully"}

@router.get("/user/{telegram_id}/submissions")
def get_user_submissions(telegram_id: int):
    conn = get_connection()
    cur = conn.cursor()
    
    # Get user id first
    cur.execute("SELECT id FROM users WHERE telegram_id = %s", (telegram_id,))
    user = cur.fetchone()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get submissions
    cur.execute("""
        SELECT ts.*, mj.title as task_title
        FROM task_submissions ts
        JOIN micro_jobs mj ON ts.task_id = mj.task_id
        WHERE ts.user_id = %s
        ORDER BY ts.created_at DESC
    """, (user['id'],))
    
    submissions = cur.fetchall()
    cur.close()
    conn.close()
    
    return submissions
