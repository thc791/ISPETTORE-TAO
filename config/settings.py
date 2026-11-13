from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

# Carica le variabili dal file .env nella root del progetto
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# --- API Keys ---
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "").strip()
TAOSTATS_API_KEY: str = os.getenv("TAOSTATS_API_KEY", "").strip()
GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "").strip()
TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "").strip()

# --- Taostats API v1 (nuovo endpoint attivo da Nov 2026) ---
TAOSTATS_BASE_URL: str = "https://api.taostats.io/v1"

# --- Modelli Google Gemini (Nov 2026) ---
GEMINI_MODEL_FAST: str = os.getenv("GEMINI_MODEL_FAST", "gemini-4-hydrogen")
GEMINI_MODEL_DEEP: str = os.getenv("GEMINI_MODEL_DEEP", "gemini-4-hydrogen")

# --- Costanti Protocollo Bittensor ---
RAO_PER_TAO: float = 1_000_000_000.0  # 1 TAO = 10^9 RAO
DAILY_TAO_EMISSION: float = 3600.0    # Post-halving Dic 2025 (0.5 TAO/blocco)
MAX_SUBNET_SLOTS: int = 128

# --- Cache TTL (secondi) per proteggere il piano Free ---
CACHE_TTL_PRICE_SEC: int = 60         # 1 minuto per il prezzo TAO
CACHE_TTL_POOLS_SEC: int = 180        # 3 minuti per le pool delle subnet
CACHE_TTL_HISTORY_SEC: int = 900      # 15 minuti per gli storici
CACHE_TTL_GITHUB_SEC: int = 3600      # 1 ora per i commit GitHub