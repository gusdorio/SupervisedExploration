@echo off
title Compilador do Analisador de Cesta Basica

REM --- Nomes de arquivos esperados ---
set PYTHON_INSTALLER_NAME=python-installer.exe
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
    goto :InstallPython
)

echo "Python encontrado. Prosseguindo para a compilacao."
echo.
goto :MainScript

REM ==========================================================
REM  SECAO DE INSTALACAO DO PYTHON (so executa se necessario)
REM ==========================================================
:InstallPython
cls
echo "----------------------------------------------------------"
echo " AVISO: Python nao esta instalado no sistema."
echo "----------------------------------------------------------"
echo "Procurando pelo instalador: '%PYTHON_INSTALLER_NAME%'"

REM Verifica se o instalador (que voce baixou) esta na pasta
if not exist "%PYTHON_INSTALLER_NAME%" (
    goto :PythonInstallerMissing
)

echo "Instalador encontrado. Iniciando instalacao silenciosa..."
echo "Aguarde, isso pode levar alguns minutos."
echo "O UAC (Controle de Conta de Usuario) pode solicitar permissao."

REM Executa o instalador do Python silenciosamente, para todos os usuarios, e ADICIONA AO PATH
start /wait %PYTHON_INSTALLER_NAME% /quiet InstallAllUsers=1 PrependPath=1 Include_pip=1

cls
echo "----------------------------------------------------------"
echo " INSTALACAO DO PYTHON CONCLUIDA"
echo "----------------------------------------------------------"
echo "IMPORTANTE: O terminal precisa ser reiniciado para"
echo "reconhecer a nova instalacao do Python."
echo.
echo "Por favor, FECHE esta janela e execute 'compilar.bat' NOVAMENTE."
echo.
pause
exit /b


REM ==========================================================
REM  SECAO PRINCIPAL DE COMPILACAO
REM ==========================================================
:MainScript
cls
echo "=========================================================="
echo " PASSO 1: Instalando dependencias e PyInstaller"
echo "=========================================================="

REM Verifica se o requirements.txt existe
if not exist "%REQUIREMENTS_FILE%" (
    goto :RequirementsMissing
)

REM Garante que o pip esta atualizado e instala o PyInstaller e as dependencias
python -m pip install --upgrade pip
pip install -U pyinstaller
pip install -r %REQUIREMENTS_FILE%

REM Verifica se a instalacao falhou
if %errorlevel% neq 0 (
    goto :PipError
)

echo "Dependencias instaladas com sucesso."
echo.
echo "=========================================================="
echo " PASSO 2: Iniciando compilacao do .exe..."
echo "=========================================================="

pyinstaller --onefile --noconsole --name "AnalisadorCestaBasica" --add-data "SupervisedExploration;SupervisedExploration" run_dashboard.py

REM Verifica se a compilacao falhou
if %errorlevel% neq 0 (
    goto :PyInstallerError
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
echo "O seu executavel esta na pasta 'dist/'."
echo "Arquivo: dist/AnalisadorCestaBasica.exe"
echo.
pause
exit /b

:PythonInstallerMissing
cls
echo "----------------------------------------------------------"
echo " ERRO: ACAO MANUAL NECESSARIA"
echo "----------------------------------------------------------"
echo "O script nao encontrou o Python, e o instalador nao esta na pasta."
echo.
echo "1. Baixe o instalador do Python (ex: v3.10) de python.org"
echo "2. Salve o .exe nesta mesma pasta com o nome: %PYTHON_INSTALLER_NAME%"
echo "3. Execute este script 'compilar.bat' novamente."
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

:PyInstallerError
cls
echo "----------------------------------------------------------"
echo " ERRO: Falha durante a compilacao com PyInstaller."
echo "----------------------------------------------------------"
echo "Ocorreu um erro ao tentar gerar o arquivo .exe."
echo "Verifique as mensagens de erro no console acima."
echo.
pause
exit /b