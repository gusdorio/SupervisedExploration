@echo off
echo "=========================================================="
echo " PASSO 1: Instalando dependencias (requirements.txt)    "
echo "=========================================================="
pip install -r requirements.txt

REM Verifica se a instalacao falhou
if %errorlevel% neq 0 (
    echo "ERRO: Falha ao instalar as dependencias. Abortando."
    pause
    exit /b %errorlevel%
)

echo "Dependencias instaladas com sucesso."
echo.
echo "=========================================================="
echo " PASSO 2: Iniciando compilacao do .exe...                 "
echo "=========================================================="

REM Executa o PyInstaller
pyinstaller --onefile --noconsole --name "AnalisadorCestaBasica" --add-data "SupervisedExploration;SupervisedExploration" run_dashboard.py

REM Verifica se a compilacao falhou
if %errorlevel% neq 0 (
    echo "ERRO: Falha ao compilar o executavel."
    pause
    exit /b %errorlevel%
)

echo.
echo "=========================================================="
echo " Compilacao concluida com sucesso!                        "
echo "=========================================================="
echo "Seu .exe esta na pasta 'dist/'."
echo.
pause