# 🤖 AI Mail Assistant

A powerful, local LLM-powered email and messaging assistant. It automatically classifies incoming messages and generates professional replies using **Llama 3.1** via **Ollama**.

![Architecture](https://img.shields.io/badge/Architecture-FastAPI%20%7C%20LangChain-blue)
![AI](https://img.shields.io/badge/AI-Ollama%20%7C%20Llama%203.1-orange)

## ✨ Recent Enhancements
- **🛡️ Approval Center**: Review and whitelist senders. New **"Process"** button allows you to manually trigger AI replies for complex messages.
- **✍️ AI Agent Signature**: Every AI-generated response now includes a custom disclaimer footer to ensure transparency with recipients.
- **📅 Smart Timestamps**: View the exact arrival date and time of pending emails directly on the dashboard.
- **🧭 Dynamic Navigation**: Quick access to **Overview**, **Connection**, **API Doc**, **Helper**, and **Working** (automation stats).
- **🚀 One-Click Helper**: Built-in "How to use this app" guide accessible right from the sidebar.

## 🛠️ Main Features
- **Smart Auto-Reply**: Classifies messages into `AUTO` or `HUMAN` (needs attention).
- **Gmail Integration**: Sync unread inbox messages via Google Cloud Console.
- **WhatsApp Integration**: Real-time replies via Twilio API.
- **Privacy-First AI**: Runs entirely on your machine via Ollama—keeping your data private and costs at zero.

## ⚙️ Setup & Installation
1. **Prerequisites**: [Ollama](https://ollama.com/) (Run `ollama pull llama3.1`).
2. **Install**: `pip install -r requirements.txt`.
3. **Configure**: Add `credentials.json` for Gmail and update `.env` for WhatsApp.
4. **Run**: `python run.py`.

## 🔒 Security
This project prioritizes privacy. All AI processing is performed locally. Sensitive files like `token.json` and credentials are never stored in version control.

---
Made by **[Rudra Gupta](https://rudra-gupta.vercel.app)**
