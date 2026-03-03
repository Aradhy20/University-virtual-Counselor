# TMU Counselor Agent - Setup Guide

This guide will help you configure the "Brain" (Google Gemini) and "Voice" (Deepgram/ElevenLabs) of your AI Agent.

## 1. Setup the Brain (Google Gemini)
You requested to use Google's model instead of OpenAI. This is now configured!

### Step 1: Get the API Key
1.  Go to [Google AI Studio](https://aistudio.google.com/app/apikey).
2.  Click **Create API key**.
3.  Copy the key (starts with `AIza...`).

### Step 2: Add it to the Agent
1.  Open the file `university_counselor/.env` in your project.
2.  Find the line:
    ```bash
    GOOGLE_API_KEY=
    ```
3.  Paste your key after the equals sign.

---

## 2. Fix the Voice Connection
Your current setup failed because the **ElevenLabs API Key** is invalid or missing permissions.

### Step 1: Get a Working ElevenLabs Key
1.  Go to [ElevenLabs](https://elevenlabs.io/app/voice-lab).
2.  Click your profile icon (top right) -> **Profile + API Key**.
3.  Click the "Eye" icon to reveal your key `sk_...`.
4.  Copy it.

### Step 2: Update the Agent
1.  Open `university_counselor/.env`.
2.  Find the line:
    ```bash
    ELEVENLABS_API_KEY=sk_...
    ```
3.  Delete the old key and paste the new one.

---

## 3. Run the Verification
Once you have pasted both keys, run this command to test everything:

```bash
# Test the Conversation Brain
python scripts/test_graph.py

# Test the Voice Connection
python scripts/check_voice.py
```

If both scripts say **SUCCESS**, your agent is ready to take calls!
