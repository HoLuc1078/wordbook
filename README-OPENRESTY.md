# OpenResty 英语单词本应用

这是英语单词本应用的OpenResty版本，使用Nginx + Lua实现。

## 安装要求

- OpenResty (>= 1.19.0.0)
- SQLite3 开发库

## 安装步骤

### 1. 安装OpenResty

从[OpenResty官网](https://openresty.org/)下载并安装适合你操作系统的版本。

### 2. 安装依赖

```bash
# 运行安装脚本（Linux/Mac）
bash install_dependencies.sh

# 或者手动安装：
# Ubuntu/Debian: sudo apt-get install sqlite3 libsqlite3-dev
# CentOS/RHEL: sudo yum install sqlite sqlite-devel
# macOS: brew install sqlite
# Windows: 使用Chocolatey或WSL
```

### 3. 配置环境变量

设置LongCat API密钥：

```bash
export LONGCAT_API_KEY="your_api_key_here"
```

或者在Windows中：

```cmd
set LONGCAT_API_KEY=your_api_key_here
```

### 4. 启动服务

使用项目自带的nginx.conf启动OpenResty：

```bash
# 使用OpenResty的nginx
/path/to/openresty/nginx -p /Code/wordbook -c nginx.conf

# 或者如果已经将OpenResty添加到PATH：
nginx -p /Code/wordbook -c nginx.conf
```

### 5. 访问应用

打开浏览器访问 http://localhost:8080

## API接口

- `GET /` - 主页
- `GET /api/words` - 获取所有单词列表
- `POST /api/words` - 添加或更新单词
- `GET /api/words/:word` - 获取单词详情
- `DELETE /api/words/:word` - 删除单词
- `GET /api/health` - 健康检查

## 项目结构

```
wordbook/
├── nginx.conf          # OpenResty配置文件
├── lua/
│   ├── init.lua        # 初始化脚本
│   ├── api.lua         # API处理脚本
│   └── index.lua       # 主页处理脚本
├── static/             # 静态资源
│   ├── css/style.css
│   └── js/app.js
├── templates/          # 模板文件
│   └── index.html
├── database/           # 数据库目录
│   └── words.db
└── README.md
```

## 注意事项

1. 确保LONGCAT_API_KEY环境变量已设置
2. 数据库会自动初始化，首次运行时会创建words表
3. 静态文件服务配置在/static/路由下
4. 日志文件会写入logs/目录

## 开发调试

查看错误日志：

```bash
tail -f logs/error.log
```

查看访问日志：

```bash
tail -f logs/access.log
```

## 与Flask版本对比

OpenResty版本的改进：
- 高性能，基于Nginx的异步架构
- 内存占用更小
- 支持高并发
- 使用Lua脚本，逻辑清晰
- 内置JSON和HTTP客户端库