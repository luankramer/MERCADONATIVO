@echo off
chcp 65001 >nul
title Mercado Nativo - enviar para o GitHub
rem Envia o projeto para https://github.com/luankramer/MERCADONATIVO
rem Na primeira vez junta com o README que ja esta no GitHub; nas proximas so envia as mudancas.
cd /d "%~dp0.."
set "REPO=https://github.com/luankramer/MERCADONATIVO.git"

where git >nul 2>nul || (
  echo Git nao encontrado. Instale com:  winget install Git.Git
  echo Depois feche e abra esta janela de novo.
  pause & exit /b 1
)

if not exist ".git" (
  git init -q
  git branch -M main
)
git remote get-url origin >nul 2>nul || git remote add origin %REPO%

rem Nome e e-mail dos commits (so define se ainda nao existir)
for /f "delims=" %%n in ('git config user.name') do set "NOME=%%n"
if not defined NOME git config user.name "Cleyton Luan Kramer Vieira"
for /f "delims=" %%e in ('git config user.email') do set "EMAIL=%%e"
if not defined EMAIL git config user.email "cleytonkramer@outlook.com"

git add -A

rem Trava de seguranca: nunca enviar senhas, ambiente Python ou backups
git diff --cached --name-only | findstr /r /i "\.env$ \.venv/ node_modules/ _backups/ backend/uploads/" >nul && (
  echo.
  echo PAREI: algum arquivo secreto ou pesado entrou na lista. Nada foi enviado.
  git diff --cached --name-only | findstr /r /i "\.env$ \.venv/ node_modules/ _backups/ backend/uploads/"
  git reset -q
  pause & exit /b 1
)

echo.
echo Arquivos novos ou alterados:
git status --short
echo.
set "MSG="
set /p "MSG=Descreva a mudanca (Enter = Atualiza o Mercado Nativo): "
if not defined MSG set "MSG=Atualiza o Mercado Nativo"

git diff --cached --quiet || git commit -q -m "%MSG%"

rem Primeira vez: junta com o README do GitHub, mantendo o README do projeto
git fetch -q origin
git rev-parse --verify -q origin/main >nul && (
  git merge-base --is-ancestor origin/main HEAD || git pull -q origin main --allow-unrelated-histories -X ours --no-edit
)

git push -u origin main
if errorlevel 1 (
  echo.
  echo O envio falhou. Copie a mensagem acima e mande para o Claude.
) else (
  echo.
  echo Pronto! Veja em https://github.com/luankramer/MERCADONATIVO
)
pause
