"""
Primeira publicação num servidor novo (ex.: Railway), quando ninguém consegue abrir um terminal
para rodar `python -m app.reset_admin` e `python -m app.seed`.

As duas ações são controladas por variáveis de ambiente e só agem com o banco vazio:
- ADMIN_INICIAL_SENHA: cria o Super Admin (ADMIN_MASTER_EMAIL) se não houver nenhum administrador.
- DADOS_DEMO=true: cadastra os produtores e produtos de demonstração se não houver produtos.
"""
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.models.admin_model import NIVEL_SUPER, Admin

SENHA_MINIMA = 8


def criar_admin_inicial(db: Session) -> bool:
    """Cria o Super Admin com a senha da variável ADMIN_INICIAL_SENHA. Devolve True se criou."""
    senha = settings.ADMIN_INICIAL_SENHA
    if not senha or db.query(Admin).count() > 0:
        return False
    if len(senha) < SENHA_MINIMA:
        print(f"⚠️  ADMIN_INICIAL_SENHA precisa ter pelo menos {SENHA_MINIMA} caracteres. Administrador não criado.")
        return False
    db.add(Admin(nome="Administrador", email=settings.ADMIN_MASTER_EMAIL, senha_hash=hash_password(senha),
                 nivel=NIVEL_SUPER, ativo=True))
    db.commit()
    print(f"👤 Super Admin criado para {settings.ADMIN_MASTER_EMAIL}. Depois do primeiro acesso, apague "
          "a variável ADMIN_INICIAL_SENHA do servidor.")
    return True


def carregar_dados_demo() -> None:
    """Cadastra os dados de demonstração (o seed só insere se o banco ainda não tiver produtos)."""
    if not settings.DADOS_DEMO:
        return
    from app import seed  # import tardio: o seed usa o banco e o serviço de mapas

    seed.main()
