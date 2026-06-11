# Server Flask + endpoint 
# app/main.py
# Server Flask con gli endpoint per Make.com e Telegram.

from flask import Flask, request, jsonify
from app.agent import agent
from app.config import config
import asyncio
import time

app = Flask(__name__)


def run_async(coro):
    """Esegue una coroutine async in contesto sincrono Flask."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def check_auth() -> bool:
    """Verifica il secret nell'header della richiesta."""
    return request.headers.get('X-Webhook-Secret') == config.WEBHOOK_SECRET


@app.route('/')
def root():
    return jsonify({"status": "online", "agent": "Research & Report Agent"})


@app.route('/health')
def health():
    return jsonify({
        "status": "healthy",
        "model_main": config.MODEL_MAIN,
        "model_fast": config.MODEL_FAST,
        "max_questions": config.MAX_RESEARCH_QUESTIONS
    })


@app.route('/research', methods=['POST'])
def research():
    """
    Endpoint principale: riceve un topic e restituisce il report completo.
    
    Body JSON:
        {"message": "intelligenza artificiale nel settore medico"}
        
    Response JSON:
        {
          "success": true,
          "topic": "...",
          "report": "testo formattato per Telegram",
          "report_data": { sezioni strutturate },
          "stats": { tempi e conteggi }
        }
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


@app.route('/webhook/make', methods=['POST'])
def make_webhook():
    """Endpoint ottimizzato per Make.com."""
    if not check_auth():
        return jsonify({"detail": "Non autorizzato"}), 403

    body = request.get_json() or {}
    message = (
        body.get("message") or
        body.get("text") or
        body.get("data", {}).get("message") or
        str(body)
    )

    if not message:
        return jsonify({"detail": "Messaggio mancante"}), 400

    result = run_async(agent.run(message))

    return jsonify({
        "success": result["success"],
        "report": result["report"],
        "topic": result.get("topic", ""),
        "stats": result.get("stats", {})
    })


if __name__ == '__main__':
    app.run(debug=True, port=8000)
