from fastapi import APIRouter, Depends, HTTPException
from dependency_injector.wiring import inject, Provide
from container import AppContainer
from app.models.football import (
    HeadToHeadResponse,
)
from app.services.head_to_head_analyzer import HeadToHeadAnalyzer

football_router = APIRouter(prefix="/football", tags=["Football API"])


@football_router.get("/head-to-head", response_model=HeadToHeadResponse)
@inject
async def check_head_to_head(
    name_team_a: str,
    name_team_b: str,
    analyzer: HeadToHeadAnalyzer = Depends(Provide[AppContainer.head_to_head_analyzer]),
):
    if not name_team_a or not name_team_b:
        raise HTTPException(status_code=400, detail="Parâmetros ausentes.")

    try:

        summary = await analyzer.generate_summary(name_team_a, name_team_b)
        return summary
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=500, detail="Erro interno ao processar análise."
        )
