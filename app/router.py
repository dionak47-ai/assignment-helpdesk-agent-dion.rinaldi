"""
Router — menentukan apakah query user butuh RAG (informasi/kebijakan)
atau tool call (aksi spesifik, misal cek status tiket).

Pola ini mengikuti workflow router yang sudah dipelajari di Sesi 12.4:
  user input -> intent detection -> jika butuh data -> retrieval (RAG)
                                  -> jika butuh aksi -> tool call
"""

import asyncio
import re

from app.rag import answer_from_knowledge_base
from app.tools import get_ticket_status

# Baseline keyword sesuai brief. Pengecekan tiket tidak memerlukan panggilan LLM.
# Tepat empat digit; TICKET-00020 tidak boleh terbaca sebagai TICKET-0002.
TICKET_ID_PATTERN = r"\bTICKET\s*-\s*([0-9]{4})(?![\w-])"


async def detect_intent(query: str) -> str:
    """
    Menentukan intent dari query user. Harus mengembalikan salah satu:
      - "faq"           -> pertanyaan informasi/kebijakan, arahkan ke RAG
      - "ticket_status"  -> permintaan cek status tiket, arahkan ke tool call

    Gunakan baseline keyword: ID tiket atau permintaan status -> ticket_status.
    Pertanyaan lain -> faq; RAG memeriksa apakah jawabannya tersedia.
    Pertanyaan prosedur umum tentang tiket tetap menuju faq.
    """
    text = query.lower()
    if extract_ticket_id(query) or re.search(r"\bticket\s*-", text):
        return "ticket_status"

    has_ticket = re.search(r"\b(?:tiket|ticket)(?:ku)?\b", text)
    has_status = re.search(r"\b(status|cek|check|lacak|tracking|progress|progres|perkembangan|selesai|diproses|update)\b", text)
    is_general = re.search(r"\b(cara|prosedur|panduan|membuat|mengajukan)\b", text)
    is_personal = re.search(r"\b(saya|aku|tiketku|ticketku)\b", text)
    if has_ticket and has_status and (not is_general or is_personal):
        return "ticket_status"
    return "faq"


async def handle_query(query: str) -> dict:
    """
    Fungsi utama yang dipanggil oleh endpoint /ask.
    Menjalankan intent detection, lalu merutekan ke RAG atau tool call yang sesuai.
    """
    intent = await detect_intent(query)

    if intent == "ticket_status":
        # Satu permintaan memproses satu tiket agar hasilnya tidak ambigu.
        ticket_ids = re.findall(TICKET_ID_PATTERN, query, flags=re.IGNORECASE)
        if len(set(ticket_ids)) > 1:
            return {"status": "error", "intent": intent, "data": "Mohon cek satu ticket_id dalam satu pertanyaan."}
        ticket_id = extract_ticket_id(query)
        if not ticket_id:
            return {
                "status": "error", "intent": intent,
                "data": "Mohon sertakan ticket_id dengan format TICKET-XXXX (empat digit), misalnya TICKET-0002.",
            }
        data = await asyncio.to_thread(get_ticket_status, ticket_id)
        return {"status": "success", "intent": "ticket_status", "data": data}

    elif intent == "faq":
        data = await answer_from_knowledge_base(query)
        return {"status": "success", "intent": "faq", "data": data}

    else:
        return {"status": "error", "intent": "unknown", "data": "Maaf, saya tidak memahami permintaan Anda."}


def extract_ticket_id(query: str) -> str:
    """
    Ekstrak ID dengan regex; huruf kecil dan spasi di sekitar '-' diperbolehkan.
    # Format ticket_id pada mock_tickets.csv adalah 'TICKET-XXXX'.
    """
    match = re.search(TICKET_ID_PATTERN, query, flags=re.IGNORECASE)
    return f"TICKET-{match.group(1)}" if match else ""
