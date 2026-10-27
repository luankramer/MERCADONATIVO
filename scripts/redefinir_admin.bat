@echo off
chcp 65001 >nul
title Mercado Nativo - Administrador
rem Cria o primeiro administrador ou troca a senha
cd /d "%~dp0..\backend"
"..\.venv\Scripts\python.exe" -m app.reset_admin %*
pause
