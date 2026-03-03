
import json
import os
from collections import Counter
from datetime import datetime

LOG_FILE = r"d:\tmu\university_counselor\data\conversation_logs.jsonl"
OUTPUT_FILE = r"d:\tmu\university_counselor\data\rag_feedback_report.md"

def generate_rag_report():
    print("Analyzing RAG Performance...")
    
    if not os.path.exists(LOG_FILE):
        print("No logs found.")
        return

    doc_usage = Counter()
    successful_docs = Counter()
    total_queries = 0
    leads_captured = 0

    with open(LOG_FILE, "r", encoding="utf-8") as f:
        for line in f:
            try:
                data = json.loads(line)
                total_queries += 1
                
                # Check if this interaction led to a lead capture (Implicit Success)
                is_success = bool(data.get("lead_updates"))
                if is_success:
                    leads_captured += 1
                
                sources = data.get("source_ids", [])
                for src in sources:
                    doc_usage[src] += 1
                    if is_success:
                        successful_docs[src] += 1
                        
            except: pass

    # Generate Markdown Report
    report = f"# 📚 RAG Knowledge Base Feedback\nGenerated: {datetime.now()}\n\n"
    report += f"**Total Queries Analyzed**: {total_queries}\n"
    report += f"**Successful Conversations**: {leads_captured}\n\n"
    
    report += "## 🏆 Top Performing Documents (Used in Lead Capture)\n"
    if successful_docs:
        for doc, count in successful_docs.most_common(10):
            report += f"- **{count}** wins: `{doc}`\n"
    else:
        report += "(No successful lead captures recorded yet)\n"
        
    report += "\n## 📉 Most Retrieved Documents (General Usage)\n"
    if doc_usage:
        for doc, count in doc_usage.most_common(10):
            report += f"- **{count}** retrievals: `{doc}`\n"
    else:
        report += "(No documents retrieved yet)\n"

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(report)
        
    print(f"RAG Feedback Report saved to: {OUTPUT_FILE}")
    print("-" * 40)
    print(report)
    print("-" * 40)

if __name__ == "__main__":
    generate_rag_report()
