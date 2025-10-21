from fastapi import APIRouter, status
from app.services.agent_service import AgentService
from app.utils.logger_config import setup_logger
import pandas as pd

router = APIRouter(prefix="/metrics", tags=["Metrics"])
service = AgentService()
logger = setup_logger(__name__)

@router.get(
    "/mttf",
    status_code=status.HTTP_200_OK,
    summary="MTTF por subsistema",
    description="Calcula o Mean Time To Failure (MTTF) agrupado por subsistema."
)
def get_mttf():
    try:
        df = service._load_and_clean_df()
        if "subsistema" not in df.columns or "dt_falha" not in df.columns:
            return {"error": "Colunas necessárias não encontradas na planilha."}

        # Ordena por data e hora de falha
        df = df.sort_values(by=["subsistema", "dt_falha", "hr_falha"])

        results = []
        for subsistema, group in df.groupby("subsistema"):
            group = group.dropna(subset=["dt_falha"])
            group = group.sort_values("dt_falha")
            if len(group) < 2:
                continue

            # Calcula diferença de dias entre falhas consecutivas
            diffs = group["dt_falha"].diff().dt.total_seconds() / (3600 * 24)
            mttf = diffs.mean(skipna=True)
            results.append({
                "subsistema": subsistema,
                "mttf_dias": round(mttf, 2) if pd.notnull(mttf) else None
            })

        results = sorted(results, key=lambda x: x["mttf_dias"] or 0, reverse=True)
        logger.info(f"MTTF calculado para {len(results)} subsistemas.")
        return results

    except Exception as e:
        logger.error(f"Erro ao calcular MTTF: {e}")
        return {"error": str(e)}
