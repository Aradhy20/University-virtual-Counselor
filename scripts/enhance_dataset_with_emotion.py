import asyncio
import json
import os
import sys
from groq import AsyncGroq
from dotenv import load_dotenv

sys.path.append(r"c:\tmu\university_counselor")
load_dotenv()

MODEL = "llama-3.3-70b-versatile"

PROMPT = """You are an emotion and intent classifier for a university counselor dataset.
Based on the text, classify the user's emotion into EXACTLY ONE of these categories:
- Neutral
- Confused
- Excited
- Urgent
- Frustrated

Respond with ONLY the category word, nothing else. No punctuation.
"""

async def classify_emotion(client, query):
    try:
        completion = await client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": PROMPT},
                {"role": "user", "content": f"Text: {query}"}
            ],
            temperature=0.0,
            max_tokens=10
        )
        val = completion.choices[0].message.content.strip()
        # Clean it
        for e in ["Neutral", "Confused", "Excited", "Urgent", "Frustrated"]:
            if e.lower() in val.lower():
                return e
        return "Neutral" # Fallback
    except Exception as e:
        print(f"Error on query '{query[:20]}': {e}")
        return "Neutral"

async def main():
    print(f"--- Enhancing Dataset with Emotion ({MODEL}) ---")
    
    file_path = r"c:\tmu\university_counselor\qa_dataset_synthetic.json"
    
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    api_key = os.getenv("GROQ_API_KEY")
    client = AsyncGroq(api_key=api_key)
    
    total = len(data)
    
    # Process in batches to respect rate limits
    batch_size = 20
    for i in range(0, total, batch_size):
        batch = data[i:i+batch_size]
        print(f"Processing batch {i} to {min(i+batch_size, total)}...")
        
        # Create tasks for this batch
        tasks = []
        for item in batch:
            tasks.append(classify_emotion(client, item["query"]))
            
        results = await asyncio.gather(*tasks)
        
        # Apply results
        for idx, emotion in enumerate(results):
            batch[idx]["emotion"] = emotion
            
        # Slight delay to avoid hitting LLM limits
        await asyncio.sleep(1.5)
        
    # Overwrite the original
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        
    print(f"\n[Done] Successfully added 'emotion' feature to {total} items!")

if __name__ == "__main__":
    asyncio.run(main())
