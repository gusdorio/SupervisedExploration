@echo off
title Compilador do Analisador de Cesta Basica

REM --- Nomes de arquivos esperados ---
set REQUIREMENTS_FILE=requirements.txt

cls

REM ==========================================================
REM  PASSO 0: VERIFICAR SE O PYTHON ESTA INSTALADO
REM ==========================================================
echo "Verificando instalacao do Python..."
python --version >nul 2>&1

REM Se o comando "python" falhar (errorlevel nao for 0), pule para a secao de instalacao
if %errorlevel% neq 0 (
    echo "Python nao encontrado. Tentando instalar..."
    goto :pythonError
)

echo "Python encontrado. Prosseguindo para a compilacao."
echo.
goto :MainScript

REM ==========================================================
REM  SECAO PRINCIPAL DE COMPILACAO
REM ==========================================================
:MainScript
cls
echo "=========================================================="
echo " PASSO 1: Instalando dependencias e iniciando o venv"
echo "=========================================================="

REM Verifica se o requirements.txt existe
if not exist "%REQUIREMENTS_FILE%" (
    goto :RequirementsMissing
)

REM Garante que o pip esta atualizado e instala o PyInstaller e as dependencias
if not exist ".venv" (
    echo "Criando ambiente virtual (.venv)..."
    python -m venv .venv
)
CALL .\.venv\Scripts\activate.bat
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\pip.exe install -r %REQUIREMENTS_FILE%

REM Verifica se a instalacao falhou
if %errorlevel% neq 0 (
    goto :PipError
)

echo "Dependencias instaladas com sucesso."
echo.
echo "=========================================================="
echo " PASSO 2: Iniciando o dashboard"
echo "=========================================================="

echo "Para encerrar o dashboard, pressione Ctrl+C na janela do terminal que sera aberta."
.venv\Scripts\streamlit.exe run dashboard.py

REM Verifica se a compilacao falhou
if %errorlevel% neq 0 (
    goto :CompileError
)

goto :Success


REM ==========================================================
REM  SECOES DE SUCESSO E ERRO
REM ==========================================================
:Success
cls
echo "----------------------------------------------------------"
echo " COMPILACAO CONCLUIDA COM SUCESSO!"
echo "----------------------------------------------------------"
echo.
pause
exit /b

:RequirementsMissing
cls
echo "----------------------------------------------------------"
echo " ERRO: Arquivo '%REQUIREMENTS_FILE%' nao encontrado."
echo "----------------------------------------------------------"
echo "Nao e possivel instalar as dependencias."
echo "Certifique-se que o arquivo de requisitos esta na mesma pasta."
echo.
pause
exit /b

:PipError
cls
echo "----------------------------------------------------------"
echo " ERRO: Falha ao instalar as dependencias via pip."
echo "----------------------------------------------------------"
echo "Verifique seu arquivo '%REQUIREMENTS_FILE%' e sua conexao"
echo "com a internet. Tente executar o script novamente."
echo.
pause
exit /b

:CompileError
cls
echo "----------------------------------------------------------"
echo " ERRO: Falha ao iniciar o dashboard"
echo "----------------------------------------------------------"
echo " Verifique a inicializacao do venv e as dependencias."
echo.
pause
exit /b

:pythonError
cls
echo "----------------------------------------------------------"
echo " ERRO: O python nao esta instalado"
echo " ou nao foi adicionado ao PATH do sistema."
echo "----------------------------------------------------------"
echo " Faca a instalacao do Python (ex: 3.10) a partir de python.org"
echo " e marque a opcao 'Add Python to PATH' durante a instalacao."
echo.
pause
exit /b