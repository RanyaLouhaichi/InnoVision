import sys
from pathlib import Path

import pygame
sys.path.append(str(Path(__file__).resolve().parent))
import tempfile
import wave
import pyaudio # type: ignore
from agents.orchestrator import MainOrchestrator, PROCEDURES_DEFAULT_PATH
from models.schemas import UserQuery
import uuid
import os
import shutil

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

TEST_TEMP_DIR = Path(tempfile.gettempdir()) / "innovision_voice_test"
os.makedirs(TEST_TEMP_DIR, exist_ok=True)

def record_audio(duration=5, filename_prefix="test_mic_input"):
    CHUNK = 1024
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 16000
    output_filename = f"{filename_prefix}_{uuid.uuid4().hex}.wav"
    output_path = TEST_TEMP_DIR / output_filename
    p = pyaudio.PyAudio()
    print(f"🎤 Recording for {duration} seconds... Speak into your microphone.")
    try:
        stream = p.open(format=FORMAT,
                        channels=CHANNELS,
                        rate=RATE,
                        input=True,
                        frames_per_buffer=CHUNK)
    except Exception as e:
        print(f"Error opening audio stream: {e}")
        print("Please ensure you have a microphone connected and PyAudio is correctly installed/configured.")
        p.terminate()
        return None
    frames = []
    for i in range(0, int(RATE / CHUNK * duration)):
        try:
            data = stream.read(CHUNK)
            frames.append(data)
        except IOError as ex:
            print(f"Warning: IOError during recording stream.read: {ex}")
            if ex.errno == pyaudio.paInputOverflowed:
                print("Input overflowed. Some audio data may have been lost.")
            else:
                raise ex
    print("✅ Recording complete!")
    stream.stop_stream()
    stream.close()
    p.terminate()
    with wave.open(str(output_path), 'wb') as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(p.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))
    print(f"Audio saved to: {output_path}")
    return str(output_path)

def play_audio_pygame(audio_path: str):
    if not os.path.exists(audio_path):
        print(f"Audio file not found for playback: {audio_path}")
        return
    try:
        if not pygame.mixer.get_init():
             pygame.mixer.init()
        pygame.mixer.music.load(audio_path)
        pygame.mixer.music.play()
        print(f"🔊 Playing audio response from: {audio_path}")
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
    except Exception as e:
        print(f"Error playing audio with Pygame: {e}")

def test_voice_flow_cli():
    print("\n🎤 INNOVISION Voice Test (CLI Interaction)")
    print("=" * 40)
    if not os.path.exists(PROCEDURES_JSON_FOR_TEST):
        print(f"Error: {PROCEDURES_JSON_FOR_TEST} not found. Skipping test.")
        return
    try:
        orchestrator = MainOrchestrator(PROCEDURES_JSON_FOR_TEST)
    except Exception as e:
        print(f"Error initializing MainOrchestrator: {e}")
        return
    user_id = str(uuid.uuid4())
    try:
        pygame.init()
        pygame.mixer.init()
    except ImportError:
        print("Pygame not installed. Audio playback for TTS response will not work.")
        pygame = None
    except Exception as e:
        print(f"Error initializing Pygame: {e}")
        pygame = None
    while True:
        print("\nChoose an action:")
        print("1. Record voice query (requires microphone and PyAudio)")
        print("2. Type text query")
        print("3. Quit")
        choice = input("Your choice (1-3): ")
        agent_response = None
        generated_tts_path = None
        if choice == "3":
            print("👋 Au revoir!")
            break
        elif choice == "1":
            try:
                recorded_audio_path = record_audio(duration=7)
                if recorded_audio_path:
                    user_q = UserQuery(user_id=user_id)
                    agent_response = orchestrator.process_with_optional_voice_output(
                        query=user_q,
                        audio_file_path=recorded_audio_path,
                        generate_tts=True
                    )
                    if agent_response and agent_response.audio_response_url:
                        filename = os.path.basename(agent_response.audio_response_url)
                        generated_tts_path = str(Path(orchestrator.tts_service.STATIC_AUDIO_DIR) / filename)
            except ImportError:
                print("⚠️ PyAudio is not installed. Cannot record audio. Try typing your query.")
                continue
            except Exception as e:
                print(f"An error occurred during voice recording/processing: {e}")
                continue
        elif choice == "2":
            text_input = input("👤 Vous (tapez votre demande): ")
            if not text_input:
                continue
            user_q = UserQuery(text=text_input, user_id=user_id)
            agent_response = orchestrator.process_with_optional_voice_output(
                query=user_q,
                audio_file_path=None,
                generate_tts=True
            )
            if agent_response and agent_response.audio_response_url:
                filename = os.path.basename(agent_response.audio_response_url)
                generated_tts_path = str(Path(orchestrator.tts_service.STATIC_AUDIO_DIR) / filename)
        else:
            print("Invalid choice. Please enter 1, 2, or 3.")
            continue
        if agent_response:
            print(f"\n🤖 Assistant: \"{agent_response.response_text}\"")
            if agent_response.todo_list:
                print("📋 Documents/Infos à préparer:")
                for item in agent_response.todo_list:
                    print(f"   - {item}")
            if agent_response.next_question:
                print(f"❓ Question suivante: {agent_response.next_question}")
            if agent_response.is_complete:
                print("✅ Procédure marquée comme complète!")
            if generated_tts_path and pygame and pygame.mixer.get_init():
                if os.path.exists(generated_tts_path):
                    play_audio_pygame(generated_tts_path)
                else:
                    print(f"Could not find TTS audio file for playback: {generated_tts_path}")
            elif generated_tts_path:
                 print(f"TTS audio generated at: {generated_tts_path} (Pygame not available for playback).")
    try:
        shutil.rmtree(TEST_TEMP_DIR)
        print(f"Cleaned up temporary test directory: {TEST_TEMP_DIR}")
    except Exception as e:
        print(f"Error cleaning up temp directory {TEST_TEMP_DIR}: {e}")

if __name__ == "__main__":
    print("--- Running INNOVISION Voice Test (CLI Interaction) ---")
    print(f"Temporary audio files for this test will be stored in: {TEST_TEMP_DIR}")
    try:
        test_voice_flow_cli()
    except ImportError as e:
        if 'pyaudio' in str(e).lower():
            print("\n⚠️ PyAudio library not found. Voice recording functionality will not work.")
            print("Please install PyAudio: pip install pyaudio")
            print("For Linux, you might need: sudo apt-get install portaudio19-dev python3-pyaudio")
            print("For Windows, try: pip install pipwin; pipwin install pyaudio")
        elif 'pygame' in str(e).lower():
            print("\n⚠️ Pygame library not found. Voice response playback will not work.")
            print("Please install Pygame: pip install pygame")
        else:
            print(f"An import error occurred: {e}")
        print("\nRunning a simple text-only test as fallback...")
        try:
            orchestrator = MainOrchestrator(PROCEDURES_JSON_FOR_TEST)
            user_q = UserQuery(text="Je veux souscrire à internet", user_id="test_fallback")
            response = orchestrator.process_user_input(text_input=user_q.text, user_id=user_q.user_id)
            print(f"\n🤖 Fallback Test Response: {response.response_text}")
        except Exception as ex_fallback:
            print(f"Error during fallback text test: {ex_fallback}")
    except Exception as e_main:
        print(f"An unexpected error occurred during the voice test: {e_main}")
    finally:
        if 'pygame' in sys.modules and sys.modules['pygame'].get_init():
            sys.modules['pygame'].quit()
        print("\n--- INNOVISION Voice Test Finished ---")