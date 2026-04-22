-- OpenResty API测试脚本
-- 用于测试API接口是否正常工作

-- 加载模块
local http = require "resty.http"
local cjson = require "cjson"

-- 配置
local API_BASE = "http://localhost:8080/api"
local TEST_WORD = "test"

-- 测试函数
local function test_health_check()
    print("测试健康检查接口...")
    local httpc = http:new()
    local res, err = httpc:request_uri(API_BASE .. "/health", {
        method = "GET"
    })

    if not res then
        print("失败: " .. err)
        return false
    end

    if res.status == 200 then
        local data = cjson.decode(res.body)
        print("成功: 状态=" .. data.status .. ", 数据库=" .. tostring(data.database))
        return true
    else
        print("失败: HTTP " .. res.status)
        return false
    end
end

local function test_add_word(word)
    print("测试添加单词: " .. word)
    local httpc = http:new()
    local res, err = httpc:request_uri(API_BASE .. "/words", {
        method = "POST",
        headers = {
            ["Content-Type"] = "application/json"
        },
        body = cjson.encode({word = word})
    })

    if not res then
        print("失败: " .. err)
        return false
    end

    if res.status == 201 or res.status == 200 then
        print("成功: 状态=" .. res.status)
        return true
    else
        print("失败: HTTP " .. res.status .. ", 响应=" .. res.body)
        return false
    end
end

local function test_get_words()
    print("测试获取单词列表...")
    local httpc = http:new()
    local res, err = httpc:request_uri(API_BASE .. "/words", {
        method = "GET"
    })

    if not res then
        print("失败: " .. err)
        return false
    end

    if res.status == 200 then
        local data = cjson.decode(res.body)
        print("成功: 获取到 " .. #data .. " 个单词")
        return true
    else
        print("失败: HTTP " .. res.status)
        return false
    end
end

local function test_get_word_detail(word)
    print("测试获取单词详情: " .. word)
    local httpc = http:new()
    local res, err = httpc:request_uri(API_BASE .. "/words/" .. word, {
        method = "GET"
    })

    if not res then
        print("失败: " .. err)
        return false
    end

    if res.status == 200 then
        print("成功: 获取单词详情")
        return true
    else
        print("失败: HTTP " .. res.status)
        return false
    end
end

local function test_delete_word(word)
    print("测试删除单词: " .. word)
    local httpc = http:new()
    local res, err = httpc:request_uri(API_BASE .. "/words/" .. word, {
        method = "DELETE"
    })

    if not res then
        print("失败: " .. err)
        return false
    end

    if res.status == 200 then
        print("成功: 单词已删除")
        return true
    else
        print("失败: HTTP " .. res.status)
        return false
    end
end

-- 运行所有测试
local function run_all_tests()
    print("=" .. "=" .. "=" .. "=" .. "=" .. "=" .. "=" .. "=" .. "=" .. "=" .. "=" .. "=" .. "=")
    print("开始API测试")
    print("=" .. "=" .. "=" .. "=" .. "=" .. "=" .. "=" .. "=" .. "=" .. "=" .. "=" .. "=" .. "=")

    local results = {}

    table.insert(results, test_health_check())
    table.insert(results, test_add_word(TEST_WORD))
    table.insert(results, test_get_words())
    table.insert(results, test_get_word_detail(TEST_WORD))
    table.insert(results, test_delete_word(TEST_WORD))

    print("=" .. "=" .. "=" .. "=" .. "=" .. "=" .. "=" .. "=" .. "=" .. "=" .. "=" .. "=" .. "=")
    print("测试完成")

    local passed = 0
    for _, result in ipairs(results) do
        if result then passed = passed + 1 end
    end

    print(string.format("结果: %d/%d 个测试通过", passed, #results))
    return passed == #results
end

-- 运行测试
run_all_tests()