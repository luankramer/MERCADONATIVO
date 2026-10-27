@echo off
chcp 65001 >nul
title Mercado Nativo - Mercado Pago
rem Grava as chaves do Mercado Pago no backend\.env  (use --testar ou --simulado)
cd /d "%~dp0..\backend"
"..\.venv\Scripts\python.exe" -m app.configurar_mp %*
pause
