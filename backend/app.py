from fastapi import FastAPI, HTTPException, Depends, Request, Form, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import psycopg2
from psycopg2.extras import RealDictCursor
import cloudinary
import cloudinary.uploader
from pydantic import BaseModel
from typing import Optional, List
import os
import json
from datetime import datetime
import uuid
from passlib.context import CryptContext

app = FastAPI(title="DVT Mini App Backend")

# CORS settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Database connection
def get_db_connection():
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://dvt_user:password@localhost/dvt_database")
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    return conn

# Cloudinary configuration
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME", "dvt-cloud"),
    api_key=os.getenv("CLOUDINARY_API_KEY", "764846719658924"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET", "OmdiuCF8")
)

# Pydantic models
class UserCreate(BaseModel):
    telegram_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    refer_code: Optional[str] = None

class TaskCreate(BaseModel):
    title: str
    description: str
    cpa_link: str
    amount: float
    max_submissions: int = 100
    daily_limit: int = 3

class WithdrawalRequest(BaseModel):
    amount: float
    method: str
    account_number: str

# Routes
@app.get("/")
def read_root():
    return {"message": "DVT Mini App Backend API", "status": "running"}

@app.get("/api/health")
def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/api/user/{telegram_id}")
def get_user(telegram_id: int):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE telegram_id = %s", (telegram_id,))
    user = cur.fetchone()
    cur.close()
    conn.close()
    
    if user:
        return user
    raise HTTPException(status_code=404, detail="User not found")

@app.post("/api/user")
def create_user(user: UserCreate):
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Generate referral code if not provided
    refer_code = user.refer_code or f"DVT-{user.telegram_id}"
    
    cur.execute("""
        INSERT INTO users (telegram_id, username, first_name, refer_code, created_at)
        VALUES (%s, %s, %s, %s, NOW())
        ON CONFLICT (telegram_id) DO NOTHING
        RETURNING *
    """, (user.telegram_id, user.username, user.first_name, refer_code))
    
    new_user = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    
    if new_user:
        return new_user
    raise HTTPException(status_code=400, detail="User creation failed")

@app.get("/api/tasks")
def get_tasks(status: str = "active"):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM micro_jobs WHERE status = %s ORDER BY created_at DESC", (status,))
    tasks = cur.fetchall()
    cur.close()
    conn.close()
    return tasks

@app.post("/api/task")
def create_task(task: TaskCreate, admin_id: int = 1):
    conn = get_db_connection()
    cur = conn.cursor()
    
    task_id = f"MJ-{str(uuid.uuid4())[:8].upper()}"
    
    cur.execute("""
        INSERT INTO micro_jobs (task_id, title, description, cpa_link, amount, 
                               max_submissions, daily_limit, admin_id, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
        RETURNING *
    """, (task_id, task.title, task.description, task.cpa_link, task.amount,
          task.max_submissions, task.daily_limit, admin_id))
    
    new_task = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    
    return new_task

@app.post("/api/upload-screenshot")
async def upload_screenshot(file: UploadFile = File(...)):
    try:
        # Upload to Cloudinary
        result = cloudinary.uploader.upload(
            file.file,
            folder="dvt-screenshots",
            resource_type="image"
        )
        
        return {
            "success": True,
            "url": result["secure_url"],
            "public_id": result["public_id"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/submit-task")
async def submit_task(
    telegram_id: int = Form(...),
    task_id: str = Form(...),
    screenshot_url: str = Form(...)
):
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Get user id
    cur.execute("SELECT id FROM users WHERE telegram_id = %s", (telegram_id,))
    user = cur.fetchone()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get task amount
    cur.execute("SELECT amount FROM micro_jobs WHERE task_id = %s", (task_id,))
    task = cur.fetchone()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Insert submission
    cur.execute("""
        INSERT INTO task_submissions (user_id, task_id, screenshot_url, amount, created_at)
        VALUES (%s, %s, %s, %s, NOW())
        RETURNING *
    """, (user['id'], task_id, screenshot_url, task['amount']))
    
    submission = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    
    return submission

@app.post("/api/withdraw")
def create_withdrawal(request: WithdrawalRequest, telegram_id: int):
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Get user
    cur.execute("""
        SELECT id, cash_wallet, 
               (SELECT COUNT(*) FROM withdrawals WHERE user_id = users.id) as withdraw_count
        FROM users WHERE telegram_id = %s
    """, (telegram_id,))
    user = cur.fetchone()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check minimum balance
    if user['cash_wallet'] < 100:
        raise HTTPException(status_code=400, detail="Minimum balance ৳100 required")
    
    if request.amount < 100:
        raise HTTPException(status_code=400, detail="Minimum withdrawal ৳100")
    
    if request.amount > user['cash_wallet']:
        raise HTTPException(status_code=400, detail="Insufficient balance")
    
    # Calculate charges
    is_first = user['withdraw_count'] == 0
    service_charge = request.amount * 0.10
    fixed_fee = 10 if is_first else 0
    total_charges = service_charge + fixed_fee
    net_amount = request.amount - total_charges
    
    # Generate withdrawal ID
    withdraw_id = f"WD-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:4].upper()}"
    
    # Create withdrawal
    cur.execute("""
        INSERT INTO withdrawals (user_id, amount, net_amount, charges, method, 
                                account_number, is_first_withdrawal, status, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, 'pending', NOW())
        RETURNING *
    """, (user['id'], request.amount, net_amount, total_charges, request.method,
          request.account_number, is_first))
    
    withdrawal = cur.fetchone()
    
    # Update user balance
    cur.execute("""
        UPDATE users 
        SET cash_wallet = cash_wallet - %s
        WHERE id = %s
    """, (request.amount, user['id']))
    
    conn.commit()
    cur.close()
    conn.close()
    
    # Send notification to admin (in real app, use Telegram Bot)
    return withdrawal

# Admin routes
@app.get("/admin", response_class=HTMLResponse)
def admin_login_page(request: Request):
    return """
    <html>
    <head>
        <title>DVT Admin Login</title>
        <style>
            body { font-family: Arial; background: #f0f2f5; display: flex; justify-content: center; align-items: center; height: 100vh; }
            .login-box { background: white; padding: 40px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); width: 300px; }
            input { width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ddd; border-radius: 5px; }
            button { background: #4f46e5; color: white; border: none; padding: 10px; width: 100%; border-radius: 5px; cursor: pointer; }
            .error { color: red; font-size: 14px; }
        </style>
    </head>
    <body>
        <div class="login-box">
            <h2>🔐 Admin Login</h2>
            <form id="loginForm">
                <input type="password" id="password" placeholder="Admin Password" required>
                <button type="submit">Login</button>
                <div id="error" class="error"></div>
            </form>
        </div>
        <script>
            document.getElementById('loginForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                const password = document.getElementById('password').value;
                if(password === 'Mizu123@@') {
                    localStorage.setItem('admin_token', 'admin_logged_in');
                    window.location.href = '/admin/dashboard';
                } else {
                    document.getElementById('error').textContent = 'Wrong password!';
                }
            });
        </script>
    </body>
    </html>
    """

@app.get("/admin/dashboard", response_class=HTMLResponse)
def admin_dashboard(request: Request):
    # Check authentication
    # In production, use proper session/cookie auth
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Get stats
    cur.execute("SELECT COUNT(*) as total_users FROM users")
    total_users = cur.fetchone()['total_users']
    
    cur.execute("SELECT COUNT(*) as pending_tasks FROM task_submissions WHERE status = 'pending'")
    pending_tasks = cur.fetchone()['pending_tasks']
    
    cur.execute("SELECT COUNT(*) as today_tasks FROM micro_jobs WHERE DATE(created_at) = CURRENT_DATE")
    today_tasks = cur.fetchone()['today_tasks']
    
    cur.execute("SELECT SUM(amount) as total_revenue FROM withdrawals WHERE status = 'completed'")
    revenue = cur.fetchone()['total_revenue'] or 0
    
    cur.close()
    conn.close()
    
    return f"""
    <html>
    <head>
        <title>DVT Admin Dashboard</title>
        <style>
            body {{ font-family: Arial; background: #f0f2f5; margin: 0; padding: 20px; }}
            .dashboard {{ max-width: 1200px; margin: 0 auto; }}
            .header {{ background: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; }}
            .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 20px; }}
            .stat-card {{ background: white; padding: 20px; border-radius: 10px; }}
            .nav {{ display: flex; gap: 10px; margin-bottom: 20px; }}
            .nav button {{ padding: 10px 20px; background: #4f46e5; color: white; border: none; border-radius: 5px; cursor: pointer; }}
            table {{ width: 100%; background: white; border-radius: 10px; overflow: hidden; }}
            th, td {{ padding: 15px; text-align: left; border-bottom: 1px solid #ddd; }}
        </style>
    </head>
    <body>
        <div class="dashboard">
            <div class="header">
                <h1>🤖 DVT Admin Dashboard</h1>
                <p>Welcome back, Admin! | Last sync: Just now</p>
            </div>
            
            <div class="stats">
                <div class="stat-card">
                    <h3>👥 Active Users</h3>
                    <p style="font-size: 24px; font-weight: bold;">{total_users}</p>
                </div>
                <div class="stat-card">
                    <h3>📋 Today's Tasks</h3>
                    <p style="font-size: 24px; font-weight: bold;">{today_tasks}</p>
                </div>
                <div class="stat-card">
                    <h3>⏳ Pending Reviews</h3>
                    <p style="font-size: 24px; font-weight: bold;">{pending_tasks}</p>
                </div>
                <div class="stat-card">
                    <h3>💰 Revenue</h3>
                    <p style="font-size: 24px; font-weight: bold;">৳{revenue}</p>
                </div>
            </div>
            
            <div class="nav">
                <button onclick="window.location.href='/admin/tasks'">🧩 Manage Tasks</button>
                <button onclick="window.location.href='/admin/submissions'">📋 Review Submissions</button>
                <button onclick="window.location.href='/admin/withdrawals'">💸 Withdrawals</button>
                <button onclick="window.location.href='/admin/users'">👥 Users</button>
            </div>
            
            <div style="background: white; padding: 20px; border-radius: 10px;">
                <h3>📊 Quick Stats</h3>
                <div id="charts">Charts will be here</div>
            </div>
        </div>
        
        <script>
            // Auto refresh every 30 seconds
            setInterval(() => {{
                window.location.reload();
            }}, 30000);
        </script>
    </body>
    </html>
    """

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
