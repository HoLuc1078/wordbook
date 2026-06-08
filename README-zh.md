# 英语单词本 Web 应用 🇨🇳

基于 Flask 的英语单词管理应用，帮助您构建个人英语词汇库，通过 AI 技术自动获取单词信息、进行多轮 AI 对话和句子分析。

## ✨ 功能特性

- **单词管理**: 添加、查看、编辑、删除和追踪英语单词
- **AI 集成**: 使用 DeepSeek AI API 自动获取单词详细信息
- **AI 对话**: 与 AI 进行多轮英语学习对话
- **句子分析**: 通过 AI 对英语句子进行语法和结构分析
- **智能追踪**: 计数器系统记录单词查询频率
- **用户系统**: 注册、登录、管理员面板与用户管理
- **导入 / 导出**: 支持 JSON 和 CSV 格式导出单词库；支持从 JSON 文件导入
- **批量操作**: 一次添加多个单词
- **单词备注**: 为每个单词添加自定义备注
- **响应式界面**: 现代化、适配移动端的网页界面，支持主题切换
- **RESTful API**: 完整的单词、聊天、句子分析和设置操作 API
- **数据库支持**: SQLite 数据库持久化存储

## 🛠️ 技术栈

- **后端**: Flask (Python)
- **前端**: HTML5, CSS3, JavaScript
- **数据库**: SQLite
- **AI API**: DeepSeek 聊天 API
- **部署**: 兼容任何 Python 托管环境

## 📋 环境要求

- Python 3.7+
- pip 包管理器
- DeepSeek API 密钥

## 🚀 快速开始

### 1. 克隆仓库
```bash
git clone <仓库地址>
cd wordbook
```

### 2. 安装依赖
```bash
pip install -r requirements.txt
```

### 3. 配置环境变量
```bash
cp .env.example .env
# 编辑 .env 文件，添加您的 DeepSeek API 密钥
```

### 4. 运行应用
```bash
python app.py
```

### 5. 访问应用
打开浏览器访问: `http://localhost:5000`

## 🔧 配置说明

编辑 `.env` 文件配置应用：

```
DEEPSEEK_API_KEY=您的API密钥
SECRET_KEY=您的密钥
```

## 🗂️ 项目结构

```
wordbook/
├── app.py                    # Flask 主应用文件
├── requirements.txt          # Python 依赖
├── .env.example             # 环境变量模板
├── .gitignore
├── LICENSE
├── README.md
├── README-zh.md
├── .deepseek/
│   └── instructions.md
├── static/
│   ├── css/
│   │   └── style.css        # 样式表
│   ├── js/
│   │   ├── app.js           # 主要前端逻辑（单词、用户、聊天、句子）
│   │   ├── offline.js       # 离线页面逻辑
│   │   └── theme.js         # 主题切换逻辑
│   └── favicon.ico
├── templates/
│   ├── index.html           # 主页模板
│   ├── ai_chat.html         # AI 对话页面
│   ├── sentence.html        # 句子分析页面
│   ├── setting.html         # 管理员设置页面
│   └── offline.html         # 离线回退页面
└── database/
    └── words.db             # SQLite 数据库（首次运行自动生成）
```

## 🎯 页面路由

| 路由 | 页面 | 说明 |
|------|------|------|
| `/` | index.html | 主页面 — 添加、查看、搜索、删除单词 |
| `/ai-chat` | ai_chat.html | 多轮 AI 英语学习对话 |
| `/sentence` | sentence.html | 上传或输入句子进行 AI 分析 |
| `/setting` | setting.html | 管理员专用：颜色库、用户管理 |
| `/offline` | offline.html | 离线回退页面，支持 PWA |

## 📖 API 文档

### 身份认证

#### `POST /api/register`
注册新用户账号。

**请求:**
```json
{
  "username": "用户名",
  "password": "密码"
}
```

#### `POST /api/login`
使用已有凭据登录。

**请求:**
```json
{
  "username": "用户名",
  "password": "密码"
}
```

#### `POST /api/logout`
退出当前会话。

#### `GET /api/current_user`
获取当前登录用户的信息。

#### `POST /api/change_password`
修改当前用户密码。

**请求:**
```json
{
  "old_password": "当前密码",
  "new_password": "新密码"
}
```

### 单词管理

#### `POST /api/words`
添加新单词（自动通过 AI 获取释义）或增加已有单词的查询计数。

**请求:**
```json
{
  "word": "example"
}
```

**响应:**
```json
{
  "message": "单词添加/更新成功",
  "word": {
    "id": 1,
    "word": "example",
    "counter": 1,
    "meaning": { ... },
    "note": "无",
    "created_at": "2024-01-01T00:00:00",
    "updated_at": "2024-01-01T00:00:00"
  }
}
```

#### `POST /api/words/batch`
批量添加多个单词。

**请求:**
```json
{
  "words": ["hello", "world", "example"]
}
```

#### `GET /api/words`
获取所有单词（按查询频率降序排列）。

#### `GET /api/words/<word>`
获取指定单词的详细信息。

#### `PUT /api/words/<word>`
更新单词的释义、词组、例句或备注。

#### `DELETE /api/words/<word>`
从数据库中删除单词。

#### `GET /api/words/export?format=json`
导出所有单词为 JSON 或 CSV 格式。查询参数：`format=json`（默认）或 `format=csv`。

#### `POST /api/words/import`
从 JSON 文件导入单词。

**请求:**
```json
{
  "words": [
    {
      "word": "example",
      "meaning": [{"pos": "n.", "translation": "例子"}],
      "phrases": [],
      "example": {"en": "...", "zh": "..."},
      "note": "无"
    }
  ]
}
```

### AI 对话

#### `POST /api/chat`
向 AI 发送消息并接收流式或非流式回复。

**请求:**
```json
{
  "message": "解释一下单词 'serendipity'",
  "conversation_id": 0
}
```

#### `GET /api/chat/conversations`
列出当前用户的所有对话线程。

#### `POST /api/chat/conversations`
创建新对话。

#### `GET /api/chat/conversations/<id>`
获取指定对话中的消息。

#### `PATCH /api/chat/conversations/<id>`
更新对话标题。

#### `DELETE /api/chat/conversations/<id>`
删除对话及其所有消息。

#### `GET /api/chat/history`
获取聊天历史消息。

#### `POST /api/chat/history`
保存聊天消息到历史记录。

#### `DELETE /api/chat/history/<id>`
删除指定聊天消息。

#### `DELETE /api/chat/history`
清空当前用户的所有聊天记录。

### 句子分析

#### `POST /api/sentence/analyze`
通过 AI 分析英语句子。

**请求:**
```json
{
  "text": "The quick brown fox jumps over the lazy dog."
}
```

#### `GET /api/sentence/history`
获取句子分析历史记录。

#### `DELETE /api/sentence/<id>`
删除句子分析记录。

### 设置

#### `GET /api/settings/colors`
获取全局颜色库。

#### `PUT /api/settings/colors`
更新颜色库（仅管理员）。

#### `POST /api/settings/colors/reset`
重置颜色库为默认值（仅管理员）。

### 管理员

#### `GET /api/admin/users`
列出所有用户（仅管理员）。

#### `PUT /api/admin/users/<id>/password`
重置用户密码（仅管理员）。

#### `DELETE /api/admin/users/<id>`
删除用户账号（仅管理员）。

### 健康检查

#### `GET /api/health`
健康检查接口。

## 🎯 使用说明

1. **注册 / 登录**: 创建账号或使用已有凭据登录
2. **添加单词**: 在输入框中输入英语单词，点击"查询/添加"——AI 将自动获取释义
3. **查看单词**: 所有添加的单词按查询频率降序显示
4. **追踪进度**: 计数器显示每个单词的查询次数
5. **AI 对话**: 前往 AI 对话页面进行多轮英语学习交流
6. **句子分析**: 在句子分析页面粘贴或输入句子，获取 AI 解析
7. **导入 / 导出**: 将单词库导出为 JSON 或 CSV；从 JSON 文件导入单词
8. **设置**: 管理员可管理颜色主题和用户账号

## 🤝 贡献

欢迎 Fork 本项目并提交 Pull Request，任何贡献都将被感激！

## 📄 许可证

本项目采用 MIT 许可证 - 详情参见 [LICENSE](LICENSE) 文件。

## 🙏 致谢

- DeepSeek AI 提供的单词信息 API
- Flask 框架提供的优秀 Web 开发体验
