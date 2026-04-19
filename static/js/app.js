/**
 * 英语单词本 - JavaScript 逻辑
 */

// 全局变量
const API_BASE_URL = '/api';
let wordsCache = []; // 缓存单词列表

// DOM 元素
const wordInput = document.getElementById('wordInput');
const queryBtn = document.getElementById('queryBtn');
const loadingIndicator = document.getElementById('loadingIndicator');
const errorMessage = document.getElementById('errorMessage');
const wordsList = document.getElementById('wordsList');
const wordModal = document.getElementById('wordModal');
const modalBody = document.getElementById('modalBody');
const closeBtn = document.querySelector('.close-btn');

// 初始化
document.addEventListener('DOMContentLoaded', function() {
    loadWordsList();
    setupEventListeners();
});

/**
 * 设置事件监听器
 */
function setupEventListeners() {
    // 查询按钮点击事件
    queryBtn.addEventListener('click', handleQueryWord);

    // 输入框回车事件
    wordInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            handleQueryWord();
        }
    });

    // 关闭弹窗事件
    closeBtn.addEventListener('click', closeModal);

    // 点击弹窗外部关闭
    wordModal.addEventListener('click', function(e) {
        if (e.target === wordModal) {
            closeModal();
        }
    });
}

/**
 * 处理查询单词
 */
async function handleQueryWord() {
    const word = wordInput.value.trim();
    if (!word) {
        showError('请输入英语单词');
        return;
    }

    // 显示加载状态
    showLoading();
    hideError();

    try {
        const response = await fetch(`${API_BASE_URL}/words`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ word: word })
        });

        const data = await response.json();

        if (response.ok) {
            // 成功处理
            wordInput.value = ''; // 清空输入框
            await loadWordsList(); // 刷新列表
        } else {
            // 显示错误信息
            showError(data.error || '操作失败');
        }
    } catch (error) {
        showError('网络错误，请检查网络连接');
        console.error('Error:', error);
    } finally {
        hideLoading();
    }
}

/**
 * 加载单词列表
 */
async function loadWordsList() {
    try {
        const response = await fetch(`${API_BASE_URL}/words`);
        const words = await response.json();

        if (response.ok) {
            wordsCache = words;
            renderWordsList(words);
        } else {
            showError('加载单词列表失败');
        }
    } catch (error) {
        showError('网络错误，请检查网络连接');
        console.error('Error:', error);
    }
}

/**
 * 渲染单词列表
 */
function renderWordsList(words) {
    if (words.length === 0) {
        wordsList.innerHTML = `
            <div class="empty-state">
                <p>暂无单词记录</p>
                <p>开始添加你的第一个单词吧！</p>
            </div>
        `;
        return;
    }

    const wordsHTML = words.map(word => {
        const meaning = word.meaning?.meaning || '暂无释义';
        return `
            <div class="word-card" onclick="showWordDetail('${word.word}')">
                <div class="word-info">
                    <div class="word-text">${word.word}</div>
                    <div class="word-meaning">${meaning}</div>
                </div>
                <div class="word-counter">${word.counter}</div>
            </div>
        `;
    }).join('');

    wordsList.innerHTML = wordsHTML;
}

/**
 * 显示单词详情
 */
async function showWordDetail(word) {
    try {
        const response = await fetch(`${API_BASE_URL}/words/${word}`);
        const wordData = await response.json();

        if (response.ok) {
            renderWordDetail(wordData);
            wordModal.style.display = 'flex';
        } else {
            showError('加载单词详情失败');
        }
    } catch (error) {
        showError('网络错误，请检查网络连接');
        console.error('Error:', error);
    }
}

/**
 * 渲染单词详情
 */
function renderWordDetail(wordData) {
    const meaning = wordData.meaning || {};
    const phrases = meaning.phrases || [];
    const example = meaning.example || {};

    const modalHTML = `
        <div class="word-detail">
            <h3>${wordData.word}</h3>

            <div class="detail-section">
                <h4>📖 中文释义</h4>
                <div class="meaning-text">${meaning.meaning || '暂无释义'}</div>
            </div>

            <div class="detail-section">
                <h4>🔗 常用词组</h4>
                <ul class="phrases-list">
                    ${phrases.length > 0
                        ? phrases.map(p => `
                            <li>
                                <span class="phrase-en">${p.phrase}</span>
                                <span class="phrase-zh">${p.meaning || ''}</span>
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

            <div class="word-stats">
                <div class="stat-item">
                    <span class="stat-label">查询次数：</span>
                    <span class="stat-value">${wordData.counter}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">添加时间：</span>
                    <span class="stat-value">${formatDate(wordData.created_at)}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">最后更新：</span>
                    <span class="stat-value">${formatDate(wordData.updated_at)}</span>
                </div>
            </div>

            <div class="modal-actions">
                <button class="delete-btn" onclick="deleteWord('${wordData.word}')">🗑️ 删除单词</button>
            </div>
        </div>
    `;

    modalBody.innerHTML = modalHTML;
}

/**
 * 关闭弹窗
 */
function closeModal() {
    wordModal.style.display = 'none';
}

/**
 * 显示加载状态
 */
function showLoading() {
    loadingIndicator.style.display = 'block';
    queryBtn.disabled = true;
}

/**
 * 隐藏加载状态
 */
function hideLoading() {
    loadingIndicator.style.display = 'none';
    queryBtn.disabled = false;
}

/**
 * 显示错误信息
 */
function showError(message) {
    errorMessage.textContent = message;
    errorMessage.style.display = 'block';

    // 3秒后自动隐藏错误信息
    setTimeout(hideError, 3000);
}

/**
 * 隐藏错误信息
 */
function hideError() {
    errorMessage.style.display = 'none';
}

/**
 * 格式化日期
 */
function formatDate(dateString) {
    if (!dateString) return '未知';

    const date = new Date(dateString);
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');

    return `${year}-${month}-${day}`;
}

/**
 * 删除单词
 */
async function deleteWord(word) {
    if (!confirm(`确定要删除单词 "${word}" 吗？此操作不可恢复。`)) {
        return;
    }

    try {
        showLoading();
        hideError();

        const response = await fetch(`${API_BASE_URL}/words/${word}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
            }
        });

        const data = await response.json();

        if (response.ok) {
            // 删除成功，关闭弹窗并刷新列表
            closeModal();
            await loadWordsList();
            showError('单词删除成功');
        } else {
            showError(data.error || '删除失败');
        }
    } catch (error) {
        showError('网络错误，请检查网络连接');
        console.error('Error:', error);
    } finally {
        hideLoading();
    }
}

/**
 * 健康检查（调试用）
 */
async function healthCheck() {
    try {
        const response = await fetch(`${API_BASE_URL}/health`);
        const data = await response.json();
        console.log('Health Check:', data);
    } catch (error) {
        console.error('Health Check Failed:', error);
    }
}