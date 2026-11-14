@echo off
chcp 65001 >nul
title Mercado Nativo - levar os dados para o Railway
rem Exporta o MySQL local e as fotos e envia para o site publicado no Railway.
rem O MySQL deste computador precisa estar ligado.
cd /d "%~dp0..\backend"
if exist "..\.venv\Scripts\python.exe" (
  "..\.venv\Scripts\python.exe" -m app.levar_dados_online
) else (
  python -m app.levar_dados_online
)
pause
