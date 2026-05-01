/**
 * 英语单词本 - JavaScript 逻辑
 */

// 全局变量
const API_BASE_URL = '/api';
let wordsCache = []; // 缓存单词列表
let currentUser = null; // 当前登录用户

// 动态加载必要的库
function loadLibraries() {
    return new Promise((resolve) => {
        // Load KaTeX if not already loaded
        if (!window.katex) {
            const katexScript = document.createElement('script');
            katexScript.src = 'https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js';
            katexScript.onload = () => {
                if (window.katex && window.marked) resolve();
            };
            document.head.appendChild(katexScript);
        }

        // Load marked if not already loaded
        if (!window.marked) {
            const markedScript = document.createElement('script');
            markedScript.src = 'https://cdn.jsdelivr.net/npm/marked/marked.min.js';
            markedScript.onload = () => {
                marked.setOptions({
                    breaks: true,
                    gfm: true,
                    headerIds: false,
                    mangle: false
                });
                if (window.katex && window.marked) resolve();
            };
            document.head.appendChild(markedScript);
        }

        // If both already loaded, resolve immediately
        if (window.katex && window.marked) {
            resolve();
        }
    });
}

/**
 * 渲染消息内容（支持Markdown和LaTeX）
 */
function renderMessageContent(content) {
    if (!content) return '';

    // Initialize libraries if needed
    if (!window.marked || !window.katex) {
        console.warn('Libraries not loaded yet, returning plain text');
        return content.replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }

    try {
        // First, render markdown
        let html = marked.parse(content);

        // Then render LaTeX expressions
        // Handle block LaTeX: $$...$$
        html = html.replace(/\$\$([\s\S]*?)\$\$/g, (match, latex) => {
            try {
                return katex.renderToString(latex.trim(), {
                    displayMode: true,
                    throwOnError: false,
                    errorColor: '#cc0000'
                });
            } catch (e) {
                return `<code style="color: #cc0000;">LaTeX Error: ${e.message}</code>`;
            }
        });

        // Handle inline LaTeX: $...$ (but not inside code blocks)
        html = html.replace(/(?<!\\)\$([^$\n]+?)(?<!\\)\$/g, (match, latex) => {
            try {
                return katex.renderToString(latex.trim(), {
                    displayMode: false,
                    throwOnError: false,
                    errorColor: '#cc0000'
                });
            } catch (e) {
                return `<code style="color: #cc0000;">LaTeX Error: ${e.message}</code>`;
            }
        });

        return html;
    } catch (error) {
        console.error('Error rendering message content:', error);
        return content;
    }
}

// DOM 元素
const wordInput = document.getElementById('wordInput');
const queryBtn = document.getElementById('queryBtn');
const loadingIndicator = document.getElementById('loadingIndicator');
const errorMessage = document.getElementById('errorMessage');
const wordsList = document.getElementById('wordsList');
const wordModal = document.getElementById('wordModal');
const modalBody = document.getElementById('modalBody');
const closeBtn = document.querySelector('.close-btn');
const loginModal = document.getElementById('loginModal');
const loginBtn = document.getElementById('loginBtn');
const userInfo = document.getElementById('userInfo');
const aiChatBtn = document.getElementById('aiChatBtn');
let chatHistory = JSON.parse(localStorage.getItem('chatHistory') || '[]'); // 聊天历史

// 仅在AI聊天模态框存在时加载聊天历史
function loadChatHistoryIfNeeded() {
    const aiChatModal = document.getElementById('aiChatModal');
    if (aiChatModal) {
        loadChatHistory();
    }
}

// 初始化
document.addEventListener('DOMContentLoaded', function() {
    checkLoginStatus();
    setupEventListeners();
    loadChatHistoryIfNeeded();
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

    // 登录按钮点击事件
    loginBtn.addEventListener('click', function() {
        loginModal.style.display = 'flex';
    });

    // 登录弹窗关闭
    loginModal.querySelector('.close-btn').addEventListener('click', function() {
        loginModal.style.display = 'none';
    });

    // 点击登录弹窗外部关闭
    loginModal.addEventListener('click', function(e) {
        if (e.target === loginModal) {
            loginModal.style.display = 'none';
        }
    });

    // AI聊天弹窗关闭
    aiChatModal.querySelector('.close-btn').addEventListener('click', function() {
        aiChatModal.style.display = 'none';
    });

    // 点击AI聊天弹窗外部关闭
    aiChatModal.addEventListener('click', function(e) {
        if (e.target === aiChatModal) {
            aiChatModal.style.display = 'none';
        }
    });
}

/**
 * 检查登录状态
 */
async function checkLoginStatus() {
    try {
        const response = await fetch(`${API_BASE_URL}/current_user`);
        const data = await response.json();

        if (response.ok) {
            currentUser = data.user;
            updateUI();
            await loadWordsList(); // 总是加载单词列表
        }
    } catch (error) {
        console.error('Error checking login status:', error);
    }
}

/**
 * 更新UI根据登录状态
 */
function updateUI() {
    if (currentUser) {
        userInfo.textContent = `欢迎，${currentUser.username}`;
        loginBtn.textContent = '退出';
        loginBtn.className = 'logout-btn';
        loginBtn.onclick = logout;
    } else {
        userInfo.textContent = '未登录（本地模式）';
        loginBtn.textContent = '登录';
        loginBtn.className = 'login-btn';
        loginBtn.onclick = function() {
            loginModal.style.display = 'flex';
        };
    }
    queryBtn.disabled = false;
    loadWordsList();
}

/**
 * 切换认证标签页
 */
function switchTab(tab) {
    const loginForm = document.getElementById('loginForm');
    const registerForm = document.getElementById('registerForm');
    const tabBtns = document.querySelectorAll('.tab-btn');

    tabBtns.forEach(btn => btn.classList.remove('active'));

    if (tab === 'login') {
        loginForm.style.display = 'block';
        registerForm.style.display = 'none';
        tabBtns[0].classList.add('active');
    } else {
        loginForm.style.display = 'none';
        registerForm.style.display = 'block';
        tabBtns[1].classList.add('active');
    }
}

/**
 * 处理登录
 */
async function handleLogin() {
    const username = document.getElementById('loginUsername').value.trim();
    const password = document.getElementById('loginPassword').value.trim();

    if (!username) {
        showError('请输入用户名');
        return;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                username: username,
                password: password || undefined
            })
        });

        const data = await response.json();

        if (response.ok) {
            // 登录成功
            currentUser = data.user;
            loginModal.style.display = 'none';
            updateUI();
            showError('登录成功');
        } else {
            showError(data.error || '登录失败');
        }
    } catch (error) {
        showError('网络错误，请检查网络连接');
        console.error('Error:', error);
    }
}

/**
 * 处理注册
 */
async function handleRegister() {
    const username = document.getElementById('registerUsername').value.trim();
    const password = document.getElementById('registerPassword').value.trim();

    if (!username || username.length < 3) {
        showError('用户名至少需要3个字符');
        return;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/register`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                username: username,
                password: password || undefined
            })
        });

        const data = await response.json();

        if (response.ok) {
            // 注册成功，自动登录
            currentUser = data.user;
            loginModal.style.display = 'none';
            updateUI();
            showError('注册并登录成功');
        } else {
            showError(data.error || '注册失败');
        }
    } catch (error) {
        showError('网络错误，请检查网络连接');
        console.error('Error:', error);
    }
}

/**
 * 处理退出登录
 */
async function logout() {
    try {
        const response = await fetch(`${API_BASE_URL}/logout`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });

        if (response.ok) {
            currentUser = null;
            wordsCache = [];
            updateUI();
            showError('已退出登录');
        }
    } catch (error) {
        console.error('Error:', error);
    }
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

    // 检查是否已登录
    if (!currentUser) {
        showError('请先登录才能添加单词');
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
                <button class="edit-btn" onclick="editWord('${wordData.word}')">✏️ 编辑单词</button>
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
 * 编辑单词
 */
function editWord(word) {
    // 找到当前单词数据
    const wordData = wordsCache.find(w => w.word === word);
    if (!wordData) return;

    const meaning = wordData.meaning || {};
    const phrases = meaning.phrases || [];
    const example = meaning.example || {};

    // 将详情转换为编辑模式
    const editHTML = `
        <div class="word-edit-form">
            <h3>编辑单词</h3>

            <div class="form-group">
                <label>英文单词：</label>
                <input type="text" id="editWordInput" value="${wordData.word}" class="form-input">
            </div>

            <div class="form-group">
                <label>中文释义：</label>
                <textarea id="editMeaningInput" class="form-input" rows="2">${meaning.meaning || ''}</textarea>
            </div>

            <div class="form-group">
                <label>词组：</label>
                <div id="editPhrasesContainer">
                    ${phrases.map((p, index) => `
                        <div class="phrase-input-group">
                            <input type="text" id="editPhraseEn${index}" value="${p.phrase}" placeholder="英文词组" class="form-input">
                            <input type="text" id="editPhraseZh${index}" value="${p.meaning || ''}" placeholder="中文含义" class="form-input">
                            <button type="button" onclick="removePhrase(${index})" class="remove-btn">删除</button>
                        </div>
                    `).join('')}
                </div>
                <button type="button" onclick="addPhrase()" class="add-btn">+ 添加词组</button>
            </div>

            <div class="form-group">
                <label>例句：</label>
                <div class="example-input-group">
                    <input type="text" id="editExampleEn" value="${example.en || ''}" placeholder="英文例句" class="form-input">
                    <input type="text" id="editExampleZh" value="${example.zh || ''}" placeholder="中文翻译" class="form-input">
                </div>
            </div>

            <div class="form-group">
                <label>查询次数：</label>
                <input type="number" id="editCounterInput" value="${wordData.counter}" min="1" class="form-input">
            </div>

            <div class="form-actions">
                <button class="save-btn" onclick="saveWord('${word}')">💾 保存</button>
                <button class="cancel-btn" onclick="cancelEdit()">❌ 取消</button>
            </div>
        </div>
    `;

    modalBody.innerHTML = editHTML;
}

// 用于跟踪当前编辑的词组数量
let currentPhraseCount = 0;

/**
 * 添加词组输入框
 */
function addPhrase() {
    currentPhraseCount++;
    const container = document.getElementById('editPhrasesContainer');
    const newPhraseHTML = `
        <div class="phrase-input-group">
            <input type="text" id="editPhraseEn${currentPhraseCount}" placeholder="英文词组" class="form-input">
            <input type="text" id="editPhraseZh${currentPhraseCount}" placeholder="中文含义" class="form-input">
            <button type="button" onclick="removePhrase(${currentPhraseCount})" class="remove-btn">删除</button>
        </div>
    `;
    container.insertAdjacentHTML('beforeend', newPhraseHTML);
}

/**
 * 删除词组输入框
 */
function removePhrase(index) {
    const element = document.getElementById(`editPhraseEn${index}`)?.parentElement;
    if (element) {
        element.remove();
    }
}

/**
 * 保存单词编辑
 */
async function saveWord(originalWord) {
    try {
        const newWord = document.getElementById('editWordInput').value.trim();
        const meaningText = document.getElementById('editMeaningInput').value.trim();
        const exampleEn = document.getElementById('editExampleEn').value.trim();
        const exampleZh = document.getElementById('editExampleZh').value.trim();
        const counter = parseInt(document.getElementById('editCounterInput').value) || 1;

        // 收集所有词组
        const phrases = [];
        const phraseGroups = document.querySelectorAll('.phrase-input-group');
        phraseGroups.forEach(group => {
            const enInput = group.querySelector('input[type="text"]:first-child');
            const zhInput = group.querySelectorAll('input[type="text"]')[1];
            if (enInput && enInput.value.trim()) {
                phrases.push({
                    phrase: enInput.value.trim(),
                    meaning: zhInput ? zhInput.value.trim() : ''
                });
            }
        });

        // 构建更新数据
        const updateData = {
            word: newWord,
            counter: counter,
            meaning: {
                meaning: meaningText,
                phrases: phrases,
                example: {
                    en: exampleEn,
                    zh: exampleZh
                }
            }
        };

        showLoading();
        hideError();

        const response = await fetch(`${API_BASE_URL}/words/${originalWord}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(updateData)
        });

        const data = await response.json();

        if (response.ok) {
            // 更新成功，刷新列表和详情
            await loadWordsList();
            closeModal();
            showError('单词更新成功');
        } else {
            showError(data.error || '更新失败');
        }
    } catch (error) {
        showError('网络错误，请检查网络连接');
        console.error('Error:', error);
    } finally {
        hideLoading();
    }
}

/**
 * 取消编辑
 */
function cancelEdit() {
    const currentWord = document.querySelector('.word-edit-form h3')?.textContent;
    if (currentWord && wordsCache.length > 0) {
        // 重新显示单词详情
        const wordData = wordsCache.find(w => w.word === currentWord);
        if (wordData) {
            renderWordDetail(wordData);
        }
    }
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
 * 切换到AI聊天页面
 */
function toggleAIChat() {
    window.location.href = '/ai-chat';
}

/**
 * 加载聊天历史
 */
function loadChatHistory() {
    const savedHistory = localStorage.getItem('chatHistory');
    if (savedHistory) {
        chatHistory = JSON.parse(savedHistory);
        renderChatMessages();
    }
}

/**
 * 保存聊天历史
 */
function saveChatHistory() {
    localStorage.setItem('chatHistory', JSON.stringify(chatHistory));
}

/**
 * 渲染聊天消息
 */
function renderChatMessages() {
    chatMessages.innerHTML = '';

    // 添加欢迎消息（只在第一次）
    if (chatHistory.length === 0) {
        const welcomeDiv = document.createElement('div');
        welcomeDiv.className = 'chat-welcome';
        welcomeDiv.innerHTML = '<p>你好！我是 LongCat AI，有什么可以帮助你的吗？</p>';
        chatMessages.appendChild(welcomeDiv);
        return;
    }

    // 渲染历史消息
    chatHistory.forEach(msg => {
        const messageWrapper = document.createElement('div');
        messageWrapper.className = 'message-wrapper';
        messageWrapper.dataset.messageId = msg.id || '';

        // Add delete button
        const deleteBtn = document.createElement('button');
        deleteBtn.className = 'message-delete-btn';
        deleteBtn.innerHTML = '×';
        deleteBtn.title = '删除消息';
        deleteBtn.onclick = () => deleteChatMessage(msg.id);
        messageWrapper.appendChild(deleteBtn);

        const messageDiv = document.createElement('div');
        messageDiv.className = `chat-message ${msg.role}`;
        messageDiv.innerHTML = `
            <div>${renderMessageContent(msg.content)}</div>
            <div class="chat-timestamp">${msg.timestamp}</div>
        `;
        messageWrapper.appendChild(messageDiv);
        chatMessages.appendChild(messageWrapper);
    });

    // 滚动到底部
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

/**
 * 处理聊天输入框回车
 */
function handleChatKeyPress(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendChatMessage();
    }
}

/**
 * 获取当前选择的 AI 模型
 */
function getCurrentAIModel() {
    const modelSelect = document.getElementById('aiModelSelect');
    return modelSelect.value;
}

/**
 * 切换 AI 模型
 */
function changeAIModel() {
    // 可以在这里添加模型切换的提示
    const model = getCurrentAIModel();
    console.log('切换到模型:', model);
}

/**
 * 删除单条聊天记录
 */
function deleteChatMessage(messageId) {
    if (!messageId) return;

    if (confirm('确定要删除这条消息吗？')) {
        // Remove from chat history
        chatHistory = chatHistory.filter(msg => msg.id !== messageId);

        // Save to localStorage
        saveChatHistory();

        // Re-render messages
        renderChatMessages();
    }
}

/**
 * 清空聊天记录
 */
function clearChatHistory() {
    if (confirm('确定要清空所有聊天记录吗？此操作不可恢复。')) {
        chatHistory = [];
        localStorage.removeItem('chatHistory');
        renderChatMessages();
    }
}

/**
 * 生成消息ID
 */
function generateMessageId() {
    return Date.now().toString(36) + Math.random().toString(36).substr(2, 9);
}

/**
 * 发送聊天消息
 */
async function sendChatMessage() {
    const message = chatInput.value.trim();
    if (!message) return;

    // 获取当前选择的模型
    const currentModel = getCurrentAIModel();

    // 添加用户消息到UI
    const userMessage = {
        id: generateMessageId(),
        role: 'user',
        content: message,
        timestamp: new Date().toLocaleTimeString()
    };
    chatHistory.push(userMessage);
    renderChatMessages();

    // 清空输入框
    chatInput.value = '';

    // 显示正在输入状态
    const typingDiv = document.createElement('div');
    typingDiv.className = 'chat-message ai';
    typingDiv.id = 'typingIndicator';
    typingDiv.innerHTML = '<div>思考中...</div>';
    chatMessages.appendChild(typingDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    try {
        // 调用AI API
        const response = await fetch(`${API_BASE_URL}/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: message,
                history: chatHistory.slice(-10).map(msg => ({
                    role: msg.role,
                    content: msg.content
                })), // 只发送最近10条消息作为上下文
                model: currentModel // 发送选择的模型
            })
        });

        const data = await response.json();

        // 移除正在输入状态
        const typingIndicator = document.getElementById('typingIndicator');
        if (typingIndicator) {
            typingIndicator.remove();
        }

        if (response.ok) {
            // 添加AI回复到UI
            const aiMessage = {
                id: generateMessageId(),
                role: 'ai',
                content: data.reply,
                timestamp: new Date().toLocaleTimeString()
            };
            chatHistory.push(aiMessage);
            renderChatMessages();
            saveChatHistory();
        } else {
            // 显示错误
            const errorDiv = document.createElement('div');
            errorDiv.className = 'chat-message ai';
            errorDiv.innerHTML = `<div>错误：${data.error || '请求失败'}</div>`;
            chatMessages.appendChild(errorDiv);
            chatMessages.scrollTop = chatMessages.scrollHeight();
        }
    } catch (error) {
        // 移除正在输入状态
        const typingIndicator = document.getElementById('typingIndicator');
        if (typingIndicator) {
            typingIndicator.remove();
        }

        // 显示错误
        const errorDiv = document.createElement('div');
        errorDiv.className = 'chat-message ai';
        errorDiv.innerHTML = '<div>错误：网络连接失败，请检查网络</div>';
        chatMessages.appendChild(errorDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight();
        console.error('Error:', error);
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