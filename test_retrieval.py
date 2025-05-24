import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent))
from agents.retrieval import RetrievalAgent
import os

PROCEDURES_JSON_FOR_TEST = str(Path(__file__).resolve().parent.parent / "data" / "procedures.json")

def test_retrieval():
    print(f"Testing RetrievalAgent with procedures from: {PROCEDURES_JSON_FOR_TEST}")
    if not os.path.exists(PROCEDURES_JSON_FOR_TEST):
        print(f"Error: {PROCEDURES_JSON_FOR_TEST} not found. Skipping test.")
        return
    try:
        agent = RetrievalAgent(PROCEDURES_JSON_FOR_TEST)
    except Exception as e:
        print(f"Error initializing RetrievalAgent: {e}")
        return
    test_queries = [
        "je veux souscrire à internet",
        "changer de titulaire",
        "انا نحب نشترك في الانترنت",
        "résiliation abonnement",
        "comment avoir la fibre optique",
        "ما هي الوثائق لتغيير الملكية"
    ]
    for query in test_queries:
        print(f"\nQuery: \"{query}\"")
        results = agent.search_procedures(query, top_k=3)
        if results:
            for result in results:
                print(f"  - Found Procedure: \"{result.procedure}\" (Source: {result.source})")
        else:
            print("  - No relevant procedures found.")

if __name__ == "__main__":
    print("--- Running Retrieval Agent Test ---")
    test_retrieval()
    print("--- Retrieval Agent Test Finished ---")