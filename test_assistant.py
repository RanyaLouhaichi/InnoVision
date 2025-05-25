import uuid
from pathlib import Path
from agents.orchestrator import MainOrchestrator
from models.schemas import ProcedureSchema, UserQuery, AgentResponse

# Configuration du logging
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def charger_procedure_test():
    """Charge une procédure réelle depuis procedures.json"""
    data_dir = Path(__file__).resolve().parent / "data"
    procedures_path = data_dir / "procedures.json"
    
    if not procedures_path.exists():
        raise FileNotFoundError(f"Fichier {procedures_path} non trouvé")
    
    import json
    with open(procedures_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # Prendre la première procédure pour le test
    procedure_data = data["procedures"][0]
    return ProcedureSchema(**procedure_data)

def test_assistant_interactif():
    logging.info("🚀 Démarrage du test interactif avec l'assistant")
    
    # 1. Initialiser l'assistant
    try:
        orchestrator = MainOrchestrator()
        logging.info("✅ Assistant initialisé avec Ollama")
    except Exception as e:
        logging.error(f"❌ Erreur lors de l'initialisation de l'assistant : {e}")
        return
    
    # 2. Simuler un utilisateur
    user_id = str(uuid.uuid4())
    logging.info(f"🔢 ID utilisateur généré : {user_id}")
    
    # 3. Première question à l'utilisateur
    print("\n🤖 Assistant : Bonjour ! Comment puis-je vous aider aujourd'hui ?")

    while True:
        # Attendre la réponse de l'utilisateur
        user_input = input("👤 Vous : ").strip()
        
        if not user_input:
            print("❌ Veuillez entrer une réponse valide.")
            continue
            
        if user_input.lower() in ["quitter", "exit", "q"]:
            print("👋 Au revoir !")
            break

        # Traiter la réponse de l'utilisateur
        try:
            # Utiliser l'orchestrateur pour générer une réponse
            agent_response = orchestrator.process_user_input(user_input, user_id)
            
            # Afficher la réponse de l'assistant
            print(f"\n🤖 Assistant : {agent_response.response_text}")
            
            # Si la procédure est terminée, redémarrer ou quitter
            if agent_response.is_complete:
                print("✅ Procédure terminée !")
                restart = input("Voulez-vous recommencer ? (o/n) ").strip().lower()
                if restart == "o":
                    user_id = str(uuid.uuid4())  # Nouvel utilisateur
                    print("🔄 Nouvelle session démarrée !")
                    print("🤖 Assistant : Bonjour ! Comment puis-je vous aider aujourd'hui ?")
                else:
                    break
                    
        except Exception as e:
            logging.error(f"❌ Erreur lors du traitement : {e}")
            print("⚠️ Une erreur est survenue. Veuillez réessayer.")

if __name__ == "__main__":
    test_assistant_interactif()