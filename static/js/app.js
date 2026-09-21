/* ==========================================================================
   SMART EXPENSE TRACKER - FRONTEND CONTROLLER (JAVASCRIPT)
   ========================================================================== */

// Global State
let currentTab = 'dashboard';
let currentUser = null;
try {
    currentUser = JSON.parse(localStorage.getItem('currentUser'));
} catch(e) { currentUser = null; }

let categoriesMap = {};
let allCategoriesList = [];
let categoryChartInstance = null;
let trendChartInstance = null;
let predictionChartInstance = null;
let currentExpensesList = [];
let mlSuggestedCategory = null;
let filterDebounceTimer = null;
let mlDebounceTimer = null;

// Helper to get active User ID
function getUserId() {
    return (currentUser && currentUser.id) ? currentUser.id : 1;
}

// Initialize App on DOM Load
document.addEventListener('DOMContentLoaded', () => {
    initApp();
});

async function initApp() {
    // Set default date picker to today
    document.getElementById('inputDate').valueAsDate = new Date();
    
    // Check Auth Status & display UI
    checkAuthStatus();

    // Load Categories from API
    await loadCategories();
    
    // Load Dashboard Statistics & Charts
    await loadDashboardStats();
    
    // Load Expenses List
    await loadExpenses();
    
    // Load Budget & Prediction ML
    await loadBudgetAndPrediction();

    // Load Profile
    if (currentUser) {
        await loadUserProfile();
    }
}

// --------------------------------------------------------------------------
// 1. NAVIGATION & TAB SWITCHING
// --------------------------------------------------------------------------
function switchTab(tabId) {
    currentTab = tabId;
    
    // Update active state in sidebar menu
    document.querySelectorAll('.nav-item').forEach(item => item.classList.remove('active'));
    const activeNav = document.getElementById(`nav-${tabId}`);
    if (activeNav) activeNav.classList.add('active');

    // Hide all tab pages, show target
    document.querySelectorAll('.tab-page').forEach(page => page.classList.add('hidden'));
    const targetPage = document.getElementById(`tab-${tabId}`);
    if (targetPage) targetPage.classList.remove('hidden');

    // Update Header Text
    const titleMap = {
        'dashboard': { title: 'Dashboard Overview', subtitle: 'Real-time financial analytics & ML category predictions' },
        'expenses': { title: 'Expense Management', subtitle: 'View, filter, edit, and track your logged transactions' },
        'ml-classifier': { title: 'ML Expense Classifier', subtitle: 'TF-IDF Vectorizer + Logistic Regression real-time classification' },
        'budget-prediction': { title: 'Budget & Next Month Forecast', subtitle: 'Linear Regression model predicting upcoming expenditure' },
        'reports': { title: 'Reports & Data Export', subtitle: 'Spending insights, metrics health score, and CSV downloads' },
        'profile': { title: 'User Profile & Settings', subtitle: 'Manage your personal details, email, physical address, and budget ceiling' }
    };
    if (titleMap[tabId]) {
        document.getElementById('pageTitle').innerText = titleMap[tabId].title;
        document.getElementById('pageSubtitle').innerText = titleMap[tabId].subtitle;
    }

    // Refresh chart renders when switching to tab
    if (tabId === 'dashboard') {
        loadDashboardStats();
    } else if (tabId === 'budget-prediction') {
        loadBudgetAndPrediction();
    } else if (tabId === 'expenses') {
        loadExpenses();
    } else if (tabId === 'profile') {
        loadUserProfile();
    }
}

// --------------------------------------------------------------------------
// 2. CATEGORY DATA & DROPDOWNS
// --------------------------------------------------------------------------
async function loadCategories() {
    try {
        const response = await fetch('/api/categories');
        if (!response.ok) throw new Error('API not available');
        const data = await response.json();
        if (data.status === 'success') {
            allCategoriesList = data.categories;
        } else {
            throw new Error('Non-success category response');
        }
    } catch (err) {
        // Fallback default categories for static preview (GitHub Pages)
        allCategoriesList = [
            { id: 1, name: 'Food & Dining', icon: 'fa-utensils', color: '#EF4444' },
            { id: 2, name: 'Transportation', icon: 'fa-car', color: '#F59E0B' },
            { id: 3, name: 'Bills & Utilities', icon: 'fa-file-invoice-dollar', color: '#10B981' },
            { id: 4, name: 'Shopping', icon: 'fa-shopping-bag', color: '#EC4899' },
            { id: 5, name: 'Entertainment', icon: 'fa-film', color: '#8B5CF6' },
            { id: 6, name: 'Health & Fitness', icon: 'fa-heartbeat', color: '#06B6D4' },
            { id: 7, name: 'Education', icon: 'fa-graduation-cap', color: '#3B82F6' },
            { id: 8, name: 'Travel & Vacation', icon: 'fa-plane', color: '#6366F1' },
            { id: 9, name: 'Investments', icon: 'fa-chart-line', color: '#10B981' },
            { id: 10, name: 'Miscellaneous', icon: 'fa-ellipsis-h', color: '#6B7280' }
        ];
    }

    categoriesMap = {};
    const filterSelect = document.getElementById('filterCategory');
    const inputSelect = document.getElementById('inputCategory');
    
    if (filterSelect && inputSelect) {
        filterSelect.innerHTML = '<option value="All">All Categories</option>';
        inputSelect.innerHTML = '<option value="">Select Category</option>';

        allCategoriesList.forEach(cat => {
            categoriesMap[cat.name] = cat;
            
            const opt1 = document.createElement('option');
            opt1.value = cat.name;
            opt1.textContent = cat.name;
            filterSelect.appendChild(opt1);

            const opt2 = document.createElement('option');
            opt2.value = cat.name;
            opt2.textContent = cat.name;
            inputSelect.appendChild(opt2);
        });
    }
}

// --------------------------------------------------------------------------
// 3. DASHBOARD STATS & CHART.JS
// --------------------------------------------------------------------------
function getDefaultDemoExpenses() {
    return [
        { id: 101, date: '2026-09-21', description: 'Starbucks mocha coffee & croissant', category: 'Food & Dining', payment_method: 'UPI', amount: 350.00, icon: 'fa-utensils', color: '#EF4444' },
        { id: 102, date: '2026-09-20', description: 'Uber ride to international airport', category: 'Transportation', payment_method: 'Card', amount: 650.00, icon: 'fa-car', color: '#F59E0B' },
        { id: 103, date: '2026-09-18', description: 'Monthly electricity power bill', category: 'Bills & Utilities', payment_method: 'Bank Transfer', amount: 1250.00, icon: 'fa-file-invoice-dollar', color: '#10B981' },
        { id: 104, date: '2026-09-15', description: 'Netflix 4K Monthly Streaming Subscription', category: 'Entertainment', payment_method: 'Credit Card', amount: 649.00, icon: 'fa-film', color: '#8B5CF6' },
        { id: 105, date: '2026-09-12', description: 'Nike Running Sneakers Shoes', category: 'Shopping', payment_method: 'Debit Card', amount: 3499.00, icon: 'fa-shopping-bag', color: '#EC4899' },
        { id: 106, date: '2026-09-08', description: 'Pharmacy prescription medicine', category: 'Health & Fitness', payment_method: 'UPI', amount: 480.00, icon: 'fa-heartbeat', color: '#06B6D4' }
    ];
}

async function loadDashboardStats() {
    try {
        const response = await fetch(`/api/dashboard/stats?user_id=${getUserId()}`);
        if (!response.ok) throw new Error('API not available');
        const data = await response.json();
        
        if (data.status === 'success') {
            const stats = data.stats;
            
            // Update Stat Cards
            document.getElementById('statTotalSpending').innerText = `₹${stats.total_spending.toLocaleString('en-IN', {minimumFractionDigits: 2})}`;
            document.getElementById('statCurrentMonth').innerText = `₹${stats.current_month_total.toLocaleString('en-IN', {minimumFractionDigits: 2})}`;
            document.getElementById('statTxCount').innerText = `${stats.current_month_count} expenses logged this month`;
            document.getElementById('headerBudgetAmount').innerText = `₹${stats.monthly_budget.toLocaleString('en-IN', {minimumFractionDigits: 2})}`;
            document.getElementById('inputMonthlyBudget').value = stats.monthly_budget;
            
            // Budget percentage & bar
            const budgetPct = Math.min(stats.budget_used_percentage, 100);
            document.getElementById('statBudgetUsedPct').innerText = `${stats.budget_used_percentage}%`;
            const progressBar = document.getElementById('statBudgetProgressBar');
            progressBar.style.width = `${budgetPct}%`;
            
            // Color status
            if (stats.budget_used_percentage > 90) {
                progressBar.style.background = 'var(--rose)';
                showAlertBanner(`Warning: You have used ${stats.budget_used_percentage}% of your monthly budget!`);
            } else if (stats.budget_used_percentage > 75) {
                progressBar.style.background = 'var(--amber)';
                hideAlertBanner();
            } else {
                progressBar.style.background = 'linear-gradient(90deg, var(--emerald), var(--cyan))';
                hideAlertBanner();
            }

            document.getElementById('statTopCategory').innerText = stats.top_category;

            // Render Category Breakdown Chart
            renderCategoryChart(data.category_breakdown);

            // Render Monthly Trend Chart
            renderTrendChart(data.monthly_trend);

            // Render Recent Transactions
            renderRecentTransactions(data.recent_expenses);
            
            // Update Report Insights
            document.getElementById('reportDailyAvg').innerText = `₹${(stats.current_month_total / 30).toFixed(2)}`;
            return;
        }
    } catch (err) {
        // Fallback for static hosting (GitHub Pages)
        const demoList = currentExpensesList.length > 0 ? currentExpensesList : getDefaultDemoExpenses();
        const total = demoList.reduce((acc, curr) => acc + parseFloat(curr.amount), 0);
        const budget = 1500;
        const budgetPct = Math.round((total / budget) * 100);

        document.getElementById('statTotalSpending').innerText = `₹${total.toFixed(2)}`;
        document.getElementById('statCurrentMonth').innerText = `₹${total.toFixed(2)}`;
        document.getElementById('statTxCount').innerText = `${demoList.length} expenses logged`;
        document.getElementById('headerBudgetAmount').innerText = `₹${budget.toFixed(2)}`;
        document.getElementById('statBudgetUsedPct').innerText = `${budgetPct}%`;
        document.getElementById('statBudgetProgressBar').style.width = `${Math.min(budgetPct, 100)}%`;
        document.getElementById('statTopCategory').innerText = 'Shopping';
        document.getElementById('reportDailyAvg').innerText = `₹${(total / 30).toFixed(2)}`;

        const catMap = {};
        demoList.forEach(item => {
            catMap[item.category] = (catMap[item.category] || 0) + parseFloat(item.amount);
        });

        renderCategoryChart({
            labels: Object.keys(catMap),
            data: Object.values(catMap)
        });

        renderTrendChart({
            labels: ['Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep'],
            data: [4500, 5200, 4800, 6100, 5900, total]
        });

        renderRecentTransactions(demoList.slice(0, 5));
    }
}

function renderCategoryChart(breakdown) {
    const ctx = document.getElementById('categoryChart').getContext('2d');
    if (categoryChartInstance) categoryChartInstance.destroy();

    const colors = breakdown.labels.map(label => {
        return (categoriesMap[label] && categoriesMap[label].color) ? categoriesMap[label].color : '#6366f1';
    });

    categoryChartInstance = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: breakdown.labels,
            datasets: [{
                data: breakdown.data,
                backgroundColor: colors,
                borderWidth: 2,
                borderColor: '#1e293b'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right',
                    labels: { color: '#94a3b8', font: { family: 'Plus Jakarta Sans', size: 12 } }
                }
            }
        }
    });
}

function renderTrendChart(trend) {
    const ctx = document.getElementById('trendChart').getContext('2d');
    if (trendChartInstance) trendChartInstance.destroy();

    trendChartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: trend.labels,
            datasets: [{
                label: 'Monthly Expenses (₹)',
                data: trend.data,
                backgroundColor: 'rgba(99, 102, 241, 0.6)',
                borderColor: '#6366f1',
                borderWidth: 2,
                borderRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: { ticks: { color: '#94a3b8' }, grid: { color: 'rgba(255, 255, 255, 0.05)' } },
                y: { ticks: { color: '#94a3b8' }, grid: { color: 'rgba(255, 255, 255, 0.05)' } }
            },
            plugins: {
                legend: { display: false }
            }
        }
    });
}

function renderRecentTransactions(transactions) {
    const tbody = document.getElementById('recentTransactionsBody');
    tbody.innerHTML = '';
    
    if (!transactions || transactions.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted">No recent transactions recorded.</td></tr>';
        return;
    }

    transactions.forEach(item => {
        const catColor = item.color || '#6366f1';
        const catIcon = item.icon || 'fa-tag';
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${item.date}</td>
            <td><strong>${escapeHtml(item.description)}</strong></td>
            <td>
                <span class="category-badge" style="background: ${catColor}20; color: ${catColor}; border: 1px solid ${catColor}40;">
                    <i class="fa-solid ${catIcon}"></i> ${escapeHtml(item.category)}
                </span>
            </td>
            <td>${escapeHtml(item.payment_method || 'Card')}</td>
            <td><strong>₹${parseFloat(item.amount).toFixed(2)}</strong></td>
        `;
        tbody.appendChild(tr);
    });
}

// --------------------------------------------------------------------------
// 4. EXPENSES MANAGEMENT (CRUD & MULTI-FILTER)
// --------------------------------------------------------------------------
async function loadExpenses() {
    const category = document.getElementById('filterCategory') ? document.getElementById('filterCategory').value : 'All';
    const search = document.getElementById('filterSearch') ? document.getElementById('filterSearch').value.trim() : '';
    const startDate = document.getElementById('filterStartDate') ? document.getElementById('filterStartDate').value : '';
    const endDate = document.getElementById('filterEndDate') ? document.getElementById('filterEndDate').value : '';

    let url = `/api/expenses?user_id=${getUserId()}`;
    if (category && category !== 'All') url += `&category=${encodeURIComponent(category)}`;
    if (search) url += `&search=${encodeURIComponent(search)}`;
    if (startDate) url += `&start_date=${startDate}`;
    if (endDate) url += `&end_date=${endDate}`;

    try {
        const response = await fetch(url);
        if (!response.ok) throw new Error('API not available');
        const data = await response.json();
        if (data.status === 'success') {
            currentExpensesList = data.expenses;
            renderExpensesTable(currentExpensesList);
            return;
        }
    } catch (err) {
        if (!currentExpensesList || currentExpensesList.length === 0) {
            currentExpensesList = getDefaultDemoExpenses();
        }
        let filtered = [...currentExpensesList];
        if (category && category !== 'All') {
            filtered = filtered.filter(e => e.category === category);
        }
        if (search) {
            filtered = filtered.filter(e => e.description.toLowerCase().includes(search.toLowerCase()) || (e.category && e.category.toLowerCase().includes(search.toLowerCase())));
        }
        renderExpensesTable(filtered);
    }
}

function renderExpensesTable(expenses) {
    const tbody = document.getElementById('expensesTableBody');
    tbody.innerHTML = '';

    if (!expenses || expenses.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted" style="padding: 24px;">No matching expenses found.</td></tr>';
        return;
    }

    expenses.forEach(item => {
        const catColor = item.color || '#6366f1';
        const catIcon = item.icon || 'fa-tag';
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>#${item.id}</td>
            <td>${item.date}</td>
            <td><strong>${escapeHtml(item.description)}</strong></td>
            <td>
                <span class="category-badge" style="background: ${catColor}20; color: ${catColor}; border: 1px solid ${catColor}40;">
                    <i class="fa-solid ${catIcon}"></i> ${escapeHtml(item.category)}
                </span>
            </td>
            <td>${escapeHtml(item.payment_method || 'Card')}</td>
            <td><strong>₹${parseFloat(item.amount).toFixed(2)}</strong></td>
            <td class="text-right">
                <button class="btn-edit-icon" onclick="openEditModal(${item.id})"><i class="fa-solid fa-pen-to-square"></i></button>
                <button class="btn-danger-icon" onclick="deleteExpense(${item.id})"><i class="fa-solid fa-trash-can"></i></button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

function debouncedFilterExpenses() {
    clearTimeout(filterDebounceTimer);
    filterDebounceTimer = setTimeout(() => {
        loadExpenses();
    }, 300);
}

function resetFilters() {
    document.getElementById('filterSearch').value = '';
    document.getElementById('filterCategory').value = 'All';
    document.getElementById('filterStartDate').value = '';
    document.getElementById('filterEndDate').value = '';
    loadExpenses();
}

// --------------------------------------------------------------------------
// 5. ML REAL-TIME CATEGORY PREDICTION (MODAL & PLAYGROUND)
// --------------------------------------------------------------------------
function debouncedMLAutoSuggest() {
    clearTimeout(mlDebounceTimer);
    mlDebounceTimer = setTimeout(async () => {
        const desc = document.getElementById('inputDescription').value.trim();
        const badge = document.getElementById('mlModalSuggestBadge');
        
        if (desc.length < 3) {
            badge.classList.add('hidden');
            return;
        }

        try {
            const res = await fetch('/api/ml/predict-category', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ description: desc })
            });
            const data = await res.json();
            
            if (data.status === 'success' && data.prediction) {
                const pred = data.prediction;
                mlSuggestedCategory = pred.predicted_category;
                
                document.getElementById('mlModalCategoryText').innerText = pred.predicted_category;
                document.getElementById('mlModalConfText').innerText = `${pred.confidence_percentage}% confidence`;
                badge.classList.remove('hidden');
            }
        } catch (err) {
            console.error('ML Auto-suggest error:', err);
        }
    }, 300);
}

function applyMLSuggestion() {
    if (mlSuggestedCategory) {
        document.getElementById('inputCategory').value = mlSuggestedCategory;
        document.getElementById('mlModalSuggestBadge').classList.add('hidden');
    }
}

// ML Classifier Playground Test
function setMLTestText(text) {
    document.getElementById('mlTestInput').value = text;
    debouncedMLPredictTest();
}

function debouncedMLPredictTest() {
    clearTimeout(mlDebounceTimer);
    mlDebounceTimer = setTimeout(async () => {
        const text = document.getElementById('mlTestInput').value.trim();
        const card = document.getElementById('mlTestResultCard');

        if (!text) {
            card.classList.add('hidden');
            return;
        }

        try {
            const res = await fetch('/api/ml/predict-category', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ description: text })
            });
            const data = await res.json();
            
            if (data.status === 'success' && data.prediction) {
                const pred = data.prediction;
                document.getElementById('mlPredictedCategoryName').innerText = pred.predicted_category;
                document.getElementById('mlConfidenceScoreText').innerText = `${pred.confidence_percentage}%`;
                document.getElementById('mlConfidenceBarFill').style.width = `${pred.confidence_percentage}%`;

                // Render top chips
                const chipContainer = document.getElementById('mlTopSuggestionsChips');
                chipContainer.innerHTML = '';
                if (pred.top_suggestions) {
                    pred.top_suggestions.forEach(([cat, prob]) => {
                        const chip = document.createElement('span');
                        chip.className = 'chip';
                        chip.innerHTML = `<strong>${cat}</strong>: ${(prob * 100).toFixed(1)}%`;
                        chipContainer.appendChild(chip);
                    });
                }

                card.classList.remove('hidden');
            }
        } catch (err) {
            // Client-side fallback rule engine for static hosting (GitHub Pages)
            const lower = text.toLowerCase();
            let cat = 'Miscellaneous';
            let conf = 88;
            if (lower.match(/coffee|pizza|burger|starbucks|restaurant|food|dinner|lunch|breakfast|swiggy|zomato|dominos|meal|kitchen|snack/)) { cat = 'Food & Dining'; conf = 96; }
            else if (lower.match(/uber|ola|cab|fuel|petrol|diesel|flight|airline|train|bus|metro|auto|fare|taxi|car/)) { cat = 'Transportation'; conf = 94; }
            else if (lower.match(/bill|electricity|power|water|internet|wifi|recharge|mobile|utility|gas/)) { cat = 'Bills & Utilities'; conf = 95; }
            else if (lower.match(/netflix|movie|cinema|spotify|youtube|game|gameplay|concert|ticket|show/)) { cat = 'Entertainment'; conf = 92; }
            else if (lower.match(/nike|shoes|shirt|clothes|amazon|flipkart|myntra|shopping|dress|watch|jacket/)) { cat = 'Shopping'; conf = 91; }
            else if (lower.match(/hospital|doctor|medicine|pharmacy|clinic|gym|fitness|workout|health/)) { cat = 'Health & Fitness'; conf = 90; }
            else if (lower.match(/course|udemy|book|school|college|tuition|fee|exam|class|learning/)) { cat = 'Education'; conf = 93; }

            document.getElementById('mlPredictedCategoryName').innerText = cat;
            document.getElementById('mlConfidenceScoreText').innerText = `${conf}%`;
            document.getElementById('mlConfidenceBarFill').style.width = `${conf}%`;

            const chipContainer = document.getElementById('mlTopSuggestionsChips');
            chipContainer.innerHTML = `
                <span class="chip"><strong>${cat}</strong>: ${conf}%</span>
                <span class="chip"><strong>Miscellaneous</strong>: ${(100 - conf).toFixed(0)}%</span>
            `;
            card.classList.remove('hidden');
        }
    }, 250);
}

async function triggerRetrainML() {
    const statusText = document.getElementById('retrainStatusText');
    statusText.innerText = 'Training ML model on database...';
    
    try {
        const res = await fetch('/api/ml/retrain', { method: 'POST' });
        const data = await res.json();
        if (data.status === 'success') {
            statusText.innerText = '✨ Model successfully re-trained!';
            setTimeout(() => { statusText.innerText = 'Model state: Ready'; }, 3000);
        }
    } catch (err) {
        statusText.innerText = 'Retrain error.';
    }
}

// --------------------------------------------------------------------------
// 6. BUDGET & NEXT MONTH ML FORECAST (LINEAR REGRESSION)
// --------------------------------------------------------------------------
async function loadBudgetAndPrediction() {
    try {
        const res = await fetch(`/api/ml/predict-next-month?user_id=${getUserId()}`);
        if (!res.ok) throw new Error('API not available');
        const data = await res.json();
        
        if (data.status === 'success') {
            const pred = data.prediction;
            document.getElementById('predNextMonthAmount').innerText = `₹${pred.predicted_amount.toLocaleString('en-IN', {minimumFractionDigits: 2})}`;
            document.getElementById('predMonthlyAvg').innerText = `₹${pred.average_monthly_spend ? pred.average_monthly_spend.toFixed(2) : '0.00'}`;
            document.getElementById('predMonthlyRate').innerText = `${pred.trend_slope > 0 ? '+' : ''}₹${pred.trend_slope ? pred.trend_slope.toFixed(2) : '0.00'} / mo`;

            const trendPill = document.getElementById('predTrendPill');
            const trendText = document.getElementById('predTrendText');

            if (pred.trend_direction === 'Increasing') {
                trendPill.style.background = 'rgba(239, 68, 68, 0.15)';
                trendPill.style.color = '#fca5a5';
                trendText.innerText = `Trending Up (+${pred.trend_slope}/mo)`;
            } else if (pred.trend_direction === 'Decreasing') {
                trendPill.style.background = 'rgba(16, 185, 129, 0.15)';
                trendPill.style.color = '#34d399';
                trendText.innerText = `Trending Down (${pred.trend_slope}/mo)`;
            } else {
                trendPill.style.background = 'rgba(99, 102, 241, 0.15)';
                trendPill.style.color = '#818cf8';
                trendText.innerText = 'Stable Trend';
            }

            renderPredictionChart(pred.monthly_labels, pred.monthly_history, pred.predicted_amount);
            return;
        }
    } catch (err) {
        // Fallback calculation for static host (GitHub Pages)
        const labels = ['Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep'];
        const history = [4500, 5200, 4800, 6100, 5900, 7178];
        const predictedAmount = 6450.00;

        document.getElementById('predNextMonthAmount').innerText = `₹${predictedAmount.toLocaleString('en-IN', {minimumFractionDigits: 2})}`;
        document.getElementById('predMonthlyAvg').innerText = `₹5,613.00`;
        document.getElementById('predMonthlyRate').innerText = `+₹320.00 / mo`;

        const trendPill = document.getElementById('predTrendPill');
        const trendText = document.getElementById('predTrendText');
        trendPill.style.background = 'rgba(16, 185, 129, 0.15)';
        trendPill.style.color = '#34d399';
        trendText.innerText = 'Stable Forecast (+320/mo)';

        renderPredictionChart(labels, history, predictedAmount);
    }
}

function renderPredictionChart(labels, history, predictedNextMonth) {
    const ctx = document.getElementById('predictionChart').getContext('2d');
    if (predictionChartInstance) predictionChartInstance.destroy();

    const chartLabels = [...(labels || []), 'Next Month (Pred)'];
    const chartData = [...(history || []), predictedNextMonth];

    predictionChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: chartLabels,
            datasets: [{
                label: 'Monthly Expense Forecast (₹)',
                data: chartData,
                borderColor: '#06b6d4',
                backgroundColor: 'rgba(6, 182, 212, 0.1)',
                borderWidth: 3,
                fill: true,
                tension: 0.3,
                pointBackgroundColor: (context) => context.dataIndex === chartData.length - 1 ? '#ef4444' : '#06b6d4',
                pointRadius: (context) => context.dataIndex === chartData.length - 1 ? 6 : 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: { ticks: { color: '#94a3b8' }, grid: { color: 'rgba(255, 255, 255, 0.05)' } },
                y: { ticks: { color: '#94a3b8' }, grid: { color: 'rgba(255, 255, 255, 0.05)' } }
            },
            plugins: { legend: { display: false } }
        }
    });
}

async function saveMonthlyBudget() {
    const val = parseFloat(document.getElementById('inputMonthlyBudget').value);
    if (isNaN(val) || val <= 0) {
        alert('Please enter a valid budget amount.');
        return;
    }

    try {
        const res = await fetch('/api/user/budget', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: getUserId(), monthly_budget: val })
        });
        const data = await res.json();
        if (data.status === 'success') {
            alert('Monthly budget saved successfully!');
            loadDashboardStats();
        }
    } catch (err) {
        console.error('Error saving budget:', err);
    }
}

// --------------------------------------------------------------------------
// 7. MODAL & EXPENSE FORM HANDLING
// --------------------------------------------------------------------------
function openAddModal() {
    document.getElementById('modalTitle').innerText = 'Add New Expense';
    document.getElementById('expenseForm').reset();
    document.getElementById('expenseId').value = '';
    document.getElementById('inputDate').valueAsDate = new Date();
    document.getElementById('mlModalSuggestBadge').classList.add('hidden');
    document.getElementById('expenseModal').classList.remove('hidden');
}

function openEditModal(expenseId) {
    const item = currentExpensesList.find(e => e.id === expenseId);
    if (!item) return;

    document.getElementById('modalTitle').innerText = 'Edit Expense';
    document.getElementById('expenseId').value = item.id;
    document.getElementById('inputDescription').value = item.description;
    document.getElementById('inputAmount').value = item.amount;
    document.getElementById('inputCategory').value = item.category;
    document.getElementById('inputDate').value = item.date;
    document.getElementById('inputPaymentMethod').value = item.payment_method || 'Card';
    document.getElementById('mlModalSuggestBadge').classList.add('hidden');
    document.getElementById('expenseModal').classList.remove('hidden');
}

function closeExpenseModal() {
    document.getElementById('expenseModal').classList.add('hidden');
}

async function handleSaveExpense(e) {
    e.preventDefault();

    const id = document.getElementById('expenseId').value;
    const description = document.getElementById('inputDescription').value.trim();
    const amount = parseFloat(document.getElementById('inputAmount').value);
    const category = document.getElementById('inputCategory').value;
    const date = document.getElementById('inputDate').value;
    const payment_method = document.getElementById('inputPaymentMethod').value;

    const payload = { user_id: getUserId(), description, amount, category, date, payment_method };
    
    const url = id ? `/api/expenses/${id}` : '/api/expenses';
    const method = id ? 'PUT' : 'POST';

    try {
        const response = await fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await response.json();

        if (data.status === 'success') {
            closeExpenseModal();
            loadExpenses();
            loadDashboardStats();
            loadBudgetAndPrediction();
        } else {
            alert(data.message || 'Error saving expense.');
        }
    } catch (err) {
        // Fallback for static hosting (GitHub Pages)
        const catObj = categoriesMap[category] || { icon: 'fa-tag', color: '#6366f1' };
        if (id) {
            const idx = currentExpensesList.findIndex(e => e.id == id);
            if (idx !== -1) {
                currentExpensesList[idx] = { id: parseInt(id), description, amount, category, date, payment_method, icon: catObj.icon, color: catObj.color };
            }
        } else {
            const newId = Date.now();
            currentExpensesList.unshift({ id: newId, description, amount, category, date, payment_method, icon: catObj.icon, color: catObj.color });
        }
        closeExpenseModal();
        loadExpenses();
        loadDashboardStats();
        loadBudgetAndPrediction();
    }
}

async function deleteExpense(id) {
    if (!confirm('Are you sure you want to delete this expense record?')) return;

    try {
        const res = await fetch(`/api/expenses/${id}`, { method: 'DELETE' });
        const data = await res.json();
        if (data.status === 'success') {
            loadExpenses();
            loadDashboardStats();
            loadBudgetAndPrediction();
        }
    } catch (err) {
        // Fallback for static hosting (GitHub Pages)
        currentExpensesList = currentExpensesList.filter(e => e.id !== id);
        loadExpenses();
        loadDashboardStats();
        loadBudgetAndPrediction();
    }
}

// --------------------------------------------------------------------------
// 8. CSV EXPORT & HELPERS
// --------------------------------------------------------------------------
function exportCSV() {
    window.location.href = `/api/reports/export?user_id=${getUserId()}`;
}

function showAlertBanner(msg) {
    const banner = document.getElementById('alertBanner');
    document.getElementById('alertMessage').innerText = msg;
    banner.classList.remove('hidden');
}

function hideAlertBanner() {
    document.getElementById('alertBanner').classList.add('hidden');
}

function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
}

// --------------------------------------------------------------------------
// 9. USER AUTHENTICATION & PROFILE CONTROLLER
// --------------------------------------------------------------------------
function checkAuthStatus() {
    const authModal = document.getElementById('authModal');
    if (!currentUser) {
        currentUser = {
            id: 1,
            name: "Demo User",
            username: "demo",
            email: "demo@expensetracker.com",
            address: "123 Tech Park, Silicon Valley, CA",
            monthly_budget: 1500
        };
        localStorage.setItem('currentUser', JSON.stringify(currentUser));
    }
    authModal.classList.add('hidden');
    document.getElementById('sidebarUserName').innerText = currentUser.name || currentUser.username;
    document.getElementById('sidebarUserEmail').innerText = currentUser.email;
}

function switchAuthTab(type) {
    const loginForm = document.getElementById('loginForm');
    const registerForm = document.getElementById('registerForm');
    const tabBtnLogin = document.getElementById('tabBtnLogin');
    const tabBtnRegister = document.getElementById('tabBtnRegister');

    if (type === 'login') {
        loginForm.classList.remove('hidden');
        registerForm.classList.add('hidden');
        tabBtnLogin.classList.add('active');
        tabBtnRegister.classList.remove('active');
    } else {
        loginForm.classList.add('hidden');
        registerForm.classList.remove('hidden');
        tabBtnLogin.classList.remove('active');
        tabBtnRegister.classList.add('active');
    }
}

async function handleLogin(e) {
    e.preventDefault();
    const loginInput = document.getElementById('loginInput').value.trim();
    const loginPassword = document.getElementById('loginPassword').value;
    const alertBox = document.getElementById('loginAlert');
    alertBox.classList.add('hidden');

    try {
        const response = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ login: loginInput, password: loginPassword })
        });
        const data = await response.json();

        if (data.status === 'success') {
            currentUser = data.user;
            localStorage.setItem('currentUser', JSON.stringify(currentUser));
            checkAuthStatus();
            await loadDashboardStats();
            await loadExpenses();
            await loadBudgetAndPrediction();
            await loadUserProfile();
        } else {
            alertBox.innerText = data.message || 'Login failed. Check your credentials.';
            alertBox.classList.remove('hidden');
        }
    } catch (err) {
        // Fallback for static hosting (GitHub Pages)
        currentUser = {
            id: 1,
            name: loginInput || 'Demo User',
            username: loginInput || 'demo',
            email: loginInput && loginInput.includes('@') ? loginInput : 'demo@expensetracker.com',
            address: '123 Tech Park, Silicon Valley, CA',
            monthly_budget: 1500
        };
        localStorage.setItem('currentUser', JSON.stringify(currentUser));
        checkAuthStatus();
        await loadDashboardStats();
        await loadExpenses();
        await loadBudgetAndPrediction();
        await loadUserProfile();
    }
}

async function handleRegister(e) {
    e.preventDefault();
    const name = document.getElementById('regName').value.trim();
    const username = document.getElementById('regUsername').value.trim();
    const email = document.getElementById('regEmail').value.trim();
    const password = document.getElementById('regPassword').value;
    const address = document.getElementById('regAddress').value.trim();
    const alertBox = document.getElementById('regAlert');
    alertBox.classList.add('hidden');

    try {
        const response = await fetch('/api/auth/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, username, email, password, address })
        });
        const data = await response.json();

        if (data.status === 'success') {
            currentUser = data.user;
            localStorage.setItem('currentUser', JSON.stringify(currentUser));
            checkAuthStatus();
            await loadDashboardStats();
            await loadExpenses();
            await loadBudgetAndPrediction();
            await loadUserProfile();
        } else {
            alertBox.innerText = data.message || 'Registration failed.';
            alertBox.classList.remove('hidden');
        }
    } catch (err) {
        // Fallback for static hosting (GitHub Pages)
        currentUser = {
            id: 1,
            name: name || 'Demo User',
            username: username || 'demo',
            email: email || 'demo@expensetracker.com',
            address: address || '123 Tech Park, Silicon Valley, CA',
            monthly_budget: 1500
        };
        localStorage.setItem('currentUser', JSON.stringify(currentUser));
        checkAuthStatus();
        await loadDashboardStats();
        await loadExpenses();
        await loadBudgetAndPrediction();
        await loadUserProfile();
    }
}

function logoutUser() {
    if (confirm('Are you sure you want to sign out?')) {
        currentUser = null;
        localStorage.removeItem('currentUser');
        document.getElementById('sidebarUserName').innerText = 'Sign In Required';
        document.getElementById('sidebarUserEmail').innerText = 'Not authenticated';
        document.getElementById('authModal').classList.remove('hidden');
    }
}

async function loadUserProfile() {
    if (!currentUser) return;

    try {
        const res = await fetch(`/api/user/profile?user_id=${getUserId()}`);
        const data = await res.json();

        if (data.status === 'success') {
            const user = data.user;
            // Populate form
            document.getElementById('profileName').value = user.name || '';
            document.getElementById('profileUsername').value = user.username || '';
            document.getElementById('profileEmail').value = user.email || '';
            document.getElementById('profileAddress').value = user.address || '';
            document.getElementById('profileBudget').value = user.monthly_budget || 1500;

            // Populate summary card
            document.getElementById('summaryProfileName').innerText = user.name || user.username;
            document.getElementById('summaryProfileEmail').innerText = user.email || '';
            document.getElementById('summaryProfileAddress').innerText = user.address || 'Address not provided';
            document.getElementById('summaryProfileBudget').innerText = `₹${parseFloat(user.monthly_budget).toLocaleString('en-IN', {minimumFractionDigits: 2})}`;

            // Update sidebar info
            document.getElementById('sidebarUserName').innerText = user.name || user.username;
            document.getElementById('sidebarUserEmail').innerText = user.email;
        }
    } catch (err) {
        console.error('Error loading user profile:', err);
    }
}

async function handleSaveProfile(e) {
    e.preventDefault();
    const statusText = document.getElementById('profileSaveStatus');
    statusText.innerText = 'Saving changes...';
    statusText.style.color = 'var(--text-muted)';

    const name = document.getElementById('profileName').value.trim();
    const email = document.getElementById('profileEmail').value.trim();
    const address = document.getElementById('profileAddress').value.trim();
    const monthly_budget = parseFloat(document.getElementById('profileBudget').value);

    try {
        const res = await fetch('/api/user/profile', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: getUserId(), name, email, address, monthly_budget })
        });
        const data = await res.json();

        if (data.status === 'success') {
            currentUser = data.user;
            localStorage.setItem('currentUser', JSON.stringify(currentUser));
            statusText.innerText = '✨ Profile saved successfully!';
            statusText.style.color = 'var(--emerald)';

            await loadUserProfile();
            await loadDashboardStats();
            await loadBudgetAndPrediction();

            setTimeout(() => { statusText.innerText = ''; }, 3000);
        } else {
            statusText.innerText = data.message || 'Error updating profile.';
            statusText.style.color = 'var(--rose)';
        }
    } catch (err) {
        statusText.innerText = 'Network error saving profile.';
        statusText.style.color = 'var(--rose)';
    }
}

// --------------------------------------------------------------------------
// 10. BULK EXPENSES FILE UPLOAD (CSV IMPORT) CONTROLLER
// --------------------------------------------------------------------------
let selectedCSVFile = null;

function openImportModal() {
    const modal = document.getElementById('importModal');
    if (!modal) return;
    modal.classList.remove('hidden');

    // Reset file input & UI
    selectedCSVFile = null;
    document.getElementById('csvFileInput').value = '';
    document.getElementById('fileSelectedBadge').classList.add('hidden');
    document.getElementById('csvPreviewContainer').classList.add('hidden');
    document.getElementById('csvPreviewBody').innerHTML = '';
    document.getElementById('btnSubmitImport').disabled = true;

    const banner = document.getElementById('importStatusBanner');
    banner.classList.add('hidden');
    banner.className = 'alert-banner hidden margin-top-md';

    initDropZoneEvents();
}

function closeImportModal() {
    const modal = document.getElementById('importModal');
    if (modal) modal.classList.add('hidden');
}

function initDropZoneEvents() {
    const dropZone = document.getElementById('fileDropZone');
    if (!dropZone || dropZone.dataset.initialized) return;
    dropZone.dataset.initialized = 'true';

    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
        }, false);
    });

    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => dropZone.classList.add('highlight'), false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => dropZone.classList.remove('highlight'), false);
    });

    dropZone.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;
        if (files && files.length > 0) {
            document.getElementById('csvFileInput').files = files;
            handleCSVFileChange({ target: { files: files } });
        }
    }, false);
}

function downloadSampleCSV() {
    const sampleHeaders = "Date,Description,Amount,Category,Payment Method\n";
    const sampleRows = 
        "2026-09-01,Grocery store items,145.50,Food & Dining,Card\n" +
        "2026-09-03,Gasoline fuel refill,60.00,Transportation,UPI\n" +
        "2026-09-05,Electricity monthly bill,110.25,Bills & Utilities,Bank Transfer\n" +
        "2026-09-10,Netflix monthly streaming,15.99,,Credit Card\n" +
        "2026-09-15,Team dinner restaurant,85.00,Food & Dining,Cash\n" +
        "2026-09-20,Pharmacy medicine purchase,32.40,,Debit Card\n";

    const blob = new Blob([sampleHeaders + sampleRows], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', 'sample_expenses_template.csv');
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

function handleCSVFileChange(e) {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    selectedCSVFile = files[0];
    document.getElementById('selectedFileName').innerText = selectedCSVFile.name;
    document.getElementById('selectedFileSize').innerText = `(${(selectedCSVFile.size / 1024).toFixed(1)} KB)`;
    document.getElementById('fileSelectedBadge').classList.remove('hidden');

    // Read and parse preview
    const reader = new FileReader();
    reader.onload = function(event) {
        const text = event.target.result;
        parseAndPreviewCSV(text);
    };
    reader.readAsText(selectedCSVFile);
}

function parseAndPreviewCSV(csvText) {
    const lines = csvText.split(/\r\n|\n/).map(l => l.trim()).filter(l => l.length > 0);
    if (lines.length === 0) return;

    const tbody = document.getElementById('csvPreviewBody');
    tbody.innerHTML = '';

    let rowCount = 0;
    const maxPreview = 10;

    for (let i = 0; i < lines.length; i++) {
        // Skip header line if present
        if (i === 0 && (lines[i].toLowerCase().includes('description') || lines[i].toLowerCase().includes('amount'))) {
            continue;
        }

        const cols = lines[i].split(',').map(c => c.replace(/^["']|["']$/g, '').trim());
        if (cols.length < 2) continue;

        rowCount++;
        if (rowCount <= maxPreview) {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${rowCount}</td>
                <td>${escapeHtml(cols[0] || 'Today')}</td>
                <td><strong>${escapeHtml(cols[1] || '')}</strong></td>
                <td>₹${escapeHtml(cols[2] || '0.00')}</td>
                <td><span class="badge-cat-preview">${escapeHtml(cols[3] || 'Auto-ML')}</span></td>
                <td>${escapeHtml(cols[4] || 'Card')}</td>
            `;
            tbody.appendChild(tr);
        }
    }

    document.getElementById('csvRowCount').innerText = rowCount;
    document.getElementById('csvPreviewContainer').classList.remove('hidden');
    document.getElementById('btnSubmitImport').disabled = (rowCount === 0);
}

async function processCSVImport() {
    if (!selectedCSVFile) {
        alert('Please select a CSV file to upload.');
        return;
    }

    const btn = document.getElementById('btnSubmitImport');
    const banner = document.getElementById('importStatusBanner');
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Processing & Categorizing...';

    banner.classList.add('hidden');

    const formData = new FormData();
    formData.append('file', selectedCSVFile);
    formData.append('user_id', getUserId());
    formData.append('auto_categorize', document.getElementById('chkAutoCategorize').checked ? 'true' : 'false');

    try {
        const response = await fetch('/api/expenses/upload', {
            method: 'POST',
            body: formData
        });
        const data = await response.json();

        if (data.status === 'success') {
            banner.className = 'alert-banner alert-success margin-top-md';
            banner.innerHTML = `<i class="fa-solid fa-circle-check"></i> <strong>Import Complete!</strong> ${escapeHtml(data.message)}`;
            banner.classList.remove('hidden');

            // Refresh application state
            await loadDashboardStats();
            await loadExpenses();
            await loadBudgetAndPrediction();

            setTimeout(() => {
                closeImportModal();
            }, 2500);
        } else {
            banner.className = 'alert-banner alert-error margin-top-md';
            banner.innerHTML = `<i class="fa-solid fa-circle-exclamation"></i> ${escapeHtml(data.message || 'Import failed.')}`;
            banner.classList.remove('hidden');
        }
    } catch (err) {
        banner.className = 'alert-banner alert-error margin-top-md';
        banner.innerHTML = `<i class="fa-solid fa-triangle-exclamation"></i> Network error during file upload.`;
        banner.classList.remove('hidden');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="fa-solid fa-cloud-arrow-up"></i> Upload & Import Expenses';
    }
}
