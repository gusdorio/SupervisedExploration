import streamlit.web.cli as stcli
import os
import sys

def get_path(relative_path):
    """ 
    Obtém o caminho absoluto para um recurso. 
    Funciona tanto em desenvolvimento normal quanto no executável do PyInstaller.
    """
    try:
        # O PyInstaller cria uma pasta temporária e armazena o caminho em _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # Se não estiver rodando via PyInstaller, usa o caminho absoluto normal
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)

if __name__ == "__main__":
    # 1. Encontra o caminho para o seu dashboard, que o PyInstaller
    #    colocou dentro da pasta "SupervisedExploration"
    dashboard_file = get_path(os.path.join("SupervisedExploration", "dashboard.py"))
    
    # 2. Muda o diretório de trabalho atual para a pasta do dashboard.
    #    Isso é CRUCIAL para que seu script encontre "./data" e "./classes"
    dashboard_dir = os.path.dirname(dashboard_file)
    os.chdir(dashboard_dir)

    # 3. Monta o comando "streamlit run ..." que será executado
    #    O "--server.headless=true" é importante para o modo .exe
    sys.argv = [
        "streamlit",
        "run",
        dashboard_file,  # Usa o caminho absoluto que encontramos
        "--server.port=8501",
        "--server.headless=true" 
    ]
    
    # 4. Inicia o Streamlit
    stcli.main()