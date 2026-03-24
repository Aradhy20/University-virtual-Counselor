"""
Session Memory — Persistent File-based Storage.
Saves chat history to data/sessions/{session_id}.json using LangChain.
"""
import logging
import json
from pathlib import Path

logger = logging.getLogger("riya.memory")

class SessionMemory:
    def __init__(self, data_dir: str = "data/sessions"):
        """
        Initialize persistent memory storage.
        """
        self.data_dir = Path(__file__).parent.parent.parent / data_dir
        if not self.data_dir.exists():
            self.data_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"SessionMemory initialized at {self.data_dir}")

    def _get_file_path(self, session_id: str) -> Path:
        return self.data_dir / f"{session_id}.json"

    def _load_history(self, session_id: str) -> list:
        file_path = self._get_file_path(session_id)
        if file_path.exists():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load memory for {session_id}: {e}")
        return []

    def _save_history(self, session_id: str, history: list):
        file_path = self._get_file_path(session_id)
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save memory for {session_id}: {e}")

    def add_user_message(self, session_id: str, message: str):
        history = self._load_history(session_id)
        history.append({"role": "student", "content": message})
        self._save_history(session_id, history)
        logger.debug(f"[{session_id[:8]}] User msg saved")

    def add_ai_message(self, session_id: str, message: str):
        history = self._load_history(session_id)
        history.append({"role": "counselor", "content": message})
        self._save_history(session_id, history)
        logger.debug(f"[{session_id[:8]}] AI msg saved")

    def get_chat_history(self, session_id: str) -> str:
        """Returns formatted chat history for the session."""
        history = self._load_history(session_id)
        if not history:
            return "No previous conversation history found. Be sure to greet the student warmly!"
            
        history_str = "PREVIOUS EXCHANGES WITH THIS STUDENT:\n"
        # Only take the last 15 turns from history to prevent context overflow
        recent_history = history[-15:]
        for msg in recent_history:
            history_str += f"{msg['role']}: {msg['content']}\n"
        return history_str

    def clear_session(self, session_id: str):
        """Clear memory file."""
        file_path = self._get_file_path(session_id)
        if file_path.exists():
            file_path.unlink()
            logger.info(f"[{session_id[:8]}] Session memory cleared")
