"""
Entry point aplikasi FastAPI — IT Helpdesk Assistant.

Alur endpoint utama:
  1. Menerima pertanyaan/permintaan dari user
  2. Meneruskan ke router (router.py) untuk menentukan intent
  3. Router memanggil RAG (rag.py) atau tool (tools.py) sesuai intent
  4. Mengembalikan response terstruktur ke client
"""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator

from app.router import handle_query

app = FastAPI(title="IT Helpdesk Assistant API")
logger = logging.getLogger(__name__)


class AskRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)

    @field_validator("query")
    @classmethod
    def validate_query(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Query tidak boleh kosong.")
        return value


class AskResponse(BaseModel):
    status: str
    intent: str
    data: str


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    """Input yang tidak valid tetap memakai bentuk status, intent, dan data."""
    return JSONResponse(
        status_code=422,
        content={
            "status": "error",
            "intent": "unknown",
            "data": "Kirim JSON dengan field 'query' berupa teks 1-2000 karakter, bukan spasi saja.",
        },
    )


@app.get("/health")
async def health():
    """Endpoint sederhana untuk memastikan service berjalan."""
    return {"status": "ok"}


@app.post("/ask", response_model=AskResponse)
async def ask(request: AskRequest):
    """
    Endpoint utama. Menerima pertanyaan bebas dari user (bisa berupa
    pertanyaan informasi/kebijakan ATAU permintaan cek status tiket),
    lalu meneruskannya ke router untuk diproses.

    Pola try/except mengikuti error handling di Sesi 13.4.
    Detail error internal tidak dikirim ke client.
    """
    try:
        result = await handle_query(request.query)
        if result["status"] == "error":
            return JSONResponse(status_code=400, content=result)
        return AskResponse(**result)
    except Exception as exc:
        # Catat jenis error saja, agar kredensial tidak muncul di response/log.
        logger.warning("Permintaan gagal diproses: %s", type(exc).__name__)
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "intent": "unknown",
                "data": "Layanan AI atau data belum dapat diakses. Periksa konfigurasi API key, koneksi, dan data, lalu coba lagi.",
            },
        )
