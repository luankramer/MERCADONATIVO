"""
Cria ou redefine o Super Admin do painel administrativo.

Uso (na pasta backend, com o venv ativo):
    python -m app.reset_admin                    -> pergunta e-mail e senha
    python -m app.reset_admin email@x.com        -> pergunta só a senha
"""
import getpass
import sys

from sqlalchemy import func

import app.models  # noqa: F401
from app.core.config import settings
from app.core.security import hash_password
from app.db.database import SessionLocal, engine
from app.db.migrations import run_migrations
from app.models.admin_model import NIVEL_SUPER, Admin


def _pedir_senha() -> str:
    while True:
        senha = getpass.getpass("Nova senha (mínimo 8 caracteres, não aparece ao digitar): ")
        if len(senha) < 8:
            print("  A senha precisa ter pelo menos 8 caracteres.")
            continue
        if senha != getpass.getpass("Repita a senha: "):
            print("  As senhas não conferem. Tente de novo.")
            continue
        return senha


def main() -> None:
    if len(sys.argv) > 1:
        email = sys.argv[1]
    else:
        email = input(f"E-mail do administrador [{settings.ADMIN_MASTER_EMAIL}]: ").strip() or settings.ADMIN_MASTER_EMAIL
    email = email.strip().lower()
    senha = _pedir_senha()

    run_migrations(engine)
    db = SessionLocal()
    try:
        admin = db.query(Admin).filter(func.lower(Admin.email) == email).first()
        if admin:
            admin.senha_hash = hash_password(senha)
            admin.nivel = NIVEL_SUPER
            admin.ativo = True
            acao = "Senha redefinida"
        else:
            db.add(Admin(nome="Administrador", email=email, senha_hash=hash_password(senha), nivel=NIVEL_SUPER, ativo=True))
            acao = "Super Admin criado"
        db.commit()
        print(f"\n✅ {acao} para {email}.\n   Acesse: http://localhost:5173/admin/login")
    finally:
        db.close()


if __name__ == "__main__":
    main()
