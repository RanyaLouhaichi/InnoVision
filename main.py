import os
import uuid
import shutil
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Request, BackgroundTasks # type: ignore
from fastapi.staticfiles import StaticFiles # type: ignore
from fastapi.middleware.cors import CORSMiddleware # type: ignore
from models.schemas import UserQuery, AgentResponse, UserTextQuery
from agents.orchestrator import MainOrchestrator, PROCEDURES_DEFAULT_PATH
from dotenv import load_dotenv

app = FastAPI(
    title="INNOVISION Voice Assistant API",
    description="API for interacting with the INNOVISION voice assistant.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

APP_DIR = Path(__file__).resolve().parent 
BACKEND_DIR = APP_DIR.parent 
STATIC_DIR = APP_DIR / "static"
GENERATED_AUDIO_DIR = STATIC_DIR / "generated_audio"
os.makedirs(GENERATED_AUDIO_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

TEMP_UPLOADS_DIR = APP_DIR / "temp_uploads"
os.makedirs(TEMP_UPLOADS_DIR, exist_ok=True)

PROCEDURES_JSON_PATH = str(BACKEND_DIR / "data" / "procedures.json")
if not Path(PROCEDURES_JSON_PATH).exists():
    if Path(PROCEDURES_DEFAULT_PATH).exists():
         PROCEDURES_JSON_PATH = PROCEDURES_DEFAULT_PATH
    else:
        print(f"FATAL: procedures.json not found at {PROCEDURES_JSON_PATH} or {PROCEDURES_DEFAULT_PATH}")

dotenv_path = BACKEND_DIR / '.env'
if dotenv_path.exists():
    load_dotenv(dotenv_path=dotenv_path)
else:
    print(f"Warning: .env file not found at {dotenv_path}. Ollama settings might be missing.")

try:
    orchestrator = MainOrchestrator(procedures_path=PROCEDURES_JSON_PATH)
except FileNotFoundError as e:
    print(f"Failed to initialize orchestrator: {e}")
    print("Please ensure 'procedures.json' is correctly placed and paths are configured.")
    orchestrator = None
except RuntimeError as e:
    print(f"Failed to initialize orchestrator due to runtime error: {e}")
    orchestrator = None

def cleanup_temp_file(file_path: str):
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"Cleaned up temp file: {file_path}")
    except Exception as e:
        print(f"Error cleaning up temp file {file_path}: {e}")

@app.get("/", tags=["General"])
async def read_root():
    return {"message": "Welcome to INNOVISION Voice Assistant API. Visit /docs for API documentation."}

@app.post("/api/v1/query/text", response_model=AgentResponse, tags=["Query"])
async def process_text_query(query: UserTextQuery, request: Request):
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not available. Service is down.")
    print(f"Received text query from {request.client.host} for user {query.user_id}: {query.text}")
    generate_tts_param = request.query_params.get("tts", "false").lower()
    should_generate_tts = generate_tts_param == "true"
    user_q = UserQuery(text=query.text, user_id=query.user_id)
    agent_response = orchestrator.process_with_optional_voice_output(
        query=user_q,
        audio_file_path=None,
        generate_tts=should_generate_tts
    )
    return agent_response

@app.post("/api/v1/query/audio", response_model=AgentResponse, tags=["Query"])
async def process_audio_query(
    background_tasks: BackgroundTasks,
    request: Request,
    user_id: str = Form(...),
    audio_file: UploadFile = File(...),
):
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not available. Service is down.")
    print(f"Received audio query from {request.client.host} for user {user_id}, filename: {audio_file.filename}")
    temp_audio_filename = f"upload_{user_id}_{uuid.uuid4().hex}{Path(audio_file.filename).suffix}"
    temp_audio_path = TEMP_UPLOADS_DIR / temp_audio_filename
    try:
        with open(temp_audio_path, "wb") as buffer:
            shutil.copyfileobj(audio_file.file, buffer)
        print(f"Audio file saved temporarily to: {temp_audio_path}")
    except Exception as e:
        print(f"Error saving uploaded audio file: {e}")
        raise HTTPException(status_code=500, detail=f"Could not save uploaded audio file: {e}")
    finally:
        audio_file.file.close()
    background_tasks.add_task(cleanup_temp_file, str(temp_audio_path))
    generate_tts_param = request.query_params.get("tts", "false").lower()
    should_generate_tts = generate_tts_param == "true"
    user_q = UserQuery(user_id=user_id)
    agent_response = orchestrator.process_with_optional_voice_output(
        query=user_q,
        audio_file_path=str(temp_audio_path),
        generate_tts=should_generate_tts
    )
    return agent_response

@app.get("/health", tags=["General"])
async def health_check():
    if orchestrator and orchestrator.retrieval_agent and orchestrator.assistant_agent:
        return {"status": "ok", "message": "INNOVISION API is running."}
    return HTTPException(status_code=503, detail="Service is degraded or not fully initialized.")

if __name__ == "__main__":
    import uvicorn # type: ignore
    print("Starting Uvicorn server for INNOVISION API...")
    print(f"Procedures expected at: {PROCEDURES_JSON_PATH}")
    print(f"Static files served from: {STATIC_DIR}")
    print(f"Generated audio will be in: {GENERATED_AUDIO_DIR}")
    print(f"Temporary uploads will be in: {TEMP_UPLOADS_DIR}")
    ollama_url_env = os.getenv("OLLAMA_BASE_URL")
    model_name_env = os.getenv("MODEL_NAME")
    print(f"OLLAMA_BASE_URL from env: {ollama_url_env}")
    print(f"MODEL_NAME from env: {model_name_env}")
    if not orchestrator:
        print("\nWARNING: Orchestrator failed to initialize. API endpoints might not work.")
        print("Please check error messages above, ensure 'procedures.json' and '.env' are correct,")
        print("and that Ollama and other dependencies are running/installed.\n")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")