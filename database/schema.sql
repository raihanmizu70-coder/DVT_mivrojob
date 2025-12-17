-- Database schema for DVT Mini App

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    username VARCHAR(100),
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    balance DECIMAL(10,2) DEFAULT 0.00,
    cash_wallet DECIMAL(10,2) DEFAULT 0.00,
    refer_code VARCHAR(50) UNIQUE NOT NULL,
    referred_by VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Micro Jobs table
CREATE TABLE IF NOT EXISTS micro_jobs (
    id SERIAL PRIMARY KEY,
    task_id VARCHAR(50) UNIQUE NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    cpa_link TEXT NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    status VARCHAR(20) DEFAULT 'active',
    max_submissions INTEGER DEFAULT 100,
    daily_limit INTEGER DEFAULT 3,
    total_submissions INTEGER DEFAULT 0,
    today_submissions INTEGER DEFAULT 0,
    admin_id INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP
);

-- Task Submissions table
CREATE TABLE IF NOT EXISTS task_submissions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    task_id VARCHAR(50) NOT NULL,
    screenshot_url TEXT NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    admin_review TEXT,
    amount DECIMAL(10,2) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    reviewed_at TIMESTAMP,
    reviewed_by INTEGER
);

-- Withdrawals table
CREATE TABLE IF NOT EXISTS withdrawals (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    amount DECIMAL(10,2) NOT NULL,
    net_amount DECIMAL(10,2) NOT NULL,
    charges DECIMAL(10,2) NOT NULL,
    method VARCHAR(50) NOT NULL,
    account_number VARCHAR(100) NOT NULL,
    account_name VARCHAR(100),
    status VARCHAR(20) DEFAULT 'pending',
    is_first_withdrawal BOOLEAN DEFAULT TRUE,
    admin_note TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    processed_at TIMESTAMP,
    transaction_id VARCHAR(100)
);

-- Referral bonuses table
CREATE TABLE IF NOT EXISTS referral_bonuses (
    id SERIAL PRIMARY KEY,
    referrer_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    referred_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    amount DECIMAL(10,2) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW(),
    credited_at TIMESTAMP
);

-- Transactions table
CREATE TABLE IF NOT EXISTS transactions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL, -- 'task_earnings', 'referral_bonus', 'withdrawal', 'transfer'
    amount DECIMAL(10,2) NOT NULL,
    description TEXT,
    reference_id VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Admin logs table
CREATE TABLE IF NOT EXISTS admin_logs (
    id SERIAL PRIMARY KEY,
    admin_id INTEGER,
    action VARCHAR(100) NOT NULL,
    details JSONB,
    ip_address VARCHAR(50),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id);
CREATE INDEX IF NOT EXISTS idx_users_refer_code ON users(refer_code);
CREATE INDEX IF NOT EXISTS idx_micro_jobs_status ON micro_jobs(status);
CREATE INDEX IF NOT EXISTS idx_micro_jobs_created_at ON micro_jobs(created_at);
CREATE INDEX IF NOT EXISTS idx_task_submissions_status ON task_submissions(status);
CREATE INDEX IF NOT EXISTS idx_task_submissions_user_id ON task_submissions(user_id);
CREATE INDEX IF NOT EXISTS idx_withdrawals_status ON withdrawals(status);
CREATE INDEX IF NOT EXISTS idx_withdrawals_user_id ON withdrawals(user_id);
CREATE INDEX IF NOT EXISTS idx_transactions_user_id ON transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_transactions_created_at ON transactions(created_at);

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_micro_jobs_updated_at BEFORE UPDATE ON micro_jobs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Create function to generate task_id
CREATE OR REPLACE FUNCTION generate_task_id()
RETURNS TRIGGER AS $$
BEGIN
    NEW.task_id = 'MJ-' || TO_CHAR(NEW.id, 'FM00000');
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger for task_id (optional, we'll generate in app)
-- CREATE TRIGGER generate_task_id_trigger BEFORE INSERT ON micro_jobs
--     FOR EACH ROW EXECUTE FUNCTION generate_task_id();

-- Create view for user statistics
CREATE OR REPLACE VIEW user_stats AS
SELECT 
    u.id,
    u.telegram_id,
    u.username,
    u.first_name,
    u.balance,
    u.cash_wallet,
    u.refer_code,
    u.created_at,
    COUNT(DISTINCT ts.id) as total_tasks,
    COUNT(DISTINCT CASE WHEN ts.status = 'success' THEN ts.id END) as completed_tasks,
    COALESCE(SUM(CASE WHEN ts.status = 'success' THEN ts.amount ELSE 0 END), 0) as total_earned,
    COUNT(DISTINCT w.id) as withdrawals_count,
    COUNT(DISTINCT u2.id) as referrals_count
FROM users u
LEFT JOIN task_submissions ts ON u.id = ts.user_id
LEFT JOIN withdrawals w ON u.id = w.user_id AND w.status = 'completed'
LEFT JOIN users u2 ON u2.referred_by = u.refer_code
GROUP BY u.id;

-- Create view for admin dashboard
CREATE OR REPLACE VIEW admin_dashboard AS
SELECT 
    (SELECT COUNT(*) FROM users) as total_users,
    (SELECT COUNT(*) FROM micro_jobs WHERE status = 'active') as active_tasks,
    (SELECT COUNT(*) FROM task_submissions WHERE status = 'pending') as pending_reviews,
    (SELECT COUNT(*) FROM withdrawals WHERE status = 'pending') as pending_withdrawals,
    (SELECT COALESCE(SUM(amount), 0) FROM withdrawals WHERE status = 'completed' AND DATE(created_at) = CURRENT_DATE) as today_revenue,
    (SELECT COUNT(*) FROM users WHERE DATE(created_at) = CURRENT_DATE) as today_users;
