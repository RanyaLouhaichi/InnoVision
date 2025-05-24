from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Union

class AIAssistantAgentSchema(BaseModel):
    required_context: List[str]
    instructions: str

class ProcedureSchema(BaseModel):
    procedure: str
    documents_required: Union[List[str], Dict[str, List[str]]]
    remarks: List[str]
    ai_assistant_agent: AIAssistantAgentSchema
    source: str

class ProceduresDataSchema(BaseModel):
    procedures: List[ProcedureSchema]

class UserQuery(BaseModel):
    text: Optional[str] = None
    user_id: str

class AgentResponse(BaseModel):
    response_text: str
    todo_list: List[str]
    missing_context: List[str]
    is_complete: bool
    next_question: Optional[str] = None
    audio_response_url: Optional[str] = None

class UserTextQuery(BaseModel):
    text: str
    user_id: str