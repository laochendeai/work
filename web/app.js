
// State
const state = {
    currentTab: 'dashboard',
    isSearching: false,
    logs: [],
    stats: null
};

// DOM Elements
const views = {
    dashboard: document.getElementById('dashboard'),
    search: document.getElementById('search'),
    results: document.getElementById('results'),
    cards: document.getElementById('cards')
};

const navLinks = document.querySelectorAll('.nav-links li');
const statusIndicator = document.getElementById('server-status');

// Init
document.addEventListener('DOMContentLoaded', () => {
    setupNavigation();
    setupSearchForm();
    connectLogSocket();

    // Initial Load
    loadStats();
    loadAnnouncements();
    loadCards();

    // Poll status
    setInterval(checkStatus, 2000);
});

// Navigation
function setupNavigation() {
    navLinks.forEach(link => {
        link.addEventListener('click', () => {
            const tabName = link.dataset.tab;
            switchTab(tabName);
        });
    });
}

function switchTab(tabName) {
    // Update Nav
    navLinks.forEach(l => l.classList.remove('active'));
    document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');

    // Update View
    Object.values(views).forEach(v => v.classList.remove('active'));
    views[tabName].classList.add('active');

    state.currentTab = tabName;

    // Refresh data if needed
    if (tabName === 'dashboard') loadStats();
    if (tabName === 'results') loadAnnouncements();
    if (tabName === 'cards') loadCards();
}

// Toggle custom date range
function toggleCustomDate() {
    const timeSelect = document.getElementById('search-time');
    const customRow = document.getElementById('custom-date-row');
    if (timeSelect.value === 'custom') {
        customRow.style.display = 'flex';
    } else {
        customRow.style.display = 'none';
    }
}

// Search Logic
function setupSearchForm() {
    const btnStart = document.getElementById('btn-start');
    const btnStop = document.getElementById('btn-stop');
    const logOutput = document.getElementById('log-output');
    const btnClearLog = document.getElementById('btn-clear-log');

    btnStart.addEventListener('click', async () => {
        const kw = document.getElementById('search-kw').value;
        const type = document.getElementById('search-type').value;
        const pinmu = document.getElementById('search-pinmu').value;
        const category = document.getElementById('search-category').value;
        const bidType = document.getElementById('search-bid-type').value;
        const time = document.getElementById('search-time').value;
        const pages = document.getElementById('search-pages').value;

        // Custom dates
        const startDate = document.getElementById('search-start-date').value;
        const endDate = document.getElementById('search-end-date').value;

        if (!kw) return alert("请输入搜索关键词");
        if (time === 'custom' && (!startDate || !endDate)) {
            return alert("请选择自定义开始和结束日期");
        }

        setSearching(true);
        appendLog("System", `正在开始搜索: ${kw}...`);

        try {
            const res = await fetch('/api/search', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    keywords: kw,
                    search_type: type,
                    pinmu: pinmu,
                    category: category,
                    bid_type: bidType,
                    time_type: time,
                    start_date: startDate,
                    end_date: endDate,
                    max_pages: parseInt(pages)
                })
            });
            const data = await res.json();
            if (data.error) throw new Error(data.error);
        } catch (e) {
            appendLog("Error", e.message);
            setSearching(false);
        }
    });

    btnStop.addEventListener('click', async () => {
        await fetch('/api/stop', { method: 'POST' });
        appendLog("System", "Stop command sent.");
    });

    btnClearLog.addEventListener('click', () => {
        logOutput.innerHTML = '';
    });
}

function setSearching(isSearching) {
    state.isSearching = isSearching;
    document.getElementById('btn-start').disabled = isSearching;
    document.getElementById('btn-stop').disabled = !isSearching;

    if (isSearching) {
        statusIndicator.classList.add('busy');
        statusIndicator.querySelector('span').textContent = "正在抓取中...";
    } else {
        statusIndicator.classList.remove('busy');
        statusIndicator.querySelector('span').textContent = "系统就绪";
    }
}

// Fix async function syntax error above
function checkStatus() {
    fetch('/api/status')
        .then(r => r.json())
        .then(data => {
            if (state.isSearching !== data.is_running) {
                setSearching(data.is_running);
            }
        })
        .catch(e => console.error(e));
}

// Log Streaming
function connectLogSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const ws = new WebSocket(`${protocol}//${window.location.host}/api/logs`);
    const logOutput = document.getElementById('log-output');

    ws.onmessage = (event) => {
        const text = event.data;
        appendLog("Output", text);
    };

    ws.onclose = () => {
        setTimeout(connectLogSocket, 2000); // Reconnect
    };
}

function appendLog(source, text) {
    const logOutput = document.getElementById('log-output');
    const div = document.createElement('div');
    div.className = 'log-line';
    if (source === 'System') div.classList.add('system');
    if (source === 'Error') div.classList.add('error');

    div.textContent = text;
    logOutput.appendChild(div);
    logOutput.scrollTop = logOutput.scrollHeight;
}

// Data Loading
async function loadStats() {
    const res = await fetch('/api/stats');
    const data = await res.json();

    if (data.error) return;

    document.getElementById('stat-total-announcements').textContent = data.total_announcements;
    document.getElementById('stat-total-cards').textContent = data.total_cards;

    const topList = document.getElementById('top-companies-list');
    topList.innerHTML = data.top_companies.map(c => `
        <li>
            <span>${c.company}</span>
            <span class="badge">${c.count}</span>
        </li>
    `).join('');
}

async function loadAnnouncements() {
    const res = await fetch('/api/announcements?limit=20');
    const data = await res.json();

    const tbody = document.getElementById('announcements-table-body');
    if (data.error) {
        tbody.innerHTML = `<tr><td colspan="5">Error: ${data.error}</td></tr>`;
        return;
    }

    tbody.innerHTML = data.map(item => `
        <tr>
            <td>${item.publish_date}</td>
            <td title="${item.title}">${item.title.substring(0, 40)}...</td>
            <td>${item.source || '未知'}</td>
            <td><a href="${item.url}" target="_blank" class="link-btn">查看</a></td>
        </tr>
    `).join('');
}

async function loadCards() {
    const input = document.getElementById('card-search-input');
    const q = input ? input.value : "";

    const res = await fetch(`/api/cards?limit=50&q=${q}`);
    const data = await res.json();

    const container = document.getElementById('cards-container');
    if (data.error) {
        container.innerHTML = `Error: ${data.error}`;
        return;
    }

    container.innerHTML = data.map(card => `
        <div class="business-card">
            <div class="card-role">${card.contact_name}</div>
            <div class="card-company" title="${card.company}">${card.company}</div>
            
            ${card.phones ? `
                <div class="card-detail">
                    <i class="fa-solid fa-phone"></i>
                    <span>${card.phones}</span>
                </div>
            ` : ''}
            
            ${card.emails ? `
                <div class="card-detail">
                    <i class="fa-solid fa-envelope"></i>
                    <span>${card.emails}</span>
                </div>
            ` : ''}
        </div>
    `).join('');

    // Add enter listener for search if not exists
    if (input && !input.dataset.listening) {
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') loadCards();
        });
        input.dataset.listening = "true";
    }
}
