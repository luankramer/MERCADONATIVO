@echo off
chcp 65001 >nul
title Mercado Nativo - ngrok (endereco HTTPS do backend)
rem Abre o backend (porta 8000) na internet com o dominio fixo do ngrok.
rem O dominio vem do PUBLIC_API_URL do backend\.env  (ex.: https://seu-nome.ngrok-free.app)
cd /d "%~dp0..\backend"
set "URL="
for /f "usebackq tokens=1,* delims==" %%a in (".env") do if /i "%%a"=="PUBLIC_API_URL" set "URL=%%b"
if "%URL%"=="" (
  echo Preencha PUBLIC_API_URL no backend\.env com o seu dominio do ngrok.
  pause
  exit /b 1
)
where ngrok >nul 2>nul || (
  echo ngrok nao encontrado. Instale com:  winget install ngrok.ngrok
  pause
  exit /b 1
)
echo Abrindo %URL%  -^>  http://localhost:8000
echo Deixe esta janela aberta enquanto testa o split e o Pix.
ngrok http 8000 --url=%URL%
pause
