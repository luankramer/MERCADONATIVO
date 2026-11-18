"""
Manda um e-mail de teste para conferir a configuração (Brevo ou SMTP) do backend/.env.

Uso (na pasta backend):  python -m app.testar_email            (ou scripts/testar_email.bat)
"""
import logging
import sys

from app.core.config import settings
from app.services import email_service


def main() -> None:
    logging.basicConfig(level=logging.WARNING, format="%(message)s")
    if email_service.brevo_configurado():
        print(f"Envio pelo Brevo, remetente {settings.EMAIL_REMETENTE}")
    elif email_service.smtp_configurado():
        print(f"Envio por SMTP ({settings.SMTP_HOST}), remetente {settings.SMTP_FROM}")
    else:
        print("❌ Nenhum envio de e-mail configurado. Preencha BREVO_API_KEY e EMAIL_REMETENTE no backend/.env.")
        return
    destino = (sys.argv[1] if len(sys.argv) > 1 else "").strip() or \
        input(f"Mandar o teste para qual e-mail? [{settings.ADMIN_MASTER_EMAIL}]: ").strip() or settings.ADMIN_MASTER_EMAIL
    ok = email_service.enviar_email(destino, "Teste de e-mail — Mercado Nativo",
                                    "Se você recebeu esta mensagem, o envio de e-mails do Mercado Nativo está funcionando.")
    if ok:
        print(f"✅ Enviado para {destino}. Confira a caixa de entrada e também o Lixo eletrônico / Spam.")
    else:
        print("❌ Não foi enviado. Veja a mensagem acima (chave errada ou remetente não verificado no Brevo).")


if __name__ == "__main__":
    main()
