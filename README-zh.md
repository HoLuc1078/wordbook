# 英语单词本 Web 应用 🇨🇳

基于 Flask 的英语单词管理应用，帮助您构建个人英语词汇库，通过 AI 技术自动获取单词信息。

## ✨ 功能特性

- **单词管理**: 添加、查看、删除和追踪英语单词
- **AI 集成**: 使用 LongCat AI API 自动获取单词详细信息
- **智能追踪**: 计数器系统记录单词查询频率
- **响应式界面**: 现代化、适配移动端的网页界面
- **RESTful API**: 完整的单词操作 API
- **数据库支持**: SQLite 数据库持久化存储

## 🛠️ 技术栈

- **后端**: Flask (Python)
- **前端**: HTML5, CSS3, JavaScript
- **数据库**: SQLite
- **AI API**: LongCat 聊天 API
- **部署**: 兼容任何 Python 托管环境

## 📋 环境要求

- Python 3.7+
- pip 包管理器
- LongCat API 密钥

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
cp ex.env .env
# 编辑 .env 文件，添加您的 LongCat API 密钥
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
LONGCAT_API_KEY=您的API密钥
```

## 📖 API 文档

### 接口列表

#### `POST /api/words`
添加新单词或更新现有单词计数器

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
    "created_at": "2024-01-01T00:00:00",
    "updated_at": "2024-01-01T00:00:00"
  }
}
```

#### `GET /api/words`
获取所有单词（按查询频率降序排列）

#### `GET /api/words/<word>`
获取指定单词的详细信息

#### `DELETE /api/words/<word>`
从数据库中删除单词

#### `GET /api/health`
健康检查接口

## 🗂️ 项目结构

```
wordbook/
├── app.py                 # Flask 主应用文件
├── requirements.txt       # Python 依赖
├── .env                  # 环境变量配置
├── .gitignore
├── LICENSE
├── README.md
├── README-zh.md
├── static/
│   ├── css/
│   │   └── style.css     # 样式表
│   └── js/
│       └── app.js        # 前端 JavaScript
├── templates/
│   └── index.html        # 主页面模板
└── database/
    └── words.db          # SQLite 数据库（首次运行自动生成）
```

## 🎯 使用说明

1. **添加单词**: 在输入框中输入英语单词，点击"查询/添加"
2. **查看单词**: 所有添加的单词按查询频率降序显示
3. **追踪进度**: 计数器显示每个单词的查询次数
4. **删除单词**: 删除不再需要的单词

## 🤝 贡献

欢迎 Fork 本项目并提交 Pull Request，任何贡献都将被感激！

## 📄 许可证

本项目采用 MIT 许可证 - 详情参见 [LICENSE](LICENSE) 文件。

## 🙏 致谢

- LongCat AI 提供的单词信息 API
- Flask 框架提供的优秀 Web 开发体验