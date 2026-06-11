# Strutture dati (dataclass/TypedDict) 
# app/models.py
#
# Definisce le strutture dati usate in tutto il progetto.
# Usare strutture dati esplicite (invece di dizionari generici)
# rende il codice più leggibile, manutenibile e meno soggetto a errori.
#
# Usiamo dataclass: classi Python con generazione automatica
# di __init__, __repr__ e altri metodi standard.

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class ResearchStatus(Enum):
    """
    Stati possibili di una singola ricerca.
    
    Enum (Enumeration) è usato per rappresentare un insieme
    fisso di valori costanti. Meglio di stringhe libere perché
    evita typo e rende espliciti i valori ammessi.
    """
    PENDING = "pending"       # In attesa di essere eseguita
    COMPLETED = "completed"   # Eseguita con successo
    FAILED = "failed"         # Fallita dopo i retry


@dataclass
class ResearchQuestion:
    """
    Rappresenta una singola domanda del piano di ricerca.
    
    dataclass genera automaticamente __init__ e __repr__,
    riducendo il codice boilerplate.
    
    Esempio:
        q = ResearchQuestion(
            question="Cos'è il machine learning?",
            focus="definizione e concetti base"
        )
    """
    question: str                           # La domanda da ricercare
    focus: str                              # Aspetto specifico su cui concentrarsi
    status: ResearchStatus = ResearchStatus.PENDING
    result: Optional[str] = None           # Risultato della ricerca (None finché non eseguita)
    sources: list = field(default_factory=list)  # Lista di fonti trovate


@dataclass
class ResearchPlan:
    """
    Il piano completo generato dal Planner.
    Contiene tutte le domande da ricercare e metadati.
    """
    topic: str                              # Argomento originale dell'utente
    questions: list                         # Lista di ResearchQuestion
    context: str = ""                       # Contesto aggiuntivo sul topic

    @property
    def completed_questions(self) -> list:
        """
        Property: restituisce solo le domande completate.
        
        @property permette di usare completed_questions come
        attributo (plan.completed_questions) invece di metodo
        (plan.completed_questions()), rendendo il codice più leggibile.
        """
        return [q for q in self.questions
                if q.status == ResearchStatus.COMPLETED]

    @property
    def is_complete(self) -> bool:
        """True se tutte le domande sono state elaborate."""
        return all(
            q.status != ResearchStatus.PENDING
            for q in self.questions
        )

    def to_research_summary(self) -> str:
        """
        Converte i risultati delle ricerche in un testo riassuntivo.
        Questo testo viene passato al Writer per generare il report.
        """
        lines = [f"ARGOMENTO: {self.topic}\n"]

        for i, q in enumerate(self.completed_questions, 1):
            lines.append(f"--- Ricerca {i}: {q.question} ---")
            lines.append(f"Focus: {q.focus}")
            lines.append(f"Risultato: {q.result}")
            lines.append("")  # Riga vuota tra le sezioni

        return "\n".join(lines)


@dataclass
class FinalReport:
    """
    Il report finale prodotto dal Writer.
    """
    topic: str
    executive_summary: str      # Riassunto breve (2-3 righe)
    sections: list              # Lista di dict {'title': ..., 'content': ...}
    key_points: list            # Lista di punti chiave (bullet points)
    conclusion: str             # Conclusione finale
    telegram_version: str = ""  # Versione formattata per Telegram

    def format_for_telegram(self) -> str:
        """
        Formatta il report per Telegram.
        
        Telegram supporta Markdown limitato:
        - *testo* = grassetto
        - _testo_ = corsivo
        - `codice` = monospace
        - Massimo 4096 caratteri per messaggio
        """
        lines = []

        # Titolo principale
        lines.append(f"📊 *REPORT: {self.topic.upper()}*\n")

        # Executive summary (panoramica rapida)
        lines.append("📌 *Panoramica*")
        lines.append(self.executive_summary)
        lines.append("")

        # Sezioni del report
        for section in self.sections:
            lines.append(f"📎 *{section['title']}*")
            lines.append(section['content'])
            lines.append("")

        # Punti chiave
        lines.append("✅ *Punti Chiave*")
        for point in self.key_points:
            lines.append(f"• {point}")
        lines.append("")

        # Conclusione
        lines.append("🔍 *Conclusione*")
        lines.append(self.conclusion)

        full_text = "\n".join(lines)

        # Telegram ha un limite di 4096 caratteri per messaggio
        # Se superiamo il limite, tronchiamo con un avviso
        if len(full_text) > 4000:
            full_text = full_text[:3900] + "\n\n_[Report troncato per limiti Telegram]_"

        return full_text
