from fastapi import HTTPException


class TeamNotFoundError(HTTPException):
    def __init__(self, team: str):
        super().__init__(status_code=400, detail=f"Seleção '{team}' não encontrada")


class InvalidDateRangeError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=400,
            detail="date_from e date_to devem ser informados juntos.",
        )


class ExternalAPIError(HTTPException):
    def __init__(self, source: str = ""):
        detail = f"API externa indisponível: {source}" if source else "API externa indisponível"
        super().__init__(status_code=503, detail=detail)
