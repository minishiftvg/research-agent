# app/telegram_sender.py
# Invia messaggi Telegram direttamente dal backend.
# Usato per mandare il report quando è pronto,
# senza aspettare Make.com (che andrebbe in timeout).

import httpx
import os
from app.config import config


async def send_message(chat_id: str, text: str) -> bool:
    """
    Invia un messaggio Telegram tramite Bot API.
    
    Args:
        chat_id: ID della chat (arriva da Make.com)
        text: Testo del messaggio
        
    Returns:
        True se inviato con successo
    """
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    
    if not token:
        print("[Telegram] TELEGRAM_BOT_TOKEN non configurato")
        return False

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": text,
                    # Markdown permette grassetto, corsivo ecc.
                    "parse_mode": "Markdown"
                },
                timeout=10.0
            )

            if response.status_code == 200:
                print(f"[Telegram] Messaggio inviato a chat {chat_id}")
                return True
            else:
                print(f"[Telegram] Errore: {response.status_code} - {response.text}")
                return False

    except Exception as e:
        print(f"[Telegram] Eccezione: {e}")
        return False


async def send_typing(chat_id: str) -> None:
    """
    Invia l'indicatore 'sta scrivendo...' su Telegram.
    Migliora l'esperienza utente durante l'elaborazione.
    """
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    if not token:
        return

    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"https://api.telegram.org/bot{token}/sendChatAction",
                json={
                    "chat_id": chat_id,
                    "action": "typing"
                },
                timeout=5.0
            )
    except Exception:
        pass  # Non critico se fallisce