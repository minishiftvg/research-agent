# app/main.py
# Server Flask con gestione asincrona delle richieste.
#
# FLUSSO ASINCRONO:
# 1. Make.com invia il messaggio al webhook
# 2. Il server risponde SUBITO con 200 OK
# 3. Un thread in background elabora la richiesta
# 4. Quando il report è pronto, viene inviato direttamente su Telegram
# 5. Make.com non aspetta mai → niente timeout!

from flask import Flask, request, jsonify
from app.agent import agent
from app.config import config
from app.telegram_sender import send_message, send_typing
import asyncio
import threading
import time

app = Flask(__name__)


def check_auth() -> bool:
    """Verifica il secret nell'header."""
    return request.headers.get('X-Webhook-Secret') == config.WEBHOOK_SECRET


def run_async(coro):
    """Esegue una coroutine async in contesto sincrono Flask."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def process_and_send(message: str, chat_id: str):
    """
    Elabora la richiesta in background e invia il risultato su Telegram.
    
    Questa funzione gira in un thread separato — Flask risponde
    subito a Make.com mentre questa continua a lavorare in background.
    
    Args:
        message: Il testo ricevuto da Telegram
        chat_id: ID della chat per inviare la risposta
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        print(f"[Background] Inizio elaborazione: '{message}'")

        # Invia indicatore "sta scrivendo..." su Telegram
        # così l'utente sa che il bot sta lavorando
        loop.run_until_complete(send_typing(chat_id))

        # Esegui la pipeline completa dell'agente
        result = loop.run_until_complete(agent.run(message))

        # Invia il report su Telegram
        if chat_id:
            loop.run_until_complete(
                send_message(chat_id, result["report"])
            )

            # Se ci sono statistiche, invia un messaggio aggiuntivo
            stats = result.get("stats", {})
            if stats:
                stats_text = (
                    f"📈 *Stats:* "
                    f"{stats.get('questions_completed', 0)}/"
                    f"{stats.get('questions_planned', 0)} ricerche • "
                    f"{stats.get('total_time_seconds', 0)}s"
                )
                loop.run_until_complete(
                    send_message(chat_id, stats_text)
                )

        print(f"[Background] Elaborazione completata per chat {chat_id}")

    except Exception as e:
        print(f"[Background] Errore: {e}")

        # Informa l'utente dell'errore direttamente su Telegram
        if chat_id:
            loop.run_until_complete(
                send_message(
                    chat_id,
                    f"❌ Errore durante la ricerca.\nRiprova tra qualche secondo."
                )
            )
    finally:
        loop.close()


# ============================================================
# ENDPOINTS
# ============================================================

@app.route('/')
def root():
    return jsonify({
        "status": "online",
        "agent": "Research & Report Agent",
        "mode": "async"
    })


@app.route('/health')
def health():
    return jsonify({
        "status": "healthy",
        "model": config.MODEL_MAIN,
        "max_questions": config.MAX_RESEARCH_QUESTIONS
    })


@app.route('/webhook/make', methods=['POST'])
def make_webhook():
    """
    Endpoint principale per Make.com.
    
    Risponde IMMEDIATAMENTE con 200 OK e avvia
    l'elaborazione in un thread separato.
    Niente timeout!
    """
    if not check_auth():
        return jsonify({"detail": "Non autorizzato"}), 403

    body = request.get_json() or {}

    # Estrai messaggio e chat_id dal payload di Make.com
    message = (
        body.get("message") or
        body.get("text") or
        str(body)
    )
    chat_id = str(body.get("chat_id", ""))

    if not message:
        return jsonify({"detail": "Messaggio mancante"}), 400

    if not chat_id:
        return jsonify({"detail": "chat_id mancante"}), 400

    print(f"[Webhook] Ricevuto da chat {chat_id}: '{message}'")

    # Avvia elaborazione in background
    thread = threading.Thread(
        target=process_and_send,
        args=(message, chat_id),
        daemon=True  # Il thread si chiude quando il server si chiude
    )
    thread.start()

    # Risposta immediata a Make.com — non aspetta il thread!
    return jsonify({
        "success": True,
        "status": "processing",
        "message": "Ricerca avviata"
    })


@app.route('/agent', methods=['POST'])
def run_agent_sync():
    """
    Endpoint sincrono per test diretti da VSCode/curl.
    Aspetta la risposta completa (può andare in timeout su PA).
    Usalo solo per test locali o con argomenti molto semplici.
    """
    if not check_auth():
        return jsonify({"detail": "Non autorizzato"}), 403

    data = request.get_json()
    if not data or not data.get('message'):
        return jsonify({"detail": "Campo 'message' mancante"}), 400

    start = time.time()
    result = run_async(agent.run(data['message']))
    result['execution_time_ms'] = int((time.time() - start) * 1000)

    return jsonify(result)


if __name__ == '__main__':
    app.run(debug=True, port=8000)