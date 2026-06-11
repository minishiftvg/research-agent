@echo off
:: Impedisce la visualizzazione dei singoli comandi a schermo per pulizia
chcp 65001 > nul
echo Creazione della struttura del progetto 'research-agent' in corso...
echo.

:: 1. Crea la cartella principale del progetto ed entra all'interno
mkdir "research-agent"
cd "research-agent"

:: 2. Crea la sottocartella app
mkdir "app"

:: 3. Crea i file all'interno della cartella app
echo # Inizializzazione modulo Python > "app\__init__.py"
echo # Configurazione centralizzata > "app\config.py"
echo # Strutture dati (dataclass/TypedDict) > "app\models.py"
echo # Tool disponibili agli agenti > "app\tools.py"
echo # Sotto-agente: genera il piano > "app\planner.py"
echo # Sotto-agente: esegue le ricerche > "app\researcher.py"
echo # Sotto-agente: scrive il report > "app\writer.py"
echo # Orchestratore: coordina tutto > "app\agent.py"
echo # Server Flask + endpoint > "app\main.py"

:: 4. Crea i file nella root del progetto
echo # Variabili d'ambiente > ".env"
echo .env > ".gitignore"
echo flask >> ".gitignore"
echo # Dipendenze del progetto > "requirements.txt"
echo ### Test VSCode REST Client > "test_local.http"

echo.
echo Struttura creata con successo!
echo.
tree /F
pause