from dotenv import load_dotenv

load_dotenv()


from fastapi import FastAPI
from app.controllers.football_controller import football_router
from container import AppContainer


def create_app() -> FastAPI:
    container = AppContainer()

    app = FastAPI(
        title="Football Stats API - Genie Tool",
        description="Backend de previsão de jogos da Copa do Mundo com integração de ferramentas externas.",
        version="1.0.0",
    )

    app.container = container
    app.include_router(football_router)

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
