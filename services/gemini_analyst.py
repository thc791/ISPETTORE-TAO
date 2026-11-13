from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple

from google import genai
from google.genai import types

from config.settings import GEMINI_API_KEY, GEMINI_MODEL_DEEP, GEMINI_MODEL_FAST
from services.web_search_client import WebSearchClient, build_clean_query


class GeminiAnalyst:
    """Motore AI di Ispettore TAO basato su Gemini 4 Hydrogen + Ricerca Web live gratuita."""

    def __init__(self, api_key: Optional[str] = None) -> None:
        self.api_key = (api_key or GEMINI_API_KEY).strip()
        self.client = (
            genai.Client(api_key=self.api_key)
            if self.api_key and "inserisci_qui" not in self.api_key
            else None
        )
        self.web_search = WebSearchClient()

    def is_ready(self) -> bool:
        return self.client is not None

    def analyze_subnet_live(
        self,
        subnet_data: Dict[str, Any],
        health_info: Dict[str, Any],
        github_info: Optional[Dict[str, Any]] = None,
        use_deep_model: bool = True,
    ) -> Tuple[str, List[Dict[str, str]]]:
        if not self.client:
            return "Chiave GEMINI_API_KEY mancante o non valida nel file .env.", []

        model_name = GEMINI_MODEL_DEEP if use_deep_model else GEMINI_MODEL_FAST
        netuid = subnet_data.get("netuid")
        name = str(subnet_data.get("name") or f"subnet {netuid}")

        # Query pulita e mirata per trovare notizie vere
        clean_name = name.split("(")[0].strip()
        search_query = f"Bittensor {clean_name} subnet {netuid}"
        web_results = self.web_search.search_web(search_query, max_results=8)

        clean_metrics = {k: v for k, v in subnet_data.items() if k != "raw"}
        context_payload = {
            "on_chain_metrics": clean_metrics,
            "health_scoring": health_info,
            "github_metrics": github_info or {},
            "live_web_results": web_results,
        }

        system_prompt = (
            "Sei l'analista senior di 'Ispettore TAO', un terminale finanziario dedicato a Bittensor (TAO e dTAO). "
            "Rispondi sempre in italiano chiaro, pragmatico e orientato a chi investe capitale reale. "
            "Non inventare MAI dati numerici: usa i numeri esatti dal JSON on-chain fornito e integra "
            "le informazioni trovate nei risultati web allegati."
        )

        user_prompt = (
            f"Analizza in modo scrupoloso la Subnet Bittensor **SN{netuid} ({name})**.\n\n"
            f"Dati on-chain verificati + risultati web raccolti ORA:\n"
            f"```json\n{json.dumps(context_payload, indent=2, ensure_ascii=False)}\n```\n\n"
            "Produci un dossier strutturato in queste 5 sezioni:\n"
            "1. **Cosa fa & Vantaggio Competitivo** (modello di business e clienti)\n"
            "2. **Sviluppi Recenti dal Web** (novità concrete emerse dalle fonti allegate)\n"
            "3. **Qualità Economica (Ricavi/Buyback vs Emissioni & Liquidità Pool)**\n"
            "4. **Rischi & Red Flags** (concentrazione whale, slippage, governance eTAO, dipendenza da sussidi)\n"
            "5. **Verdetto Operativo per l'Investitore** (profilo rischio/rendimento e cosa monitorare nei prossimi 30gg)"
        )

        config = types.GenerateContentConfig(system_instruction=system_prompt, temperature=0.3)

        try:
            response = self.client.models.generate_content(
                model=model_name,
                contents=user_prompt,
                config=config,
            )
            sources = [{"title": r["title"], "url": r["url"]} for r in web_results if r.get("url")]
            return (response.text or "Nessuna risposta generata."), sources
        except Exception as exc:
            return f"Errore chiamata Gemini: {exc}", []

    def ask_copilot(
        self,
        user_message: str,
        chat_history: List[Dict[str, str]],
        terminal_context: Dict[str, Any],
        enable_web_search: bool = True,
        use_deep_model: bool = False,
    ) -> Tuple[str, List[Dict[str, str]]]:
        if not self.client:
            return "Chiave GEMINI_API_KEY mancante o non valida nel file .env.", []

        model_name = GEMINI_MODEL_DEEP if use_deep_model else GEMINI_MODEL_FAST

        web_results: List[Dict[str, str]] = []
        if enable_web_search:
            clean_q = build_clean_query(user_message, prefix="Bittensor")
            web_results = self.web_search.search_web(clean_q, max_results=6)

        system_prompt = (
            "Sei 'Ispettore TAO Copilot', assistente finanziario e tecnico esperto dell'ecosistema Bittensor (TAO, dTAO, "
            "Alpha token, eTAO, Gamma, ETF/ETP europei e SEC USA). Rispondi in italiano in modo diretto, analitico e trasparente. "
            "Hai accesso ai dati LIVE del terminale dell'utente e ai risultati web recenti allegati.\n\n"
            f"CONTESTO LIVE DEL TERMINALE:\n{json.dumps(terminal_context, ensure_ascii=False)}\n\n"
            f"RISULTATI WEB RECENTI SULLA DOMANDA:\n{json.dumps(web_results, ensure_ascii=False)}"
        )

        contents: List[types.Content] = []
        for msg in chat_history[-10:]:
            role = "user" if msg.get("role") == "user" else "model"
            contents.append(
                types.Content(role=role, parts=[types.Part.from_text(text=msg.get("content", ""))])
            )
        contents.append(types.Content(role="user", parts=[types.Part.from_text(text=user_message)]))

        config = types.GenerateContentConfig(system_instruction=system_prompt, temperature=0.4)

        try:
            response = self.client.models.generate_content(
                model=model_name,
                contents=contents,
                config=config,
            )
            sources = [{"title": r["title"], "url": r["url"]} for r in web_results if r.get("url")]
            return (response.text or "Nessuna risposta."), sources
        except Exception as exc:
            return f"Errore Gemini Copilot: {exc}", []