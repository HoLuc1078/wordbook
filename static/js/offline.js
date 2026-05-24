/**
 * 离线单词本 — 纯前端逻辑，零 API 调用
 */

// ==================== 全局变量 ====================
let allWords = [];       // 全部单词数据
let filteredWords = [];  // 搜索/排序后的单词
const PAGE_SIZE = 20;
let currentPage = 1;
let totalPages = 1;

// DOM 元素
const uploadSection = document.getElementById('uploadSection');
const uploadZone = document.getElementById('uploadZone');
const fileInput = document.getElementById('fileInput');
const uploadError = document.getElementById('uploadError');
const wordsSection = document.getElementById('wordsSection');
const wordsList = document.getElementById('wordsList');
const wordCount = document.getElementById('wordCount');
const searchInput = document.getElementById('searchInput');
const sortSelect = document.getElementById('sortSelect');
const pagination = document.getElementById('pagination');
const wordModal = document.getElementById('wordModal');
const modalBody = document.getElementById('modalBody');

// ==================== 初始化 ====================
document.addEventListener('DOMContentLoaded', function() {
    setupEventListeners();
    // 尝试从 localStorage 加载上次的文件
    loadCachedData();
});

function setupEventListeners() {
    // 点击上传区域
    uploadZone.addEventListener('click', function() {
        fileInput.click();
    });

    // 文件选择
    fileInput.addEventListener('change', function(e) {
        const file = e.target.files[0];
        if (file) handleFile(file);
    });

    // 拖放
    uploadZone.addEventListener('dragover', function(e) {
        e.preventDefault();
        uploadZone.classList.add('drag-over');
    });
    uploadZone.addEventListener('dragleave', function(e) {
        e.preventDefault();
        uploadZone.classList.remove('drag-over');
    });
    uploadZone.addEventListener('drop', function(e) {
        e.preventDefault();
        uploadZone.classList.remove('drag-over');
        const file = e.dataTransfer.files[0];
        if (file) handleFile(file);
    });

    // 搜索
    searchInput.addEventListener('input', function() {
        filterAndRender();
    });

    // 排序
    sortSelect.addEventListener('change', function() {
        filterAndRender();
    });

    // 单词列表点击
    wordsList.addEventListener('click', function(e) {
        const card = e.target.closest('.word-card');
        if (card) {
            const word = card.dataset.word;
            if (word) showWordDetail(word);
        }
    });

    // 模态框关闭
    wordModal.addEventListener('click', function(e) {
        if (e.target === wordModal) closeModal();
    });
}

// ==================== 文件处理 ====================
function handleFile(file) {
    hideUploadError();

    if (!file.name.toLowerCase().endsWith('.json')) {
        showUploadError('请选择 .json 文件');
        return;
    }

    const reader = new FileReader();
    reader.onload = function(e) {
        try {
            const data = JSON.parse(e.target.result);
            const words = extractWords(data);
            if (words.length === 0) {
                showUploadError('文件中未找到有效单词数据');
                return;
            }
            // 缓存到 localStorage
            try {
                localStorage.setItem('offline_words', JSON.stringify(words));
            } catch (err) {
                console.warn('localStorage 存储失败:', err);
            }
            loadWords(words);
        } catch (err) {
            showUploadError('JSON 解析失败: ' + err.message);
        }
    };
    reader.onerror = function() {
        showUploadError('文件读取失败');
    };
    reader.readAsText(file);
}

function extractWords(data) {
    let words;
    if (Array.isArray(data)) {
        words = data;
    } else if (typeof data === 'object' && data !== null) {
        if (Array.isArray(data.words)) {
            words = data.words;
        } else {
            return [];
        }
    } else {
        return [];
    }
    // 过滤有效条目
    return words.filter(w => w && typeof w === 'object' && w.word && String(w.word).trim());
}

function loadCachedData() {
    const cached = localStorage.getItem('offline_words');
    if (cached) {
        try {
            const words = JSON.parse(cached);
            if (words.length > 0) {
                loadWords(words);
            }
        } catch (e) {
            localStorage.removeItem('offline_words');
        }
    }
}

function loadWords(words) {
    allWords = words;
    // 标准化数据
    allWords.forEach(w => {
        w.word = String(w.word).trim().toLowerCase();
        w.counter = w.counter || 1;
        w.note = w.note || '无';
        // 标准化 meaning
        if (!w.meaning) {
            w.meaning = [];
        } else if (typeof w.meaning === 'string') {
            w.meaning = [{ pos: '', translation: w.meaning }];
        }
        // 确保 phrases/example 存在
        if (!w.phrases) w.phrases = [];
        if (!w.example) w.example = {};
    });

    uploadSection.style.display = 'none';
    wordsSection.style.display = 'block';
    filterAndRender();
}

function resetFile() {
    allWords = [];
    filteredWords = [];
    wordsSection.style.display = 'none';
    uploadSection.style.display = 'block';
    fileInput.value = '';
    hideUploadError();
}

// ==================== 搜索与排序 ====================
function filterAndRender() {
    const query = searchInput.value.trim().toLowerCase();

    if (query) {
        filteredWords = allWords.filter(w =>
            w.word.toLowerCase().includes(query) ||
            meaningText(w).toLowerCase().includes(query)
        );
    } else {
        filteredWords = [...allWords];
    }

    // 排序
    const sortBy = sortSelect.value;
    if (sortBy === 'counter') {
        filteredWords.sort((a, b) => b.counter - a.counter || a.word.localeCompare(b.word));
    } else {
        filteredWords.sort((a, b) => a.word.localeCompare(b.word));
    }

    currentPage = 1;
    totalPages = Math.max(1, Math.ceil(filteredWords.length / PAGE_SIZE));
    wordCount.textContent = `(${filteredWords.length} / ${allWords.length})`;
    renderCurrentPage();
}

// ==================== 渲染 ====================
function renderCurrentPage() {
    const startIndex = (currentPage - 1) * PAGE_SIZE;
    const endIndex = startIndex + PAGE_SIZE;
    const pageWords = filteredWords.slice(startIndex, endIndex);

    if (filteredWords.length === 0) {
        wordsList.innerHTML = `
            <div class="empty-state">
                <p>没有找到匹配的单词</p>
            </div>
        `;
        pagination.style.display = 'none';
        return;
    }

    const wordsHTML = pageWords.map(w => {
        const meaningStr = meaningText(w);
        return `
            <div class="word-card" data-word="${w.word}">
                <div class="word-info">
                    <div class="word-text">${w.word}</div>
                    <div class="word-meaning">${meaningStr || '暂无释义'}</div>
                </div>
                <div class="word-counter">${w.counter}</div>
            </div>
        `;
    }).join('');

    wordsList.innerHTML = wordsHTML;

    if (totalPages > 1) {
        pagination.style.display = 'flex';
        document.getElementById('pageInfo').textContent = `${currentPage} / ${totalPages}`;
        document.getElementById('prevPageBtn').disabled = currentPage <= 1;
        document.getElementById('nextPageBtn').disabled = currentPage >= totalPages;
    } else {
        pagination.style.display = 'none';
    }
}

function changePage(delta) {
    const newPage = currentPage + delta;
    if (newPage >= 1 && newPage <= totalPages) {
        currentPage = newPage;
        renderCurrentPage();
    }
}

// ==================== 单词详情 ====================
function showWordDetail(word) {
    const w = allWords.find(item => item.word === word);
    if (!w) return;

    // 标准化 meaning 数据
    let meaningArr = [];
    let phrases = [];
    let example = {};

    if (Array.isArray(w.meaning)) {
        meaningArr = w.meaning;
        phrases = w.phrases || [];
        example = w.example || {};
    } else if (typeof w.meaning === 'object' && w.meaning !== null) {
        if (Array.isArray(w.meaning.meaning)) {
            meaningArr = w.meaning.meaning;
            phrases = w.meaning.phrases || [];
            example = w.meaning.example || {};
        } else if (w.meaning.meaning) {
            meaningArr = [{ pos: '', translation: w.meaning.meaning }];
        }
        if (!phrases.length && w.phrases) phrases = w.phrases;
        if (!example.en && w.example) example = w.example;
    } else if (typeof w.meaning === 'string') {
        meaningArr = [{ pos: '', translation: w.meaning }];
    }

    let meaningHTML;
    if (meaningArr.length > 0) {
        meaningHTML = meaningArr.map(item => {
            const pos = item.pos || '';
            const translation = item.translation || '';
            return `<div class="meaning-item"><span class="pos-tag">${pos}</span> ${translation}</div>`;
        }).join('');
    } else {
        meaningHTML = '<div class="meaning-item">暂无释义</div>';
    }

    const modalHTML = `
        <div class="word-detail">
            <h3>${w.word}</h3>

            <div class="detail-section">
                <h4>📖 中文释义</h4>
                <div class="meaning-list">${meaningHTML}</div>
            </div>

            <div class="detail-section">
                <h4>🔗 常用词组</h4>
                <ul class="phrases-list">
                    ${phrases.length > 0
                        ? phrases.map(p => `
                            <li>
                                <span class="phrase-en">${p.phrase || p.en || ''}</span>
                                <span class="phrase-zh">${p.meaning || p.zh || ''}</span>
                            </li>
                        `).join('')
                        : '<li>暂无词组</li>'
                    }
                </ul>
            </div>

            <div class="detail-section">
                <h4>📝 例句</h4>
                <div class="example-box">
                    <div class="example-en">${example.en || '暂无例句'}</div>
                    <div class="example-zh">${example.zh || ''}</div>
                </div>
            </div>

            <div class="detail-section">
                <h4>🏷️ 备注</h4>
                <div class="note-box">${w.note || '无'}</div>
            </div>

            <div class="word-stats">
                <div class="stat-item">
                    <span class="stat-label">查询次数：</span>
                    <span class="stat-value">${w.counter || 1}</span>
                </div>
            </div>
        </div>
    `;

    modalBody.innerHTML = modalHTML;
    wordModal.style.display = 'flex';
}

function closeModal() {
    wordModal.style.display = 'none';
}

// ==================== 工具函数 ====================
function meaningText(w) {
    if (!w.meaning) return '';
    if (typeof w.meaning === 'string') return w.meaning;
    if (Array.isArray(w.meaning)) {
        return w.meaning.map(item => {
            if (typeof item === 'object') {
                const pos = item.pos || '';
                const trans = item.translation || '';
                return pos ? `${pos} ${trans}` : trans;
            }
            return '';
        }).filter(Boolean).join('；');
    }
    if (typeof w.meaning === 'object') {
        if (Array.isArray(w.meaning.meaning)) {
            return w.meaning.meaning.map(item => {
                const pos = item.pos || '';
                const trans = item.translation || '';
                return pos ? `${pos} ${trans}` : trans;
            }).filter(Boolean).join('；');
        }
        if (typeof w.meaning.meaning === 'string') return w.meaning.meaning;
    }
    return '';
}

function showUploadError(msg) {
    uploadError.textContent = msg;
    uploadError.style.display = 'block';
}

function hideUploadError() {
    uploadError.style.display = 'none';
}

// ==================== 主题切换（复用 theme.js 中的函数） ====================
// theme.js 已加载，直接使用其中的 toggleThemeDropdown, setTheme 等函数
