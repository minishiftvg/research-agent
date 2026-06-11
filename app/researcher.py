# Sotto-agente: esegue le ricerche 
# app/researcher.py
#
# Il Researcher è il secondo sotto-agente.
# Per ogni domanda del piano, esegue ricerche web reali
# e raccoglie le informazioni trovate.
#
# Usa il tool calling per invocare search_web in modo strutturato,
# permettendo all'LLM di raffinare la query se necessario.

import json
import asyncio
from openai import AsyncOpenAI
from app.config import config
from app.models import ResearchPlan, ResearchQuestion, ResearchStatus
from app.tools import TOOLS_SCHEMA, execute_tool

RESEARCHER_SYSTEM_PROMPT = """Sei un ricercatore esperto e meticoloso.
Il tuo compito è trovare informazioni accurate e rilevanti
usando il tool search_web.

ISTRUZIONI:
1. Ricevi una domanda di ricerca e un focus specifico
2. Formula 1-2 query di ricerca efficaci (brevi, specifiche)
3. Usa search_web per trovare le informazioni
4. Se la prima ricerca non è soddisfacente, prova con una query diversa
5. Sintetizza le informazioni trovate in modo chiaro e conciso
6. Rispondi in italiano
7. Sii obiettivo e basati solo sulle informazioni trovate"""


class Researcher:
    """
    Sotto-agente responsabile dell'esecuzione delle ricerche.
    
    Per ogni domanda nel piano di ricerca:
    1. Formula una query ottimizzata per la ricerca web
    2. Esegue la ricerca tramite tool calling
    3. Sintetizza i risultati in un testo strutturato
    """

    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=config.OPENROUTER_API_KEY,
            base_url=config.OPENROUTER_BASE_URL
        )

    async def research_all(self, plan: ResearchPlan) -> ResearchPlan:
        """
        Esegue tutte le ricerche del piano in sequenza.
        
        Nota: le ricerche vengono eseguite in SEQUENZA (una alla volta)
        e non in parallelo. Questo è più lento ma:
        - Evita di sovraccaricare le API esterne
        - Permette di usare i risultati precedenti come contesto
        - È più facile da debuggare
        
        In un sistema di produzione avanzato si potrebbe usare
        asyncio.gather() per parallelizzare le ricerche indipendenti.
        
        Args:
            plan: Il piano con le domande da ricercare
            
        Returns:
            Lo stesso piano con i risultati aggiunti alle domande
        """
        print(f"\n[Researcher] Inizio ricerca per {len(plan.questions)} domande")

        for i, question in enumerate(plan.questions, 1):
            print(f"\n[Researcher] Ricerca {i}/{len(plan.questions)}: {question.question}")

            # Esegui la ricerca con retry automatico
            success = await self._research_question(question, plan.topic)

            if success:
                print(f"[Researcher] ✓ Domanda {i} completata")
            else:
                print(f"[Researcher] ✗ Domanda {i} fallita")

            # Piccola pausa tra le ricerche per non sovraccaricare le API
            # (rate limiting prevention)
            if i < len(plan.questions):
                await asyncio.sleep(0.5)

        completed = len(plan.completed_questions)
        print(f"\n[Researcher] Completato: {completed}/{len(plan.questions)} ricerche")

        return plan

    async def _research_question(
        self,
        question: ResearchQuestion,
        topic: str
    ) -> bool:
        """
        Ricerca una singola domanda usando il ciclo tool calling.
        
        Implementa il pattern ReAct per questa singola domanda:
        - Reason: il LLM decide quale query usare
        - Act: chiama search_web
        - Observe: legge i risultati
        - Reason: decide se i risultati sono sufficienti
        
        Args:
            question: La domanda da ricercare
            topic: Contesto generale (argomento principale)
            
        Returns:
            True se la ricerca ha avuto successo, False altrimenti
        """
        # Costruisci il messaggio per il Researcher
        # Includiamo sia la domanda specifica che il contesto generale
        user_message = (
            f"Argomento generale: {topic}\n"
            f"Domanda specifica: {question.question}\n"
            f"Focus richiesto: {question.focus}\n\n"
            f"Cerca informazioni per rispondere a questa domanda."
        )

        messages = [
            {"role": "system", "content": RESEARCHER_SYSTEM_PROMPT},
            {"role": "user", "content": user_message}
        ]

        # Il Researcher ha max 3 iterazioni per trovare la risposta
        # (può fare 2-3 ricerche web prima di sintetizzare)
        max_iterations = 3

        for iteration in range(max_iterations):
            response = await self.client.chat.completions.create(
                model=config.MODEL_MAIN,
                messages=messages,
                tools=TOOLS_SCHEMA,
                tool_choice="auto",
                max_tokens=1000,
                temperature=0.3   # Bassa temperatura per ricerche fattuali
            )

            assistant_message = response.choices[0].message
            messages.append(assistant_message)

            if assistant_message.tool_calls:
                # Il Researcher vuole usare un tool → eseguilo
                for tool_call in assistant_message.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments)

                    tool_result = await execute_tool(tool_name, tool_args)

                    # Aggiungi il risultato alla conversazione
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": tool_result
                    })
            else:
                # Nessun tool richiesto → il Researcher ha la sua sintesi
                result_text = assistant_message.content or ""

                if result_text and len(result_text) > 20:
                    # Salva il risultato nella domanda
                    question.result = result_text
                    question.status = ResearchStatus.COMPLETED
                    return True
                else:
                    # Risposta troppo corta → considera come fallimento
                    question.status = ResearchStatus.FAILED
                    return False

        # Superato il limite di iterazioni
        question.status = ResearchStatus.FAILED
        return False
