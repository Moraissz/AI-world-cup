from typing import List, Optional

from pydantic import BaseModel, Field


class ConversationTurn(BaseModel):
    role: str = Field(..., examples=["user"], description="'user' ou 'agent'")
    text: str = Field(..., examples=["Brasil vs Argentina"], description="Texto da mensagem")
    ts: str = Field(..., examples=["2026-06-19T18:00:00"], description="Timestamp UTC (ISO 8601)")


class MemoryResponse(BaseModel):
    chat_id: str = Field(..., examples=["153485102297129@lid"])
    last_teams: Optional[List[str]] = Field(
        None,
        examples=[["Brazil", "Argentina"]],
        description="Último par de times discutidos — usado para resolver referências implícitas",
    )
    preferred_language: Optional[str] = Field(
        None,
        examples=["pt"],
        description="Idioma preferido detectado pelo agente",
    )
    history: List[ConversationTurn] = Field(
        default_factory=list,
        description="Últimas 10 trocas da conversa",
    )


class MemoryTurnRequest(BaseModel):
    user_msg: str = Field(..., description="Mensagem enviada pelo usuário")
    agent_rep: str = Field(..., description="Resposta enviada pelo agente")
    team_a: str = Field(default="", description="Primeiro time discutido (vazio se nenhum)")
    team_b: str = Field(default="", description="Segundo time discutido (vazio se nenhum)")
    preferred_language: Optional[str] = Field(
        default=None,
        description="Idioma detectado ('pt', 'en', etc.) — preserva valor anterior se omitido",
    )
