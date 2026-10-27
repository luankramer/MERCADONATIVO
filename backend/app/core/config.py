"""
Configurações do Mercado Nativo, lidas do arquivo backend/.env (modelo em .env.example).
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]  # pasta backend/


def _load_env_file() -> None:
    env_path = BASE_DIR / ".env"
    if not env_path.exists():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.split(" #", 1)[0].strip().strip('"').strip("'")
        os.environ.setdefault(key.strip(), value)  # variável do sistema tem prioridade


_load_env_file()


def _bool(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).strip().lower() in ("1", "true", "sim", "yes", "on")


def _lista(name: str, default: str) -> list[str]:
    return [u.strip().rstrip("/") for u in os.getenv(name, default).split(",") if u.strip()]


class Settings:
    APP_NAME = "Mercado Nativo API"
    # "dev" (padrão) ou "producao" — em produção a documentação /docs fica desligada
    APP_ENV = os.getenv("APP_ENV", "dev").strip().lower()
    FRONTEND_URLS = _lista("FRONTEND_URLS", "http://localhost:5173,http://127.0.0.1:5173")
    # Para onde o produtor volta depois de conectar o Mercado Pago
    FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/")
    # Endereço público HTTPS do backend (ngrok/servidor). Necessário para o webhook do Mercado Pago.
    PUBLIC_API_URL = os.getenv("PUBLIC_API_URL", "").rstrip("/")
    UPLOAD_DIR = BASE_DIR / "uploads"
    MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "5"))

    DATABASE_URL = os.getenv("DATABASE_URL", "mysql+pymysql://root:@localhost:3306/mercado_nativo")

    # Segurança
    SECRET_KEY = os.getenv("SECRET_KEY", "")
    # Chave para criptografar tokens do Mercado Pago no banco (se vazia, é derivada da SECRET_KEY)
    ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", "")
    PRODUCER_TOKEN_HOURS = int(os.getenv("PRODUCER_TOKEN_HOURS", "168"))  # 7 dias
    ADMIN_TOKEN_HOURS = int(os.getenv("ADMIN_TOKEN_HOURS", "8"))

    ADMIN_MASTER_EMAIL = os.getenv("ADMIN_MASTER_EMAIL", "cleytonkramer@outlook.com").lower()

    # WhatsApp (Evolution API)
    EVOLUTION_BASE_URL = os.getenv("EVOLUTION_BASE_URL", "")
    EVOLUTION_TOKEN = os.getenv("EVOLUTION_TOKEN", "")
    EVOLUTION_INSTANCE = os.getenv("EVOLUTION_INSTANCE", "mercadonativo")
    # true = se o WhatsApp falhar, o código aparece SÓ no terminal do backend (nunca no navegador)
    OTP_DEV_MODE = _bool("OTP_DEV_MODE", False)
    OTP_EXPIRE_MINUTES = int(os.getenv("OTP_EXPIRE_MINUTES", "5"))

    # Assistente de texto
    OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
    OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "60"))
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

    # Pagamentos: "simulado" ou "mercadopago"
    PAYMENT_MODE = os.getenv("PAYMENT_MODE", "simulado").strip().lower()
    MP_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN", "")      # credencial da plataforma
    MP_PUBLIC_KEY = os.getenv("MP_PUBLIC_KEY", "")
    MP_CLIENT_ID = os.getenv("MP_CLIENT_ID", "")            # para o split (OAuth dos produtores)
    MP_CLIENT_SECRET = os.getenv("MP_CLIENT_SECRET", "")
    MP_REDIRECT_URI = os.getenv("MP_REDIRECT_URI", "")      # ex.: https://SEU.ngrok.app/api/v1/mercadopago/callback
    MP_WEBHOOK_SECRET = os.getenv("MP_WEBHOOK_SECRET", "")
    PLATFORM_FEE_PERCENT = float(os.getenv("PLATFORM_FEE_PERCENT", "10"))
    # Versão atual dos Termos de Uso / Política de Privacidade (mude quando o texto mudar)
    TERMOS_VERSAO = os.getenv("TERMOS_VERSAO", "1.0")
    PREMIUM_PRICE = float(os.getenv("PREMIUM_PRICE", "9.90"))
    PREMIUM_DAYS = int(os.getenv("PREMIUM_DAYS", "30"))

    @property
    def is_producao(self) -> bool:
        return self.APP_ENV in ("producao", "production", "prod")


settings = Settings()

if len(settings.SECRET_KEY) < 32:
    # Sem uma chave forte os tokens poderiam ser forjados: gera uma temporária e avisa.
    import secrets as _secrets

    settings.SECRET_KEY = _secrets.token_urlsafe(48)
    print("⚠️  SECRET_KEY ausente ou curta no .env — usando uma chave temporária (logins expiram ao reiniciar).")
