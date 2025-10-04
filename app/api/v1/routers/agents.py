from fastapi import APIRouter, Body, status
from app.services.agent_service import AgentService

router = APIRouter(prefix="/agents", tags=["Agents"])
service = AgentService()

@router.post(
    "/echo",
    status_code=status.HTTP_200_OK,
    summary="Echo de string",
    description="Recebe uma string e retorna a mesma string."
)
def echo(text: str = Body(..., embed=True)):
    return {"text": service.echo(text)}
