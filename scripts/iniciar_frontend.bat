@echo off
chcp 65001 >nul
title Mercado Nativo - Site
rem Abre o site em http://localhost:5173 (deixe esta janela aberta)
cd /d "%~dp0..\front-mercado"
if not exist "node_modules" call npm install
call npm run dev -- --open
pause
