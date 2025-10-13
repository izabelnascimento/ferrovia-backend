from fastapi import APIRouter, Body, status
from app.services.agent_service import AgentService
from app.utils.logger_config import setup_logger

router = APIRouter(prefix="/agents", tags=["Agents"])
service = AgentService()
logger = setup_logger(__name__)

@router.post(
    "/echo",
    status_code=status.HTTP_200_OK,
    summary="Echo de string",
    description="Recebe uma string e retorna a mesma string."
)
def echo(text: str = Body(..., embed=True)):
    logger.info(f"Received echo request with text length: {len(text)}")
    try:
        result = service.echo(text)
        logger.info("Echo request processed successfully")
        return {"text": result}
    except Exception as e:
        logger.error(f"Error in echo: {e}")
        return {"error": str(e)}
