from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter
from fastapi.params import Depends

from app.models.memory import MemoryResponse, MemoryTurnRequest
from app.services.memory_service import MemoryService
from container import AppContainer

memory_router = APIRouter(prefix="/memory", tags=["Conversation Memory"])


@memory_router.get(
    "/{chat_id}",
    response_model=MemoryResponse,
    summary="Carregar memória da conversa",
    description="Retorna o histórico e contexto persistido para um chat_id. Retorna estrutura vazia se não houver histórico.",
)
@inject
async def get_memory(
    chat_id: str,
    service: MemoryService = Depends(Provide[AppContainer.memory_service]),
):
    data = await service.load(chat_id)
    return MemoryResponse(chat_id=chat_id, **data)


@memory_router.post(
    "/{chat_id}",
    response_model=MemoryResponse,
    summary="Salvar turno na memória da conversa",
    description="Adiciona um par usuário/agente ao histórico e atualiza last_teams e preferred_language se fornecidos. TTL de 7 dias.",
)
@inject
async def save_memory_turn(
    chat_id: str,
    body: MemoryTurnRequest,
    service: MemoryService = Depends(Provide[AppContainer.memory_service]),
):
    data = await service.save_turn(chat_id, body)
    return MemoryResponse(chat_id=chat_id, **data)
