import os
import re
import unicodedata
from pathlib import Path
from typing import List

import pandas as pd
from dotenv import load_dotenv
from langchain.schema import Document
from langchain_community.vectorstores import Chroma

from langchain_google_genai import (
    ChatGoogleGenerativeAI,
)
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate, FewShotPromptTemplate


class AgentService:
    def __init__(self) -> None:
        load_dotenv()
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GOOGLE_API_KEY não definida. Ex.: export GOOGLE_API_KEY='sua_chave'"
            )

        # === 1) Caminhos ===
        self.BASE_DIR = Path(__file__).resolve().parents[2]
        self.DATA_FILE = self.BASE_DIR / "data" / "dados.xlsx"
        self.CHROMA_DIR = self.BASE_DIR / "chromadb"

        # === 2) LLM e Embeddings (Gemini) ===
        self.embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-m3")
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            temperature=0,
            google_api_key=api_key,          # ✅ e aqui também
        )

        # === 3) Inicializa pipeline RAG ===
        self.retriever = self._init_retriever()
        self.qa = self._build_qa_chain()

    # ------------------------------
    # Helpers de preparação de dados
    # ------------------------------
    def _slugify_cols(self, cols: List[str]) -> List[str]:
        out = []
        for c in cols:
            c = c.strip().lower()
            c = unicodedata.normalize("NFKD", c)
            c = c.encode("ascii", "ignore").decode("utf-8")
            c = re.sub(r"[^\w\s]", "", c)
            c = re.sub(r"\s+", "_", c)
            out.append(c)
        return out

    def _load_and_clean_df(self) -> pd.DataFrame:
        if not self.DATA_FILE.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {self.DATA_FILE}")

        df = pd.read_excel(self.DATA_FILE, header=0)
        df.columns = self._slugify_cols(list(df.columns))

        for col in ["dt_falha", "dt_enc"]:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], format="%Y-%m-%d", errors="coerce")

        for col in ["hr_falha", "hr_enc"]:
            if col in df.columns:
                df[col] = (
                    df[col].astype(str).str.strip().str.replace(r"\s+", "", regex=True)
                )
                df[col] = pd.to_datetime(df[col], format="%H:%M", errors="coerce").dt.time

        for col in ["solicitacao", "ordem"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        for col in ["subsistema", "local", "prioridade", "descricao", "solucao", "reclamante"]:
            if col in df.columns:
                df[col] = df[col].astype("string")

        return df

    def _df_to_documents(self, df: pd.DataFrame) -> List[Document]:
        docs: List[Document] = []
        for idx, row in df.iterrows():
            text = " | ".join([f"{col}: {row[col]}" for col in df.columns])
            docs.append(Document(page_content=text, metadata={"row_index": int(idx)}))
        return docs

    # ------------------------------
    # Vetorstore + Retriever
    # ------------------------------
    def _init_retriever(self):
        if self.CHROMA_DIR.exists() and any(self.CHROMA_DIR.iterdir()):
            vectordb = Chroma(
                persist_directory=str(self.CHROMA_DIR),
                embedding_function=self.embeddings
            )
        else:
            df = self._load_and_clean_df()
            documents = self._df_to_documents(df)
            self.CHROMA_DIR.mkdir(parents=True, exist_ok=True)
            vectordb = Chroma.from_documents(
                documents=documents,
                embedding=self.embeddings,               # ok nessa versão
                persist_directory=str(self.CHROMA_DIR)
            )
        return vectordb.as_retriever(search_type="similarity", search_kwargs={"k": 5})

    # ------------------------------
    # Prompt few-shot + Cadeia RAG
    # ------------------------------
    def _build_qa_chain(self):
        examples = [
            {
                "question": "Calcule o MTTF do subsistema SINCDVCAV.",
                "context": "Use dt_falha/hr_falha; calcule intervalos entre falhas e a média.",
                "answer": "Converta timestamps, calcule intervalos e tire a média (horas/dias).",
            },
            {
                "question": "Qual é o MTTR do subsistema SINCDVFLO?",
                "context": "Use (dt_enc/hr_enc) - (dt_falha/hr_falha) por registro e tire a média.",
                "answer": "Calcule as durações e reporte o MTTR médio em horas.",
            },
            {
                "question": "Qual subsistema apresenta mais falhas?",
                "context": "Conte ocorrências por subsistema e estime porcentagem.",
                "answer": "Informe contagem e % do total para o topo.",
            },
        ]

        example_template = (
            "Pergunta: {question}\nContexto: {context}\nResposta: {answer}"
        )
        example_prompt = PromptTemplate(
            input_variables=["question", "context", "answer"],
            template=example_template
        )

        system_instruction = (
            "Você é um assistente especializado em analisar dados de falhas/incidentes "
            "provenientes de uma planilha XLSX (solicitacao, subsistema, local, dt_falha, hr_falha, "
            "prioridade, descricao, dt_enc, hr_enc, solucao, ordem, reclamante). "
            "Responda SEMPRE com base no contexto recuperado; se faltar dado, explique a limitação. "
            "Faça cálculos (MTTF, MTTR) quando solicitado. Português objetivo."
        )

        few_shot_prompt = FewShotPromptTemplate(
            examples=examples,
            example_prompt=example_prompt,
            prefix=system_instruction,
            suffix="Pergunta do usuário: {question}\nContexto recuperado:\n{context}\nResposta:",
            input_variables=["context", "question"]
        )

        qa = RetrievalQA.from_chain_type(
            llm=self.llm,
            retriever=self.retriever,
            chain_type="stuff",
            chain_type_kwargs={"prompt": few_shot_prompt},
            return_source_documents=False
        )
        return qa

    # ------------------------------
    # Método usado pelo endpoint
    # ------------------------------
    def echo(self, text: str) -> str:
        try:
            result = self.qa.invoke({"query": text})
            return (result.get("result") or "").strip()
        except Exception as e:
            return f"Erro ao processar a pergunta: {e}"
