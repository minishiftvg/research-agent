# Sotto-agente: genera il piano 
# app/planner.py
#
# Il Planner è il primo sotto-agente della pipeline.
# Il suo unico compito è: ricevere un argomento e produrre
# un piano strutturato di ricerca (lista di domande chiave).
#
# Separare il planning dall'esecuzione è un pattern fondamentale
# negli agent AI avanzati perché:
# 1. Permette di verificare il piano prima di eseguirlo
# 2. Ogni agente è ottimizzato per un solo compito
# 3. Facilita il debugging (sai esattamente dove fallisce)

import json
from openai import AsyncOpenAI
from app.config import config
from app.models import ResearchPlan, ResearchQuestion

# System prompt del Planner.
# È molto specifico: dice esattamente cosa produrre e in che formato.
# L'output JSON strutturato è fondamentale per parsare la risposta
# in modo affidabile nel codice Python.
PLANNER_SYSTEM_PROMPT = """Sei un esperto pianificatore di ricerche.
Il tuo compito è analizzare un argomento e generare un piano
di ricerca strutturato con domande chiave.

ISTRUZIONI:
1. Analizza l'argomento ricevuto
2. Identifica i 4 aspetti più importanti da investigare
3. Per ogni aspetto, formula una domanda di ricerca specifica
4. Rispondi ESCLUSIVAMENTE in formato JSON valido

FORMATO OUTPUT (JSON obbligatorio):
{
  "topic_analysis": "breve analisi dell'argomento in 1-2 frasi",
  "questions": [
    {
      "question": "domanda di ricerca specifica",
      "focus": "aspetto specifico da estrarre (es: definizione, statistiche, esempi, trend)"
    }
  ]
}

Non aggiungere testo prima o dopo il JSON. Solo JSON puro."""


class Planner:
    """
    Sotto-agente responsabile della pianificazione della ricerca.
    
    Riceve un argomento grezzo dall'utente e produce un piano
    strutturato con domande specifiche da ricercare.
    """

    def __init__(self):
        # Client OpenAI configurato per OpenRouter
        self.client = AsyncOpenAI(
            api_key=config.OPENROUTER_API_KEY,
            base_url=config.OPENROUTER_BASE_URL
        )

    async def create_plan(self, topic: str) -> ResearchPlan:
        """
        Genera il piano di ricerca per l'argomento dato.
        
        Args:
            topic: L'argomento da ricercare (input dell'utente)
            
        Returns:
            ResearchPlan con le domande generate dal LLM
        """
        print(f"\n[Planner] Generazione piano per: '{topic}'")

        # Chiediamo al LLM di generare il piano
        response = await self.client.chat.completions.create(
            model=config.MODEL_MAIN,
            messages=[
                {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
                {"role": "user", "content": f"Argomento da ricercare: {topic}"}
            ],
            # temperature=0 rende l'output deterministico e strutturato
            # Per task creativi si usa temperature alta (0.7-1.0)
            # Per task strutturati (come generare JSON) si usa 0
            temperature=0,
            max_tokens=800
        )

        raw_output = response.choices[0].message.content
        print(f"[Planner] Output LLM ricevuto ({len(raw_output)} caratteri)")

        # Parsa il JSON restituito dal LLM
        plan_data = self._parse_plan_json(raw_output, topic)

        # Costruisci l'oggetto ResearchPlan dai dati parsati
        questions = []
        for q_data in plan_data.get("questions", [])[:config.MAX_RESEARCH_QUESTIONS]:
            questions.append(ResearchQuestion(
                question=q_data.get("question", ""),
                focus=q_data.get("focus", "generale")
            ))

        plan = ResearchPlan(
            topic=topic,
            questions=questions,
            context=plan_data.get("topic_analysis", "")
        )

        print(f"[Planner] Piano creato con {len(questions)} domande:")
        for i, q in enumerate(questions, 1):
            print(f"  {i}. {q.question}")

        return plan

    def _parse_plan_json(self, raw_output: str, topic: str) -> dict:
        """
        Parsa il JSON restituito dal LLM con gestione degli errori.
        
        L'LLM a volte aggiunge testo prima o dopo il JSON,
        o usa formattazione Markdown (```json ... ```).
        Questo metodo gestisce questi casi comuni.
        
        Args:
            raw_output: Output grezzo del LLM
            topic: Usato per creare un piano di fallback
            
        Returns:
            Dizionario Python con i dati del piano
        """
        # Pulizia: rimuovi eventuali blocchi markdown ```json ... ```
        cleaned = raw_output.strip()
        if cleaned.startswith("```"):
            # Rimuovi la prima riga (```json) e l'ultima (```)
            lines = cleaned.split("\n")
            cleaned = "\n".join(lines[1:-1])

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            print(f"[Planner] Errore parsing JSON: {e}")
            print(f"[Planner] Output grezzo: {raw_output[:200]}")

            # Piano di fallback: se il LLM non produce JSON valido,
            # creiamo un piano generico per non bloccare l'esecuzione
            return {
                "topic_analysis": f"Ricerca su: {topic}",
                "questions": [
                    {"question": f"Cos'è {topic}?", "focus": "definizione"},
                    {"question": f"Quali sono le applicazioni di {topic}?", "focus": "applicazioni"},
                    {"question": f"Quali sono i vantaggi e svantaggi di {topic}?", "focus": "analisi"},
                    {"question": f"Quali sono i trend recenti di {topic}?", "focus": "trend"}
                ]
            }
