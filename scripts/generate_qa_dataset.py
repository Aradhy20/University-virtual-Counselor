
import asyncio
import os
import json
import random
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field
from typing import List

# Load env
load_dotenv(r"d:\tmu\university_counselor\.env")

class QueryItem(BaseModel):
    query: str = Field(description="The user query text")
    intent: str = Field(description="The expected intent: RAG, INTERESTED, or CHITCHAT")
    language: str = Field(description="Language of query: Hindi, English, or Hinglish")

class Dataset(BaseModel):
    items: List[QueryItem]

async def generate_dataset(batch_size=50, total_batches=4):
    print(f"--- Generating Synthetic QA Dataset ({batch_size * total_batches} items) ---")
    
    groq_api_key = os.getenv("GROQ_API_KEY")
    llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.8, groq_api_key=groq_api_key)
    
    parser = JsonOutputParser(pydantic_object=Dataset)
    
    prompt = PromptTemplate(
        template="""You are generating a test dataset for a University Admission AI Agent (Aditi).
        Generate {batch_size} diverse user queries mixed in Hindi, English, and Hinglish.
        
        Intents:
        - RAG: Questions about fees, courses, placements, hostel, exams, faculty, transport.
        - INTERESTED: "I want to apply", "Register me", "Admission form kaise bhare", "Mera naam X hai".
        - CHITCHAT: Greetings, thanks, bye, how are you.
        
        Make them realistic, including some spelling mistakes and casual language.
        
        {format_instructions}
        """,
        input_variables=["batch_size"],
        partial_variables={"format_instructions": parser.get_format_instructions()}
    )
    
    chain = prompt | llm | parser
    
    all_data = []
    
    for i in range(total_batches):
        print(f"Generating batch {i+1}/{total_batches}...")
        try:
            result = await chain.ainvoke({"batch_size": batch_size})
            items = result.get("items", [])
            all_data.extend(items)
            print(f"  Got {len(items)} items")
        except Exception as e:
            print(f"  Error in batch {i+1}: {e}")
            
    # Save to JSON
    filename = "qa_dataset_synthetic.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(all_data, f, indent=2, ensure_ascii=False)
        
    print(f"\n[DONE] Generated {len(all_data)} items. Saved to {filename}")

if __name__ == "__main__":
    asyncio.run(generate_dataset())
