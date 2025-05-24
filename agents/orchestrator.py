from agents.retrieval import RetrievalAgent
from agents.assistant import AIAssistantAgent
from services.transcription import TranscriptionService
from services.tts import TTSService
from models.schemas import UserQuery, AgentResponse, ProcedureSchema 
from typing import List, Optional, Tuple
import os
import uuid
from pathlib import Path

PROCEDURES_DEFAULT_PATH = str(Path(__file__).resolve().parent.parent.parent / "data" / "procedures.json")

class MainOrchestrator:
    def __init__(self, procedures_path: str = PROCEDURES_DEFAULT_PATH):
        self.retrieval_agent = RetrievalAgent(procedures_path)
        self.assistant_agent = AIAssistantAgent()
        self.transcription_service = TranscriptionService(model_name="base")
        self.tts_service = TTSService()
        print("🚀 INNOVISION Orchestrator initialized!")
        print(f"Procedures loaded from: {procedures_path}")
        print(f"Ollama URL: {self.assistant_agent.ollama_url}, Model: {self.assistant_agent.model_name}")

    def process_user_input(self, text_input: str, user_id: str) -> AgentResponse:
        if not text_input:
            return AgentResponse(
                response_text="Je n'ai reçu aucun message. Comment puis-je vous aider ?",
                todo_list=[], missing_context=[], is_complete=False,
                next_question="Que souhaitez-vous faire ?"
            )
        print(f"📝 Processing text for user {user_id}: \"{text_input}\"")
        relevant_procedures: List[ProcedureSchema] = self.retrieval_agent.search_procedures(text_input)
        print(f"🔍 Found {len(relevant_procedures)} relevant procedures for query: '{text_input}'")
        response = self.assistant_agent.generate_response(
            text_input, 
            relevant_procedures, 
            user_id
        )
        print(f"🤖 Generated response for user {user_id}: \"{response.response_text[:100]}...\"")
        return response

    def process_user_query_object(self, query: UserQuery, audio_file_path: Optional[str] = None) -> AgentResponse:
        text_to_process = query.text
        if audio_file_path:
            print(f"🎤 Transcribing audio for user {query.user_id} from: {audio_file_path}")
            transcribed_text = self.transcription_service.transcribe_audio(audio_file_path)
            if not transcribed_text:
                return AgentResponse(
                    response_text="Désolé, je n'ai pas pu comprendre l'audio. Pouvez-vous répéter ou taper votre demande ?",
                    todo_list=[], missing_context=[], is_complete=False,
                    next_question="Pouvez-vous répéter votre demande ?"
                )
            text_to_process = transcribed_text
            print(f"🗣️ Transcription result for user {query.user_id}: \"{text_to_process}\"")
        if not text_to_process:
             return AgentResponse(
                response_text="Je n'ai pas pu obtenir de texte à traiter. Comment puis-je vous aider ?",
                todo_list=[], missing_context=[], is_complete=False,
                next_question="Que souhaitez-vous faire ?"
            )
        return self.process_user_input(text_input=text_to_process, user_id=query.user_id)

    def process_with_optional_voice_output(self, query: UserQuery, audio_file_path: Optional[str] = None, generate_tts: bool = False) -> AgentResponse:
        agent_response = self.process_user_query_object(query, audio_file_path)
        if generate_tts and agent_response.response_text:
            unique_id = str(uuid.uuid4()).split('-')[0] 
            filename_prefix = f"response_{query.user_id}_{unique_id}"
            response_lang = "fr" 
            relative_audio_path = self.tts_service.generate_audio_file(
                agent_response.response_text, 
                filename_prefix,
                lang=response_lang 
            )
            if relative_audio_path:
                agent_response.audio_response_url = os.path.join("/static", relative_audio_path).replace("\\", "/")
                print(f"🔊 TTS audio generated for user {query.user_id}: {agent_response.audio_response_url}")
            else:
                print(f"⚠️ TTS audio generation failed for user {query.user_id}.")
        return agent_response