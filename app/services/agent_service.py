import google.generativeai as genai

class AgentService:
    def __init__(self) -> None:
        # api_key = os.getenv("GOOGLE_API_KEY")
        api_key = "AIzaSyBlX0NUeeW7P0VVhoePNqWZPl8Jq74sHmo"
        if not api_key:
            raise RuntimeError("GOOGLE_API_KEY não definida. Ex.: export GOOGLE_API_KEY='...'.")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-2.0-flash")

    def echo(self, text: str) -> str:
        try:
            resp = self.model.generate_content(text)
            content = (resp.text or "").strip()
            if not content:
                return ""
            return content
        except Exception as e:
            return f"Erro ao chamar o Gemini: {e}"
