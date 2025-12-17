// Configuration
const API_URL = 'https://dvt-backend.onrender.com'; // Change to your Render URL
const CLOUDINARY_CLOUD_NAME = 'dvt-cloud'; // Change to your Cloudinary cloud name

// Global state
let currentUser = null;
let currentPage = 'home';
let selectedTask = null;
let selectedWithdrawalAmount = null;
let selectedWithdrawalMethod = null;

// Initialize Telegram Web App
const tg = window.Telegram.WebApp;

// Initialize app
async function initApp() {
    try {
        // Expand the app
        tg.expand();
        
        // Get user data from Telegram
        const user = tg.initDataUnsafe?.user;
        
        if (user) {
            currentUser = {
                id: user.id,
                username: user.username,
                first_name: user.first_name,
                last_name: user.last_name
            };
            
            // Update UI with user info
            document.getElementById('userName').textContent = `Hello, ${user.first_name || 'User'}!`;
            document.getElementById('userId').textContent = `ID: ${user.id}`;
            
            // Register/Login user to our backend
            await registerUser(user);
            
            // Load initial page
            loadPage('home');
        } else {
            // Test mode (for browser testing)
            currentUser = {
                id: 123456789,
                username: 'testuser',
                first_name: 'Test'
            };
            document.getElementById('userName').textContent = 'Hello, Test User!';
            loadPage('home');
        }
    } catch (error) {
        console.error('Initialization error:', error);
        showError('Failed to initialize app. Please restart.');
    }
}

// Register user to backend
async function registerUser(telegramUser) {
    try {
        const response = await fetch(`${API_URL}/api/user`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                telegram_id: telegramUser.id,
                username: telegramUser.username,
                first_name: telegramUser.first_name,
                refer_code: getUrlParameter('ref')
            })
        });
        
        if (!response.ok) {
            throw new Error('Failed to register user');
        }
        
        const userData = await response.json();
        updateBalance(userData.balance || 0);
    } catch (error) {
        console.error('Registration error:', error);
    }
}

// Update balance display
function updateBalance(balance) {
    document.getElementById('userBalance').textContent = `৳${balance.toFixed(2)}`;
}

// Load different pages
async function loadPage(page) {
    currentPage = page;
    
    // Update active nav item
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
    });
    document.querySelectorAll('.nav-item')[getNavIndex(page)].classList.add('active');
    
    // Load page content
    const contentDiv = document.getElementById('content');
    
    switch (page) {
        case 'home':
            await loadHomePage(contentDiv);
            break;
        case 'tasks':
            await loadTasksPage(contentDiv);
            break;
        case 'refer':
            await loadReferPage(contentDiv);
            break;
        case 'withdraw':
            await loadWithdrawPage(contentDiv);
            break;
        case 'profile':
            await loadProfilePage(contentDiv);
            break;
    }
}

// Get nav index
function getNavIndex(page) {
    const pages = ['home', 'tasks', 'refer', 'withdraw', 'profile'];
    return pages.indexOf(page);
}

// Load Home Page
async function loadHomePage(container) {
    try {
        // Get user stats
        const response = await fetch(`${API_URL}/api/user/${currentUser.id}`);
        const data = await response.json();
        
        container.innerHTML = `
            <div class="welcome-section">
                <h2>🎯 Welcome Back!</h2>
                <p>Start earning money with simple tasks</p>
            </div>
            
            <div class="quick-stats">
                <div class="stat-card">
                    <div class="stat-value">৳${(data.stats?.total_earned || 0).toFixed(2)}</div>
                    <div class="stat-label">Total Earned</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${data.stats?.completed_tasks || 0}</div>
                    <div class="stat-label">Tasks Done</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${data.stats?.referrals || 0}</div>
                    <div class="stat-label">Referrals</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">৳${(data.user?.cash_wallet || 0).toFixed(2)}</div>
                    <div class="stat-label">Cash Wallet</div>
                </div>
            </div>
            
            <div class="quick-actions">
                <div class="action-btn" onclick="loadPage('tasks')">
                    <span>🧩</span>
                    <div>Micro Jobs</div>
                </div>
                <div class="action-btn" onclick="loadPage('refer')">
                    <span>👥</span>
                    <div>Refer & Earn</div>
                </div>
                <div class="action-btn" onclick="loadPage('withdraw')">
                    <span>💳</span>
                    <div>Withdraw</div>
                </div>
            </div>
            
            <div class="recent-activity">
                <h3>📈 Recent Activity</h3>
                <div id="recentActivities">Loading...</div>
            </div>
            
            <div class="announcements">
                <h3>📢 Announcements</h3>
                <div class="announcement">
                    <strong>🎉 Welcome Bonus!</strong>
                    <p>Complete your first 5 tasks and get ৳20 bonus!</p>
                </div>
                <div class="announcement">
                    <strong>🤝 Referral Program</strong>
                    <p>Earn ৳5 for every friend who withdraws!</p>
                </div>
            </div>
        `;
        
        updateBalance(data.user?.balance || 0);
        
        // Load recent activities
        await loadRecentActivities();
    } catch (error) {
        container.innerHTML = `<div class="error">Failed to load home page: ${error.message}</div>`;
    }
}

// Load Tasks Page
async function loadTasksPage(container) {
    try {
        const response = await fetch(`${API_URL}/api/tasks`);
        const tasks = await response.json();
        
        if (tasks.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <span style="font-size: 3rem;">🧩</span>
                    <h3>No Tasks Available</h3>
                    <p>Check back later for new tasks!</p>
                </div>
            `;
            return;
        }
        
        let tasksHTML = `
            <div class="page-header">
                <h2>🧩 Micro Jobs</h2>
                <p>Complete tasks and earn money</p>
            </div>
            
            <div class="task-list">
        `;
        
        tasks.forEach(task => {
            tasksHTML += `
                <div class="task-card" onclick="openTaskModal('${task.task_id}')">
                    <div class="task-header">
                        <span class="task-id">${task.task_id}</span>
                        <span class="task-amount">৳${task.amount}</span>
                    </div>
                    <div class="task-title">${task.title}</div>
                    <div class="task-description">${task.description.substring(0, 100)}...</div>
                    <div class="task-stats">
                        <span>📊 ${task.max_submissions} slots</span>
                        <span>⏰ Daily: ${task.daily_limit}</span>
                    </div>
                </div>
            `;
        });
        
        tasksHTML += `</div>`;
        container.innerHTML = tasksHTML;
    } catch (error) {
        container.innerHTML = `<div class="error">Failed to load tasks: ${error.message}</div>`;
    }
}

// Open Task Modal
async function openTaskModal(taskId) {
    try {
        const response = await fetch(`${API_URL}/api/tasks/${taskId}`);
        const task = await response.json();
        
        selectedTask = task;
        
        document.getElementById('taskTitle').textContent = task.title;
        document.getElementById('taskDescription').textContent = task.description;
        document.getElementById('taskLink').href = task.cpa_link;
        
        document.getElementById('taskModal').style.display = 'flex';
    } catch (error) {
        showError('Failed to load task details');
    }
}

// Close Modal
function closeModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
    selectedTask = null;
}

// Upload Screenshot
async function uploadScreenshot() {
    const fileInput = document.getElementById('screenshotFile');
    const file = fileInput.files[0];
    
    if (!file) {
        showError('Please select a screenshot file');
        return;
    }
    
    if (!selectedTask) {
        showError('No task selected');
        return;
    }
    
    try {
        const uploadProgress = document.getElementById('uploadProgress');
        uploadProgress.innerHTML = '📤 Uploading...';
        
        // Create form data
        const formData = new FormData();
        formData.append('file', file);
        
        // Upload to backend
        const uploadResponse = await fetch(`${API_URL}/api/upload-screenshot`, {
            method: 'POST',
            body: formData
        });
        
        const uploadResult = await uploadResponse.json();
        
        if (!uploadResult.success) {
            throw new Error(uploadResult.error || 'Upload failed');
        }
        
        uploadProgress.innerHTML = '✅ Uploaded! Submitting task...';
        
        // Submit task
        const submitResponse = await fetch(`${API_URL}/api/submit-task`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: new URLSearchParams({
                telegram_id: currentUser.id,
                task_id: selectedTask.task_id,
                screenshot_url: uploadResult.url
            })
        });
        
        const submitResult = await submitResponse.json();
        
        uploadProgress.innerHTML = '🎉 Task submitted successfully!';
        
        // Close modal after 2 seconds
        setTimeout(() => {
            closeModal('taskModal');
            fileInput.value = '';
            uploadProgress.innerHTML = '';
            showSuccess('Task submitted for review!');
            loadPage('tasks');
        }, 2000);
        
    } catch (error) {
        document.getElementById('uploadProgress').innerHTML = `❌ Error: ${error.message}`;
    }
}

// Load Referral Page
async function loadReferPage(container) {
    try {
        const response = await fetch(`${API_URL}/api/user/${currentUser.id}/referrals`);
        const data = await response.json();
        
        const referralCode = data.user?.refer_code || `DVT-${currentUser.id}`;
        const referralLink = `https://t.me/digitalvishon_1235bot?start=${referralCode}`;
        
        container.innerHTML = `
            <div class="page-header">
                <h2>👥 Refer & Earn</h2>
                <p>Invite friends and earn bonuses</p>
            </div>
            
            <div class="referral-stats">
                <div class="stat-card">
                    <div class="stat-value">${data.stats?.total_referrals || 0}</div>
                    <div class="stat-label">Total Referrals</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${data.stats?.active_referrals || 0}</div>
                    <div class="stat-label">Active Referrals</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">৳${(data.stats?.total_bonus_earned || 0).toFixed(2)}</div>
                    <div class="stat-label">Bonus Earned</div>
                </div>
            </div>
            
            <div class="referral-code">
                <h3>🎯 Your Referral Code</h3>
                <div class="code-display" id="referralCode">${referralCode}</div>
                <button class="btn" onclick="copyReferralCode()">📋 Copy Code</button>
            </div>
            
            <div class="referral-link">
                <h3>🔗 Your Referral Link</h3>
                <div class="code-display" style="font-size: 0.9rem;">${referralLink}</div>
                <button class="btn" onclick="copyReferralLink()">🔗 Copy Link</button>
            </div>
            
            <div class="share-buttons">
                <div class="share-btn" onclick="shareToTelegram()">
                    <span>💬</span>
                    <div>Telegram</div>
                </div>
                <div class="share-btn" onclick="shareToWhatsApp()">
                    <span>📲</span>
                    <div>WhatsApp</div>
                </div>
                <div class="share-btn" onclick="shareToOthers()">
                    <span>📤</span>
                    <div>Others</div>
                </div>
            </div>
            
            <div class="referral-rules">
                <h3>💰 How It Works</h3>
                <ol style="padding-left: 20px; margin: 15px 0;">
                    <li>Share your referral code/link with friends</li>
                    <li>Friend joins using your code</li>
                    <li>Friend completes first withdrawal</li>
                    <li>You get <strong>৳5 bonus</strong> automatically!</li>
                </ol>
                <p><small>Note: Bonus is credited within 24 hours after friend's first withdrawal.</small></p>
            </div>
        `;
    } catch (error) {
        container.innerHTML = `<div class="error">Failed to load referral page: ${error.message}</div>`;
    }
}

// Copy Referral Code
function copyReferralCode() {
    const code = document.getElementById('referralCode').textContent;
    navigator.clipboard.writeText(code).then(() => {
        showSuccess('Referral code copied!');
    });
}

// Copy Referral Link
function copyReferralLink() {
    const link = `https://t.me/digitalvishon_1235bot?start=${currentUser.id}`;
    navigator.clipboard.writeText(link).then(() => {
        showSuccess('Referral link copied!');
    });
}

// Share functions
function shareToTelegram() {
    const text = `Join DVT Mini App and earn money! Use my referral code: ${document.getElementById('referralCode').textContent}\n\nhttps://t.me/digitalvishon_1235bot`;
    window.open(`https://t.me/share/url?url=${encodeURIComponent(text)}`, '_blank');
}

function shareToWhatsApp() {
    const text = `Join DVT Mini App and earn money! Use my referral code: ${document.getElementById('referralCode').textContent}\n\nhttps://t.me/digitalvishon_1235bot`;
    window.open(`https://wa.me/?text=${encodeURIComponent(text)}`, '_blank');
}

function shareToOthers() {
    const text = `Join DVT Mini App and earn money! Use my referral code: ${document.getElementById('referralCode').textContent}\n\nhttps://t.me/digitalvishon_1235bot`;
    
    if (navigator.share) {
        navigator.share({
            title: 'DVT Mini App - Earn Money',
            text: text,
            url: 'https://t.me/digitalvishon_1235bot'
        });
    } else {
        navigator.clipboard.writeText(text).then(() => {
            showSuccess('Message copied to clipboard!');
        });
    }
}

// Load Withdrawal Page
async function loadWithdrawPage(container) {
    try {
        const response = await fetch(`${API_URL}/api/user/${currentUser.id}`);
        const userData = await response.json();
        
        const cashWallet = userData.user?.cash_wallet || 0;
        
        container.innerHTML = `
            <div class="page-header">
                <h2>💳 Withdraw Money</h2>
                <p>Transfer to your mobile wallet</p>
            </div>
            
            <div class="wallet-info">
                <div class="stat-card">
                    <div class="stat-value">৳${cashWallet.toFixed(2)}</div>
                    <div class="stat-label">Cash Wallet Balance</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">৳100</div>
                    <div class="stat-label">Minimum Withdraw</div>
                </div>
            </div>
            
            <div class="amount-selection">
                <h3>🎯 Select Amount</h3>
                <div class="amount-options">
                    ${[100, 300, 500, 1000].map(amount => {
                        const charges = calculateCharges(amount);
                        return `
                            <div class="amount-option" onclick="selectWithdrawalAmount(${amount})" id="amount-${amount}">
                                <div class="amount">৳${amount}</div>
                                <div class="receive-amount">Get: ৳${charges.netAmount}</div>
                            </div>
                        `;
                    }).join('')}
                </div>
                
                <div class="custom-amount" style="margin-top: 20px;">
                    <h4>🔢 Custom Amount</h4>
                    <input type="number" id="customAmount" placeholder="Enter amount (৳100 minimum)" 
                           style="width: 100%; padding: 12px; border: 2px solid #e2e8f0; border-radius: 10px;"
                           onchange="updateCustomAmount()">
                    <small style="color: #64748b;">Must be in multiples of ৳100</small>
                </div>
            </div>
            
            <div class="method-selection" style="margin-top: 30px;">
                <h3>🏦 Select Method</h3>
                <div class="method-options">
                    <div class="method-option" onclick="selectWithdrawalMethod('bkash')" id="method-bkash">
                        <span style="font-size: 1.5rem;">💰</span>
                        <div>
                            <strong>bKash</strong>
                            <small style="display: block; color: #64748b;">Instant Transfer</small>
                        </div>
                    </div>
                    <div class="method-option" onclick="selectWithdrawalMethod('nagad')" id="method-nagad">
                        <span style="font-size: 1.5rem;">💸</span>
                        <div>
                            <strong>Nagad</strong>
                            <small style="display: block; color: #64748b;">Instant Transfer</small>
                        </div>
                    </div>
                    <div class="method-option" onclick="selectWithdrawalMethod('rocket')" id="method-rocket">
                        <span style="font-size: 1.5rem;">🚀</span>
                        <div>
                            <strong>Rocket</strong>
                            <small style="display: block; color: #64748b;">DBBL Mobile Banking</small>
                        </div>
                    </div>
                </div>
            </div>
            
            <div id="accountDetails" style="display: none; margin-top: 20px;">
                <h3>📱 Enter Account Details</h3>
                <input type="text" id="accountNumber" placeholder="Account Number (01XXXXXXXXX)" 
                       style="width: 100%; padding: 12px; border: 2px solid #e2e8f0; border-radius: 10px; margin-bottom: 10px;">
                <input type="text" id="accountName" placeholder="Account Holder Name" 
                       style="width: 100%; padding: 12px; border: 2px solid #e2e8f0; border-radius: 10px;">
            </div>
            
            <div id="chargesSummary" style="margin-top: 20px; padding: 15px; background: #f8fafc; border-radius: 10px; display: none;">
                <h4>📋 Charges Summary</h4>
                <div id="chargesDetails"></div>
            </div>
            
            <button class="btn" id="withdrawButton" onclick="submitWithdrawal()" 
                    style="margin-top: 20px;" disabled>
                💸 Request Withdrawal
            </button>
            
            <div class="withdrawal-rules" style="margin-top: 20px; padding: 15px; background: #fef3c7; border-radius: 10px;">
                <h4>⚠️ Important Rules</h4>
                <ul style="padding-left: 20px; font-size: 0.9rem;">
                    <li>First withdrawal: 10% + ৳10 fixed fee</li>
                    <li>Regular withdrawal: 10% only</li>
                    <li>Minimum withdrawal: ৳100</li>
                    <li>Processing time: 24-48 hours</li>
                </ul>
            </div>
        `;
        
        // Check if user has enough balance
        if (cashWallet < 100) {
            document.getElementById('withdrawButton').innerHTML = '❌ Insufficient Balance';
            document.getElementById('withdrawButton').style.background = '#ef4444';
            document.getElementById('withdrawButton').disabled = true;
        }
    } catch (error) {
        container.innerHTML = `<div class="error">Failed to load withdrawal page: ${error.message}</div>`;
    }
}

// Calculate withdrawal charges
function calculateCharges(amount) {
    // This should come from backend API
    // For now, using static calculation
    const serviceCharge = amount * 0.10;
    const fixedFee = 10; // First time only
    const totalCharges = serviceCharge + fixedFee;
    const netAmount = amount - totalCharges;
    
    return {
        serviceCharge,
        fixedFee,
        totalCharges,
        netAmount
    };
}

// Select withdrawal amount
function selectWithdrawalAmount(amount) {
    selectedWithdrawalAmount = amount;
    
    // Update UI
    document.querySelectorAll('.amount-option').forEach(option => {
        option.classList.remove('selected');
    });
    document.getElementById(`amount-${amount}`).classList.add('selected');
    
    // Update custom amount input
    document.getElementById('customAmount').value = amount;
    
    // Show charges summary
    updateChargesSummary();
    
    // Check if we can enable withdraw button
    checkWithdrawButton();
}

// Update custom amount
function updateCustomAmount() {
    const amount = parseInt(document.getElementById('customAmount').value);
    
    if (amount >= 100 && amount % 100 === 0) {
        selectWithdrawalAmount(amount);
    }
}

// Select withdrawal method
function selectWithdrawalMethod(method) {
    selectedWithdrawalMethod = method;
    
    // Update UI
    document.querySelectorAll('.method-option').forEach(option => {
        option.classList.remove('selected');
    });
    document.getElementById(`method-${method}`).classList.add('selected');
    
    // Show account details
    document.getElementById('accountDetails').style.display = 'block';
    
    // Update placeholder based on method
    const placeholder = method === 'rocket' ? 'Rocket Account Number' : `${method} Account Number (01XXXXXXXXX)`;
    document.getElementById('accountNumber').placeholder = placeholder;
    
    // Check if we can enable withdraw button
    checkWithdrawButton();
}

// Update charges summary
function updateChargesSummary() {
    if (!selectedWithdrawalAmount) return;
    
    const charges = calculateCharges(selectedWithdrawalAmount);
    
    document.getElementById('chargesSummary').style.display = 'block';
    document.getElementById('chargesDetails').innerHTML = `
        <div style="display: flex; justify-content: space-between; margin: 5px 0;">
            <span>Amount:</span>
            <strong>৳${selectedWithdrawalAmount}</strong>
        </div>
        <div style="display: flex; justify-content: space-between; margin: 5px 0;">
            <span>Service Charge (10%):</span>
            <span>-৳${charges.serviceCharge}</span>
        </div>
        <div style="display: flex; justify-content: space-between; margin: 5px 0;">
            <span>Fixed Fee:</span>
            <span>-৳${charges.fixedFee}</span>
        </div>
        <div style="display: flex; justify-content: space-between; margin: 5px 0; border-top: 1px solid #ddd; padding-top: 10px;">
            <span>You Will Receive:</span>
            <strong style="color: #10b981;">৳${charges.netAmount}</strong>
        </div>
    `;
}

// Check if withdraw button can be enabled
function checkWithdrawButton() {
    const button = document.getElementById('withdrawButton');
    const accountNumber = document.getElementById('accountNumber')?.value;
    
    if (selectedWithdrawalAmount && selectedWithdrawalMethod && accountNumber && accountNumber.length >= 11) {
        button.disabled = false;
        button.innerHTML = `💸 Request Withdrawal (Get: ৳${calculateCharges(selectedWithdrawalAmount).netAmount})`;
    } else {
        button.disabled = true;
        button.innerHTML = '💸 Request Withdrawal';
    }
}

// Submit withdrawal request
async function submitWithdrawal() {
    if (!selectedWithdrawalAmount || !selectedWithdrawalMethod) {
        showError('Please select amount and method');
        return;
    }
    
    const accountNumber = document.getElementById('accountNumber').value;
    const accountName = document.getElementById('accountName').value;
    
    if (!accountNumber || accountNumber.length < 11) {
        showError('Please enter valid account number');
        return;
    }
    
    try {
        const response = await fetch(`${API_URL}/api/withdrawals/request/${currentUser.id}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                amount: selectedWithdrawalAmount,
                method: selectedWithdrawalMethod,
                account_number: accountNumber,
                account_name: accountName
            })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Withdrawal failed');
        }
        
        const result = await response.json();
        
        showSuccess('Withdrawal request submitted successfully!');
        
        // Reset form
        setTimeout(() => {
            loadPage('withdraw');
        }, 2000);
        
    } catch (error) {
        showError(`Withdrawal failed: ${error.message}`);
    }
}

// Load Profile Page
async function loadProfilePage(container) {
    try {
        const response = await fetch(`${API_URL}/api/user/${currentUser.id}`);
        const data = await response.json();
        
        container.innerHTML = `
            <div class="page-header">
                <h2>👤 My Profile</h2>
                <p>Account information and settings</p>
            </div>
            
            <div class="profile-card">
                <div class="profile-header">
                    <div style="font-size: 3rem;">👤</div>
                    <div>
                        <h3>${data.user?.first_name || 'User'}</h3>
                        <p>@${data.user?.username || 'No username'}</p>
                    </div>
                </div>
                
                <div class="profile-info" style="margin-top: 20px;">
                    <div class="info-row">
                        <span>🆔 User ID:</span>
                        <strong>${data.user?.telegram_id}</strong>
                    </div>
                    <div class="info-row">
                        <span>📅 Joined:</span>
                        <span>${new Date(data.user?.created_at).toLocaleDateString()}</span>
                    </div>
                    <div class="info-row">
                        <span>🎯 Referral Code:</span>
                        <strong>${data.user?.refer_code}</strong>
                    </div>
                </div>
            </div>
            
            <div class="wallet-info" style="margin-top: 20px;">
                <h3>💰 Wallet Balance</h3>
                <div class="stat-card">
                    <div class="stat-value">৳${(data.user?.balance || 0).toFixed(2)}</div>
                    <div class="stat-label">Main Wallet</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">৳${(data.user?.cash_wallet || 0).toFixed(2)}</div>
                    <div class="stat-label">Cash Wallet</div>
                </div>
                
                <button class="btn btn-secondary" onclick="showTransferModal()" 
                        style="margin-top: 10px;">
                    💱 Transfer to Cash Wallet
                </button>
            </div>
            
            <div class="stats-grid" style="margin-top: 20px; display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                <div class="stat-card">
                    <div class="stat-value">${data.stats?.completed_tasks || 0}</div>
                    <div class="stat-label">Tasks Done</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">৳${(data.stats?.total_earned || 0).toFixed(2)}</div>
                    <div class="stat-label">Total Earned</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${data.stats?.referrals || 0}</div>
                    <div class="stat-label">Referrals</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">৳${(data.stats?.total_bonus_earned || 0).toFixed(2)}</div>
                    <div class="stat-label">Referral Bonus</div>
                </div>
            </div>
            
            <div class="action-buttons" style="margin-top: 20px;">
                <button class="btn" onclick="window.open('https://t.me/Miju132', '_blank')">
                    📞 Contact Support
                </button>
                <button class="btn btn-secondary" onclick="showTransactionHistory()" style="margin-top: 10px;">
                    📋 Transaction History
                </button>
            </div>
        `;
        
        updateBalance(data.user?.balance || 0);
    } catch (error) {
        container.innerHTML = `<div class="error">Failed to load profile: ${error.message}</div>`;
    }
}

// Load recent activities
async function loadRecentActivities() {
    try {
        const container = document.getElementById('recentActivities');
        
        // Get user's recent task submissions
        const response = await fetch(`${API_URL}/api/tasks/user/${currentUser.id}/submissions`);
        const submissions = await response.json();
        
        if (submissions.length === 0) {
            container.innerHTML = '<p>No recent activity</p>';
            return;
        }
        
        let html = '';
        submissions.slice(0, 5).forEach(sub => {
            const time = new Date(sub.created_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
            html += `
                <div class="activity-item" style="padding: 10px 0; border-bottom: 1px solid #e2e8f0;">
                    <div style="display: flex; justify-content: space-between;">
                        <span>${sub.task_title}</span>
                        <span style="color: ${sub.status === 'success' ? '#10b981' : sub.status === 'rejected' ? '#ef4444' : '#f59e0b'}">
                            ${sub.status}
                        </span>
                    </div>
                    <div style="display: flex; justify-content: space-between; font-size: 0.9rem; color: #64748b;">
                        <span>${time}</span>
                        <span>৳${sub.amount}</span>
                    </div>
                </div>
            `;
        });
        
        container.innerHTML = html;
    } catch (error) {
        console.error('Failed to load activities:', error);
    }
}

// Show success message
function showSuccess(message) {
    tg.showPopup({
        title: '✅ Success',
        message: message,
        buttons: [{ type: 'ok' }]
    });
}

// Show error message
function showError(message) {
    tg.showPopup({
        title: '❌ Error',
        message: message,
        buttons: [{ type: 'ok' }]
    });
}

// Get URL parameter
function getUrlParameter(name) {
    name = name.replace(/[\[\]]/g, '\\$&');
    const regex = new RegExp('[?&]' + name + '(=([^&#]*)|&|#|$)');
    const results = regex.exec(window.location.href);
    if (!results) return null;
    if (!results[2]) return '';
    return decodeURIComponent(results[2].replace(/\+/g, ' '));
}

// Initialize app when page loads
document.addEventListener('DOMContentLoaded', initApp);

// Listen for account number input
document.addEventListener('input', function(e) {
    if (e.target.id === 'accountNumber') {
        checkWithdrawButton();
    }
});
