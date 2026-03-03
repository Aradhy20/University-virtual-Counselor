import asyncio
import os
import sys
import pyaudio
import wave
from dotenv import load_dotenv

# Add parent to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.voice import VoiceService
from deepgram import DeepgramClient

# Load Env
load_dotenv(r"d:\tmu\university_counselor\.env")

# Audio Config
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
CHUNK = 1024
RECORD_SECONDS = 5 # Simple 5s recording for proof of concept

def record_audio(filename="input.wav"):
    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT, channels=CHANNELS,
                    rate=RATE, input=True,
                    frames_per_buffer=CHUNK)
    
    print("* Recording (Speak now for 5s)...")
    frames = []
    
    for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
        data = stream.read(CHUNK)
        frames.append(data)
        
    print("* Recording Complete.")
    stream.stop_stream()
    stream.close()
    p.terminate()
    
    wf = wave.open(filename, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()

async def transcribe_audio(filename="input.wav"):
    print("* Transcribing with Deepgram...")
    dg_key = os.getenv("DEEPGRAM_API_KEY")
    deepgram = DeepgramClient(dg_key)
    
    with open(filename, "rb") as audio:
        buffer_data = audio.read()
        
    payload = {"buffer": buffer_data}
    options = {
        "smart_format": True,
        "model": "nova-2",
        "language": "en-IN"
    }
    response = deepgram.listen.prerecorded.v("1").transcribe_file(payload, options)
    transcript = response["results"]["channels"][0]["alternatives"][0]["transcript"]
    return transcript

def play_audio_stream(audio_stream):
    print("* Playing Response (ElevenLabs)...")
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paFloat32, # ElevenLabs usually sends PCM/mp3
                    channels=1,
                    rate=44100, # ElevenLabs default
                    output=True)
    
    # This is tricky without decoding mp3 stream on the fly.
    # For simplicity, we might save to file and play via OS command or use pydub + simpleaudio
    # Streaming playback requires ffmpeg decoding usually.
    # We'll skip complex streaming playback in this simple script and save/play file.
    pass

async def conversation_loop():
    print("--- Aditi Local Voice Chat ---")
    
    # Initialize Groq Direct (Bypassing LangChain to avoid conflicts)
    from groq import Groq
    groq_key = os.getenv("GROQ_API_KEY")
    if not groq_key:
        print("ERROR: GROQ_API_KEY missing.")
        return
    client = Groq(api_key=groq_key)
    
    voice = VoiceService()
    
    # Simple Aditi Persona for Local Test
    system_prompt = "You are Aditi, a senior admission counselor at TMU. Answer briefly (1-2 sentences). Be warm and professional."
    
    while True:
        input("Press Enter to Speak (or Ctrl+C to quit)...")
        record_audio("temp_input.wav")
        
        try:
            user_text = await transcribe_audio("temp_input.wav")
            print(f"You said: {user_text}")
            
            if not user_text.strip():
                print("No speech detected.")
                continue
                
            print("Aditi is thinking...")
            
            # Direct Generation
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_text}
                ],
                temperature=0.3,
                max_tokens=150
            )
            ai_response = completion.choices[0].message.content
            print(f"Aditi: {ai_response}")
            
            print("Generating Voice...")
            # Save to file to ensure playback works without streaming complexity
            audio = voice.eleven.generate(
                text=ai_response,
                voice="xAmuYLyEOAjjvwszDZPp",
                model="eleven_turbo_v2"
            )
            
            output_file = "temp_response.mp3"
            with open(output_file, "wb") as f:
                for chunk in audio:
                    if chunk:
                        f.write(chunk)
                        
            print(f"* Playing {output_file}...")
            # Use OS default player for reliability
            os.system(f"start {output_file}")
            
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(conversation_loop())
