# English Wordbook Web Application 🇬🇧

A Flask-based web application for managing and reviewing English vocabulary. This application helps you build your personal English word dictionary with AI-powered word information retrieval, multi-turn AI chat, and sentence analysis.

## ✨ Features

- **Word Management**: Add, view, edit, delete, and track your English vocabulary
- **AI Integration**: Automatic word information retrieval using DeepSeek AI API
- **AI Chat**: Multi-turn conversation with AI for English learning and questions
- **Sentence Analysis**: Analyze English sentences with AI-powered breakdown
- **Smart Tracking**: Counter system to track word query frequency
- **User System**: Registration, login, admin panel with user management
- **Import / Export**: Export words as JSON or CSV; import from JSON files
- **Batch Operations**: Add multiple words at once
- **Word Notes**: Add custom notes to each word entry
- **Responsive UI**: Modern, mobile-friendly web interface with theme support
- **RESTful API**: Complete API for word operations, chat, sentences, and settings
- **Database**: SQLite database for persistent storage

## 🛠️ Technology Stack

- **Backend**: Flask (Python)
- **Frontend**: HTML5, CSS3, JavaScript
- **Database**: SQLite
- **AI API**: DeepSeek Chat API
- **Deployment**: Ready for any Python-compatible hosting

## 📋 Requirements

- Python 3.7+
- pip package manager
- DeepSeek API key

## 🚀 Quick Start

### 1. Clone the repository
```bash
git clone <repository-url>
cd wordbook
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure environment variables
```bash
cp .env.example .env
# Edit .env and add your DeepSeek API key
```

### 4. Run the application
```bash
python app.py
```

### 5. Access the application
Open your browser and visit: `http://localhost:5000`

## 🔧 Configuration

Edit the `.env` file to configure your application:

```
DEEPSEEK_API_KEY=your_api_key_here
SECRET_KEY=your-secret-key-here
```

## 🗂️ Project Structure

```
wordbook/
├── app.py                    # Main Flask application
├── requirements.txt          # Python dependencies
├── .env.example             # Environment variable template
├── .gitignore
├── LICENSE
├── README.md
├── README-zh.md
├── .deepseek/
│   └── instructions.md
├── static/
│   ├── css/
│   │   └── style.css        # Stylesheets
│   ├── js/
│   │   ├── app.js           # Main frontend logic (words, user, chat, sentence)
│   │   ├── offline.js       # Offline page logic
│   │   └── theme.js         # Theme switching logic
│   └── favicon.ico
├── templates/
│   ├── index.html           # Main wordbook page
│   ├── ai_chat.html         # AI chat page
│   ├── sentence.html        # Sentence analysis page
│   ├── setting.html         # Admin settings page
│   └── offline.html         # Offline fallback page
└── database/
    └── words.db             # SQLite database (generated on first run)
```

## 🎯 Pages

| Route | Page | Description |
|-------|------|-------------|
| `/` | index.html | Main wordbook — add, view, search, delete words |
| `/ai-chat` | ai_chat.html | Multi-turn AI conversation for English learning |
| `/sentence` | sentence.html | Upload or type sentences for AI analysis |
| `/setting` | setting.html | Admin-only: color library, user management |
| `/offline` | offline.html | Offline fallback with PWA support |

## 📖 API Documentation

### Authentication

#### `POST /api/register`
Register a new user account.

**Request:**
```json
{
  "username": "your_username",
  "password": "your_password"
}
```

#### `POST /api/login`
Log in with existing credentials.

**Request:**
```json
{
  "username": "your_username",
  "password": "your_password"
}
```

#### `POST /api/logout`
Log out the current session.

#### `GET /api/current_user`
Get the currently logged-in user's information.

#### `POST /api/change_password`
Change the current user's password.

**Request:**
```json
{
  "old_password": "current_password",
  "new_password": "new_password"
}
```

### Words

#### `POST /api/words`
Add a new word (auto-fetches AI meaning) or increment counter if existing.

**Request:**
```json
{
  "word": "example"
}
```

**Response:**
```json
{
  "message": "Word added/updated successfully",
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
Add multiple words at once.

**Request:**
```json
{
  "words": ["hello", "world", "example"]
}
```

#### `GET /api/words`
Get all words sorted by query frequency (descending).

#### `GET /api/words/<word>`
Get detailed information about a specific word.

#### `PUT /api/words/<word>`
Update a word's meaning, phrases, example, or note.

#### `DELETE /api/words/<word>`
Delete a word from the database.

#### `GET /api/words/export?format=json`
Export all words in JSON or CSV format. Query param: `format=json` (default) or `format=csv`.

#### `POST /api/words/import`
Import words from a JSON file.

**Request:**
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

### AI Chat

#### `POST /api/chat`
Send a message to the AI chat and receive a streaming or non-streaming response.

**Request:**
```json
{
  "message": "Tell me about the word 'serendipity'",
  "conversation_id": 0
}
```

#### `GET /api/chat/conversations`
List all conversation threads for the current user.

#### `POST /api/chat/conversations`
Create a new conversation.

#### `GET /api/chat/conversations/<id>`
Get messages in a specific conversation.

#### `PATCH /api/chat/conversations/<id>`
Update a conversation's title.

#### `DELETE /api/chat/conversations/<id>`
Delete a conversation and all its messages.

#### `GET /api/chat/history`
Get chat history messages.

#### `POST /api/chat/history`
Save a chat message to history.

#### `DELETE /api/chat/history/<id>`
Delete a specific chat message.

#### `DELETE /api/chat/history`
Clear all chat history for the current user.

### Sentence Analysis

#### `POST /api/sentence/analyze`
Analyze an English sentence with AI.

**Request:**
```json
{
  "text": "The quick brown fox jumps over the lazy dog."
}
```

#### `GET /api/sentence/history`
Get sentence analysis history.

#### `DELETE /api/sentence/<id>`
Delete a sentence analysis record.

### Settings

#### `GET /api/settings/colors`
Get the global color library.

#### `PUT /api/settings/colors`
Update the color library (admin only).

#### `POST /api/settings/colors/reset`
Reset the color library to defaults (admin only).

### Admin

#### `GET /api/admin/users`
List all users (admin only).

#### `PUT /api/admin/users/<id>/password`
Reset a user's password (admin only).

#### `DELETE /api/admin/users/<id>`
Delete a user account (admin only).

### Health

#### `GET /api/health`
Health check endpoint.

## 🎯 Usage

1. **Register / Login**: Create an account or log in with existing credentials
2. **Add a Word**: Type an English word in the input field and click "Query/Add" — AI will fetch its meaning automatically
3. **View Words**: All added words are displayed in descending order by query frequency
4. **Track Progress**: The counter shows how many times you've looked up each word
5. **Chat with AI**: Go to AI Chat page for multi-turn English learning conversations
6. **Analyze Sentences**: Paste or type sentences on the Sentence page for AI analysis
7. **Import / Export**: Export your word collection as JSON or CSV; import from JSON files
8. **Settings**: Admin users can manage color themes and user accounts

## 🤝 Contributing

Feel free to fork this project and submit pull requests. Any contributions are welcome!

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- DeepSeek AI for providing the word information API
- Flask framework for the excellent web development experience
