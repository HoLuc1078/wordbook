/**
 * 主题切换逻辑 - 公共模块
 * 被 index.html 和 ai_chat.html 共用
 */
const THEME_KEY = 'theme-preference';

function getSystemTheme() {
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

function applyTheme(theme) {
    const root = document.documentElement;
    if (theme === 'system') {
        root.setAttribute('data-theme', getSystemTheme());
    } else {
        root.setAttribute('data-theme', theme);
    }
    updateThemeUI(theme);
    localStorage.setItem(THEME_KEY, theme);
}

function setTheme(theme) {
    applyTheme(theme);
    closeThemeDropdown();
}

function updateThemeUI(theme) {
    const themeIcon = document.getElementById('themeIcon');
    const themeLabel = document.getElementById('themeLabel');
    const options = document.querySelectorAll('.theme-option');

    const icons = { light: '☀️', dark: '🌙', system: '🌓' };
    const labels = { light: '浅色', dark: '深色', system: '跟随系统' };

    if (themeIcon) themeIcon.textContent = icons[theme] || '🌓';
    if (themeLabel) themeLabel.textContent = labels[theme] || '跟随系统';

    options.forEach(opt => {
        opt.classList.toggle('active', opt.dataset.value === theme);
    });
}

function toggleThemeDropdown() {
    const dropdown = document.getElementById('themeDropdown');
    if (dropdown) dropdown.classList.toggle('show');
}

function closeThemeDropdown() {
    const dropdown = document.getElementById('themeDropdown');
    if (dropdown) dropdown.classList.remove('show');
}

// Close dropdown when clicking outside
document.addEventListener('click', function(e) {
    if (!e.target.closest('.theme-toggle')) {
        closeThemeDropdown();
    }
});

// Listen for system theme changes
window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function() {
    const saved = localStorage.getItem(THEME_KEY) || 'system';
    if (saved === 'system') {
        applyTheme('system');
    }
});

// Initialize theme
(function initTheme() {
    const saved = localStorage.getItem(THEME_KEY) || 'system';
    applyTheme(saved);
})();
