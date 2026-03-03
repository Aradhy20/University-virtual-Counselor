
import json
import csv
import os
from collections import Counter
from datetime import datetime
import re

# Paths
LOG_FILE = r"d:\tmu\university_counselor\data\conversation_logs.jsonl"
MISSED_FILE = r"d:\tmu\university_counselor\data\missed_queries.csv"
REPORT_FILE = r"d:\tmu\university_counselor\data\learning_report.md"

def analyze_missed_queries():
    """Reads missed queries and finds common patterns (simple clustering)."""
    if not os.path.exists(MISSED_FILE):
        return "No missed queries logged yet."

    queries = []
    with open(MISSED_FILE, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader, None) # Skip header
        for row in reader:
            if len(row) >= 2:
                queries.append(row[1])

    if not queries:
        return "No missed queries found."

    # Simple keyword extraction (Naive clustering)
    words = []
    stopwords = {"is", "the", "what", "how", "to", "in", "for", "of", "a", "are", "i", "can", "you", "me", "tell", "tmu"}
    for q in queries:
        # Tokenize
        tokens = re.findall(r'\w+', q.lower())
        words.extend([w for w in tokens if w not in stopwords and len(w) > 3])

    common_themes = Counter(words).most_common(5)
    
    report = "### 🚨 Knowledge Gaps (Missed Queries)\n"
    report += f"Total Missed: {len(queries)}\n\n"
    report += "**Top Recurring Keywords:**\n"
    for word, count in common_themes:
        report += f"- **{word}**: {count} occurrences\n"
    
    report += "\n**Recent Missed Queries:**\n"
    for q in queries[-5:]:
        report += f"- {q}\n"
        
    return report

def analyze_conversation_quality():
    """Analyzes conversation logs for success/failure signals."""
    if not os.path.exists(LOG_FILE):
        return "No conversation logs found."

    total = 0
    intent_counts = Counter()
    low_confidence = 0
    leads_captured = 0

    with open(LOG_FILE, "r", encoding="utf-8") as f:
        for line in f:
            try:
                data = json.loads(line)
                total += 1
                intent_counts[data.get("intent", "unknown")] += 1
                if data.get("confidence_score", 1.0) < 0.65:
                    low_confidence += 1
                if data.get("lead_updates"):
                    leads_captured += 1
            except: pass

    report = "### 📊 Conversation Performance\n"
    report += f"- **Total Turns**: {total}\n"
    report += f"- **Leads Captured**: {leads_captured}\n"
    report += f"- **Low Confidence Rate**: {((low_confidence/total)*100):.1f}% ({low_confidence}/{total})\n\n"
    
    report += "**Intent Distribution:**\n"
    for intent, count in intent_counts.items():
        report += f"- {intent}: {count}\n"

    return report

def generate_report():
    print("Running Self-Learning Analysis...")
    
    missed_report = analyze_missed_queries()
    quality_report = analyze_conversation_quality()
    
    final_report = f"# 🧠 Aditi Self-Learning Report\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
    final_report += quality_report + "\n\n" + missed_report
    
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write(final_report)
        
    print(f"Report generated: {REPORT_FILE}")
    print("-" * 40)
    print(final_report)
    print("-" * 40)

if __name__ == "__main__":
    generate_report()
