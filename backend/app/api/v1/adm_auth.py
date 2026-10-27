"""Login e gestão da equipe administrativa."""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.rate_limit import ip_cliente, limpar, registrar, verificar
from app.core.security import (
    create_access_token, get_current_admin, get_super_admin, hash_password, verify_password,
)
from app.db.database import get_db
from app.models.admin_model import NIVEL_ADMIN, Admin
from app.schemas.admin import AdminCreate, AdminLogin, AdminUpdate

router = APIRouter()


def _admin_dict(admin: Admin) -> dict:
    return {
        "id": admin.id,
        "nome": admin.nome,
        "email": admin.email,
        "nivel": "Super Admin" if admin.is_super else "Administrador",
        "is_super": admin.is_super,
    }


# 1. Rota de Listagem
@router.get("/list")
async def list_admins(db: Session = Depends(get_db), _=Depends(get_current_admin)):
    return [_admin_dict(a) for a in db.query(Admin).order_by(Admin.id).all()]


# 2. Rota de Registro (somente Super Admin)
@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_admin(admin: AdminCreate, db: Session = Depends(get_db), _=Depends(get_super_admin)):
    if db.query(Admin).filter(func.lower(Admin.email) == admin.email.lower()).first():
        raise HTTPException(status_code=400, detail="E-mail já cadastrado.")
    novo = Admin(nome=admin.nome, email=admin.email.lower(), senha_hash=hash_password(admin.senha), nivel=NIVEL_ADMIN)
    db.add(novo)
    db.commit()
    return {"mensagem": "Acesso criado com sucesso"}


# 3. Rota de Edição (somente Super Admin)
@router.put("/{admin_id}")
async def update_admin(admin_id: int, admin_data: AdminUpdate, db: Session = Depends(get_db),
                       _=Depends(get_super_admin)):
    admin_db = db.get(Admin, admin_id)
    if not admin_db:
        raise HTTPException(status_code=404, detail="Administrador não encontrado")
    duplicado = db.query(Admin).filter(func.lower(Admin.email) == admin_data.email.lower(), Admin.id != admin_id).first()
    if duplicado:
        raise HTTPException(status_code=400, detail="E-mail já cadastrado.")
    admin_db.nome = admin_data.nome
    admin_db.email = admin_data.email.lower()
    if admin_data.senha:  # Só atualiza a senha se for preenchida
        if len(admin_data.senha) < 8:
            raise HTTPException(400, "A senha precisa ter pelo menos 8 caracteres.")
        admin_db.senha_hash = hash_password(admin_data.senha)
    db.commit()
    return {"mensagem": "Administrador atualizado."}


# 4. Rota de Exclusão (somente Super Admin; não pode excluir a si mesmo)
@router.delete("/{admin_id}")
async def delete_admin(admin_id: int, db: Session = Depends(get_db), atual: Admin = Depends(get_super_admin)):
    admin_db = db.get(Admin, admin_id)
    if not admin_db:
        raise HTTPException(status_code=404, detail="Administrador não encontrado")
    if admin_db.id == atual.id or admin_db.is_super:
        raise HTTPException(status_code=400, detail="O Super Admin não pode ser excluído.")
    db.delete(admin_db)
    db.commit()
    return {"mensagem": "Administrador excluído."}


# 5. Rota de Login
@router.post("/login")
async def login_admin(admin: AdminLogin, request: Request, db: Session = Depends(get_db)):
    # Proteção contra tentativa e erro de senhas: 5 erros por e-mail/IP a cada 15 minutos
    chave = f"admin-login:{ip_cliente(request)}:{admin.email.lower()}"
    registrar(f"admin-login-ip:{ip_cliente(request)}", 30, 900)
    verificar(chave, 5, 900)
    db_admin = db.query(Admin).filter(func.lower(Admin.email) == admin.email.lower()).first()
    if not db_admin or not verify_password(admin.senha, db_admin.senha_hash):
        try:
            registrar(chave, 5, 900)
        except HTTPException:
            pass  # a 6ª tentativa já será bloqueada pelo verificar()
        raise HTTPException(status_code=401, detail="E-mail ou senha incorretos")
    limpar(chave)
    if db_admin.ativo is False:
        raise HTTPException(status_code=403, detail="Acesso desativado.")
    return {
        "access_token": create_access_token(db_admin.id, "admin"),
        "token_type": "bearer",
        "email": db_admin.email,
        "nome": db_admin.nome,
        "is_super": db_admin.is_super,
    }


@router.get("/me")
async def me(admin: Admin = Depends(get_current_admin)):
    return _admin_dict(admin)
