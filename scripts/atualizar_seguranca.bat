@echo off
chcp 65001 >nul
REM Atualiza as bibliotecas do Mercado Nativo para versoes sem falhas conhecidas.
cd /d "%~dp0.."

echo === 1/3 Back-end (Python) ===
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install --upgrade -r backend\requirements.txt
REM Pacotes antigos que o projeto nao usa mais
".venv\Scripts\python.exe" -m pip uninstall -y google-generativeai google-ai-generativelanguage groq passlib 2>nul

echo.
echo === 2/3 Front-end (Node) ===
cd front-mercado
call npm install
cd ..

echo.
echo === 3/3 Versoes instaladas ===
".venv\Scripts\python.exe" -m pip show fastapi starlette urllib3 certifi | findstr /b "Name Version"
cd front-mercado
call npx vite --version
cd ..

echo.
echo Pronto. Pode fechar esta janela.
pause
