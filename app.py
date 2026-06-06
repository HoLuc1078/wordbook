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
from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

# 加载环境变量
load_dotenv()

# 初始化 Flask 应用
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'wordbook-secret-key-2024')  # Session 密钥
CORS(app)  # 启用跨域支持

# 配置
DATABASE = os.path.join(os.path.dirname(__file__), 'database', 'words.db')
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_MODEL = "deepseek-v4-pro"

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

def login_required(f):
    """登录验证装饰器"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': '请先登录'}), 401
        return f(*args, **kwargs)
    return wrapper

def admin_required(f):
    """管理员权限验证装饰器（API 路由版，返回 JSON 错误）"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': '请先登录'}), 401
        if session.get('username') != 'admin':
            return jsonify({'error': '需要管理员权限'}), 403
        return f(*args, **kwargs)
    return wrapper

def admin_required_redirect(f):
    """管理员权限验证装饰器（页面路由版，未登录/无权限时重定向到首页）"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('index'))
        if session.get('username') != 'admin':
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return wrapper

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
            note TEXT DEFAULT '无',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            UNIQUE(user_id, word)
        )
    ''')

    # 添加 note 列（兼容旧数据库）
    try:
        cursor.execute("ALTER TABLE words ADD COLUMN note TEXT DEFAULT '无'")
    except sqlite3.OperationalError:
        pass  # 列已存在

    # 创建索引以优化查询性能
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_words_user_id ON words(user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_words_counter ON words(counter DESC)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_words_user_word ON words(user_id, word)')

    # 创建聊天记录表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_chat_messages_user_id ON chat_messages(user_id)')

    # 创建句子分析记录表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sentences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            original_text TEXT NOT NULL,
            analysis_result TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_sentences_user_id ON sentences(user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_sentences_created ON sentences(user_id, created_at DESC)')

    # 创建设置表（全局 key-value 存储，如颜色库）
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # 初始化默认颜色库（如果不存在）
    cursor.execute('''
        INSERT OR IGNORE INTO settings (key, value)
        VALUES ('color_library', ?)
    ''', (json.dumps([
        "#d0e6ff", "#d4f0d4", "#ffe0b2", "#f3e5f5", "#fff9c4", "#e0f7fa"
    ]),))

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

def fetch_word_info_from_deepseek(word):
    """
    调用 DeepSeek API 获取单词信息
    返回: dict - 包含 meaning, phrases, example
    """
    if not DEEPSEEK_API_KEY:
        raise ValueError("DEEPSEEK_API_KEY not found in environment variables")

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }

    prompt = f"""请为英语单词 "{word}" 提供以下信息，并用严格的 JSON 格式返回（词组可以不止一个，不要包含任何其他文字）：
{{
  "meaning": [{{"pos": "词性简写", "translation": "中文释义"}}, {{"pos": "词性简写2", "translation": "中文释义2"}}],
  "phrases": [{{"phrase": "词组1", "meaning": "中文含义1"}}, {{"phrase": "词组2", "meaning": "中文含义2"}}],
  "example": {{"en": "英文例句", "zh": "中文翻译"}},
  "note": "如果该单词是原型（如动词原形、名词单数等），则为"无"；如果是变形形式，则标注其原型和变形类型，例如："apple的复数形式"、"go的过去式形式"、"good的比较级形式"、"write的过去分词形式"等"
}}

词性简写可以是任意标准格式，如：c., uc., adj., adv., prep., conj., pron., int., art., num., vt., vi., pl., sing. 等注意标记名词是否可数（c. uc.）以及动词是否及物（vi. vt.）。确保返回的JSON格式严格正确，不要包含任何其他文字。
"""

    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": "你是一个英语词典助手，请严格按照 JSON 格式输出，不要有任何额外文字。"},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3,
        "max_tokens": 1024
    }

    try:
        response = requests.post(
            DEEPSEEK_API_URL,
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

@app.route('/api/words/batch', methods=['POST'])
@login_required
@rate_limit(max_requests=10, window_seconds=60)
def batch_add_words():
    """
    批量添加单词
    POST /api/words/batch
    Body: {"words": ["word1", "word2", ...]}
    逐个查询，返回成功/失败列表
    """
    try:
        data = request.get_json()
        if not data or 'words' not in data:
            return jsonify({'error': '缺少 words 参数'}), 400

        words = data['words']
        if not isinstance(words, list) or len(words) == 0:
            return jsonify({'error': 'words 必须是非空数组'}), 400

        # 限制批量数量
        if len(words) > 50:
            return jsonify({'error': '单次最多查询50个单词'}), 400

        user_id = session['user_id']
        results = {'success': [], 'failed': [], 'skipped': []}

        with get_db() as conn:
            cursor = conn.cursor()

            for raw_word in words:
                word = raw_word.strip().lower()
                if not word:
                    continue

                # 检查是否已存在
                cursor.execute("SELECT * FROM words WHERE word = ? AND user_id = ?", (word, user_id))
                existing = cursor.fetchone()

                if existing:
                    cursor.execute(
                        "UPDATE words SET counter = counter + 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                        (existing['id'],)
                    )
                    conn.commit()
                    cursor.execute("SELECT * FROM words WHERE id = ?", (existing['id'],))
                    updated = cursor.fetchone()
                    results['skipped'].append({
                        'word': word,
                        'message': '单词已存在，计数器已更新',
                        'counter': updated['counter']
                    })
                else:
                    try:
                        word_info = fetch_word_info_from_deepseek(word)
                        meaning_json = json.dumps(word_info, ensure_ascii=False)
                        note = word_info.get('note', '无')

                        cursor.execute(
                            "INSERT INTO words (word, user_id, meaning, note) VALUES (?, ?, ?, ?)",
                            (word, user_id, meaning_json, note)
                        )
                        conn.commit()

                        word_id = cursor.lastrowid
                        cursor.execute("SELECT * FROM words WHERE id = ?", (word_id,))
                        new_word = cursor.fetchone()
                        results['success'].append({
                            'word': word,
                            'id': new_word['id'],
                            'counter': new_word['counter']
                        })
                    except Exception as e:
                        results['failed'].append({
                            'word': word,
                            'error': str(e)
                        })

        return jsonify({
            'message': f'批量查询完成：成功 {len(results["success"])} 个，已存在 {len(results["skipped"])} 个，失败 {len(results["failed"])} 个',
            'results': results
        }), 200

    except Exception as e:
        return jsonify({'error': f'服务器错误: {str(e)}'}), 500


@app.route('/api/words/export', methods=['GET'])
@login_required
def export_words():
    """
    导出单词列表
    GET /api/words/export?format=json|csv
    默认 json 格式
    """
    try:
        fmt = request.args.get('format', 'json').lower()
        user_id = session['user_id']

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, word, counter, meaning, note, created_at
                FROM words
                WHERE user_id = ?
                ORDER BY counter DESC, word ASC
            """, (user_id,))

            rows = cursor.fetchall()

        if fmt == 'json':
            words_list = []
            for row in rows:
                meaning_data = json.loads(row['meaning']) if row['meaning'] else {}
                # 标准化 meaning 为数组格式
                if isinstance(meaning_data, list):
                    meaning_arr = meaning_data
                elif isinstance(meaning_data, dict) and 'meaning' in meaning_data:
                    meaning_arr = meaning_data['meaning']
                else:
                    meaning_arr = []

                phrases = meaning_data.get('phrases', []) if isinstance(meaning_data, dict) else []
                example = meaning_data.get('example', {}) if isinstance(meaning_data, dict) else {}

                words_list.append({
                    'word': row['word'],
                    'meaning': meaning_arr,
                    'phrases': phrases,
                    'example': example,
                    'note': row['note'] or '无',
                    'counter': row['counter']
                })

            export_data = {
                'version': '1.0',
                'exported_at': datetime.now().isoformat(),
                'words': words_list
            }

            content = json.dumps(export_data, ensure_ascii=False, indent=2)
            mimetype = 'application/json; charset=utf-8'
            filename = 'wordbook.json'

        else:
            # CSV format
            import csv
            import io
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(['单词', '释义', '查询次数', '备注', '添加时间'])
            for row in rows:
                meaning_data = json.loads(row['meaning']) if row['meaning'] else {}
                if isinstance(meaning_data, list):
                    meaning_text = '；'.join(
                        f"{m.get('pos', '')} {m.get('translation', '')}".strip()
                        for m in meaning_data if isinstance(m, dict)
                    )
                elif isinstance(meaning_data, dict) and 'meaning' in meaning_data:
                    meaning_text = '；'.join(
                        f"{m.get('pos', '')} {m.get('translation', '')}".strip()
                        for m in meaning_data['meaning'] if isinstance(m, dict)
                    )
                else:
                    meaning_text = str(meaning_data)
                writer.writerow([
                    row['word'],
                    meaning_text,
                    row['counter'],
                    row['note'] or '无',
                    row['created_at']
                ])
            content = output.getvalue()
            mimetype = 'text/csv; charset=utf-8-sig'
            filename = 'wordbook.csv'

        from flask import Response
        response = Response(content, mimetype=mimetype)
        response.headers['Content-Disposition'] = f'attachment; filename={filename}'
        return response

    except Exception as e:
        return jsonify({'error': f'服务器错误: {str(e)}'}), 500


def _import_word_item(item, user_id, cursor):
    """
    将一个单词 dict 写入数据库（不调用 AI）
    返回: ('success', dict) | ('updated', dict) | ('failed', dict)
    """
    if not isinstance(item, dict):
        return None

    word = str(item.get('word', '')).strip().lower()
    if not word:
        return None

    meaning_raw = item.get('meaning', [])
    phrases_raw = item.get('phrases', [])
    example_raw = item.get('example', {})
    note_raw = item.get('note', '无')

    # 标准化 meaning
    if isinstance(meaning_raw, list):
        meaning_arr = meaning_raw
    elif isinstance(meaning_raw, str):
        meaning_arr = [{'pos': '', 'translation': meaning_raw}]
    else:
        meaning_arr = []

    meaning_to_save = meaning_raw
    if isinstance(meaning_arr, list) and not isinstance(meaning_raw, dict):
        meaning_to_save = {
            'meaning': meaning_arr,
            'phrases': phrases_raw if isinstance(phrases_raw, list) else [],
            'example': example_raw if isinstance(example_raw, dict) else {}
        }

    meaning_json = json.dumps(meaning_to_save, ensure_ascii=False)
    note = str(note_raw) if note_raw else '无'

    cursor.execute("SELECT * FROM words WHERE word = ? AND user_id = ?", (word, user_id))
    existing = cursor.fetchone()

    if existing:
        cursor.execute(
            "UPDATE words SET meaning = ?, note = ?, counter = counter + 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (meaning_json, note, existing['id'])
        )
        cursor.execute("SELECT counter FROM words WHERE id = ?", (existing['id'],))
        updated_counter = cursor.fetchone()['counter']
        return ('updated', {'word': word, 'counter': updated_counter})
    else:
        counter = item.get('counter', 1)
        cursor.execute(
            "INSERT INTO words (word, user_id, meaning, note, counter) VALUES (?, ?, ?, ?, ?)",
            (word, user_id, meaning_json, note, counter)
        )
        return ('success', {'word': word, 'id': cursor.lastrowid, 'counter': counter})


@app.route('/api/words/import', methods=['POST'])
@login_required
@rate_limit(max_requests=10, window_seconds=60)
def import_words():
    """
    从 JSON / CSV 文件导入单词（直接写入数据库，不调用 AI）
    POST /api/words/import  (multipart/form-data, file field: 'file')
    JSON 格式：
      1. {"version":"1.0","words":[{word,meaning,phrases,example,note,counter},...]}
      2. {"words":[{word,meaning,...},...]}
      3. [{word,meaning,...},...]
    CSV 格式：
      首行为列名，支持：word/单词, meaning/释义/翻译, phrases/词组, example/例句, note/备注, counter/查询次数
    """
    try:
        if 'file' not in request.files:
            return jsonify({'error': '请上传文件'}), 400

        file = request.files['file']
        if not file or file.filename == '':
            return jsonify({'error': '请选择文件'}), 400

        filename = file.filename.lower()
        if not (filename.endswith('.json') or filename.endswith('.csv')):
            return jsonify({'error': '只支持 .json 或 .csv 文件'}), 400

        raw = file.read().decode('utf-8')

        if filename.endswith('.csv'):
            import csv
            import io
            reader = csv.DictReader(io.StringIO(raw))
            # 列名映射
            words = []
            for row in reader:
                # 找 word 列
                word_val = (row.get('word') or row.get('单词') or '').strip()
                if not word_val:
                    continue
                meaning_val = (row.get('meaning') or row.get('释义') or row.get('翻译') or '').strip()
                phrases_val = (row.get('phrases') or row.get('词组') or '').strip()
                example_val = (row.get('example') or row.get('例句') or '').strip()
                note_val = (row.get('note') or row.get('备注') or '无').strip()
                counter_val = (row.get('counter') or row.get('查询次数') or '1').strip()

                item = {
                    'word': word_val,
                    'meaning': meaning_val if meaning_val else [],
                    'phrases': phrases_val if phrases_val else [],
                    'example': example_val if example_val else {},
                    'note': note_val if note_val else '无',
                    'counter': int(counter_val) if counter_val.isdigit() else 1
                }
                words.append(item)
        else:
            # JSON
            try:
                data = json.loads(raw)
            except json.JSONDecodeError as e:
                return jsonify({'error': f'JSON 解析失败: {str(e)}'}), 400

            if isinstance(data, list):
                words = data
            elif isinstance(data, dict):
                if 'words' in data:
                    words = data['words']
                else:
                    return jsonify({'error': 'JSON 格式不正确，需要包含 "words" 数组或为纯数组'}), 400
            else:
                return jsonify({'error': 'JSON 格式不正确'}), 400

        if not words:
            return jsonify({'error': '未找到有效单词'}), 400

        if len(words) > 200:
            return jsonify({'error': '单次最多导入200个单词'}), 400

        user_id = session['user_id']
        results = {'success': [], 'updated': [], 'failed': []}

        with get_db() as conn:
            cursor = conn.cursor()
            for item in words:
                try:
                    result = _import_word_item(item, user_id, cursor)
                    if result is None:
                        continue
                    status, info = result
                    if status == 'success':
                        results['success'].append(info)
                    elif status == 'updated':
                        results['updated'].append(info)
                except Exception as e:
                    w = item.get('word', '?') if isinstance(item, dict) else '?'
                    results['failed'].append({'word': str(w), 'error': str(e)})
            conn.commit()

        return jsonify({
            'message': f'导入完成：新增 {len(results["success"])} 个，更新 {len(results["updated"])} 个，失败 {len(results["failed"])} 个',
            'results': results
        }), 200

    except Exception as e:
        return jsonify({'error': f'服务器错误: {str(e)}'}), 500


@app.route('/api/words', methods=['POST'])
@login_required
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

        # 获取用户ID
        user_id = session['user_id']

        with get_db() as conn:
            cursor = conn.cursor()

            # 检查该用户的单词是否已存在
            cursor.execute("SELECT * FROM words WHERE word = ? AND user_id = ?", (word, user_id))
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
                    word_info = fetch_word_info_from_deepseek(word)
                    meaning_json = json.dumps(word_info, ensure_ascii=False)
                    note = word_info.get('note', '无')

                    # 插入新单词
                    cursor.execute(
                        "INSERT INTO words (word, user_id, meaning, note) VALUES (?, ?, ?, ?)",
                        (word, user_id, meaning_json, note)
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
                        'note': new_word['note'],
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
@login_required
def get_all_words():
    """获取单词列表，按 counter 降序排序"""
    try:
        # 获取用户ID
        user_id = session['user_id']

        with get_db() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT id, word, counter, meaning, note
                FROM words
                WHERE user_id = ?
                ORDER BY counter DESC, word ASC
            """, (user_id,))

            words = []
            for row in cursor.fetchall():
                words.append({
                    'id': row['id'],
                    'word': row['word'],
                    'counter': row['counter'],
                    'meaning': json.loads(row['meaning']) if row['meaning'] else None,
                    'note': row['note']
                })

            return jsonify(words), 200

    except Exception as e:
        return jsonify({'error': f'服务器错误: {str(e)}'}), 500

@app.route('/api/words/<word>', methods=['GET'])
@login_required
def get_word_detail(word):
    """获取单词详细信息"""
    try:
        word = word.lower()
        user_id = session['user_id']

        with get_db() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM words WHERE word = ? AND user_id = ?", (word, user_id))
            word_data = cursor.fetchone()

            if not word_data:
                return jsonify({'error': '单词不存在'}), 404

            result = {
                'id': word_data['id'],
                'word': word_data['word'],
                'counter': word_data['counter'],
                'meaning': json.loads(word_data['meaning']) if word_data['meaning'] else None,
                'note': word_data['note'],
                'created_at': word_data['created_at'],
                'updated_at': word_data['updated_at']
            }

            return jsonify(result), 200

    except Exception as e:
        return jsonify({'error': f'服务器错误: {str(e)}'}), 500

@app.route('/api/words/<word>', methods=['DELETE'])
@login_required
def delete_word(word):
    """删除单词"""
    try:
        word = word.lower()
        user_id = session['user_id']

        with get_db() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM words WHERE word = ? AND user_id = ?", (word, user_id))
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
@login_required
def update_word(word):
    """更新当前用户的单词信息"""
    try:
        word = word.lower()
        user_id = session['user_id']

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

                # 更新备注
                if 'note' in data:
                    updates.append("note = ?")
                    params.append(data['note'])

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
                    'note': updated_word['note'],
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
@login_required
@rate_limit(max_requests=20, window_seconds=60)
def chat_with_ai():
    """与 DeepSeek AI 对话接口"""
    try:
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({'error': '缺少 message 参数'}), 400

        user_message = data['message']
        history = data.get('history', [])
        model = data.get('model', DEEPSEEK_MODEL)  # 获取选择的模型

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

        # 调用 DeepSeek API
        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": model,  # 使用选择的模型
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 32767
        }

        response = requests.post(
            DEEPSEEK_API_URL,
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

@app.route('/api/chat/history', methods=['GET'])
@login_required
def get_chat_history():
    """获取当前用户的聊天记录"""
    try:
        user_id = session['user_id']

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, role, content, timestamp FROM chat_messages WHERE user_id = ? ORDER BY id ASC",
                (user_id,)
            )
            messages = []
            for row in cursor.fetchall():
                messages.append({
                    'id': row['id'],
                    'role': row['role'],
                    'content': row['content'],
                    'timestamp': row['timestamp']
                })
            return jsonify(messages), 200
    except Exception as e:
        return jsonify({'error': f'服务器错误: {str(e)}'}), 500

@app.route('/api/chat/history', methods=['POST'])
@login_required
def save_chat_message():
    """保存一条聊天记录"""
    try:
        user_id = session['user_id']

        data = request.get_json()
        if not data or 'role' not in data or 'content' not in data or 'timestamp' not in data:
            return jsonify({'error': '缺少必要参数'}), 400

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO chat_messages (user_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
                (user_id, data['role'], data['content'], data['timestamp'])
            )
            conn.commit()
            return jsonify({'id': cursor.lastrowid, 'message': '保存成功'}), 201
    except Exception as e:
        return jsonify({'error': f'服务器错误: {str(e)}'}), 500

@app.route('/api/chat/history/<int:message_id>', methods=['DELETE'])
@login_required
def delete_chat_message(message_id):
    """删除一条聊天记录"""
    try:
        user_id = session['user_id']

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM chat_messages WHERE id = ? AND user_id = ?",
                (message_id, user_id)
            )
            conn.commit()
            return jsonify({'message': '删除成功'}), 200
    except Exception as e:
        return jsonify({'error': f'服务器错误: {str(e)}'}), 500

@app.route('/api/chat/history', methods=['DELETE'])
@login_required
def clear_chat_history():
    """清空当前用户的聊天记录"""
    try:
        user_id = session['user_id']

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM chat_messages WHERE user_id = ?",
                (user_id,)
            )
            conn.commit()
            return jsonify({'message': '聊天记录已清空'}), 200
    except Exception as e:
        return jsonify({'error': f'服务器错误: {str(e)}'}), 500

@app.route('/api/change_password', methods=['POST'])
@login_required
def change_password():
    """修改当前用户密码"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': '缺少请求数据'}), 400

        old_password = data.get('old_password', '')
        new_password = data.get('new_password', '')
        confirm_password = data.get('confirm_password', '')

        # 验证新密码
        if not new_password:
            return jsonify({'error': '新密码不能为空'}), 400

        if new_password != confirm_password:
            return jsonify({'error': '两次输入的新密码不一致'}), 400

        if len(new_password) < 4:
            return jsonify({'error': '新密码至少需要4个字符'}), 400

        user_id = session['user_id']

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            user = cursor.fetchone()

            if not user:
                return jsonify({'error': '用户不存在'}), 404

            # 如果用户已设置密码，需要验证原密码
            if user['password_hash']:
                if not old_password:
                    return jsonify({'error': '请输入原密码'}), 400
                if not check_password_hash(user['password_hash'], old_password):
                    return jsonify({'error': '原密码错误'}), 401

            # 更新密码
            new_hash = generate_password_hash(new_password)
            cursor.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_hash, user_id))
            conn.commit()

            return jsonify({'message': '密码修改成功'}), 200

    except Exception as e:
        return jsonify({'error': f'服务器错误: {str(e)}'}), 500

@app.route('/api/admin/users', methods=['GET'])
@admin_required
def admin_get_users():
    """管理员获取所有用户列表"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, username, password_hash, created_at FROM users ORDER BY id ASC")
            users = []
            for row in cursor.fetchall():
                users.append({
                    'id': row['id'],
                    'username': row['username'],
                    'has_password': bool(row['password_hash']),
                    'created_at': row['created_at']
                })
            return jsonify(users), 200
    except Exception as e:
        return jsonify({'error': f'服务器错误: {str(e)}'}), 500

@app.route('/api/admin/users/<int:user_id>/password', methods=['PUT'])
@admin_required
def admin_change_user_password(user_id):
    """管理员修改任意用户密码"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': '缺少请求数据'}), 400

        new_password = data.get('new_password', '')

        with get_db() as conn:
            cursor = conn.cursor()

            # 检查目标用户是否存在
            cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            target_user = cursor.fetchone()
            if not target_user:
                return jsonify({'error': '用户不存在'}), 404

            # 更新密码（空密码设为 NULL，表示未设置密码）
            if new_password:
                new_hash = generate_password_hash(new_password)
                cursor.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_hash, user_id))
                msg = f'用户 {target_user["username"]} 的密码已修改'
            else:
                cursor.execute("UPDATE users SET password_hash = NULL WHERE id = ?", (user_id,))
                msg = f'用户 {target_user["username"]} 的密码已清除'
            conn.commit()

            return jsonify({'message': msg}), 200

    except Exception as e:
        return jsonify({'error': f'服务器错误: {str(e)}'}), 500

@app.route('/api/admin/users/<int:user_id>', methods=['DELETE'])
@admin_required
def admin_delete_user(user_id):
    """管理员删除用户"""
    try:
        # 不能删除自己
        if user_id == session.get('user_id'):
            return jsonify({'error': '不能删除自己的账户'}), 400

        with get_db() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            target_user = cursor.fetchone()
            if not target_user:
                return jsonify({'error': '用户不存在'}), 404

            # 删除用户的单词
            cursor.execute("DELETE FROM words WHERE user_id = ?", (user_id,))
            # 删除用户的聊天记录
            cursor.execute("DELETE FROM chat_messages WHERE user_id = ?", (user_id,))
            # 删除用户
            cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
            conn.commit()

            return jsonify({'message': f'用户 {target_user["username"]} 已删除'}), 200

    except Exception as e:
        return jsonify({'error': f'服务器错误: {str(e)}'}), 500

@app.route('/setting')
@admin_required_redirect
def setting_page():
    """管理员设置页面"""
    return render_template('setting.html')

@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'database': os.path.exists(DATABASE),
        'deepseek_api_key': bool(DEEPSEEK_API_KEY)
    }), 200

@app.route('/offline')
def offline_page():
    """离线单词浏览页面（无需登录）"""
    return render_template('offline.html')

@app.route('/ai-chat')
@login_required
def ai_chat_page():
    """渲染AI聊天页面"""
    return render_template('ai_chat.html')

@app.route('/sentence')
@login_required
def sentence_page():
    """渲染句子分析页面"""
    return render_template('sentence.html')

@app.route('/api/sentence/analyze', methods=['POST'])
@login_required
@rate_limit(max_requests=15, window_seconds=60)
def analyze_sentence():
    """分析句子语法成分"""
    try:
        data = request.get_json()
        if not data or 'sentence' not in data:
            return jsonify({'error': '缺少 sentence 参数'}), 400

        sentence = data['sentence'].strip()
        if not sentence:
            return jsonify({'error': '句子不能为空'}), 400

        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }

        prompt = f"""请严格按照以下格式分析英语句子的语法成分，返回 JSON 对象（不要包含任何其他文字）：

{{
  "translation": "整句的中文翻译",
  "components": [
    {{"text": "成分文本", "type": "成分类型", "meaning": "该成分在此句中的语法含义解释"}},
    ...
  ]
}}

分析规则：
1. 必须将句子拆分为最细粒度的语法成分，每个单词或词组都必须被独立标注
2. 修饰性成分（定语、状语、补语、同位语等）必须全部独立拆分出来，不要合并到主干成分中
3. type 根据该成分的真实语法角色灵活命名，例如：
   - 主干：主语、谓语动词、宾语、表语、系动词、间接宾语、直接宾语
   - 修饰：定语、状语、补语、同位语
   - 功能词：冠词、介词、连词、助动词、情态动词
   - 短语：介词短语、不定式短语、分词短语、名词短语
   - 其他：标点、感叹词、插入语
4. meaning 要简洁清晰地说明该成分的语法功能

示例输入：The little boy quickly ran to the store.
示例输出：
{{
  "translation": "那个小男孩快速跑向了商店。",
  "components": [
    {{"text": "The", "type": "冠词", "meaning": "定冠词，修饰主语boy"}},
    {{"text": "little", "type": "定语", "meaning": "形容词作前置定语，修饰主语boy"}},
    {{"text": "boy", "type": "主语", "meaning": "句子主语，表示动作的执行者"}},
    {{"text": "quickly", "type": "状语", "meaning": "副词作方式状语，修饰谓语动词ran"}},
    {{"text": "ran", "type": "谓语动词", "meaning": "谓语动词，表示跑的动作"}},
    {{"text": "to", "type": "介词", "meaning": "介词，引导方向状语"}},
    {{"text": "the", "type": "冠词", "meaning": "定冠词，修饰名词store"}},
    {{"text": "store", "type": "介词宾语", "meaning": "介词to的宾语，表示方向目的地"}},
    {{"text": ".", "type": "标点", "meaning": "句末标点，表示陈述句结束"}}
  ]
}}

另一个示例输入：She is a very talented singer who won many awards.
示例输出：
{{
  "translation": "她是一位赢得许多奖项的非常有才华的歌手。",
  "components": [
    {{"text": "She", "type": "主语", "meaning": "句子主语，第三人称代词"}},
    {{"text": "is", "type": "系动词", "meaning": "系动词，连接主语和表语"}},
    {{"text": "a", "type": "冠词", "meaning": "不定冠词，修饰singer"}},
    {{"text": "very", "type": "状语", "meaning": "副词作程度状语，修饰形容词talented"}},
    {{"text": "talented", "type": "定语", "meaning": "形容词作前置定语，修饰singer"}},
    {{"text": "singer", "type": "表语", "meaning": "名词作表语，说明主语的身份"}},
    {{"text": "who", "type": "关系代词", "meaning": "关系代词，引导定语从句，指代singer"}},
    {{"text": "won", "type": "谓语动词", "meaning": "定语从句中的谓语动词"}},
    {{"text": "many", "type": "定语", "meaning": "形容词作定语，修饰awards"}},
    {{"text": "awards", "type": "宾语", "meaning": "定语从句中的宾语"}},
    {{"text": ".", "type": "标点", "meaning": "句末标点"}}
  ]
}}

请分析以下句子：
{sentence}

只返回 JSON 对象，不要包含任何其他文字。"""

        payload = {
            "model": DEEPSEEK_MODEL,
            "messages": [
                {"role": "system", "content": "你是一个英语语法分析助手，请严格按照 JSON 数组格式输出句子成分分析结果，不要有任何额外文字。"},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 2048
        }

        response = requests.post(
            DEEPSEEK_API_URL,
            headers=headers,
            json=payload,
            timeout=60
        )
        response.raise_for_status()

        result = response.json()
        content = result['choices'][0]['message']['content']

        content = content.strip()
        if content.startswith('```json'):
            content = content[7:]
        if content.startswith('```'):
            content = content[3:]
        if content.endswith('```'):
            content = content[:-3]
        content = content.strip()

        analysis_data = json.loads(content)

        # 支持两种格式：新格式 {"translation": "...", "components": [...]}；旧格式 [...]（兼容）
        if isinstance(analysis_data, dict) and 'components' in analysis_data:
            translation = analysis_data.get('translation', '')
            components = analysis_data['components']
        elif isinstance(analysis_data, list):
            translation = ''
            components = analysis_data
        else:
            return jsonify({'error': 'AI 返回格式不正确'}), 500

        # 存储完整结果（含翻译）
        save_data = {'translation': translation, 'components': components}

        user_id = session['user_id']
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO sentences (user_id, original_text, analysis_result) VALUES (?, ?, ?)",
                (user_id, sentence, json.dumps(save_data, ensure_ascii=False))
            )
            conn.commit()
            sentence_id = cursor.lastrowid

        return jsonify({
            'id': sentence_id,
            'sentence': sentence,
            'translation': translation,
            'analysis': components
        }), 200

    except json.JSONDecodeError:
        return jsonify({'error': 'AI 返回的 JSON 格式无效'}), 500
    except requests.RequestException as e:
        return jsonify({'error': f'API 请求失败: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'error': f'分析失败: {str(e)}'}), 500

@app.route('/api/sentence/history', methods=['GET'])
@login_required
def get_sentence_history():
    """获取当前用户的句子分析历史"""
    try:
        user_id = session['user_id']
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, original_text, analysis_result, created_at FROM sentences WHERE user_id = ? ORDER BY created_at DESC LIMIT 50",
                (user_id,)
            )
            sentences = []
            for row in cursor.fetchall():
                sentences.append({
                    'id': row['id'],
                    'original_text': row['original_text'],
                    'analysis_result': json.loads(row['analysis_result']) if row['analysis_result'] else None,
                    'created_at': row['created_at']
                })
            return jsonify(sentences), 200
    except Exception as e:
        return jsonify({'error': f'服务器错误: {str(e)}'}), 500

@app.route('/api/sentence/<int:sentence_id>', methods=['DELETE'])
@login_required
def delete_sentence(sentence_id):
    """删除句子分析记录"""
    try:
        user_id = session['user_id']
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM sentences WHERE id = ? AND user_id = ?",
                (sentence_id, user_id)
            )
            conn.commit()
            return jsonify({'message': '删除成功'}), 200
    except Exception as e:
        return jsonify({'error': f'服务器错误: {str(e)}'}), 500

@app.route('/api/settings/colors', methods=['GET'])
def get_color_library():
    """获取颜色库配置"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM settings WHERE key = 'color_library'")
            row = cursor.fetchone()
            if row:
                return jsonify({'colors': json.loads(row['value'])}), 200
            else:
                default_colors = ["#d0e6ff", "#d4f0d4", "#ffe0b2", "#f3e5f5", "#fff9c4", "#e0f7fa"]
                return jsonify({'colors': default_colors}), 200
    except Exception as e:
        return jsonify({'error': f'服务器错误: {str(e)}'}), 500

@app.route('/api/settings/colors', methods=['PUT'])
@admin_required
def update_color_library():
    """更新颜色库配置（管理员）"""
    try:
        data = request.get_json()
        if not data or 'colors' not in data:
            return jsonify({'error': '缺少 colors 参数'}), 400

        colors = data['colors']
        if not isinstance(colors, list) or len(colors) == 0:
            return jsonify({'error': 'colors 必须是非空数组'}), 400

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES ('color_library', ?, CURRENT_TIMESTAMP)",
                (json.dumps(colors, ensure_ascii=False),)
            )
            conn.commit()
            return jsonify({'message': '颜色库已更新', 'colors': colors}), 200
    except Exception as e:
        return jsonify({'error': f'服务器错误: {str(e)}'}), 500

@app.route('/api/settings/colors/reset', methods=['POST'])
@admin_required
def reset_color_library():
    """重置颜色库为默认值（管理员）"""
    try:
        default_colors = ["#d0e6ff", "#d4f0d4", "#ffe0b2", "#f3e5f5", "#fff9c4", "#e0f7fa"]
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES ('color_library', ?, CURRENT_TIMESTAMP)",
                (json.dumps(default_colors, ensure_ascii=False),)
            )
            conn.commit()
            return jsonify({'message': '颜色库已重置为默认值', 'colors': default_colors}), 200
    except Exception as e:
        return jsonify({'error': f'服务器错误: {str(e)}'}), 500

if __name__ == '__main__':
    # 初始化数据库
    init_db()
    print(f"数据库已初始化: {DATABASE}")
    print(f"DeepSeek API Key 已配置: {bool(DEEPSEEK_API_KEY)}")

    # 启动 Flask 应用
    app.run(host='0.0.0.0', port=5000, debug=False)