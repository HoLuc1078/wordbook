"""
英语单词本 Web 应用 - Flask 后端
"""
import os
import sqlite3
import json
from contextlib import contextmanager
from datetime import datetime
from dotenv import load_dotenv
import requests
from flask import Flask, request, jsonify, render_template, session
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash

# 加载环境变量
load_dotenv()

# 初始化 Flask 应用
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'wordbook-secret-key-2024')  # Session 密钥
CORS(app)  # 启用跨域支持

# 配置
DATABASE = os.path.join(os.path.dirname(__file__), 'database', 'words.db')
LONGCAT_API_KEY = os.getenv('LONGCAT_API_KEY')
LONGCAT_API_URL = "https://api.longcat.chat/openai/v1/chat/completions"
LONGCAT_MODEL = "LongCat-Flash-Lite"

# ==================== 简单的内存频率限制器 ====================
_request_counts = {}

def check_rate_limit(key, max_requests=30, window_seconds=60):
    """
    检查请求频率限制
    key: 限制标识（如 IP 地址）
    max_requests: 时间窗口内允许的最大请求数
    window_seconds: 时间窗口（秒）
    返回: True 表示通过，False 表示超限
    """
    now = datetime.now().timestamp()
    if key not in _request_counts:
        _request_counts[key] = []

    # 清理过期记录
    _request_counts[key] = [t for t in _request_counts[key] if now - t < window_seconds]

    if len(_request_counts[key]) >= max_requests:
        return False

    _request_counts[key].append(now)
    return True

def rate_limit(max_requests=30, window_seconds=60):
    """频率限制装饰器"""
    def decorator(f):
        def wrapper(*args, **kwargs):
            key = request.remote_addr or 'unknown'
            route_key = f"{key}:{request.endpoint}"
            if not check_rate_limit(route_key, max_requests, window_seconds):
                return jsonify({'error': '请求过于频繁，请稍后再试'}), 429
            return f(*args, **kwargs)
        wrapper.__name__ = f.__name__
        return wrapper
    return decorator

def init_db():
    """初始化数据库，创建 users 和 words 表"""
    os.makedirs(os.path.dirname(DATABASE), exist_ok=True)
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # 创建用户表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 创建单词表（添加 user_id 外键）
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS words (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word TEXT NOT NULL,
            user_id INTEGER,
            counter INTEGER DEFAULT 1,
            meaning TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            UNIQUE(user_id, word)
        )
    ''')

    # 创建索引以优化查询性能
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_words_user_id ON words(user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_words_counter ON words(counter DESC)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_words_user_word ON words(user_id, word)')

    conn.commit()
    conn.close()

def get_db_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # 使返回结果可按字典访问
    return conn

@contextmanager
def get_db():
    """数据库连接上下文管理器，确保异常时也能关闭连接"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def fetch_word_info_from_longcat(word):
    """
    调用 LongCat API 获取单词信息
    返回: dict - 包含 meaning, phrases, example
    """
    if not LONGCAT_API_KEY:
        raise ValueError("LONGCAT_API_KEY not found in environment variables")

    headers = {
        "Authorization": f"Bearer {LONGCAT_API_KEY}",
        "Content-Type": "application/json"
    }

    prompt = f"""请为英语单词 "{word}" 提供以下信息，并用严格的 JSON 格式返回（词组可以不止一个，不要包含任何其他文字）：
{{
  "meaning": [{{"pos": "词性简写", "translation": "中文释义"}}, {{"pos": "词性简写2", "translation": "中文释义2"}}],
  "phrases": [{{"phrase": "词组1", "meaning": "中文含义1"}}, {{"phrase": "词组2", "meaning": "中文含义2"}}],
  "example": {{"en": "英文例句", "zh": "中文翻译"}}
}}

词性简写可以是任意标准格式，如：c., uc., adj., adv., prep., conj., pron., int., art., num., vt., vi., pl., sing. 等注意标记名词是否可数（c. uc.）以及动词是否及物（vi. vt.）。确保返回的JSON格式严格正确，不要包含任何其他文字。
"""

    payload = {
        "model": LONGCAT_MODEL,
        "messages": [
            {"role": "system", "content": "你是一个英语词典助手，请严格按照 JSON 格式输出，不要有任何额外文字。"},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3,
        "max_tokens": 1024
    }

    try:
        response = requests.post(
            LONGCAT_API_URL,
            headers=headers,
            json=payload,
            timeout=30
        )
        response.raise_for_status()

        result = response.json()
        content = result['choices'][0]['message']['content']

        # 清理可能存在的 markdown 代码块标记
        content = content.strip()
        if content.startswith('```json'):
            content = content[7:]
        if content.endswith('```'):
            content = content[:-3]

        word_info = json.loads(content)

        # 验证返回的数据结构
        required_fields = ['meaning', 'phrases', 'example']
        for field in required_fields:
            if field not in word_info:
                raise ValueError(f"Missing required field: {field}")

        return word_info

    except requests.RequestException as e:
        raise Exception(f"API 请求失败: {str(e)}")
    except json.JSONDecodeError as e:
        raise Exception(f"API 返回的 JSON 格式无效: {str(e)}")
    except Exception as e:
        raise Exception(f"获取单词信息失败: {str(e)}")

@app.route('/')
def index():
    """渲染主页"""
    return render_template('index.html')

@app.route('/api/words', methods=['POST'])
@rate_limit(max_requests=20, window_seconds=60)
def add_or_update_word():
    """
    添加新单词或更新现有单词的查询次数
    POST /api/words
    Body: {"word": "example"}
    """
    try:
        data = request.get_json()
        if not data or 'word' not in data:
            return jsonify({'error': '缺少 word 参数'}), 400

        word = data['word'].strip().lower()  # 转换为小写
        if not word:
            return jsonify({'error': '单词不能为空'}), 400

        # 获取用户ID（如果未登录，使用 None）
        user_id = session.get('user_id')

        with get_db() as conn:
            cursor = conn.cursor()

            # 检查该用户的单词是否已存在（如果 user_id 为 None，则查询所有未登录用户的单词）
            if user_id:
                cursor.execute("SELECT * FROM words WHERE word = ? AND user_id = ?", (word, user_id))
            else:
                cursor.execute("SELECT * FROM words WHERE word = ? AND user_id IS NULL", (word,))
            existing_word = cursor.fetchone()

            if existing_word:
                # 单词已存在，更新 counter
                cursor.execute(
                    "UPDATE words SET counter = counter + 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (existing_word['id'],)
                )
                conn.commit()

                # 获取更新后的单词信息
                cursor.execute("SELECT * FROM words WHERE id = ?", (existing_word['id'],))
                updated_word = cursor.fetchone()

                result = {
                    'id': updated_word['id'],
                    'word': updated_word['word'],
                    'counter': updated_word['counter'],
                    'meaning': json.loads(updated_word['meaning']) if updated_word['meaning'] else None,
                    'created_at': updated_word['created_at'],
                    'updated_at': updated_word['updated_at']
                }

                return jsonify({
                    'message': '单词已存在，计数器已更新',
                    'word': result
                }), 200
            else:
                # 单词不存在，调用 AI API 获取信息
                try:
                    word_info = fetch_word_info_from_longcat(word)
                    meaning_json = json.dumps(word_info, ensure_ascii=False)

                    # 插入新单词（如果未登录，user_id 为 None）
                    cursor.execute(
                        "INSERT INTO words (word, user_id, meaning) VALUES (?, ?, ?)",
                        (word, user_id, meaning_json)
                    )
                    conn.commit()

                    # 获取新插入的单词信息
                    word_id = cursor.lastrowid
                    cursor.execute("SELECT * FROM words WHERE id = ?", (word_id,))
                    new_word = cursor.fetchone()

                    result = {
                        'id': new_word['id'],
                        'word': new_word['word'],
                        'counter': new_word['counter'],
                        'meaning': word_info,
                        'created_at': new_word['created_at'],
                        'updated_at': new_word['updated_at']
                    }

                    return jsonify({
                        'message': '新单词已添加',
                        'word': result
                    }), 201

                except Exception as e:
                    return jsonify({'error': f'调用 AI API 失败: {str(e)}'}), 500

    except Exception as e:
        return jsonify({'error': f'服务器错误: {str(e)}'}), 500

@app.route('/api/words', methods=['GET'])
def get_all_words():
    """获取单词列表，按 counter 降序排序"""
    try:
        # 获取用户ID（如果未登录，使用 None）
        user_id = session.get('user_id')

        with get_db() as conn:
            cursor = conn.cursor()

            if user_id:
                # 已登录用户，只获取该用户的单词
                cursor.execute("""
                    SELECT id, word, counter, meaning
                    FROM words
                    WHERE user_id = ?
                    ORDER BY counter DESC, word ASC
                """, (user_id,))
            else:
                # 未登录用户，获取所有未登录用户的单词
                cursor.execute("""
                    SELECT id, word, counter, meaning
                    FROM words
                    WHERE user_id IS NULL
                    ORDER BY counter DESC, word ASC
                """)

            words = []
            for row in cursor.fetchall():
                words.append({
                    'id': row['id'],
                    'word': row['word'],
                    'counter': row['counter'],
                    'meaning': json.loads(row['meaning']) if row['meaning'] else None
                })

            return jsonify(words), 200

    except Exception as e:
        return jsonify({'error': f'服务器错误: {str(e)}'}), 500

@app.route('/api/words/<word>', methods=['GET'])
def get_word_detail(word):
    """获取单词详细信息"""
    try:
        word = word.lower()
        # 获取用户ID（如果未登录，使用 None）
        user_id = session.get('user_id')

        with get_db() as conn:
            cursor = conn.cursor()

            if user_id:
                cursor.execute("SELECT * FROM words WHERE word = ? AND user_id = ?", (word, user_id))
            else:
                cursor.execute("SELECT * FROM words WHERE word = ? AND user_id IS NULL", (word,))
            word_data = cursor.fetchone()

            if not word_data:
                return jsonify({'error': '单词不存在'}), 404

            result = {
                'id': word_data['id'],
                'word': word_data['word'],
                'counter': word_data['counter'],
                'meaning': json.loads(word_data['meaning']) if word_data['meaning'] else None,
                'created_at': word_data['created_at'],
                'updated_at': word_data['updated_at']
            }

            return jsonify(result), 200

    except Exception as e:
        return jsonify({'error': f'服务器错误: {str(e)}'}), 500

@app.route('/api/words/<word>', methods=['DELETE'])
def delete_word(word):
    """删除单词"""
    try:
        word = word.lower()
        # 获取用户ID（如果未登录，使用 None）
        user_id = session.get('user_id')

        with get_db() as conn:
            cursor = conn.cursor()

            # 检查单词是否存在且属于当前用户
            if user_id:
                cursor.execute("SELECT * FROM words WHERE word = ? AND user_id = ?", (word, user_id))
            else:
                cursor.execute("SELECT * FROM words WHERE word = ? AND user_id IS NULL", (word,))
            word_data = cursor.fetchone()

            if not word_data:
                return jsonify({'error': '单词不存在'}), 404

            # 删除单词
            cursor.execute("DELETE FROM words WHERE id = ?", (word_data['id'],))
            conn.commit()

            return jsonify({'message': '单词删除成功'}), 200

    except Exception as e:
        return jsonify({'error': f'服务器错误: {str(e)}'}), 500

@app.route('/api/words/<word>', methods=['PUT'])
def update_word(word):
    """更新当前用户的单词信息"""
    try:
        word = word.lower()
        # 检查是否已登录
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': '请先登录才能更新单词'}), 401

        data = request.get_json()
        if not data:
            return jsonify({'error': '缺少更新数据'}), 400

        with get_db() as conn:
            cursor = conn.cursor()

            try:
                # 检查单词是否存在且属于当前用户
                cursor.execute("SELECT * FROM words WHERE word = ? AND user_id = ?", (word, user_id))
                word_data = cursor.fetchone()

                if not word_data:
                    return jsonify({'error': '单词不存在'}), 404

                # 构建更新语句
                updates = []
                params = []

                # 更新单词本身
                if 'word' in data and data['word'].lower() != word:
                    new_word = data['word'].lower()
                    # 检查新单词在当前用户下是否已存在
                    cursor.execute("SELECT * FROM words WHERE word = ? AND user_id = ?", (new_word, user_id))
                    if cursor.fetchone():
                        return jsonify({'error': '新单词已存在'}), 400
                    updates.append("word = ?")
                    params.append(new_word)

                # 更新计数器
                if 'counter' in data:
                    updates.append("counter = ?")
                    params.append(data['counter'])

                # 更新含义（JSON格式）
                if 'meaning' in data:
                    # 支持新的数组格式和旧的对象格式
                    meaning_data = data['meaning']
                    # 如果 meaning 包含 'meaning' 字段，说明是嵌套格式，需要提取内部的 meaning 数组
                    if isinstance(meaning_data, dict) and 'meaning' in meaning_data:
                        meaning_to_save = meaning_data['meaning']
                    else:
                        meaning_to_save = meaning_data
                    meaning_json = json.dumps(meaning_to_save, ensure_ascii=False)
                    updates.append("meaning = ?")
                    params.append(meaning_json)

                # 如果有更新字段
                if updates:
                    updates.append("updated_at = CURRENT_TIMESTAMP")
                    update_sql = f"UPDATE words SET {', '.join(updates)} WHERE id = ?"
                    params.append(word_data['id'])
                    cursor.execute(update_sql, params)
                    conn.commit()

                # 获取更新后的单词信息
                cursor.execute("SELECT * FROM words WHERE id = ?", (word_data['id'],))
                updated_word = cursor.fetchone()

                result = {
                    'id': updated_word['id'],
                    'word': updated_word['word'],
                    'counter': updated_word['counter'],
                    'meaning': json.loads(updated_word['meaning']) if updated_word['meaning'] else None,
                    'created_at': updated_word['created_at'],
                    'updated_at': updated_word['updated_at']
                }

                return jsonify({
                    'message': '单词更新成功',
                    'word': result
                }), 200

            except Exception as e:
                conn.rollback()
                raise e

    except Exception as e:
        return jsonify({'error': f'服务器错误: {str(e)}'}), 500

@app.route('/api/register', methods=['POST'])
@rate_limit(max_requests=5, window_seconds=60)
def register():
    """用户注册接口"""
    try:
        data = request.get_json()
        if not data or 'username' not in data:
            return jsonify({'error': '缺少 username 参数'}), 400

        username = data['username'].strip()
        password = data.get('password', '').strip()

        if not username:
            return jsonify({'error': '用户名不能为空'}), 400

        if len(username) < 3:
            return jsonify({'error': '用户名至少需要3个字符'}), 400

        with get_db() as conn:
            cursor = conn.cursor()

            # 检查用户名是否已存在
            cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
            if cursor.fetchone():
                return jsonify({'error': '用户名已存在'}), 400

            # 创建用户
            password_hash = generate_password_hash(password) if password else None
            cursor.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                (username, password_hash)
            )
            conn.commit()

            # 获取新创建的用户ID
            user_id = cursor.lastrowid

            # 设置session
            session['user_id'] = user_id
            session['username'] = username

            return jsonify({
                'message': '注册成功',
                'user': {
                    'id': user_id,
                    'username': username
                }
            }), 201

    except Exception as e:
        return jsonify({'error': f'服务器错误: {str(e)}'}), 500

@app.route('/api/login', methods=['POST'])
@rate_limit(max_requests=10, window_seconds=60)
def login():
    """用户登录接口"""
    try:
        data = request.get_json()
        if not data or 'username' not in data:
            return jsonify({'error': '缺少 username 参数'}), 400

        username = data['username'].strip()
        password = data.get('password', '').strip()

        if not username:
            return jsonify({'error': '用户名不能为空'}), 400

        with get_db() as conn:
            cursor = conn.cursor()

            # 查找用户
            cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
            user = cursor.fetchone()

            if not user:
                return jsonify({'error': '用户不存在'}), 404

            # 验证密码（如果用户有设置密码）
            if user['password_hash']:
                if not password:
                    return jsonify({'error': '请输入密码'}), 400
                if not check_password_hash(user['password_hash'], password):
                    return jsonify({'error': '密码错误'}), 401

            # 设置session
            session['user_id'] = user['id']
            session['username'] = user['username']

            return jsonify({
                'message': '登录成功',
                'user': {
                    'id': user['id'],
                    'username': user['username']
                }
            }), 200

    except Exception as e:
        return jsonify({'error': f'服务器错误: {str(e)}'}), 500

@app.route('/api/logout', methods=['POST'])
def logout():
    """用户登出接口"""
    session.clear()
    return jsonify({'message': '登出成功'}), 200

@app.route('/api/current_user', methods=['GET'])
def get_current_user():
    """获取当前登录用户信息"""
    if 'user_id' in session:
        return jsonify({
            'user': {
                'id': session['user_id'],
                'username': session['username']
            }
        }), 200
    else:
        return jsonify({'user': None}), 200

@app.route('/api/chat', methods=['POST'])
@rate_limit(max_requests=20, window_seconds=60)
def chat_with_ai():
    """与 LongCat AI 对话接口"""
    try:
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({'error': '缺少 message 参数'}), 400

        user_message = data['message']
        history = data.get('history', [])
        model = data.get('model', LONGCAT_MODEL)  # 获取选择的模型

        # 构建对话历史
        messages = [
            {"role": "system", "content": "你是一只可爱的猫娘，内嵌在了英语词典中，帮助用户学习和查询英语单词，请你在适当的位置增加喵，要求足够可爱，但是不要使用🐱。"}
        ]

        # 添加历史消息
        for msg in history:
            if msg.get('role') in ['user', 'assistant']:
                messages.append({
                    "role": msg['role'],
                    "content": msg['content']
                })

        # 添加当前消息
        messages.append({"role": "user", "content": user_message})

        # 调用 LongCat API
        headers = {
            "Authorization": f"Bearer {LONGCAT_API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": model,  # 使用选择的模型
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 32767
        }

        response = requests.post(
            LONGCAT_API_URL,
            headers=headers,
            json=payload,
            timeout=30
        )
        response.raise_for_status()

        result = response.json()
        ai_reply = result['choices'][0]['message']['content']

        return jsonify({'reply': ai_reply}), 200

    except Exception as e:
        return jsonify({'error': f'聊天功能暂时不可用: {str(e)}'}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'database': os.path.exists(DATABASE),
        'longcat_api_key': bool(LONGCAT_API_KEY)
    }), 200

@app.route('/ai-chat')
def ai_chat_page():
    """渲染AI聊天页面"""
    return render_template('ai_chat.html')

if __name__ == '__main__':
    # 初始化数据库
    init_db()
    print(f"数据库已初始化: {DATABASE}")
    print(f"LongCat API Key 已配置: {bool(LONGCAT_API_KEY)}")

    # 启动 Flask 应用
    app.run(host='0.0.0.0', port=5000, debug=False)
