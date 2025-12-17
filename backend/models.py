from datetime import datetime
from typing import Optional
from pydantic import BaseModel

class User(BaseModel):
    id: int
    telegram_id: int
    username: Optional[str]
    first_name: Optional[str]
    balance: float = 0.0
    cash_wallet: float = 0.0
    refer_code: str
    referred_by: Optional[str]
    created_at: datetime

class MicroJob(BaseModel):
    id: int
    task_id: str
    title: str
    description: str
    cpa_link: str
    amount: float
    status: str = "active"
    max_submissions: int = 100
    daily_limit: int = 3
    admin_id: int
    created_at: datetime

class TaskSubmission(BaseModel):
    id: int
    user_id: int
    task_id: str
    screenshot_url: str
    status: str = "pending"
    admin_review: Optional[str]
    amount: float
    created_at: datetime

class Withdrawal(BaseModel):
    id: int
    user_id: int
    amount: float
    net_amount: float
    charges: float
    method: str
    account_number: str
    status: str = "pending"
    is_first_withdrawal: bool = True
    created_at: datetime
