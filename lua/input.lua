-- 主页处理脚本

local function get_index_html()
    return [[
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>英语单词本</title>
    <link rel="stylesheet" href="/static/css/style.css">
</head>
<body>
    <div class="container">
        <header>
            <h1>📚 英语单词本</h1>
            <p>记录和复习你的英语单词</p>
        </header>

        <!-- 单词输入区域 -->
        <section class="input-section">
            <div class="input-group">
                <input type="text" id="wordInput" placeholder="输入英语单词..." autocomplete="off">
                <button id="queryBtn">查询/添加</button>
            </div>
            <div id="loadingIndicator" class="loading" style="display: none;">
                <span>查询中...</span>
            </div>
            <div id="errorMessage" class="error-message" style="display: none;"></div>
        </section>

        <!-- 单词列表展示区域 -->
        <section class="words-section">
            <h2>单词列表</h2>
            <div id="wordsList" class="words-list">
                <div class="empty-state">
                    <p>暂无单词记录</p>
                    <p>开始添加你的第一个单词吧！</p>
                </div>
            </div>
        </section>

        <!-- 单词详情弹窗 -->
        <div id="wordModal" class="modal" style="display: none;">
            <div class="modal-content">
                <span class="close-btn">&times;</span>
                <div id="modalBody">
                    <!-- 动态内容 -->
                </div>
            </div>
        </div>
    </div>

    <script src="/static/js/app.js"></script>
</body>
</html>
    ]]
end

-- 主入口
ngx.header["Content-Type"] = "text/html"
ngx.say(get_index_html())