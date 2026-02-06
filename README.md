# HR Call AI – Automated Voice Interview System

HR Call AI is an **automated voice-based HR interview platform** built with **Django, Twilio, Speech-to-Text, and LLMs**. It conducts real-time phone interviews, dynamically adapts questions based on candidate responses, evaluates answers using AI, and generates a final HR decision with scoring and summaries.

This project is designed to **reduce HR screening workload** by automating first-round interviews while maintaining structured, fair, and experience-aware evaluation.

---

## 🚀 Features

* 📞 **Automated Phone Interviews** using Twilio
* 🗣 **Speech-to-Text (STT)** with AssemblyAI
* 🤖 **Dynamic AI Interviewer** (LLM-powered)
* 🔁 Real-time adaptive questions based on candidate answers
* 📊 **AI-based Scoring & Evaluation** (Communication + Justification)
* 🧠 Experience-aware evaluation (Junior / Mid / Senior)
* 🚩 Red-flag detection (refusals, vague answers, insufficient detail)
* 📝 Final HR Summary & Hiring Decision
* 🧾 Full conversation stored per candidate

---

## 🏗 Tech Stack

* **Backend**: Django (Python)
* **Voice Calls**: Twilio
* **Speech to Text**: AssemblyAI
* **LLM Provider**: Groq (LLaMA 3.1)
* **Database**: Django ORM (SQLite / PostgreSQL)
* **Tunneling (Dev)**: Ngrok

---

## 📂 Project Structure

```
interview/
├── urls.py                # App routes
├── views.py               # Twilio voice flow & call UI
├── models.py              # Candidate model
├── services/
│   ├── speech_to_text.py  # Audio transcription
│   ├── ai_analysis.py     # Interview logic, scoring, evaluation
│   └── twilio_service.py  # Call initiation
└── templates/
    └── interview/
        └── call_ui.html   # Simple call trigger UI
```

---

## 🔁 Interview Flow

1. HR initiates a call from the web UI
2. Candidate receives a phone call
3. AI introduces the interview
4. AI asks dynamic questions (minimum enforced)
5. Candidate answers via voice
6. Answers are transcribed (STT)
7. AI adapts next question in real time
8. Interview ends automatically when enough data is collected
9. AI evaluates all answers together
10. Final score, decision, red flags, and HR summary are saved

---

## 🧠 AI Evaluation Logic

### Per Question

* **Communication Score** (0–10)
* **Justification Score** (0–10)
* Real-world signals are rewarded (tools, production systems, ownership)
* Explicit refusals score 0

### Final Output

* **Final Score**: 0–100 (normalized)
* **Decision**:

  * STRONG HIRE (≥ 70)
  * CONSIDER (≥ 55)
  * LESS CONSIDER (≥ 40)
  * REJECT (< 40)
* **HR Summary**: Auto-generated explanation
* **Red Flags**: Detected risks or refusals

---

## ⚙️ Environment Variables

Create a `.env` file or configure environment variables:

```
DJANGO_SECRET_KEY=your_secret_key
DEBUG=True

TWILIO_SID=your_twilio_sid
TWILIO_AUTH=your_twilio_auth_token
TWILIO_NUMBER=your_twilio_phone_number

ASSEMBLYAI_API_KEY=your_assemblyai_key
GROQ_API_KEY=your_groq_api_key

BASE_URL=https://your-ngrok-url
```

---

## ▶️ Setup & Run

### 1️⃣ Clone Repository

```
git clone https://github.com/your-username/hr-call-ai.git
cd hr-call-ai
```

### 2️⃣ Create Virtual Environment

```
python -m venv venv
source venv/bin/activate
```

### 3️⃣ Install Dependencies

```
pip install -r requirements.txt
```

### 4️⃣ Migrate Database

```
python manage.py makemigrations
python manage.py migrate
```

### 5️⃣ Run Server

```
python manage.py runserver
```

### 6️⃣ Expose with Ngrok (Required for Twilio)

```
ngrok http 8000
```

Update `BASE_URL` and Twilio webhook URL accordingly.

---

## 🌐 API Endpoints

| Endpoint  | Method   | Description          |
| --------- | -------- | -------------------- |
| `/`       | GET/POST | Call initiation UI   |
| `/voice/` | POST     | Twilio voice webhook |

---

## 🧪 Notes

* Minimum number of questions is enforced before ending interview
* Very short or warm-up answers are ignored
* Interview adapts difficulty based on candidate responses
* Built for **spoken interviews**, not written ones

---

## 📌 Future Improvements

* Admin dashboard for HR review
* Multi-language support
* Resume-based question seeding
* Interview analytics & comparison
* WebSocket-based real-time monitoring

---


**Built with ❤️ to automate and improve real-world HR screening.**
