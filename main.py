import asyncio
from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI

from app.controllers.football_controller import football_router
from app.controllers.memory_controller import memory_router
from container import AppContainer


async def _warm_cache(container: AppContainer) -> None:
    try:
        service = container.football_service()
        await asyncio.gather(
            service.get_standings(),
            service.get_matches(),
            service.get_top_scorers(),
            return_exceptions=True,
        )
    except Exception:
        pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    await app.container.init_resources()
    asyncio.create_task(_warm_cache(app.container))
    yield
    await app.container.shutdown_resources()


def create_app() -> FastAPI:
    container = AppContainer()

    app = FastAPI(
        title="Football Stats API - Genie Tool",
        description="Backend de previsão de jogos da Copa do Mundo com integração de ferramentas externas.",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.container = container
    app.include_router(football_router)
    app.include_router(memory_router)

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
