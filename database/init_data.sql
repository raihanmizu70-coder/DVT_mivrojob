-- Initial data for DVT Mini App

-- Insert admin user (if not exists)
INSERT INTO users (telegram_id, username, first_name, refer_code, balance, cash_wallet)
VALUES (6561117046, 'Miju132', 'Admin', 'ADMIN-001', 0, 0)
ON CONFLICT (telegram_id) DO NOTHING;

-- Insert sample micro jobs
INSERT INTO micro_jobs (task_id, title, description, cpa_link, amount, max_submissions, daily_limit)
VALUES 
    ('MJ-001', 'Sign up for ABC Platform', 
     'Complete registration form on ABC Platform and submit screenshot of confirmation.', 
     'https://cpa-lead.com/abc-signup', 3.00, 100, 3),
    
    ('MJ-002', 'Install Mobile App', 
     'Download and install the mobile app from Play Store, open it and submit screenshot.', 
     'https://cpa-grip.com/app-install', 5.00, 50, 2),
    
    ('MJ-003', 'Complete Survey', 
     'Complete a short survey about your preferences and submit completion screenshot.', 
     'https://cpa-lead.com/survey-123', 4.00, 200, 5),
    
    ('MJ-004', 'Subscribe to Newsletter', 
     'Subscribe to email newsletter and submit screenshot of confirmation email.', 
     'https://cpa-grip.com/newsletter', 2.50, 150, 3),
    
    ('MJ-005', 'Watch Video Tutorial', 
     'Watch the complete video tutorial and submit screenshot at the end.', 
     'https://cpa-lead.com/video-tutorial', 3.50, 80, 2)
ON CONFLICT (task_id) DO NOTHING;

-- Insert sample transaction types
INSERT INTO transaction_types (type, description)
VALUES 
    ('task_earnings', 'Earnings from completing tasks'),
    ('referral_bonus', 'Bonus from referring friends'),
    ('withdrawal', 'Money withdrawn from account'),
    ('transfer', 'Transfer between wallets')
ON CONFLICT (type) DO NOTHING;

-- Create sample withdrawal methods
INSERT INTO withdrawal_methods (method, name, min_amount, fee_percent, fixed_fee)
VALUES 
    ('bkash', 'bKash', 100, 10, 10),
    ('nagad', 'Nagad', 100, 10, 10),
    ('rocket', 'Rocket', 100, 10, 10)
ON CONFLICT (method) DO NOTHING;
