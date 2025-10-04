# Ferrovia Backend — FastAPI + RAG (Chroma) + Gemini

Microserviço FastAPI que recebe uma pergunta via POST, busca contexto no `data/dados.xlsx` (RAG com Chroma) e responde usando a LLM **Gemini**.

## ✅ Pré-requisitos

* Git configurado
* **Docker** e **Docker Compose** instalados
* Uma **chave da API do Gemini**

  * Crie em: [https://aistudio.google.com/](https://aistudio.google.com/)  → “Get API key”
  * Guarde a chave (ex.: `AIza...`)

---

## 📦 Clonar o projeto

```bash
git clone <URL-DO-SEU-REPO>.git
cd ferrovia-backend
```

---

## 🔐 Configurar variáveis de ambiente

Edite o `.env` e informe sua chave do Gemini:

```env
GOOGLE_API_KEY=AIza...sua_chave_aqui
```

> **Importante:** não faça commit do `.env`. Adicione-o no `.gitignore`.

---

> Na primeira execução, o serviço cria a base vetorial e a **persiste** em `chromadb/`.
> Se você atualizar o Excel e quiser reindexar, **apague a pasta**:
>
> ```bash
> rm -rf chromadb
> ```

---

## ▶️ Rodar com Docker (1 comando)

```bash
docker compose up --build
```

* Swagger: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
* ReDoc:   [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

Para rodar em **segundo plano**:

```bash
docker compose up -d --build
```

Parar tudo:

```bash
docker compose down
```

---

## 🧪 Teste rápido

Pelo Swagger (em `/docs`) chame `POST /agents/echo` com um JSON:

```json
{
  "text": "Calcule o MTTF do subsistema SINCDVCAV."
}
```

Ou via cURL:

```bash
curl -X POST http://127.0.0.1:8000/agents/echo \
  -H "Content-Type: application/json" \
  -d '{"text":"Calcule o MTTF do subsistema SINCDVCAV."}'
```

A resposta virá no campo `"text"`.

---

## 🗂️ Estrutura do projeto

```
ferrovia-backend/
├─ app/
│  ├─ api/v1/routers/agents.py    # endpoint POST /agents/echo
│  ├─ services/agent_service.py   # RAG + LLM (Gemini)
│  └─ main.py                     # FastAPI app
├─ data/
│  └─ dados.xlsx                  # planilha de entrada
├─ chromadb/                      # persistência do índice vetorial (gerado)
├─ Dockerfile
├─ docker-compose.yml
├─ requirements.txt
├─ .env                           # (seu) NÃO versionar
├─ .env.example                   # (exemplo)
└─ README.md
```

---

## ⚙️ Detalhes de implementação

* **LLM**: Gemini (`gemini-2.0-flash`)
* **Embeddings**: por padrão **locais** (FastEmbed) → imagem leve e sem limites de cota
  *(você pode trocar para HuggingFace ou embeddings do Gemini se quiser — ajustar `requirements.txt` e `AgentService`)*
* **Vector Store**: Chroma (persistido em `chromadb/`)
* **API**: FastAPI + Swagger automático

---

## 💡 Desenvolvimento local (opcional, sem Docker)

Se preferir rodar direto no Python:

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -U pip
pip install -r requirements.txt
cp .env.example .env               # adicione sua GOOGLE_API_KEY
uvicorn app.main:app --reload --port 8000
```
