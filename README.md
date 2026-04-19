# English Wordbook Web Application 🇬🇧

A Flask-based web application for managing and reviewing English vocabulary. This application helps you build your personal English word dictionary with AI-powered word information retrieval.

## ✨ Features

- **Word Management**: Add, view, delete, and track your English vocabulary
- **AI Integration**: Automatic word information retrieval using LongCat AI API
- **Smart Tracking**: Counter system to track word query frequency
- **Responsive UI**: Modern, mobile-friendly web interface
- **RESTful API**: Complete API for word operations
- **Database**: SQLite database for persistent storage

## 🛠️ Technology Stack

- **Backend**: Flask (Python)
- **Frontend**: HTML5, CSS3, JavaScript
- **Database**: SQLite
- **AI API**: LongCat Chat API
- **Deployment**: Ready for any Python-compatible hosting

## 📋 Requirements

- Python 3.7+
- pip package manager
- LongCat API key

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
cp ex.env .env
# Edit .env and add your LongCat API key
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
LONGCAT_API_KEY=your_api_key_here
```

## 📖 API Documentation

### Endpoints

#### `POST /api/words`
Add a new word or update existing word counter

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
    "created_at": "2024-01-01T00:00:00",
    "updated_at": "2024-01-01T00:00:00"
  }
}
```

#### `GET /api/words`
Get all words sorted by query frequency

#### `GET /api/words/<word>`
Get detailed information about a specific word

#### `DELETE /api/words/<word>`
Delete a word from the database

#### `GET /api/health`
Health check endpoint

## 🗂️ Project Structure

```
wordbook/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── .env                  # Environment variables
├── .gitignore
├── LICENSE
├── README.md
├── static/
│   ├── css/
│   │   └── style.css     # Stylesheets
│   └── js/
│       └── app.js        # Frontend JavaScript
├── templates/
│   └── index.html        # Main HTML template
└── database/
    └── words.db          # SQLite database (generated on first run)
```

## 🎯 Usage

1. **Add a Word**: Type an English word in the input field and click "Query/Add"
2. **View Words**: All added words are displayed in descending order by query frequency
3. **Track Progress**: The counter shows how many times you've looked up each word
4. **Delete Words**: Remove words you no longer need

## 🤝 Contributing

Feel free to fork this project and submit pull requests. Any contributions are welcome!

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- LongCat AI for providing the word information API
- Flask framework for the excellent web development experience