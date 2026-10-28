"""
Modul Tools — fungsi-fungsi "aksi" yang dipanggil router ketika intent
BUKAN pertanyaan informasi/kebijakan, melainkan permintaan spesifik
yang butuh pengecekan data langsung (bukan retrieval semantik).

Pola ini mengikuti konsep Tool Integration di Sesi 12.3.
"""

from pathlib import Path

import pandas as pd

MOCK_TICKETS_PATH = Path(__file__).resolve().parent.parent / "data" / "mock_tickets.csv"


def get_ticket_status(ticket_id: str) -> str:
    """
    Mencari status tiket berdasarkan ticket_id pada data mock_tickets.csv.

    Pencarian mencocokkan ID secara persis, bukan berdasarkan kemiripan teks.
    Jika tiket tidak ditemukan, kembalikan pesan informatif tanpa crash.
    """
    ticket_id = ticket_id.strip().upper()
    if not ticket_id:
        return "Mohon sertakan ticket_id, misalnya TICKET-0002."

    df = pd.read_csv(MOCK_TICKETS_PATH, encoding="utf-8-sig", dtype=str).fillna("")
    matches = df[df["ticket_id"].str.strip().str.upper() == ticket_id]
    if matches.empty:
        return f"Tiket {ticket_id} tidak ditemukan. Periksa kembali ticket_id Anda."

    ticket = matches.iloc[0]
    return (
        f"Tiket: {ticket['ticket_id']}\n"
        f"Subjek: {ticket['subject']}\n"
        f"Status: {ticket['status']}\n"
        f"Pembaruan terakhir: {ticket['last_update']}"
    )
