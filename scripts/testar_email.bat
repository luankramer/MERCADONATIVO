@echo off
chcp 65001 >nul
title Mercado Nativo - teste de e-mail
rem Manda um e-mail de teste usando a configuracao do backend\.env (Brevo ou SMTP)
cd /d "%~dp0..\backend"
"..\.venv\Scripts\python.exe" -m app.testar_email %*
pause
