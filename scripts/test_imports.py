
import os
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

try:
    from app.services.config_loader import config_loader
    from app.services.voice import VoiceService
    from app.services.agent_workflow import run_crew_agent
    from app.services.emotional_tracker import EmotionalTracker
    print("Imports successful!")
except Exception as e:
    import traceback
    traceback.print_exc()
    sys.exit(1)
