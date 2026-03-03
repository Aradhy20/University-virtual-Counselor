
try:
    print("Checking pydantic_v1...")
    from langchain_core.pydantic_v1 import BaseModel
    print("Success: langchain_core.pydantic_v1")
except ImportError as e:
    print(f"Error: {e}")

try:
    print("Checking llama_index...")
    import llama_index.core
    print("Success: llama_index.core")
except ImportError as e:
    print(f"Error: {e}")

try:
    print("Checking agent_workflow import...")
    import sys
    import os
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    from app.services.agent_workflow import run_agent
    print("Success: agent_workflow import")
except Exception as e:
    print(f"Error importing agent_workflow: {e}")
