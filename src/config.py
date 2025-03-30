from typing import List
from pydantic import BaseModel

class PersonaConfig(BaseModel):
    name: str
    description: str
    tone: str
    interests: List[str]
    adaptive: bool

class LoopConfig(BaseModel):
    tl_retrieval_length: int
    tl_retrieval_interval: float
    engagement_retrieval_interval: float
    ppo_interval: float

class SFTConfig(BaseModel):
    approximate_tokens: int = 8_000_000_000

class PPOConfig(BaseModel):
    pass

class ModelConfig(BaseModel):
    hf_repo_id: str = "HuggingFaceTB/SmolLM2-360M-Instruct"
    checkpoint_dir: str = "checkpoints"

class VibeBotConfig(BaseModel):
    user_id: str
    accounts_to_follow: List[str]
    persona: PersonaConfig
    loop: LoopConfig
    sft: SFTConfig
    ppo: PPOConfig
    model: ModelConfig
