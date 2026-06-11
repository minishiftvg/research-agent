# Tool disponibili agli agenti 
# app/tools.py
#
# Strumenti disponibili agli agenti.
# Rispetto alla versione base, aggiungiamo:
# - Retry automatico con backoff esponenziale
# - Estrazione più ricca dai risultati di ricerca
# - Tool per analisi del testo
# - Logging dettagliato per debugging

import httpx
import asyncio
import time
from datetime import datetime


# ============================================================
# SCHEMA DEI TOOL (formato OpenAI function calling)
# ============================================================
# Questi schemi vengono inviati all'LLM per descrivere
# quali tool sono disponibili e come usarli.

TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": (
                "Cerca informazioni su internet su un argomento specifico. "
                "Restituisce un riassunto delle informazioni trovate. "
                "Usa query brevi e specifiche per risultati migliori."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Query di ricerca (max 10 parole, specifica)"
                    },
                    "focus": {
                        "type": "string",
                        "description": "Aspetto specifico su cui concentrarsi nei risultati"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "Esegue calcoli matematici su espressioni Python.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "Espressione matematica Python valida"
                    }
                },
                "required": ["expression"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_datetime",
            "description": "Restituisce data e ora corrente.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }
]


# ============================================================
# IMPLEMENTAZIONE DEI TOOL
# ============================================================

async def search_web(query: str, focus: str = "") -> str:
    """
    Ricerca web con retry automatico.
    
    Retry con backoff esponenziale: se la prima richiesta fallisce,
    aspetta 1 secondo e riprova. Se fallisce ancora, aspetta 2 secondi.
    Questo evita di sovraccaricare il server e gestisce
    problemi di rete temporanei.
    
    Args:
        query: Termini di ricerca
        focus: Aspetto specifico da estrarre dai risultati
        
    Returns:
        Stringa con i risultati trovati
    """
    max_retries = 3

    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.duckduckgo.com/",
                    params={
                        "q": query,
                        "format": "json",
                        "no_html": "1",
                        "skip_disambig": "1"
                    },
                    timeout=15.0
                )

                if response.status_code == 200:
                    data = response.json()
                    results = []

                    # Abstract principale
                    if data.get("Abstract"):
                        results.append(f"Informazione principale: {data['Abstract']}")
                        if data.get("AbstractURL"):
                            results.append(f"Fonte: {data['AbstractURL']}")

                    # Risultati correlati (fino a 5)
                    topics = data.get("RelatedTopics", [])[:5]
                    for topic in topics:
                        if isinstance(topic, dict) and topic.get("Text"):
                            results.append(f"• {topic['Text']}")

                    # Risposta diretta (es. per domande fattuali)
                    if data.get("Answer"):
                        results.append(f"Risposta diretta: {data['Answer']}")

                    if results:
                        output = f"Risultati per '{query}':\n" + "\n".join(results)
                        # Se è specificato un focus, aggiungiamo un'istruzione
                        if focus:
                            output += f"\n[Focus richiesto: {focus}]"
                        return output
                    else:
                        return f"Nessun risultato trovato per: {query}"

        except httpx.TimeoutException:
            # Backoff esponenziale: aspetta 2^attempt secondi
            # Attempt 0 → 1 sec, attempt 1 → 2 sec, attempt 2 → 4 sec
            wait_time = 2 ** attempt
            print(f"[Tool] Timeout ricerca (tentativo {attempt+1}/{max_retries}), "
                  f"riprovo tra {wait_time}s...")
            await asyncio.sleep(wait_time)

        except Exception as e:
            print(f"[Tool] Errore ricerca: {e}")
            if attempt == max_retries - 1:
                return f"Ricerca fallita dopo {max_retries} tentativi: {str(e)}"
            await asyncio.sleep(1)

    return f"Ricerca '{query}' non riuscita dopo {max_retries} tentativi."


def calculate(expression: str) -> str:
    """Calcolo matematico sicuro."""
    safe_namespace = {
        "__builtins__": {},
        "abs": abs, "round": round, "min": min,
        "max": max, "sum": sum, "pow": pow,
        "int": int, "float": float
    }
    try:
        result = eval(expression, safe_namespace)
        return f"Risultato: {result}"
    except ZeroDivisionError:
        return "Errore: divisione per zero"
    except Exception as e:
        return f"Errore nel calcolo: {str(e)}"


def get_current_datetime() -> str:
    """Data e ora corrente."""
    return datetime.now().strftime("Data: %d/%m/%Y, Ora: %H:%M:%S")


async def execute_tool(tool_name: str, tool_args: dict) -> str:
    """
    Dispatcher: esegue il tool richiesto dall'LLM.
    Centralizza la logica di routing verso le funzioni corrette.
    """
    print(f"[Tool] Esecuzione: {tool_name}({tool_args})")

    if tool_name == "search_web":
        return await search_web(
            tool_args.get("query", ""),
            tool_args.get("focus", "")
        )
    elif tool_name == "calculate":
        return calculate(tool_args.get("expression", ""))
    elif tool_name == "get_current_datetime":
        return get_current_datetime()
    else:
        return f"Tool '{tool_name}' non disponibile."
