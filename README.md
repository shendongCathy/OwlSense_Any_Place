# OwlSense_Any_Place

OwlSense_Any_Place is a **campus-oriented emotional companion prototype**, and an early pilot of **OwlSense (OS! Any Place)** — an AI-based emotional support platform.

This project was built as an experimental campus version to explore how AI can provide **low-barrier, non-judgmental emotional support** for students.  
The system emphasizes *listening*, *gentle reflection*, and *emotional organization*, rather than giving instructions or replacing professional help.

---

## 🌐 Demo
- Live site (Render):  
  https://owlsense-any-place.onrender.com

> Note: This service is deployed on Render (free tier).  
> The first request after inactivity may take some time due to cold start.

---

## 🦉 What This Prototype Does
- Provides an AI chat interface for students to express emotions
- Encourages users to talk at their own pace (no pressure to finish everything at once)
- Includes **clear safety reminders**, guiding users to seek trusted adults or professionals when necessary
- Designed specifically for **campus emotional support scenarios**

This prototype **does not replace teachers, counselors, or therapists**.  
It is meant to be a *supportive first step* for emotional expression.

---

## 🧱 Tech Stack
- **Backend:** Python 3, Flask
- **AI:** Google AI Studio / Gemini API
- **Deployment:** Render (Web Service)
- **Frontend:** Web-based UI (lightweight, no installation required)

---

## 🚀 Local Development
```bash
git clone https://github.com/shendongCathy/OwlSense_Any_Place.git
cd OwlSense_Any_Place
pip install -r requirements.txt

export GEMINI_API_KEY="YOUR_API_KEY"
python app.py

