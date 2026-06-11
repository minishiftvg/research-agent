# Configurazione centralizzata 
# app/config.py
#
# Gestione centralizzata della configurazione.
# Tutti i parametri dell'applicazione vengono letti da qui.
# Modificare un parametro qui lo cambia in tutta l'app.

import os
from pathlib import Path
from dotenv import load_dotenv

# Path assoluto al file .env
# Path(__file__) = percorso di config.py
# .parent = cartella app/
# .parent = cartella root del progetto
# / '.env' = file .env nella root
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

class Config:
    """
    Configurazione dell'applicazione letta da variabili d'ambiente.
    
    Pattern Singleton: viene creata una sola istanza (config)
    usata da tutti i moduli dell'applicazione.
    """

    # --- OpenRouter ---
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_BASE_URL: str = os.getenv(
        "OPENROUTER_BASE_URL",
        "https://openrouter.ai/api/v1"
    )

    # Modello principale per ragionamento complesso
    # GPT-4o-mini: buon equilibrio qualità/velocità/costo
    MODEL_MAIN: str = os.getenv("MODEL_MAIN", "openai/gpt-4o-mini")

    # Modello veloce per task semplici (es. classificazione, estrazione)
    # Haiku è molto più veloce e costa meno di GPT-4o-mini
    MODEL_FAST: str = os.getenv("MODEL_FAST", "anthropic/claude-3-haiku")

    # --- Sicurezza ---
    WEBHOOK_SECRET: str = os.getenv("WEBHOOK_SECRET", "changeme")

    # --- Limiti operativi ---
    # Numero massimo di domande nel piano di ricerca
    MAX_RESEARCH_QUESTIONS: int = int(os.getenv("MAX_RESEARCH_QUESTIONS", "4"))

    # Numero massimo di retry per ogni ricerca web
    MAX_RETRY: int = int(os.getenv("MAX_RETRY", "2"))

    # Timeout per le richieste HTTP ai tool esterni (secondi)
    HTTP_TIMEOUT: int = int(os.getenv("HTTP_TIMEOUT", "15"))

    def validate(self) -> None:
        """Verifica che la configurazione minima sia presente."""
        if not self.OPENROUTER_API_KEY:
            raise ValueError(
                "OPENROUTER_API_KEY mancante nel file .env"
            )

# Istanza globale — importata dagli altri moduli
config = Config()
