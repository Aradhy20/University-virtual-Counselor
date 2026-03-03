"""
Configuration Schema for Enterprise Agent Control Center.
Defines the structure for dynamic agent settings.
"""
from typing import Optional, List, Dict
from pydantic import BaseModel, Field

class LLMConfig(BaseModel):
    provider: str = Field("groq", description="LLM Provider (groq, openai)")
    model_name: str = Field("llama-3.1-8b-instant", description="Model Identifier")
    temperature: float = Field(0.1, ge=0.0, le=2.0, description="Creativity level")
    max_tokens: int = Field(512, description="Max response tokens")
    
class VoiceConfig(BaseModel):
    provider: str = Field("deepgram", description="TTS Provider")
    voice_id: str = Field("aura-asteria-en", description="Voice ID (e.g. Aditi)")
    stability: float = Field(0.35, ge=0.0, le=1.0, description="Voice Stability")
    similarity_boost: float = Field(0.85, ge=0.0, le=1.0, description="Voice Similarity")
    style: float = Field(0.40, ge=0.0, le=1.0, description="Style Exaggeration")
    use_speaker_boost: bool = Field(True, description="Boost clarity")

class RAGConfig(BaseModel):
    top_k: int = Field(3, description="Number of chunks to retrieve")
    similarity_threshold: float = Field(0.0, ge=0.0, le=1.0, description="Minimum similarity score")
    enable_reranker: bool = Field(False, description="Use Cross-Encoder Re-ranking")
    rerank_threshold: float = Field(0.65, description="Re-ranker confidence threshold")

class PromptsConfig(BaseModel):
    system_prompt: str = Field(..., description="Main Persona System Prompt")
    clarification_prompt: str = Field(..., description="Prompt for low confidence")
    safety_rules: List[str] = Field(default_factory=list, description="List of safety protocols")

class APIConfig(BaseModel):
    groq_api_key: str = ""
    deepgram_api_key: str = ""
    elevenlabs_api_key: str = ""
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_phone_number: str = ""
    tunnel_url: str = ""
    supabase_url: str = ""
    supabase_service_key: str = ""

class SecurityConfig(BaseModel):
    enable_input_safety: bool = True
    blocklist: List[str] = [
        "ignore previous instructions",
        "forget all instructions",
        "system prompt",
        "reveal your instructions",
        "act as a linux",
        "act as a developer",
        "hacked",
        "override system",
        "new persona"
    ]

class AgentConfig(BaseModel):
    llm: LLMConfig
    voice: VoiceConfig
    rag: RAGConfig
    prompts: PromptsConfig
    api: APIConfig
    security: SecurityConfig

