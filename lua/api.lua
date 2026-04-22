-- API处理主文件
-- 处理所有 /api/* 路由

-- 加载模块
local cjson = require "cjson"
local resty_http = require "resty.http"
local init = require "init"

-- 设置JSON选项
cjson.encode_empty_table_as_object(false)

-- 路由分发
local function route_request()
    local method = ngx.req.get_method()
    local uri = ngx.var.uri

    -- 健康检查
    if uri == "/api/health" and method == "GET" then
        return handle_health_check()

    -- 单词列表操作
    elseif uri == "/api/words" then
        if method == "GET" then
            return handle_get_words()
        elseif method == "POST" then
            return handle_add_or_update_word()
        end

    -- 单个单词操作
    elseif uri:match("^/api/words/.+$") then
        local word = uri:match("/api/words/(.+)$")
        if method == "GET" then
            return handle_get_word_detail(word)
        elseif method == "DELETE" then
            return handle_delete_word(word)
        end
    end

    -- 未知路由
    return send_error(404, "接口不存在")
end

-- 执行SQL查询
local function execute_query(sql, ...)
    local db = sqlite3.open(DATABASE_PATH)
    if not db then
        error("无法打开数据库")
    end

    local stmt = db:prepare(sql)
    if not stmt then
        db:close()
        error("SQL准备失败: " .. db:errmsg())
    end

    if ... then
        stmt:bind_values(...)
    end

    local results = {}
    for row in stmt:nrows() do
        table.insert(results, row)
    end

    stmt:finalize()
    db:close()
    return results
end

-- 执行修改操作
local function execute_update(sql, ...)
    local db = sqlite3.open(DATABASE_PATH)
    if not db then
        error("无法打开数据库")
    end

    local stmt = db:prepare(sql)
    if not stmt then
        db:close()
        error("SQL准备失败: " .. db:errmsg())
    end

    if ... then
        stmt:bind_values(...)
    end

    stmt:step()
    stmt:finalize()

    local last_id = db:last_insert_rowid()
    db:close()
    return last_id
end

-- 健康检查
function handle_health_check()
    local db_exists = io.open(DATABASE_PATH, "r") ~= nil
    local api_key_set = LONGCAT_API_KEY ~= ""

    return send_success({
        status = "healthy",
        timestamp = os.date("!%Y-%m-%dT%H:%M:%SZ"),
        database = db_exists,
        longcat_api_key = api_key_set
    })
end

-- 获取所有单词
function handle_get_words()
    local results = execute_query([[
        SELECT id, word, counter, meaning
        FROM words
        ORDER BY counter DESC, word ASC
    ]])

    local words = {}
    for _, row in ipairs(results) do
        table.insert(words, {
            id = row.id,
            word = row.word,
            counter = row.counter,
            meaning = row.meaning and cjson.decode(row.meaning) or nil
        })
    end

    return send_success(words)
end

-- 添加或更新单词
function handle_add_or_update_word()
    local body = get_request_body()
    if not body or not body.word then
        return send_error(400, "缺少 word 参数")
    end

    local word = string.trim(body.word:lower())
    if word == "" then
        return send_error(400, "单词不能为空")
    end

    -- 检查单词是否存在
    local results = execute_query("SELECT * FROM words WHERE word = ?", word)
    local existing_word = results[1]

    if existing_word then
        -- 单词已存在，更新计数器
        execute_update("UPDATE words SET counter = counter + 1, updated_at = CURRENT_TIMESTAMP WHERE word = ?", word)
        results = execute_query("SELECT * FROM words WHERE word = ?", word)
        local updated_word = results[1]

        local result = {
            id = updated_word.id,
            word = updated_word.word,
            counter = updated_word.counter,
            meaning = updated_word.meaning and cjson.decode(updated_word.meaning) or nil,
            created_at = updated_word.created_at,
            updated_at = updated_word.updated_at
        }

        return send_success({
            message = "单词已存在，计数器已更新",
            word = result
        })
    else
        -- 单词不存在，调用AI API
        local success, word_info = pcall(fetch_word_info_from_longcat, word)
        if not success then
            return send_error(500, "调用 AI API 失败: " .. word_info)
        end

        local meaning_json = cjson.encode(word_info)
        local word_id = execute_update("INSERT INTO words (word, meaning) VALUES (?, ?)", word, meaning_json)

        results = execute_query("SELECT * FROM words WHERE id = ?", word_id)
        local new_word = results[1]

        local result = {
            id = new_word.id,
            word = new_word.word,
            counter = new_word.counter,
            meaning = word_info,
            created_at = new_word.created_at,
            updated_at = new_word.updated_at
        }

        return send_success({
            message = "新单词已添加",
            word = result
        })
    end
end

-- 获取单词详情
function handle_get_word_detail(word)
    local results = execute_query("SELECT * FROM words WHERE word = ?", word:lower())
    local word_data = results[1]

    if not word_data then
        return send_error(404, "单词不存在")
    end

    local result = {
        id = word_data.id,
        word = word_data.word,
        counter = word_data.counter,
        meaning = word_data.meaning and cjson.decode(word_data.meaning) or nil,
        created_at = word_data.created_at,
        updated_at = word_data.updated_at
    }

    return send_success(result)
end

-- 删除单词
function handle_delete_word(word)
    local results = execute_query("SELECT * FROM words WHERE word = ?", word:lower())
    local word_data = results[1]

    if not word_data then
        return send_error(404, "单词不存在")
    end

    execute_update("DELETE FROM words WHERE word = ?", word:lower())

    return send_success({message = "单词删除成功"})
end

-- 调用LongCat API获取单词信息
function fetch_word_info_from_longcat(word)
    if LONGCAT_API_KEY == "" then
        error("LONGCAT_API_KEY not found in environment variables")
    end

    local prompt = string.format([[
        请为英语单词 "%s" 提供以下信息，并用严格的 JSON 格式返回（不要包含任何其他文字）：
        {
          "meaning": "中文释义",
          "phrases": [{"phrase": "词组1", "meaning": "中文含义1"}, {"phrase": "词组2", "meaning": "中文含义2"}],
          "example": {"en": "英文例句", "zh": "中文翻译"}
        }
    ]], word)

    local payload = {
        model = LONGCAT_MODEL,
        messages = {
            {role = "system", content = "你是一个英语词典助手，请严格按照 JSON 格式输出，不要有任何额外文字。"},
            {role = "user", content = prompt}
        },
        temperature = 0.3,
        max_tokens = 800
    }

    local httpc = resty_http:new()
    httpc:set_timeout(30000)

    local res, err = httpc:request_uri(LONGCAT_API_URL, {
        method = "POST",
        headers = {
            ["Authorization"] = "Bearer " .. LONGCAT_API_KEY,
            ["Content-Type"] = "application/json"
        },
        body = cjson.encode(payload)
    })

    if not res then
        error("API请求失败: " .. err)
    end

    if res.status ~= 200 then
        error("API返回错误: HTTP " .. res.status)
    end

    local result = cjson.decode(res.body)
    local content = result.choices[1].message.content

    -- 清理可能的markdown代码块
    content = content:gsub("^```json", "")
    content = content:gsub("```$", "")
    content = string.trim(content)

    local word_info = cjson.decode(content)

    -- 验证必要字段
    if not word_info.meaning or not word_info.phrases or not word_info.example then
        error("API返回的数据结构不完整")
    end

    return word_info
end

-- 主入口
local ok, err = pcall(route_request)
if not ok then
    log_error("请求处理失败: " .. err)
    return send_error(500, "服务器错误")
end