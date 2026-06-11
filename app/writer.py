# Sotto-agente: scrive il report 
# app/writer.py
#
# Il Writer è il terzo e ultimo sotto-agente.
# Riceve il riassunto di tutte le ricerche e produce
# un report finale strutturato e formattato.
#
# Il Writer NON usa tool: ha già tutte le informazioni
# che gli servono dal Researcher. Il suo compito è
# puramente di sintesi e scrittura.

import json
from openai import AsyncOpenAI
from app.config import config
from app.models import ResearchPlan, FinalReport

WRITER_SYSTEM_PROMPT = """Sei un giornalista esperto e scrittore tecnico.
Il tuo compito è trasformare ricerche grezze in un report
professionale, chiaro e ben strutturato.

ISTRUZIONI:
1. Analizza tutte le ricerche ricevute
2. Sintetizza le informazioni in modo coerente
3. Organizza il contenuto in sezioni logiche
4. Identifica i punti chiave più importanti
5. Scrivi in italiano, tono professionale ma accessibile
6. Rispondi ESCLUSIVAMENTE in formato JSON valido

FORMATO OUTPUT (JSON obbligatorio):
{
  "executive_summary": "panoramica dell'argomento in 2-3 frasi",
  "sections": [
    {
      "title": "titolo della sezione",
      "content": "contenuto della sezione (2-4 frasi)"
    }
  ],
  "key_points": [
    "punto chiave 1",
    "punto chiave 2",
    "punto chiave 3",
    "punto chiave 4",
    "punto chiave 5"
  ],
  "conclusion": "conclusione finale in 2-3 frasi"
}

Non aggiungere testo prima o dopo il JSON. Solo JSON puro."""


class Writer:
    """
    Sotto-agente responsabile della scrittura del report finale.
    
    Trasforma i dati grezzi delle ricerche in un report
    strutturato pronto per essere consegnato all'utente.
    """

    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=config.OPENROUTER_API_KEY,
            base_url=config.OPENROUTER_BASE_URL
        )

    async def write_report(self, plan: ResearchPlan) -> FinalReport:
        """
        Genera il report finale dalle ricerche completate.
        
        Args:
            plan: Il piano con tutti i risultati delle ricerche
            
        Returns:
            FinalReport con il report strutturato
        """
        print(f"\n[Writer] Generazione report per: '{plan.topic}'")

        # Prepara il materiale per il Writer
        # Trasformiamo il piano in un testo riassuntivo delle ricerche
        research_summary = plan.to_research_summary()

        print(f"[Writer] Materiale di ricerca: {len(research_summary)} caratteri")

        # Chiedi al LLM di scrivere il report
        response = await self.client.chat.completions.create(
            model=config.MODEL_MAIN,
            messages=[
                {"role": "system", "content": WRITER_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"Scrivi un report completo basandoti su queste ricerche:\n\n"
                        f"{research_summary}"
                    )
                }
            ],
            # Il Writer ha bisogno di più token per produrre un report completo
            max_tokens=2000,
            # Temperatura leggermente più alta per testo più fluente
            temperature=0.4
        )

        raw_output = response.choices[0].message.content
        print(f"[Writer] Report generato ({len(raw_output)} caratteri)")

        # Parsa il JSON del report
        report_data = self._parse_report_json(raw_output, plan.topic)

        # Costruisci l'oggetto FinalReport
        report = FinalReport(
            topic=plan.topic,
            executive_summary=report_data.get("executive_summary", ""),
            sections=report_data.get("sections", []),
            key_points=report_data.get("key_points", []),
            conclusion=report_data.get("conclusion", "")
        )

        # Genera la versione formattata per Telegram
        report.telegram_version = report.format_for_telegram()

        print(f"[Writer] Report Telegram: {len(report.telegram_version)} caratteri")

        return report

    def _parse_report_json(self, raw_output: str, topic: str) -> dict:
        """
        Parsa il JSON del report con gestione degli errori.
        Se il parsing fallisce, crea un report di fallback
        usando il testo grezzo del LLM.
        """
        cleaned = raw_output.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            cleaned = "\n".join(lines[1:-1])

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            print(f"[Writer] Errore parsing JSON, uso testo grezzo come fallback")

            # Fallback: usa il testo grezzo come executive summary
            return {
                "executive_summary": f"Report su: {topic}",
                "sections": [
                    {"title": "Analisi", "content": raw_output[:500]}
                ],
                "key_points": ["Vedere il testo completo per i dettagli"],
                "conclusion": "Report generato con dati parziali."
            }
