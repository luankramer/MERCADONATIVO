@echo off
chcp 65001 >nul
title Mercado Nativo - Backend
rem Sobe a API em http://127.0.0.1:8000 (deixe esta janela aberta)
cd /d "%~dp0.."
if not exist ".venv\Scripts\python.exe" (
  echo Criando o ambiente virtual .venv...
  python -m venv .venv
)
echo Verificando bibliotecas...
".venv\Scripts\python.exe" -m pip install -q --disable-pip-version-check -r backend\requirements.txt
cd backend
if not exist ".env" copy ".env.example" ".env" >nul
echo.
echo API: http://127.0.0.1:8000   (celular no mesmo Wi-Fi: use o IPv4 abaixo com a porta 5173)
ipconfig | findstr /i "IPv4"
echo.
"..\.venv\Scripts\python.exe" -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
pause
