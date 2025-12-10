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
    summary="MTTF por subsistema (dias)",
    description="Calcula o Mean Time To Failure (MTTF) agrupado por subsistema."
)
def get_mttf():
    try:
        df = service._load_and_clean_df()
        if "subsistema" not in df.columns or "dt_falha" not in df.columns:
            return {"error": "Colunas necessárias não encontradas na planilha."}

        df = df.sort_values(by=["subsistema", "dt_falha", "hr_falha"])
        results = []

        for subsistema, group in df.groupby("subsistema"):
            group = group.dropna(subset=["dt_falha"])
            if len(group) < 2:
                continue

            diffs = group["dt_falha"].diff().dt.total_seconds() / (3600 * 24)
            mttf = diffs.mean(skipna=True)
            results.append({
                "subsistema": subsistema,
                "mttf_dias": round(mttf, 2) if pd.notnull(mttf) else None
            })

        results = sorted(results, key=lambda x: x["mttf_dias"] or 0, reverse=True)
        return results

    except Exception as e:
        logger.error(f"Erro ao calcular MTTF: {e}")
        return {"error": str(e)}


@router.get(
    "/mttr",
    status_code=status.HTTP_200_OK,
    summary="MTTR por subsistema (horas)",
    description="Calcula o Mean Time To Repair (MTTR) agrupado por subsistema."
)
def get_mttr():
    try:
        df = service._load_and_clean_df()
        if not {"subsistema", "dt_falha", "hr_falha", "dt_enc", "hr_enc"}.issubset(df.columns):
            return {"error": "Colunas necessárias não encontradas na planilha."}

        results = []
        for subsistema, group in df.groupby("subsistema"):
            group = group.dropna(subset=["dt_falha", "dt_enc"])
            if len(group) == 0:
                continue

            start = pd.to_datetime(group["dt_falha"].astype(str) + " " + group["hr_falha"].astype(str), errors="coerce")
            end = pd.to_datetime(group["dt_enc"].astype(str) + " " + group["hr_enc"].astype(str), errors="coerce")
            diffs = (end - start).dt.total_seconds() / 3600  # horas
            mttr = diffs.mean(skipna=True)

            results.append({
                "subsistema": subsistema,
                "mttr_horas": round(mttr, 2) if pd.notnull(mttr) else None
            })

        results = sorted(results, key=lambda x: x["mttr_horas"] or 0)
        return results

    except Exception as e:
        logger.error(f"Erro ao calcular MTTR: {e}")
        return {"error": str(e)}


@router.get(
    "/disponibilidade",
    status_code=status.HTTP_200_OK,
    summary="Disponibilidade por subsistema (%)",
    description="Calcula a disponibilidade percentual (MTTF / (MTTF + MTTR))."
)
def get_disponibilidade():
    try:
        df = service._load_and_clean_df()
        if not {"subsistema", "dt_falha", "hr_falha", "dt_enc", "hr_enc"}.issubset(df.columns):
            return {"error": "Colunas necessárias não encontradas na planilha."}

        # --- Reutiliza os cálculos de MTTF e MTTR ---
        mttf_df = pd.DataFrame(get_mttf())
        mttr_df = pd.DataFrame(get_mttr())

        merged = pd.merge(mttf_df, mttr_df, on="subsistema", how="inner")
        merged["disponibilidade"] = (
            merged["mttf_dias"] * 24 / (merged["mttf_dias"] * 24 + merged["mttr_horas"])
        ) * 100

        merged = merged[["subsistema", "disponibilidade"]].sort_values(
            by="disponibilidade", ascending=False
        )
        merged["disponibilidade"] = merged["disponibilidade"].round(2)

        return merged.to_dict(orient="records")

    except Exception as e:
        logger.error(f"Erro ao calcular disponibilidade: {e}")
        return {"error": str(e)}


@router.get(
    "/falhas",
    status_code=status.HTTP_200_OK,
    summary="Subsistemas que mais falham",
    description="Conta o número de falhas registradas por subsistema e retorna em ordem decrescente."
)
def get_falhas_por_subsistema():
    try:
        df = service._load_and_clean_df()
        if "subsistema" not in df.columns:
            return {"error": "Coluna 'subsistema' não encontrada na planilha."}

        counts = df["subsistema"].value_counts().reset_index()
        counts.columns = ["subsistema", "quantidade_falhas"]
        counts = counts.sort_values(by="quantidade_falhas", ascending=False)

        logger.info(f"Falhas por subsistema calculadas para {len(counts)} registros.")
        return counts.to_dict(orient="records")

    except Exception as e:
        logger.error(f"Erro ao calcular falhas por subsistema: {e}")
        return {"error": str(e)}


@router.get(
    "/quantidade-subsistemas",
    status_code=status.HTTP_200_OK,
    summary="Quantidade de subsistemas",
    description="Retorna a quantidade de subsistemas únicos no DataFrame."
)
def get_quantidade_subsistemas():
    try:
        df = service._load_and_clean_df()
        if "subsistema" not in df.columns:
            return {"error": "Coluna 'subsistema' não encontrada na planilha."}

        quantidade_subsistemas = df["subsistema"].nunique()
        logger.info(f"Quantidade de subsistemas únicos: {quantidade_subsistemas}")
        return {"quantidade_subsistemas": quantidade_subsistemas}

    except Exception as e:
        logger.error(f"Erro ao calcular a quantidade de subsistemas: {e}")
        return {"error": str(e)}


@router.get(
    "/disponibilidade-media",
    status_code=status.HTTP_200_OK,
    summary="Disponibilidade média dos subsistemas (%)",
    description="Calcula a disponibilidade média de todos os subsistemas."
)
def get_disponibilidade_media():
    try:
        df = service._load_and_clean_df()
        if not {"subsistema", "dt_falha", "hr_falha", "dt_enc", "hr_enc"}.issubset(df.columns):
            return {"error": "Colunas necessárias não encontradas na planilha."}

        # --- Reutiliza os cálculos de MTTF e MTTR ---
        mttf_df = pd.DataFrame(get_mttf())
        mttr_df = pd.DataFrame(get_mttr())

        merged = pd.merge(mttf_df, mttr_df, on="subsistema", how="inner")
        merged["disponibilidade"] = (
            merged["mttf_dias"] * 24 / (merged["mttf_dias"] * 24 + merged["mttr_horas"])
        ) * 100

        # Calcula a disponibilidade média
        disponibilidade_media = merged["disponibilidade"].mean()

        logger.info(f"Disponibilidade média calculada: {disponibilidade_media:.2f}%")
        return {"disponibilidade_media": round(disponibilidade_media, 2)}

    except Exception as e:
        logger.error(f"Erro ao calcular a disponibilidade média: {e}")
        return {"error": str(e)}
