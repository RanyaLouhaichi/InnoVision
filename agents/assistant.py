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
                    "temperature": 0.3,  # Lower temperature for more consistent responses
                    "top_p": 0.8,
                    "num_predict": 500,  # Limit response length
                }
            }
            response = requests.post(url, json=payload, timeout=30)
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
        """Analyze user intent and match to procedures with better logic"""
        if not relevant_procedures:
            return {"intent": "unknown", "confidence": 0.0, "detected_language": "fr"}
        
        # Simple keyword matching first for exact procedure names
        user_lower = user_input.lower()
        for proc in relevant_procedures:
            proc_lower = proc.procedure.lower()
            # Check for key terms in the procedure name
            key_terms = proc_lower.split()
            if len(key_terms) > 2:  # For compound procedure names
                if all(term in user_lower for term in key_terms[:2]):  # Match first two key terms
                    return {
                        "intent": proc.procedure,
                        "confidence": 0.9,
                        "detected_language": "fr"
                    }
            elif any(term in user_lower for term in key_terms if len(term) > 3):  # Match significant terms
                return {
                    "intent": proc.procedure,
                    "confidence": 0.8,
                    "detected_language": "fr"
                }
        
        # Fallback to Ollama for complex cases
        system_prompt = """Tu es un assistant pour un opérateur télécom. 
        Analyse l'intention de l'utilisateur et détermine quelle procédure correspond le mieux.
        Réponds UNIQUEMENT avec le nom exact de la procédure ou "unknown" si aucune ne correspond.
        Ne donne pas d'explication, juste le nom de la procédure."""
        
        procedures_text = "\n".join([f"- {proc.procedure}" for proc in relevant_procedures])
        prompt = f"""
        Demande utilisateur: "{user_input}"
        Procédures disponibles:
        {procedures_text}
        
        Quelle procédure correspond exactement à cette demande?
        """
        
        response_str = self._call_ollama(prompt, system_prompt)
        
        # Find matching procedure
        for proc in relevant_procedures:
            if proc.procedure.lower() in response_str.lower():
                return {
                    "intent": proc.procedure,
                    "confidence": 0.7,
                    "detected_language": "fr"
                }
                
        return {
            "intent": relevant_procedures[0].procedure if relevant_procedures else "unknown",
            "confidence": 0.5,
            "detected_language": "fr"
        }

    def collect_missing_context(self, procedure: ProcedureSchema, user_input: str, conversation_history: List[Dict]) -> AgentResponse:
        """Collect missing context with improved logic"""
        required_context = procedure.ai_assistant_agent.required_context if procedure.ai_assistant_agent else []
        
        # Filter out "Aucun context requis"
        required_context_items = [ctx for ctx in required_context if ctx != "Aucun context requis"]
        
        if not required_context_items:
            return self._generate_complete_response(procedure, {})
        
        # Extract context from current input and conversation
        collected_context = self._extract_context_from_conversation(
            user_input, conversation_history, required_context_items
        )
        
        # Find missing context
        missing_context_items = [ctx for ctx in required_context_items if not collected_context.get(ctx)]
        
        if not missing_context_items:
            return self._generate_complete_response(procedure, collected_context)
        else:
            # Ask for next missing context item
            next_question = self._generate_context_question(missing_context_items[0], procedure)
            return AgentResponse(
                response_text=next_question,
                todo_list=[],
                missing_context=missing_context_items,
                is_complete=False,
                next_question=next_question
            )

    def _extract_context_from_conversation(self, current_input: str, history: List[Dict], required_context: List[str]) -> Dict[str, Optional[str]]:
        """Extract context using simple pattern matching and conversation analysis"""
        context_values = {}
        
        # Combine all conversation text
        all_text = current_input + " " + " ".join([msg.get('content', '') for msg in history])
        all_text_lower = all_text.lower()
        
        for ctx_item in required_context:
            value = None
            ctx_lower = ctx_item.lower()
            
            # Pattern matching for different context types
            if "offre" in ctx_lower or "type" in ctx_lower:
                if "fibre" in all_text_lower:
                    value = "Fibre"
                elif "adsl" in all_text_lower:
                    value = "ADSL"
                elif "5g" in all_text_lower or "box" in all_text_lower:
                    value = "Box 5G"
            
            elif "adresse" in ctx_lower:
                # Look for address patterns (very basic)
                address_match = re.search(r'(\d+.*?(?:rue|avenue|boulevard|av|blvd).*?)(?:\.|,|$)', all_text_lower)
                if address_match:
                    value = address_match.group(1).strip()
            
            elif "paiement" in ctx_lower:
                if any(word in all_text_lower for word in ["carte", "bancaire", "cb"]):
                    value = "Carte bancaire"
                elif any(word in all_text_lower for word in ["prélèvement", "virement"]):
                    value = "Prélèvement automatique"
                elif "espèces" in all_text_lower:
                    value = "Espèces"
            
            elif "client" in ctx_lower:
                if any(word in all_text_lower for word in ["particulier", "personne", "individu"]):
                    value = "Particulier"
                elif any(word in all_text_lower for word in ["entreprise", "société", "business"]):
                    value = "Entreprise"
            
            elif "numéro" in ctx_lower and "ligne" in ctx_lower:
                # Look for phone number patterns
                phone_match = re.search(r'\b(\d{8})\b', all_text)
                if phone_match:
                    value = phone_match.group(1)
            
            elif "volume" in ctx_lower:
                # Look for data volume patterns
                volume_match = re.search(r'(\d+)\s*(mo|go|mb|gb)', all_text_lower)
                if volume_match:
                    value = f"{volume_match.group(1)} {volume_match.group(2).upper()}"
            
            context_values[ctx_item] = value
        
        return context_values

    def _generate_context_question(self, missing_context_item: str, procedure: ProcedureSchema) -> str:
        """Generate appropriate questions for missing context"""
        questions_map = {
            "type d'offre souhaitée": "Quel type d'offre internet souhaitez-vous ? (Fibre, ADSL, ou Box 5G)",
            "adresse du domicile": "Quelle est votre adresse complète ?",
            "mode de paiement": "Quel mode de paiement préférez-vous ? (Carte bancaire, prélèvement automatique, etc.)",
            "type de client": "Êtes-vous un particulier ou une entreprise ?",
            "numéro de la ligne": "Quel est le numéro de la ligne concernée ?",
            "volume à transférer": "Quel volume de données souhaitez-vous transférer ? (en Mo ou Go)",
            "identité du titulaire": "Pouvez-vous confirmer l'identité du titulaire de la ligne ?"
        }
        
        # Find matching question
        for key, question in questions_map.items():
            if key.lower() in missing_context_item.lower():
                return question
        
        # Default question
        return f"Pour continuer avec '{procedure.procedure}', j'ai besoin de connaître : {missing_context_item}. Pouvez-vous me le fournir ?"

    def _generate_complete_response(self, procedure: ProcedureSchema, context: Dict) -> AgentResponse:
        """Generate final response with procedure details"""
        todo_list = []
        
        # Handle different document structures
        if isinstance(procedure.documents_required, list):
            todo_list = procedure.documents_required
        elif isinstance(procedure.documents_required, dict):
            # Use context to determine client type
            client_type = context.get("Type de client", "").lower()
            if "entreprise" in client_type:
                todo_list = procedure.documents_required.get("entreprise", procedure.documents_required.get("particulier", []))
            else:
                todo_list = procedure.documents_required.get("particulier", [])
        
        # Build response text
        response_parts = [
            f"Parfait ! Pour votre demande de '{procedure.procedure}', voici ce dont vous avez besoin :"
        ]
        
        if context:
            response_parts.append("\n📋 Informations confirmées :")
            for key, value in context.items():
                if value:
                    response_parts.append(f"• {key} : {value}")
        
        if todo_list:
            response_parts.append("\n📄 Documents requis :")
            for doc in todo_list:
                response_parts.append(f"• {doc}")
        
        if procedure.remarks:
            response_parts.append("\n⚠️ Remarques importantes :")
            for remark in procedure.remarks:
                response_parts.append(f"• {remark}")
        
        response_text = "\n".join(response_parts)
        
        return AgentResponse(
            response_text=response_text,
            todo_list=todo_list,
            missing_context=[],
            is_complete=True,
            next_question=None
        )

    def generate_response(self, user_input: str, relevant_procedures: List[ProcedureSchema], user_id: str) -> AgentResponse:
        """Main response generation with improved flow"""
        # Initialize conversation history
        if user_id not in self.conversation_history:
            self.conversation_history[user_id] = []
        
        current_conversation = self.conversation_history[user_id]
        current_conversation.append({"role": "user", "content": user_input})

        # Handle no procedures found
        if not relevant_procedures:
            response_text = "Désolé, je n'ai pas trouvé de procédure correspondant à votre demande. Pouvez-vous reformuler ou préciser ce que vous souhaitez faire ?"
            current_conversation.append({"role": "assistant", "content": response_text})
            return AgentResponse(
                response_text=response_text,
                todo_list=[],
                missing_context=[],
                is_complete=False,
                next_question="Que souhaitez-vous faire exactement ?"
            )

        # Analyze intent
        intent_result = self.analyze_user_intent(user_input, relevant_procedures)
        target_procedure = next((p for p in relevant_procedures if p.procedure == intent_result["intent"]), None)

        # Handle ambiguous intent
        if not target_procedure and len(relevant_procedures) > 1:
            proc_names = [p.procedure for p in relevant_procedures[:3]]
            clarification = f"Je vois plusieurs procédures possibles. Laquelle vous intéresse ?\n" + "\n".join([f"• {name}" for name in proc_names])
            current_conversation.append({"role": "assistant", "content": clarification})
            return AgentResponse(
                response_text=clarification,
                todo_list=[],
                missing_context=proc_names,
                is_complete=False,
                next_question=clarification
            )

        # Use first procedure if only one available
        if not target_procedure:
            target_procedure = relevant_procedures[0]

        # Collect missing context and generate response
        agent_response = self.collect_missing_context(target_procedure, user_input, current_conversation)
        current_conversation.append({"role": "assistant", "content": agent_response.response_text})

        # Clear history if conversation is complete
        if agent_response.is_complete:
            self.conversation_history[user_id] = []

        return agent_response