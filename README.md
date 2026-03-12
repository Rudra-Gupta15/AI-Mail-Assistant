# 🤖 AI Mail Assistant

A powerful, local LLM-powered email and messaging assistant. It automatically classifies incoming messages and generates professional replies using **Llama 3.1** via **Ollama**.

![Architecture](https://img.shields.io/badge/Architecture-FastAPI%20%7C%20LangChain-blue)
![AI](https://img.shields.io/badge/AI-Ollama%20%7C%20Llama%203.1-orange)

## ✨ Features

- **🚀 Smart Auto-Reply**: Automatically classifies messages into `AUTO` (safe for AI reply) or `HUMAN` (needs attention).
- **📧 Gmail Integration**: Connect your Gmail inbox via OAuth2 to auto-process and thread replies.
- **💬 WhatsApp Integration**: Real-time auto-replies via Twilio WhatsApp API.
- **🧠 Local AI**: Runs entirely on your machine using Ollama—keeping your data private and costs at zero.
- **🎨 Premium Dashboard**: A modern, easy-to-use web interface for monitoring and manual testing.

## 🛠️ Setup & Installation

### 1. Prerequisites
- Python 3.9+ 
- [Ollama](https://ollama.com/) (Download and run `ollama pull llama3.1`)

### 2. Installation
```bash
# Create a virtual environment
python -m venv venv
source venv/bin/activate # On Windows: .\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configuration
Create a `.env` file in the root:
```env
APP_NAME="AI Mail Assistant"
DEFAULT_MODEL="llama3.1"

# For WhatsApp (Optional)
TWILIO_ACCOUNT_SID=your_sid
TWILIO_AUTH_TOKEN=your_token
TWILIO_WHATSAPP_NUMBER=whatsapp:+...
```

## 🚀 Running the Assistant

Execute the main script:
```bash
python run.py
```
Open **http://localhost:8000** in your browser to access the dashboard.

## 📁 Project Structure

- `app/api`: FastAPI routes and webhooks.
- `app/services`: Core logic for Gmail, WhatsApp, and AI processing.
- `app/models`: Pydantic schemas for data validation.
- `app/utils`: Prompt templates and utility functions.
- `config`: Application settings and environment management.

## 🔒 Security Note
This project uses OAuth2 and local AI. Your `credentials.json`, `token.json`, and `.env` files contain sensitive information and are excluded via `.gitignore`. **Never commit them to GitHub.**

---
Built with ❤️ for productive communication.
