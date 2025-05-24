from pathlib import Path
import requests
import json
from typing import List, Dict, Optional
import os
from dotenv import load_dotenv
import re
from models.schemas import ProcedureSchema, AgentResponse

dotenv_path = Path(__file__).resolve().parent.parent.parent / '.env'
load_dotenv(dotenv_path=dotenv_path)

class AIAssistantAgent:
    def __init__(self):
        self.ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model_name = os.getenv("MODEL_NAME", "llama3")
        if not self.ollama_url or not self.model_name:
            print("Warning: OLLAMA_BASE_URL or MODEL_NAME not set in .env or environment.")
        self.conversation_history: Dict[str, List[Dict]] = {}

    def _call_ollama(self, prompt: str, system_prompt: str = "") -> str:
        try:
            url = f"{self.ollama_url}/api/generate"
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "system": system_prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                }
            }
            response = requests.post(url, json=payload, timeout=60)
            response.raise_for_status()
            response_json = response.json()
            return response_json.get("response", "Désolé, je n'ai pas pu générer de réponse.")
        except requests.exceptions.RequestException as e:
            print(f"Ollama API request error: {e}")
            return "Erreur de connexion avec l'assistant Ollama. Veuillez vérifier qu'il est bien lancé et accessible."
        except json.JSONDecodeError as e:
            print(f"Ollama API JSON decode error: {e}")
            return "Réponse invalide reçue de l'assistant Ollama."
        except Exception as e:
            print(f"Unexpected error calling Ollama API: {e}")
            return "Une erreur inattendue est survenue avec l'assistant."

    def analyze_user_intent(self, user_input: str, relevant_procedures: List[ProcedureSchema]) -> Dict:
        system_prompt = """Tu es un assistant intelligent pour un opérateur télécom. 
        Analyse l'intention de l'utilisateur en Français ou en Arabe Tunisien et détermine quelle procédure il souhaite effectuer parmi la liste fournie.
        Si l'intention semble correspondre à une procédure, retourne le nom exact de cette procédure.
        Si l'intention n'est pas claire ou ne correspond à aucune procédure, retourne "unknown".
        Réponds UNIQUEMENT en JSON avec cette structure:
        {
            "intent": "nom_exact_de_la_procedure_ou_unknown", 
            "confidence": 0.0_a_1.0,
            "detected_language": "fr_ou_ar_ou_tunisian_ou_unknown" 
        }"""
        if not relevant_procedures:
            return { "intent": "unknown", "confidence": 0.0, "detected_language": "unknown" }
        procedures_text = "\n".join([f"- {proc.procedure}" for proc in relevant_procedures])
        prompt = f"""
        Input utilisateur: "{user_input}"
        Procédures disponibles (choisir parmi celles-ci):
        {procedures_text}
        Quelle procédure l'utilisateur veut-il effectuer? Analyse attentivement et retourne le nom exact de la procédure.
        """
        response_str = self._call_ollama(prompt, system_prompt)
        try:
            match = re.search(r'\{.*\}', response_str, re.DOTALL)
            if match:
                json_str = match.group(0).strip('` \n\t')
                intent_data = json.loads(json_str)
                if "intent" in intent_data and "confidence" in intent_data:
                    return intent_data
            return {
                "intent": relevant_procedures[0].procedure,
                "confidence": 0.3,
                "detected_language": "unknown"
            }
        except json.JSONDecodeError:
            return {
                "intent": "unknown",
                "confidence": 0.2,
                "detected_language": "unknown"
            }

    def collect_missing_context(self, procedure: ProcedureSchema, user_input: str, conversation_history: List[Dict]) -> AgentResponse:
        required_context = procedure.ai_assistant_agent.required_context if procedure.ai_assistant_agent else []
        required_context_items = required_context if required_context and required_context != ["Aucun context requis"] else []
        
        if not required_context_items:
            return self._generate_complete_response(procedure, {})
        
        collected_context = self._extract_context_with_ollama(user_input, conversation_history, required_context_items, procedure.procedure)
        missing_context_items = [ctx for ctx in required_context_items if not collected_context.get(ctx)]
        
        if not missing_context_items:
            return self._generate_complete_response(procedure, collected_context)
        else:
            next_question_prompt = self._generate_context_question_prompt(missing_context_items[0], procedure, collected_context)
            system_prompt_question = "Tu es un assistant conversationnel. Pose la question suivante de manière naturelle et amicale."
            next_question = self._call_ollama(f"Question à poser: {next_question_prompt}", system_prompt_question).strip()
            if any(msg in next_question for msg in ["Désolé", "Erreur"]) or len(next_question) < 10:
                next_question = next_question_prompt
            return AgentResponse(
                response_text=next_question,
                todo_list=[],
                missing_context=missing_context_items,
                is_complete=False,
                next_question=next_question
            )

    def _extract_context_with_ollama(self, current_input: str, history: List[Dict], required_context: List[str], procedure_name: str) -> Dict[str, Optional[str]]:
            context_values = {key: None for key in required_context}
            full_conversation_text = "\n".join([f"{msg.get('role', 'unknown')}: {msg.get('content', '')}" for msg in history])
            full_conversation_text += f"\nuser: {current_input}"

            system_prompt = f"""
            Tu es un extracteur d'informations. Analyse la conversation suivante pour la procédure "{procedure_name}".
            Pour chaque élément de contexte requis listé ci-dessous, extrais la valeur fournie par l'utilisateur.
            Réponds UNIQUEMENT en JSON avec les clés étant les éléments de contexte requis.
            
            Éléments de contexte requis: {', '.join(required_context)}
            
            Exemple de format de réponse:
            {{
                {", ".join([f'"{ctx}": null' for ctx in required_context])}
            }}
            """
            response_str = self._call_ollama(f"Extract from: {full_conversation_text}", system_prompt)
            try:
                match = re.search(r'\{.*\}', response_str, re.DOTALL)
                if match:
                    json_str = match.group(0).strip('` \n\t')
                    extracted_data = json.loads(json_str)
                    for ctx_item in required_context:
                        context_values[ctx_item] = extracted_data.get(ctx_item)
                    return context_values
                return context_values
            except json.JSONDecodeError:
                return context_values

    def _generate_context_question_prompt(self, missing_context_item: str, procedure: ProcedureSchema, collected_context: Dict) -> str:
        questions_map = {
            "Type d'offre souhaitée": "Quel type d'offre internet souhaitez-vous ?",
            "Adresse du domicile": "Pourriez-vous me donner votre adresse complète ?",
            "Mode de paiement": "Quel mode de paiement préférez-vous ?",
            "Type de client": "Êtes-vous un particulier ou une entreprise ?",
            "Numéro de la ligne": "Quel est le numéro de la ligne concernée ?"
        }
        for key, question in questions_map.items():
            if key.lower() in missing_context_item.lower():
                return question
        return f"Pour finaliser '{procedure.procedure}', j'ai besoin de : {missing_context_item}. Pouvez-vous me le fournir ?"

    def _generate_complete_response(self, procedure: ProcedureSchema, context: Dict) -> AgentResponse:
        todo_list = []
        if isinstance(procedure.documents_required, list):
            todo_list = procedure.documents_required
        elif isinstance(procedure.documents_required, dict):
            todo_list = procedure.documents_required.get("particulier", [])
        
        context_summary = "\n".join([f"- {k}: {v}" for k, v in context.items() if v])
        response_prompt = f"""
        Génère une réponse finale pour la procédure "{procedure.procedure}" avec:
        - Informations: {context_summary or "Aucune"}
        - Documents: {', '.join(todo_list) or "Aucun"}
        - Remarques: {', '.join(procedure.remarks) or "Aucune"}
        """
        final_response_text = self._call_ollama(response_prompt, "Sois clair et concis.").strip()
        
        return AgentResponse(
            response_text=final_response_text,
            todo_list=todo_list,
            missing_context=[],
            is_complete=True,
            next_question=None
        )

    def generate_response(self, user_input: str, relevant_procedures: List[ProcedureSchema], user_id: str) -> AgentResponse:
        if user_id not in self.conversation_history:
            self.conversation_history[user_id] = []
        current_conversation = self.conversation_history[user_id]
        current_conversation.append({"role": "user", "content": user_input})

        if not relevant_procedures:
            response_text = "Désolé, je n'ai pas trouvé de procédure correspondante. Pouvez-vous reformuler ?"
            current_conversation.append({"role": "assistant", "content": response_text})
            return AgentResponse(
                response_text=response_text,
                todo_list=[],
                missing_context=[],
                is_complete=False,
                next_question="Pouvez-vous préciser votre demande ?"
            )

        intent_result = self.analyze_user_intent(user_input, relevant_procedures)
        target_procedure = next((p for p in relevant_procedures if p.procedure == intent_result["intent"]), None)

        if not target_procedure:
            if len(relevant_procedures) == 1:
                target_procedure = relevant_procedures[0]
            else:
                proc_names = [p.procedure for p in relevant_procedures[:3]]
                clarification = f"Voulez-vous dire : {', '.join(proc_names)} ?" if proc_names else "Pouvez-vous reformuler ?"
                current_conversation.append({"role": "assistant", "content": clarification})
                return AgentResponse(
                    response_text=clarification,
                    todo_list=[],
                    missing_context=proc_names,
                    is_complete=False,
                    next_question=clarification
                )

        agent_response = self.collect_missing_context(target_procedure, user_input, current_conversation)
        current_conversation.append({"role": "assistant", "content": agent_response.response_text})

        if agent_response.is_complete:
            self.conversation_history[user_id] = []

        return agent_response