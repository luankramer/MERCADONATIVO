@echo off
chcp 65001 >nul
title Mercado Nativo - Testes
rem Roda os testes automaticos do backend (usam um banco temporario, nao mexem no MySQL)
cd /d "%~dp0..\backend"
"..\.venv\Scripts\python.exe" -m pytest -q
pause
