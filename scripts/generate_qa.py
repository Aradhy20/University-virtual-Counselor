import random

# Sample lists of courses
tech_courses = ["B.Tech CSE", "B.Tech Mechanical", "BCA", "MCA", "B.Sc Computing"]
medical_courses = ["MBBS", "BDS", "BPT", "BSc Nursing", "MSc Medical"]
management_courses = ["BBA", "MBA", "B.Com"]
other_courses = ["BA LLB", "B.Ed", "B.Sc Agriculture", "B.Pharma"]
all_courses = tech_courses + medical_courses + management_courses + other_courses

# General topics
hostel_queries = [
    "What is the hostel fee?",
    "Are AC hostels available?",
    "Is the hostel on campus?",
    "What kind of food is provided in the hostel?"
]

transport_queries = [
    "Is transport available from Moradabad city?",
    "What is the bus fee?",
    "Do you provide buses for Delhi?"
]

placement_queries = [
    "What is the highest package?",
    "Who are the top recruiters?",
    "Do we get placement support?",
    "What is the average package for CSE?"
]

admission_queries = [
    "What is the admission procedure?",
    "Do I need to give an entrance exam?",
    "What are the eligibility criteria?",
    "Can I apply online?"
]

# Generate Q&A
qa_pairs = []

# Generate course-specific questions (Fee, Duration, Eligibility)
for course in all_courses:
    # 1. Fee
    qa_pairs.append(f"Q: What is the fee structure for {course}?\nA: The fee for {course} varies depending on the specialisation, but typically ranges between 50,000 to 1,50,000 per year. For precise details, please let me know your specific branch of interest.")
    qa_pairs.append(f"Q: How much does {course} cost?\nA: {course} fees are generally structured on a per-semester basis. Please allow me to check the exact amount for this year for {course}.")
    qa_pairs.append(f"Q: Are there any scholarships available for {course}?\nA: Yes, TMU offers merit-based scholarships for {course} based on your 12th percentage or entrance exam scores.")
    
    # 2. Duration / Eligibility
    qa_pairs.append(f"Q: What is the duration of the {course} program?\nA: Duration depends on the level. Generally, Bachelor's programs are 3-4 years, and Master's are 2 years. {course} follows the standard UGC guidelines.")
    qa_pairs.append(f"Q: What are the eligibility criteria for {course}?\nA: To apply for {course}, you must have completed the prerequisite qualification (10+2 for UG, Graduation for PG) with a minimum of 50% marks from a recognized board or university.")
    qa_pairs.append(f"Q: Can I get direct admission in {course}?\nA: Yes, TMU provides admission based on merit, though specific professional courses like {course} might require an entrance exam or interview.")

    # 3. Placements
    qa_pairs.append(f"Q: How are the placements for {course}?\nA: Placements for {course} are excellent at TMU. Top companies visit the campus every year for recruitment with great packages.")

# Generate General questions
for _ in range(200):
    q = random.choice(hostel_queries)
    qa_pairs.append(f"Q: {q}\nA: TMU offers fantastic hostel facilities including AC and Non-AC rooms with Wi-Fi, 24/7 security, and hygienic mess food. Fees vary based on the room type.")

for _ in range(100):
    q = random.choice(transport_queries)
    qa_pairs.append(f"Q: {q}\nA: TMU provides a robust transport facility with buses running across Moradabad and to nearby towns to ensure complete safety and convenience for students.")

for _ in range(200):
    q = random.choice(placement_queries)
    qa_pairs.append(f"Q: {q}\nA: TMU has a great track record with the highest package reaching 60 LPA. Top recruiters include TCS, Infosys, Wipro, and many multinational companies.")

for _ in range(200):
    q = random.choice(admission_queries)
    qa_pairs.append(f"Q: {q}\nA: The admission process at TMU is straightforward. You can apply easily online or visit the campus in Moradabad. Admission is primarily merit-based.")

# More varied queries to reach ~1000
course_comparisons = [
    "Which is better, BBA or B.Com?",
    "Should I choose B.Tech CSE or BCA?",
    "Is MBBS better than BDS?",
    "What is the difference between MBA and PGDM?"
]

for _ in range(150):
    q = random.choice(course_comparisons)
    qa_pairs.append(f"Q: {q}\nA: Both courses offer great career opportunities. At TMU, our expert faculty will guide you to choose the program that perfectly aligns with your career goals and interests.")

random.shuffle(qa_pairs)

with open(r"c:\tmu\university_counselor\university details\synthetic_qa_dataset.txt", "w", encoding="utf-8") as f:
    f.write("========== TMU 1000 ADMISSION QA DATASET ==========\n\n")
    for i, qa in enumerate(qa_pairs, 1):
        f.write(f"--- QA {i} ---\n{qa}\n\n")

print(f"Generated {len(qa_pairs)} QA pairs!")
