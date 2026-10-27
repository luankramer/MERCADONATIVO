"""
Migração automática e leve do banco.

`Base.metadata.create_all` cria tabelas novas, mas NÃO adiciona colunas novas em
tabelas que já existem (como a `producers` e a `products` do seu MySQL).
Esta rotina compara os modelos com o banco e executa `ALTER TABLE ... ADD COLUMN`
para cada coluna que estiver faltando. É segura para rodar a cada inicialização.
"""
import logging

from sqlalchemy import Text, inspect, text
from sqlalchemy.engine import Engine

from app.db.database import Base

log = logging.getLogger("mercado_nativo.migrations")


def _default_sql(column) -> str:
    default = column.server_default
    if default is None:
        return ""
    arg = default.arg
    value = arg.text if hasattr(arg, "text") else str(arg)
    return f" DEFAULT {value}" if value.upper() in ("0", "1", "NULL") or value.startswith("'") else f" DEFAULT '{value}'"


def run_migrations(engine: Engine) -> list[str]:
    """Cria tabelas ausentes e adiciona colunas ausentes. Retorna as colunas criadas."""
    Base.metadata.create_all(bind=engine)

    inspector = inspect(engine)
    added: list[str] = []
    with engine.begin() as conn:
        for table in Base.metadata.sorted_tables:
            existing = {c["name"] for c in inspector.get_columns(table.name)}
            for column in table.columns:
                if column.name in existing:
                    continue
                col_type = column.type.compile(dialect=engine.dialect)
                sql = f"ALTER TABLE {table.name} ADD COLUMN {column.name} {col_type} NULL{_default_sql(column)}"
                conn.execute(text(sql))
                added.append(f"{table.name}.{column.name}")
                log.warning("Coluna adicionada automaticamente: %s.%s", table.name, column.name)

        # MySQL: colunas que eram VARCHAR(255) e agora guardam textos longos (ex.: história do produtor)
        if engine.dialect.name == "mysql":
            for table in Base.metadata.sorted_tables:
                tipos = {c["name"]: c["type"] for c in inspector.get_columns(table.name)}
                for column in table.columns:
                    atual = tipos.get(column.name)
                    if isinstance(column.type, Text) and atual is not None and "CHAR" in str(atual).upper():
                        conn.execute(text(f"ALTER TABLE {table.name} MODIFY COLUMN {column.name} TEXT NULL"))
                        log.warning("Coluna ampliada para TEXT: %s.%s", table.name, column.name)

        # Segurança: apaga dados bancários guardados por versões anteriores (não são mais usados)
        colunas_producers = {c["name"] for c in inspector.get_columns("producers")}
        antigas = [c for c in ("cpf_cnpj", "chave_pix", "banco_codigo", "agencia", "conta", "conta_digito",
                               "tipo_conta", "pagarme_recipient_id") if c in colunas_producers]
        if antigas:
            conn.execute(text("UPDATE producers SET " + ", ".join(f"{c} = NULL" for c in antigas)))

        # Pedidos/assinaturas antigos ganham um código público aleatório
        from app.models.order_model import novo_codigo
        for tabela in ("orders", "premium_subscriptions"):
            ids = conn.execute(text(f"SELECT id FROM {tabela} WHERE codigo IS NULL")).fetchall()
            for (id_,) in ids:
                conn.execute(text(f"UPDATE {tabela} SET codigo = :c WHERE id = :i"), {"c": novo_codigo(), "i": id_})

        # Produtos que já existiam antes da curadoria continuam visíveis na vitrine
        if "products.status" in added:
            conn.execute(text("UPDATE products SET status = 'aprovado' WHERE status IS NULL OR status = 'pendente'"))
        # Padroniza contadores nulos
        for col in ("visualizacoes", "contatos_whatsapp"):
            if f"products.{col}" in added:
                conn.execute(text(f"UPDATE products SET {col} = 0 WHERE {col} IS NULL"))
    return added
