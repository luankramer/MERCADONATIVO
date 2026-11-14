@echo off
chcp 65001 >nul
title Mercado Nativo - variaveis para o Railway
rem Gera backend\railway-backend.env.local e backend\railway-site.env.local a partir dos .env locais.
rem Esses arquivos tem senhas e NAO vao para o GitHub.
cd /d "%~dp0..\backend"
if exist "..\.venv\Scripts\python.exe" (
  "..\.venv\Scripts\python.exe" -m app.gerar_env_railway
) else (
  python -m app.gerar_env_railway
)
pause
