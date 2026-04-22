-- OpenResty 初始化脚本
-- 初始化数据库连接和其他全局配置

-- 使用OpenResty自带的JSON模块
local cjson = require "cjson"

-- 数据库配置
DATABASE_PATH = "/Code/wordbook/database/words.db"

-- 工具函数
function string.trim(s)
    return s:match'^%s*(.*%S)' or ''
end

function string.startswith(s, prefix)
    return string.sub(s, 1, string.len(prefix)) == prefix
end

function string.endswith(s, suffix)
    return suffix == '' or string.sub(s, -string.len(suffix)) == suffix
end

-- API配置
LONGCAT_API_KEY = os.getenv("LONGCAT_API_KEY") or ""
LONGCAT_API_URL = "https://api.longcat.chat/openai/v1/chat/completions"
LONGCAT_MODEL = "LongCat-Flash-Lite"

-- 响应处理函数
function send_json_response(status_code, data)
    ngx.status = status_code
    ngx.header["Content-Type"] = "application/json"
    ngx.say(cjson.encode(data))
    return ngx.exit(status_code)
end

function send_error(status_code, error_message)
    return send_json_response(status_code, {error = error_message})
end

function send_success(data)
    return send_json_response(200, data)
end

-- 日志函数
function log_info(msg)
    ngx.log(ngx.INFO, msg)
end

function log_error(msg)
    ngx.log(ngx.ERR, msg)
end

-- 获取请求体
function get_request_body()
    local data = ngx.req.get_body_data()
    if not data then
        return nil
    end
    return cjson.decode(data)
end

-- 初始化数据库（使用shell命令）
local function init_db()
    os.execute("mkdir -p /Code/wordbook/database")
    local sql = [[
        CREATE TABLE IF NOT EXISTS words (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word TEXT UNIQUE NOT NULL,
            counter INTEGER DEFAULT 1,
            meaning TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ]]
    local escaped_sql = sql:gsub("'", "'\\''")
    os.execute(string.format("sqlite3 '%s' '%s'", DATABASE_PATH, escaped_sql))

    log_info("数据库已初始化完成")
end

init_db()

-- 加载SQLite模块（如果可用）
local sqlite3_available = pcall(function()
    sqlite3 = require "lsqlite3"
end)

if not sqlite3_available then
    log_info("警告：lsqlite3模块不可用，将使用os.execute作为备选方案")
end