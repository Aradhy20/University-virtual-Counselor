# TMU Admission Counselor AI

Welcome to the **Teerthanker Mahaveer University (TMU) Admission Counselor AI** project. This is a comprehensive, voice-first AI agent designed to assist prospective university students with admission inquiries, fee details, eligibility criteria, and more. 

The application utilizes a real-time voice streaming architecture integrating Deepgram for Speech-to-Text (STT) and ElevenLabs for Text-to-Speech (TTS), powered by a FastAPI backend. It also features a conversational AI brain powered by Google Gemini and specialized RAG (Retrieval-Augmented Generation) for precise university knowledge.

## 🌟 Key Features

- **Real-Time Voice Streaming:** WebSockets interface with Twilio and LiveKit for ultra-low latency conversational AI.
- **Bilingual Support:** Understands and speaks in both English and Hindi.
- **Emotional Intelligence Tracking:** Detects user mood and adapts response style and TTS voice attributes dynamically.
- **Hallucination Guards:** Built-in safeguards to ensure the agent only speaks factual information based on the TMU knowledge base.
- **Lead Capture:** Automatically captures user names, phone numbers, courses, and cities during conversations and exports them.
- **RAG & Semantic Routing:** Accurately routes user queries to specialized AI agents for admissions, fees, and general queries.

## 🛠️ Technology Stack

- **Backend:** FastAPI (Python), Uvicorn, WebSockets
- **AI / LLM:** Google Gemini via CrewAI
- **Speech-to-Text (STT):** Deepgram (Nova-2 API)
- **Text-to-Speech (TTS):** ElevenLabs (Streaming API)
- **Vector Database:** FAISS
- **Frontend Dashboard:** React, Vite, TailwindCSS
- **Telephony / Voice Hooks:** Twilio, LiveKit

## 🚀 Getting Started

To get the application up and running locally, refer to the [Setup Guide](setup_guide.md).

### Quick Start
1. Ensure you have your `GOOGLE_API_KEY`, `ELEVENLABS_API_KEY`, and `DEEPGRAM_API_KEY` configured in your `.env` file.
2. Install Python dependencies: `pip install -r requirements.txt`
3. Start the Backend server: `uvicorn app.main:app --reload`
4. Start the Frontend dashboard: `cd frontend && npm run dev`

### Project Structure
- `app/` - The core FastAPI application (routers, services, and AI logic)
- `data/` - University knowledge bases, FAISS index, and exported conversation logs
- `frontend/` - React-based dashboard for system monitoring
- `scripts/` - Utility scripts for testing TTS, APIs, and tunnel deployments
- `README_API.md` - Documentation for interacting directly via the text API endpoints

## 🧪 Testing

We provide individual scripts to test different components of the system:
- `python scripts/check_voice.py` - Tests the Speech/TTS integration.
- `python scripts/test_retrieval_robust.py` - Tests RAG retrieval accuracy.
- `python scripts/test_api_functional.py` - Tests the text-based endpoint interactions.

---
*Built for Teerthanker Mahaveer University (TMU).*
