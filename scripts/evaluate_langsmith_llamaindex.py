import os
import json
import logging
from dotenv import load_dotenv

# Set up LangSmith strictly
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"
# Let it pick up API Key and Project from .env if possible
load_dotenv(r"c:\tmu\university_counselor\.env")

from llama_index.llms.groq import Groq
from langsmith import traceable

# ---------------------------------------------------------
# Test Script
# ---------------------------------------------------------

DATASET_PATH = r"c:\tmu\university_counselor\qa_dataset_synthetic.json"
MODEL_NAME = "llama-3.3-70b-versatile"

ACER_PROMPT = """You are Aditi, the sweet and professional Senior Admission Counselor at TMU.
A student is asking a question. Your response MUST follow the A.C.E.R. model:
1. ACKNOWLEDGE: Warmly acknowledge their question.
2. COUNSEL: Provide a direct, factual answer (make it up safely if you must, but sound authoritative about university topics).
3. EMPATHIZE: Show you care about their journey.
4. REDIRECT: End with a friendly follow-up question.

Student Emotion Detected: {emotion}
Student Question: {query}

Aditi's Response:"""

from llama_index.core import Settings
from llama_index.core.prompts import PromptTemplate

@traceable(name="Evaluate_Aditi_LlamaIndex")
def process_llama_index_query(llm, query, emotion, template):
    fmt_prompt = template.format(query=query, emotion=emotion)
    response = llm.complete(fmt_prompt)
    return str(response).strip()

def main():
    print(f"--- Starting LlamaIndex Evaluation mapped to LangSmith ---")
    
    # 1. Setup Groq through LlamaIndex
    api_key = os.getenv("GROQ_API_KEY")
    llm = Groq(model=MODEL_NAME, api_key=api_key, temperature=0.2)
    Settings.llm = llm
    
    # 2. Setup Prompt Template
    template = PromptTemplate(ACER_PROMPT)
    
    # 3. Load Dataset
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    # Take just 5 random samples to evaluate the tracing
    import random
    random.seed(101)
    samples = random.sample(data, 5)
    
    # 4. Process
    print(f"Evaluating {len(samples)} questions through LlamaIndex. Traces will appear in LangSmith Project: {os.getenv('LANGCHAIN_PROJECT')}...\n")
    
    for i, item in enumerate(samples):
        query = item.get("query", "")
        emotion = item.get("emotion", "Neutral")
        
        print(f"[{i+1}/5] Student [{emotion}]: {query}")
        
        # Format prompt
        fmt_prompt = template.format(query=query, emotion=emotion)
        
        response = process_llama_index_query(llm, query, emotion, template)
        
        print(f"      Aditi: {response}\n")
        
    print("Done! Check your LangSmith dashboard to see the full LlamaIndex traces.")

if __name__ == "__main__":
    main()
