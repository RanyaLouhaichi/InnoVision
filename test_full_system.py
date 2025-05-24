import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent))
from agents.orchestrator import MainOrchestrator, PROCEDURES_DEFAULT_PATH
from models.schemas import UserQuery
import uuid
import os

PROCEDURES_JSON_FOR_TEST = str(Path(__file__).resolve().parent.parent / "data" / "procedures.json")
if not os.path.exists(PROCEDURES_JSON_FOR_TEST):
    PROCEDURES_JSON_FOR_TEST = PROCEDURES_DEFAULT_PATH 

dotenv_path = Path(__file__).resolve().parent.parent / '.env'
if dotenv_path.exists():
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=dotenv_path)
    print(f"Loaded .env from {dotenv_path}")
else:
    print(f"Warning: .env file not found at {dotenv_path}")

def test_fiber_subscription():
    print("\n🧪 Testing Fiber Subscription Flow")
    print("-" * 40)
    if not os.path.exists(PROCEDURES_JSON_FOR_TEST):
        print(f"Error: {PROCEDURES_JSON_FOR_TEST} not found. Skipping test.")
        return
    try:
        orchestrator = MainOrchestrator(PROCEDURES_JSON_FOR_TEST)
    except Exception as e:
        print(f"Error initializing MainOrchestrator: {e}")
        return
    user_id = str(uuid.uuid4())
    test_inputs = [
        "Je veux souscrire à internet",
        "Je voudrais la Fibre optique s'il vous plait",
        "Mon adresse est Tunis, Menzah 6, rue des Jasmins",
        "Je préfère le prélèvement automatique comme mode de paiement"
    ]
    for i, input_text in enumerate(test_inputs):
        print(f"\n👤 Input {i+1} (User: {user_id}): \"{input_text}\"")
        response = orchestrator.process_user_input(text_input=input_text, user_id=user_id)
        print(f"🤖 Assistant: \"{response.response_text}\"")
        if response.todo_list:
            print("📋 Documents/Infos à préparer:")
            for item in response.todo_list:
                print(f"   - {item}")
        if response.missing_context:
            print(f"❓ Contexte manquant: {', '.join(response.missing_context)}")
        if response.next_question:
            print(f"❓ Question suivante: {response.next_question}")
        if response.is_complete:
            print("\n✅ Procédure marquée comme complète!")
            break 
        elif not response.next_question and not response.is_complete:
            print("⚠️  Le flux semble bloqué (pas de prochaine question, pas complet).")
            break

def test_arabic_input():
    print("\n🧪 Testing Arabic Input")
    print("-" * 40)
    if not os.path.exists(PROCEDURES_JSON_FOR_TEST):
        print(f"Error: {PROCEDURES_JSON_FOR_TEST} not found. Skipping test.")
        return
    try:
        orchestrator = MainOrchestrator(PROCEDURES_JSON_FOR_TEST)
    except Exception as e:
        print(f"Error initializing MainOrchestrator: {e}")
        return
    user_id = str(uuid.uuid4())
    arabic_queries = [
        "نحب نشترك في الانترنت",
        "باش نبدل التيتولير متاع الخط",
        "نحب نقص الاشتراك متاعي"
    ]
    for query_text in arabic_queries:
        print(f"\n👤 Arabic Input (User: {user_id}): \"{query_text}\"")
        response = orchestrator.process_user_input(text_input=query_text, user_id=user_id)
        print(f"🤖 Assistant: \"{response.response_text}\"")
        if response.next_question:
            print(f"❓ Question suivante: {response.next_question}")

def test_all_procedures_recognition():
    print("\n🧪 Testing All Procedures Recognition (Intent)")
    print("-" * 40)
    if not os.path.exists(PROCEDURES_JSON_FOR_TEST):
        print(f"Error: {PROCEDURES_JSON_FOR_TEST} not found. Skipping test.")
        return
    try:
        orchestrator = MainOrchestrator(PROCEDURES_JSON_FOR_TEST)
    except Exception as e:
        print(f"Error initializing MainOrchestrator: {e}")
        return
    test_queries_for_intent = {
        "Souscription Internet Fixe": "Je veux un nouvel abonnement internet pour la maison.",
        "Changement de Titulaire": "Comment changer le nom sur le contrat de ma ligne fixe ?",
        "Résiliation d'Abonnement": "Je souhaite résilier mon abonnement internet.",
        "Transfert de Ligne (Déménagement)": "Je déménage, comment transférer ma ligne ADSL ?",
        "Partage de Connexion Mobile": "Comment activer le partage de connexion sur mon mobile ?"
    }
    for procedure_name, query in test_queries_for_intent.items():
        print(f"\n👤 Testing for intent related to \"{procedure_name}\" with query: \"{query}\"")
        user_id = str(uuid.uuid4())
        response = orchestrator.process_user_input(text_input=query, user_id=user_id)
        print(f"🤖 Assistant: \"{response.response_text}\"")
        if response.next_question:
            print(f"   ➡️ Assistant asks for: {response.next_question}")
        elif response.is_complete:
             print(f"   ➡️ Assistant considers it complete with ToDo: {response.todo_list}")
        else:
            print(f"   ➡️ Assistant response does not ask for more info, nor is it complete.")

if __name__ == "__main__":
    print("--- Running Full System Orchestrator Tests (CLI Style) ---")
    test_arabic_input()
    print("\n--- Full System Orchestrator Tests Finished ---")
    print("Note: 'test_fiber_subscription' and 'test_all_procedures_recognition' can be lengthy due to multiple LLM calls.")
    print("Uncomment them in the script if you wish to run them.")