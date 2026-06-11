# Orchestratore: coordina tutto 
# app/agent.py
#
# L'Orchestratore coordina i tre sotto-agenti in sequenza.
# È il "direttore d'orchestra" che:
# 1. Riceve la richiesta dell'utente
# 2. Passa il topic al Planner
# 3. Passa il piano al Researcher
# 4. Passa i risultati al Writer
# 5. Restituisce il report finale
#
# Questo pattern si chiama "Pipeline" o "Chain of Responsibility":
# ogni componente fa una cosa sola e passa il risultato al successivo.

import time
from app.config import config
from app.planner import Planner
from app.researcher import Researcher
from app.writer import Writer


class ResearchAgent:
    """
    Orchestratore della pipeline di ricerca.
    
    Coordina Planner → Researcher → Writer in sequenza,
    gestendo errori e tracciando i tempi di esecuzione.
    """

    def __init__(self):
        config.validate()

        # Inizializza i tre sotto-agenti
        # Ognuno ha il suo client OpenAI e system prompt dedicato
        self.planner = Planner()
        self.researcher = Researcher()
        self.writer = Writer()

        print("[Agent] ResearchAgent inizializzato")

    async def run(self, user_input: str) -> dict:
        """
        Esegue la pipeline completa di ricerca e report.
        
        Args:
            user_input: Messaggio grezzo dell'utente
            
        Returns:
            Dizionario con il report e metadati sull'esecuzione
        """
        start_time = time.time()

        print(f"\n{'='*60}")
        print(f"[Agent] Nuova richiesta: {user_input}")
        print(f"{'='*60}")

        # Estrai il topic dal messaggio dell'utente
        # Rimuove prefissi comuni come "ricerca su:", "dimmi di:", ecc.
        topic = self._extract_topic(user_input)
        print(f"[Agent] Topic estratto: '{topic}'")

        try:
            # ── FASE 1: PLANNING ────────────────────────────────────
            print("\n[Agent] === FASE 1: PLANNING ===")
            t1 = time.time()
            plan = await self.planner.create_plan(topic)
            planning_time = round(time.time() - t1, 2)
            print(f"[Agent] Planning completato in {planning_time}s")

            # Verifica che il piano abbia domande valide
            if not plan.questions:
                return self._error_response("Impossibile generare il piano di ricerca.")

            # ── FASE 2: RESEARCH ─────────────────────────────────────
            print("\n[Agent] === FASE 2: RESEARCH ===")
            t2 = time.time()
            plan = await self.researcher.research_all(plan)
            research_time = round(time.time() - t2, 2)
            print(f"[Agent] Research completato in {research_time}s")

            # Verifica che almeno alcune ricerche abbiano avuto successo
            if not plan.completed_questions:
                return self._error_response(
                    "Nessuna ricerca completata con successo. "
                    "Riprova con un argomento diverso."
                )

            # ── FASE 3: WRITING ──────────────────────────────────────
            print("\n[Agent] === FASE 3: WRITING ===")
            t3 = time.time()
            report = await self.writer.write_report(plan)
            writing_time = round(time.time() - t3, 2)
            print(f"[Agent] Writing completato in {writing_time}s")

            # ── RISULTATO FINALE ─────────────────────────────────────
            total_time = round(time.time() - start_time, 2)

            print(f"\n[Agent] ✓ Pipeline completata in {total_time}s totali")
            print(f"  Planning:  {planning_time}s")
            print(f"  Research:  {research_time}s")
            print(f"  Writing:   {writing_time}s")

            return {
                "success": True,
                "topic": topic,
                "report": report.telegram_version,
                "report_data": {
                    "executive_summary": report.executive_summary,
                    "sections": report.sections,
                    "key_points": report.key_points,
                    "conclusion": report.conclusion
                },
                "stats": {
                    "questions_planned": len(plan.questions),
                    "questions_completed": len(plan.completed_questions),
                    "total_time_seconds": total_time,
                    "planning_time": planning_time,
                    "research_time": research_time,
                    "writing_time": writing_time
                }
            }

        except Exception as e:
            total_time = round(time.time() - start_time, 2)
            print(f"[Agent] ✗ Errore dopo {total_time}s: {e}")

            return self._error_response(f"Errore durante la ricerca: {str(e)}")

    def _extract_topic(self, user_input: str) -> str:
        """
        Estrae il topic pulito dal messaggio dell'utente.
        
        Rimuove prefissi comuni che l'utente potrebbe usare
        per formulare la richiesta in modo naturale.
        
        Esempi:
            "ricerca su Python" → "Python"
            "dimmi di React" → "React"
            "voglio sapere di machine learning" → "machine learning"
            "Fotosintesi" → "Fotosintesi"  (nessun prefisso)
        """
        prefixes = [
            "ricerca su ", "ricerca: ", "ricerca ",
            "dimmi di ", "dimmi su ",
            "voglio sapere di ", "voglio sapere su ",
            "informazioni su ", "info su ",
            "spiega ", "cos'è ", "cosa è "
        ]

        cleaned = user_input.strip()

        for prefix in prefixes:
            if cleaned.lower().startswith(prefix):
                # Rimuovi il prefisso e capitalizza la prima lettera
                cleaned = cleaned[len(prefix):].strip()
                cleaned = cleaned[0].upper() + cleaned[1:] if cleaned else cleaned
                break

        return cleaned

    def _error_response(self, message: str) -> dict:
        """Genera una risposta di errore standardizzata."""
        return {
            "success": False,
            "topic": "",
            "report": f"❌ {message}",
            "report_data": {},
            "stats": {}
        }


# Istanza globale dell'agente
agent = ResearchAgent()
