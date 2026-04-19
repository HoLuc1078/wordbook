"""
英语单词本 Web 应用 - Flask 后端
"""
import os
import sqlite3
import json
from datetime import datetime
from dotenv import load_dotenv
import requests
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS

# 加载环境变量
load_dotenv()

# 初始化 Flask 应用
app = Flask(__name__)
CORS(app)  # 启用跨域支持

# 配置
DATABASE = os.path.join(os.path.dirname(__file__), 'database', 'words.db')
LONGCAT_API_KEY = os.getenv('LONGCAT_API_KEY')
LONGCAT_API_URL = "https://api.longcat.chat/openai/v1/chat/completions"
LONGCAT_MODEL = "LongCat-Flash-Lite"

def init_db():
    """初始化数据库，创建 words 表"""
    os.makedirs(os.path.dirname(DATABASE), exist_ok=True)
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS words (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word TEXT UNIQUE NOT NULL,
            counter INTEGER DEFAULT 1,
            meaning TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def get_db_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # 使返回结果可按字典访问
    return conn

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

    prompt = f"""请为英语单词 "{word}" 提供以下信息，并用严格的 JSON 格式返回（不要包含任何其他文字）：
{{
  "meaning": "中文释义",
  "phrases": [{{"phrase": "词组1", "meaning": "中文含义1"}}, {{"phrase": "词组2", "meaning": "中文含义2"}}],
  "example": {{"en": "英文例句", "zh": "中文翻译"}}
}}"""

    payload = {
        "model": LONGCAT_MODEL,
        "messages": [
            {"role": "system", "content": "你是一个英语词典助手，请严格按照 JSON 格式输出，不要有任何额外文字。"},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3,
        "max_tokens": 800
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

        conn = get_db_connection()
        cursor = conn.cursor()

        # 检查单词是否已存在
        cursor.execute("SELECT * FROM words WHERE word = ?", (word,))
        existing_word = cursor.fetchone()

        if existing_word:
            # 单词已存在，更新 counter
            cursor.execute(
                "UPDATE words SET counter = counter + 1, updated_at = CURRENT_TIMESTAMP WHERE word = ?",
                (word,)
            )
            conn.commit()

            # 获取更新后的单词信息
            cursor.execute("SELECT * FROM words WHERE word = ?", (word,))
            updated_word = cursor.fetchone()

            result = {
                'id': updated_word['id'],
                'word': updated_word['word'],
                'counter': updated_word['counter'],
                'meaning': json.loads(updated_word['meaning']) if updated_word['meaning'] else None,
                'created_at': updated_word['created_at'],
                'updated_at': updated_word['updated_at']
            }

            conn.close()
            return jsonify({
                'message': '单词已存在，计数器已更新',
                'word': result
            }), 200
        else:
            # 单词不存在，调用 AI API 获取信息
            try:
                word_info = fetch_word_info_from_longcat(word)
                meaning_json = json.dumps(word_info, ensure_ascii=False)

                # 插入新单词
                cursor.execute(
                    "INSERT INTO words (word, meaning) VALUES (?, ?)",
                    (word, meaning_json)
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

                conn.close()
                return jsonify({
                    'message': '新单词已添加',
                    'word': result
                }), 201

            except Exception as e:
                conn.close()
                return jsonify({'error': f'调用 AI API 失败: {str(e)}'}), 500

    except Exception as e:
        return jsonify({'error': f'服务器错误: {str(e)}'}), 500

@app.route('/api/words', methods=['GET'])
def get_all_words():
    """获取所有单词列表，按 counter 降序排序"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, word, counter, meaning
            FROM words
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

        conn.close()
        return jsonify(words), 200

    except Exception as e:
        return jsonify({'error': f'服务器错误: {str(e)}'}), 500

@app.route('/api/words/<word>', methods=['GET'])
def get_word_detail(word):
    """获取指定单词的详细信息"""
    try:
        word = word.lower()
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM words WHERE word = ?", (word,))
        word_data = cursor.fetchone()

        if not word_data:
            conn.close()
            return jsonify({'error': '单词不存在'}), 404

        result = {
            'id': word_data['id'],
            'word': word_data['word'],
            'counter': word_data['counter'],
            'meaning': json.loads(word_data['meaning']) if word_data['meaning'] else None,
            'created_at': word_data['created_at'],
            'updated_at': word_data['updated_at']
        }

        conn.close()
        return jsonify(result), 200

    except Exception as e:
        return jsonify({'error': f'服务器错误: {str(e)}'}), 500

@app.route('/api/words/<word>', methods=['DELETE'])
def delete_word(word):
    """删除指定单词"""
    try:
        word = word.lower()
        conn = get_db_connection()
        cursor = conn.cursor()

        # 检查单词是否存在
        cursor.execute("SELECT * FROM words WHERE word = ?", (word,))
        word_data = cursor.fetchone()

        if not word_data:
            conn.close()
            return jsonify({'error': '单词不存在'}), 404

        # 删除单词
        cursor.execute("DELETE FROM words WHERE word = ?", (word,))
        conn.commit()
        conn.close()

        return jsonify({'message': '单词删除成功'}), 200

    except Exception as e:
        return jsonify({'error': f'服务器错误: {str(e)}'}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'database': os.path.exists(DATABASE),
        'longcat_api_key': bool(LONGCAT_API_KEY)
    }), 200

if __name__ == '__main__':
    # 初始化数据库
    init_db()
    print(f"数据库已初始化: {DATABASE}")
    print(f"LongCat API Key 已配置: {bool(LONGCAT_API_KEY)}")

    # 启动 Flask 应用
    app.run(debug=True, port=5000)