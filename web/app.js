
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
    setupKeywordUpload();
    setupCardExport();
    connectLogSocket();

    // Initial Load
    loadStats();
    loadAnnouncements();
    loadCards();
    loadSavedKeywords();

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

// Announcements state for pagination
let announcementsState = {
    offset: 0,
    limit: 50,
    total: 0,
    query: "",
    province: ""
};

async function loadAnnouncements(resetPage = true) {
    const tbody = document.getElementById('announcements-table-body');

    try {
        if (resetPage) {
            announcementsState.offset = 0;
        }

        const searchInput = document.getElementById('announcement-search-input');
        const provinceSelect = document.getElementById('province-filter');

        announcementsState.query = searchInput ? searchInput.value : "";
        announcementsState.province = provinceSelect ? provinceSelect.value : "";

        const params = new URLSearchParams({
            limit: announcementsState.limit,
            offset: announcementsState.offset,
            q: announcementsState.query,
            province: announcementsState.province
        });

        const res = await fetch(`/api/announcements?${params}`);
        const data = await res.json();

        if (data.error) {
            tbody.innerHTML = `<tr><td colspan="5">Error: ${data.error}</td></tr>`;
            return;
        }

        // Update state
        announcementsState.total = data.total || 0;
        const items = data.items || [];

        // Update header
        updateAnnouncementsHeader();

        if (items.length === 0) {
            tbody.innerHTML = `<tr><td colspan="5" class="no-data">暂无公告数据</td></tr>`;
            return;
        }

        tbody.innerHTML = items.map(item => `
            <tr>
                <td>${item.publish_date || ''}</td>
                <td title="${item.title || ''}">${(item.title || '').substring(0, 50)}${item.title && item.title.length > 50 ? '...' : ''}</td>
                <td>${item.source || '未知'}</td>
                <td>
                    <button class="btn small" onclick="viewAnnouncement(${item.id})">详情</button>
                    <a href="${item.url}" target="_blank" class="link-btn" style="margin-left:8px">原文</a>
                </td>
            </tr>
        `).join('');
    } catch (err) {
        console.error('loadAnnouncements error:', err);
        tbody.innerHTML = `<tr><td colspan="5">加载失败: ${err.message}</td></tr>`;
    }
}

function updateAnnouncementsHeader() {
    const countSpan = document.getElementById('announcements-count-info');
    const prevBtn = document.getElementById('btn-prev-announcements');
    const nextBtn = document.getElementById('btn-next-announcements');

    if (countSpan) {
        if (announcementsState.total === 0) {
            countSpan.textContent = '共 0 条';
        } else {
            const start = announcementsState.offset + 1;
            const end = Math.min(announcementsState.offset + announcementsState.limit, announcementsState.total);
            countSpan.textContent = `显示 ${start}-${end} / 共 ${announcementsState.total} 条`;
        }
    }

    if (prevBtn) {
        prevBtn.disabled = announcementsState.offset === 0;
    }
    if (nextBtn) {
        nextBtn.disabled = announcementsState.offset + announcementsState.limit >= announcementsState.total;
    }
}

function loadMoreAnnouncements() {
    if (announcementsState.offset + announcementsState.limit < announcementsState.total) {
        announcementsState.offset += announcementsState.limit;
        loadAnnouncements(false);
    }
}

function loadPrevAnnouncements() {
    if (announcementsState.offset > 0) {
        announcementsState.offset = Math.max(0, announcementsState.offset - announcementsState.limit);
        loadAnnouncements(false);
    }
}

// Cards state for pagination
let cardsState = {
    offset: 0,
    limit: 50,
    total: 0,
    query: ""
};

async function loadCards(resetPage = true) {
    const container = document.getElementById('cards-container');

    try {
        const input = document.getElementById('card-search-input');
        const q = input ? input.value : "";

        if (resetPage) {
            cardsState.offset = 0;
        }
        cardsState.query = q;

        const res = await fetch(`/api/cards?limit=${cardsState.limit}&offset=${cardsState.offset}&q=${encodeURIComponent(q)}`);
        const data = await res.json();

        if (data.error) {
            container.innerHTML = `<div class="no-data">Error: ${data.error}</div>`;
            return;
        }

        // Update cards state
        cardsState.total = data.total || 0;
        const items = data.items || [];

        // Update header with count info
        updateCardsHeader();

        if (items.length === 0) {
            container.innerHTML = '<div class="no-data">暂无名片数据</div>';
            return;
        }

        container.innerHTML = items.map(card => {
            const safeCompany = (card.company || '').replace(/'/g, "\\'");
            const safeContact = (card.contact_name || '').replace(/'/g, "\\'");
            const initial = card.contact_name ? card.contact_name.charAt(0) : '?';

            return `
            <div class="business-card" onclick="viewCardMentions(${card.id}, '${safeCompany}', '${safeContact}')">
                <div class="bc-top">
                    <div class="bc-avatar">${initial}</div>
                    <div class="bc-info">
                        <div class="bc-name">${card.contact_name || ''}</div>
                        <div class="bc-company" title="${card.company || ''}">${card.company || ''}</div>
                    </div>
                </div>
                
                <div class="bc-details">
                    ${card.phones ? `
                        <div class="bc-row">
                            <i class="fa-solid fa-phone"></i>
                            <span>${card.phones}</span>
                        </div>
                    ` : '<div class="bc-row placeholder">暂无电话</div>'}
                    
                    ${card.emails ? `
                        <div class="bc-row">
                            <i class="fa-solid fa-envelope"></i>
                            <span>${card.emails}</span>
                        </div>
                    ` : ''}
                </div>
                
                <div class="bc-footer">
                    <div class="bc-source">
                        <i class="fa-solid fa-link"></i>
                        <span>关联 ${card.projects_count || 0} 个来源</span>
                    </div>
                    <i class="fa-solid fa-chevron-right arrow-icon"></i>
                </div>
            </div>
        `}).join('');

        // Add enter listener for search if not exists
        if (input && !input.dataset.listening) {
            input.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') loadCards(true);
            });
            input.dataset.listening = "true";
        }
    } catch (err) {
        console.error('loadCards error:', err);
        container.innerHTML = `<div class="no-data">加载失败: ${err.message}</div>`;
    }
}

function updateCardsHeader() {
    const countSpan = document.getElementById('cards-count-info');
    const prevBtn = document.getElementById('btn-prev-cards');
    const nextBtn = document.getElementById('btn-next-cards');

    if (countSpan) {
        if (cardsState.total === 0) {
            countSpan.textContent = '共 0 条';
        } else {
            const start = cardsState.offset + 1;
            const end = Math.min(cardsState.offset + cardsState.limit, cardsState.total);
            countSpan.textContent = `显示 ${start}-${end} / 共 ${cardsState.total} 条`;
        }
    }

    // Update pagination buttons
    if (prevBtn) {
        prevBtn.disabled = cardsState.offset === 0;
    }
    if (nextBtn) {
        nextBtn.disabled = cardsState.offset + cardsState.limit >= cardsState.total;
    }
}

function loadMoreCards() {
    if (cardsState.offset + cardsState.limit < cardsState.total) {
        cardsState.offset += cardsState.limit;
        loadCards(false);
    }
}

function loadPrevCards() {
    if (cardsState.offset > 0) {
        cardsState.offset = Math.max(0, cardsState.offset - cardsState.limit);
        loadCards(false);
    }
}


// Modal Logic
const modal = document.getElementById('detail-modal');
const closeModal = document.querySelector('.close-modal');

if (closeModal) {
    closeModal.onclick = function () {
        modal.style.display = "none";
    }
}

window.onclick = function (event) {
    if (event.target == modal) {
        modal.style.display = "none";
    }
}

async function viewAnnouncement(id) {
    try {
        const res = await fetch(`/api/announcements/${id}`);
        const data = await res.json();

        if (data.error) return alert(data.error);

        document.getElementById('modal-title').textContent = data.title;
        document.getElementById('modal-date').textContent = data.publish_date;
        document.getElementById('modal-source').textContent = data.source;
        document.getElementById('modal-url').href = data.url;
        document.getElementById('modal-content').textContent = data.content || "暂无详情内容";

        modal.style.display = "block";
    } catch (e) {
        console.error(e);
        alert("加载失败");
    }
}

// Card Modal Logic
const cardModal = document.getElementById('card-detail-modal');
const closeCardModal = document.querySelector('.close-card-modal');

if (closeCardModal) {
    closeCardModal.onclick = function () {
        cardModal.style.display = "none";
    }
}

// Update global window click to handle both modals
const originalWindowClick = window.onclick;
window.onclick = function (event) {
    if (originalWindowClick) originalWindowClick(event);
    if (event.target == cardModal) {
        cardModal.style.display = "none";
    }
    if (event.target == modal) { // Ensure the original modal also closes
        modal.style.display = "none";
    }
}

async function viewCardMentions(id, company, contact) {
    document.getElementById('card-modal-title').textContent = company;
    document.getElementById('card-modal-contact').textContent = "联系人: " + contact;

    const mentionsDiv = document.getElementById('card-modal-mentions');
    mentionsDiv.innerHTML = '<div style="padding: 20px; text-align: center; color: #666;"><i class="fa-solid fa-spinner fa-spin"></i> 加载中...</div>';

    cardModal.style.display = "block";

    try {
        const res = await fetch(`/api/cards/${id}/mentions`);
        const data = await res.json();

        if (data.error) {
            mentionsDiv.innerHTML = `<p class="error">Error: ${data.error}</p>`;
            return;
        }

        if (!data || data.length === 0) {
            mentionsDiv.innerHTML = '<p style="padding: 10px; color: #666;">暂无关联来源信息</p>';
            return;
        }

        mentionsDiv.innerHTML = data.map(m => `
            <div class="mention-item" style="margin-bottom: 12px; padding: 12px; background: #f8f9fa; border-left: 3px solid #007bff; border-radius: 4px;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                    <span style="font-weight: 600; color: #2c3e50;">${m.source || '未知来源'}</span>
                    <span style="font-size: 0.85em; color: #6c757d;">${m.publish_date}</span>
                </div>
                <div style="margin-bottom: 6px;">
                    <a href="${m.url}" target="_blank" style="color: #007bff; text-decoration: none; font-weight: 500;">
                        ${m.title} <i class="fa-solid fa-external-link-alt" style="font-size: 0.8em;"></i>
                    </a>
                </div>
                ${m.role ? `<div style="font-size: 0.85em; color: #555;">角色: ${m.role}</div>` : ''}
            </div>
        `).join('');

    } catch (e) {
        mentionsDiv.innerHTML = `<p class="error">加载失败: ${e.message}</p>`;
    }
}

// ========== Keyword File Upload ==========
function setupKeywordUpload() {
    const uploadBtn = document.getElementById('btn-upload-keywords');
    const fileInput = document.getElementById('keyword-file-input');
    const fileNameHint = document.getElementById('keyword-file-name');
    const kwInput = document.getElementById('search-kw');

    if (!uploadBtn || !fileInput) return;

    uploadBtn.addEventListener('click', () => {
        fileInput.click();
    });

    fileInput.addEventListener('change', async (e) => {
        const file = e.target.files[0];
        if (!file) return;

        fileNameHint.textContent = `已选: ${file.name}`;

        // Read file content
        const text = await file.text();

        // Parse keywords (support comma, newline, semicolon separation)
        const keywords = text
            .split(/[\n\r,;，；]+/)
            .map(k => k.trim())
            .filter(k => k && !k.startsWith('#'));  // Filter empty and comments

        if (keywords.length === 0) {
            alert('文件中未找到有效关键词');
            return;
        }

        // Update input field
        kwInput.value = keywords.join(', ');

        // Save to server
        try {
            const res = await fetch('/api/keywords', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    keywords: keywords,
                    filename: file.name
                })
            });
            const data = await res.json();
            if (data.error) {
                console.error('保存关键词失败:', data.error);
            } else {
                fileNameHint.textContent = `已保存: ${file.name} (${keywords.length} 个关键词)`;
            }
        } catch (err) {
            console.error('保存关键词失败:', err);
        }
    });
}

async function loadSavedKeywords() {
    try {
        const res = await fetch('/api/keywords');
        const data = await res.json();

        if (data.keywords && data.keywords.length > 0) {
            const kwInput = document.getElementById('search-kw');
            const fileNameHint = document.getElementById('keyword-file-name');

            kwInput.value = data.keywords.join(', ');
            if (data.filename) {
                fileNameHint.textContent = `已加载: ${data.filename} (${data.keywords.length} 个)`;
            }
        }
    } catch (err) {
        console.log('无已保存关键词');
    }
}

// ========== Card Export ==========
function setupCardExport() {
    const exportBtn = document.getElementById('btn-export-cards');
    if (!exportBtn) return;

    exportBtn.addEventListener('click', async () => {
        const searchInput = document.getElementById('card-search-input');
        const q = searchInput ? searchInput.value : '';

        exportBtn.disabled = true;
        exportBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> 导出中...';

        try {
            const response = await fetch(`/api/cards/export?q=${encodeURIComponent(q)}`);

            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.error || '导出失败');
            }

            // Get filename from header or use default
            const contentDisposition = response.headers.get('Content-Disposition');
            let filename = 'business_cards.xlsx';
            if (contentDisposition) {
                const match = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
                if (match && match[1]) {
                    filename = match[1].replace(/['"]/g, '');
                }
            }

            // Download file
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            a.remove();

        } catch (err) {
            alert('导出失败: ' + err.message);
        } finally {
            exportBtn.disabled = false;
            exportBtn.innerHTML = '<i class="fa-solid fa-download"></i> 导出名片';
        }
    });
}
