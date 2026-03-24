
import logging
import os

try:
    import numpy as np
except ImportError:
    np = None

try:
    from sentence_transformers import SentenceTransformer, util
except ImportError:
    SentenceTransformer = None
    util = None

logger = logging.getLogger("riya.semantic_router")

class SemanticRouter:
    def __init__(self, model_name="paraphrase-multilingual-MiniLM-L12-v2", threshold=0.45):
        """
        Initialize vector-based router.
        Args:
            model_name: HuggingFace model (default: paraphrase-multilingual-MiniLM-L12-v2 for Hindi/Hinglish)
            threshold: Similarity threshold to accept a match (0.0 to 1.0)
        """
        self.threshold = threshold
        try:
            logger.info(f"Loading Semantic Router model: {model_name}...")
            if SentenceTransformer is None or np is None:
                raise ImportError("sentence-transformers or numpy is not installed")
            self.model = SentenceTransformer(model_name)
            logger.info("Semantic Router model loaded.")
        except Exception as e:
            logger.warning(f"Failed to load embedding model: {e}. Semantic routing disabled.")
            self.model = None

        # Define Anchor Sentences (Prototypes) for each Intent
        self.routes = {
            "RAG": [
                # English — Fees & Cost
                "What is the fee structure?",
                "How much does BTech cost?",
                "What are the total fees for MBA?",
                # English — Facilities
                "Is there a hostel facility?",
                "Tell me about the campus",
                "Where is the campus located?",
                "Do you have a library?",
                "Is there a gym on campus?",
                # English — Placements & Career
                "Tell me about placements",
                "What is the highest package?",
                "Which companies come for recruitment?",
                # English — Admission Process (NOT enrollment action)
                "How do I get admission?",
                "What is the admission process?",
                "How do I join TMU?",
                "What is the eligibility criteria?",
                "Can I get admission through CUET?",
                "What documents are required?",
                "When does admission start?",
                "Is there an entrance exam?",
                "Do you accept JEE scores?",
                # English — General Info
                "Do you offer scholarships?",
                "Tell me about the faculty",
                "Why should I choose TMU?",
                "Is TMU a good university?",
                "What courses are available?",
                "Tell me about BTech at TMU",
                "I am interested in BTech details",
                "I want to know about MBA program",
                # Hinglish / Hindi — Info seeking
                "Fees kitni hai?",
                "BTech ka cost kya hai?",
                "Hostel hai kya?",
                "Placement kaisa hai?",
                "College kahan hai?",
                "Scholarship milti hai kya?",
                "Admission kab shuru hoga?",
                "Kya CUET se admission milega?",
                "Faculty kaise hain?",
                "Job lagti hai kya?",
                "Mujhe jankari chahiye",
                "Course ki details batao",
                "Mujhe BTech ke bare mein batao",
                "Kya placements acche hain?",
                "Hostel ki suvidha hai?",
                "Admission kaise lein?",
                "Form kaise bharein?",
                "Admission process kya hai?",
                "Kya entrance exam hota hai?",
                "Documents kya chahiye?",
            ],
            "INTERESTED": [
                # ONLY genuine enrollment/registration actions (not info queries)
                # English
                "I want to apply now",
                "Please register me for admission",
                "I want to take admission in BTech",
                "I want to enroll today",
                "Sign me up for the course",
                "Start my application please",
                "I am ready to apply",
                # Providing personal details (enrollment action signals)
                "My name is Priya and I want to apply",
                "My name is Rahul, I am from Delhi",
                "I am calling from Mumbai, I want admission",
                # Hinglish / Hindi — enrollment action
                "Mujhe admission lena hai abhi",
                "Main apply karna chahta hoon aaj",
                "Registration karna hai mera",
                "Mujhe join karna hai TMU",
                "Admission form bhar do mera",
                "Main admission chahta hoon, form bhej do",
                "Mera naam Karan hai, Delhi se hoon",
            ],
            "CHITCHAT": [
                # English
                "Hello",
                "Hi there",
                "Good morning",
                "Good afternoon",
                "Good evening",
                "Thank you so much",
                "Thanks for the help",
                "Bye",
                "Goodbye",
                "Ok great",
                "That's helpful",
                "How are you?",
                # Hinglish / Hindi
                "Namaste",
                "Kaise ho?",
                "Shukriya",
                "Dhanyavad",
                "Alvida",
                "Theek hai",
                "Accha laga baat karke",
                "Ok bye",
                "Haan ji",
                "Accha",
            ]
        }


        # Pre-compute embeddings for anchors
        self.route_embeddings = {}
        if self.model:
            logger.info("Encoding router anchors...")
            for route, sentences in self.routes.items():
                self.route_embeddings[route] = self.model.encode(sentences, convert_to_tensor=True)
            logger.info(f"Router anchors encoded. Routes: {list(self.routes.keys())}")

    async def route_query(self, query: str) -> str:
        """
        Route query to the most semantically similar intent.
        Returns: "RAG", "INTERESTED", "CHITCHAT", or "UNKNOWN"
        """
        if not self.model:
            logger.warning("Model not loaded, falling back to UNKNOWN")
            return "UNKNOWN"

        query_emb = self.model.encode(query, convert_to_tensor=True)
        
        best_route = "UNKNOWN"
        best_score = -1.0

        for route, anchor_embs in self.route_embeddings.items():
            # Calculate cosine similarity with all anchors for this route
            # util.cos_sim returns a tensor [[score1, score2, ...]]
            scores = util.cos_sim(query_emb, anchor_embs)[0] 
            
            # Take the max score for this route (match closest anchor)
            max_score_for_route = float(np.max(scores.cpu().numpy()))
            
            if max_score_for_route > best_score:
                best_score = max_score_for_route
                best_route = route

        logger.info(f"Semantic Route: '{query}' -> {best_route} (Score: {best_score:.4f})")

        if best_score < self.threshold:
            logger.info(f"Score {best_score:.4f} below threshold {self.threshold}. Returning UNKNOWN.")
            return "UNKNOWN" # Let LLM fallback handle it or default to RAG later

        return best_route
