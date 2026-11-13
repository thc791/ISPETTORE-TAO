from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class SubnetProfile:
    netuid: int
    name: str
    category: str
    tier: str  # "proven" | "promising" | "extra"
    thesis: str
    revenue_note: str
    github_repo: str = ""  # formato "owner/repo" se noto


# ==============================================================================
# 1. LE 10 MIGLIORI SUBNET "PROVEN" (Risultati concreti & adozione oggi)
# ==============================================================================
PROVEN_SUBNETS: List[SubnetProfile] = [
    SubnetProfile(
        netuid=51,
        name="lium.io",
        category="GPU Marketplace",
        tier="proven",
        thesis="Marketplace GPU NVIDIA decentralizzato; i provider trattengono il 95% dei ricavi.",
        revenue_note="$8M-$10M/anno stimati da clienti esterni + buyback Alpha attivo.",
    ),
    SubnetProfile(
        netuid=64,
        name="Chutes",
        category="Serverless AI Inference",
        tier="proven",
        thesis="Inferenza AI serverless (Rayon Labs) fino all'85-90% più economica dei cloud tradizionali.",
        revenue_note="$3.37M-$5M/anno tracciati (DefiLlama Q1-Q3 2026); pool più liquida della rete.",
    ),
    SubnetProfile(
        netuid=4,
        name="Targon",
        category="Confidential & Verifiable Compute",
        tier="proven",
        thesis="Compute verificabile in TVM (Manifold Labs, Series A $10.5M).",
        revenue_note="$5.5M-$6M/anno + buyback & burn massicci; top inflow on-chain.",
    ),
    SubnetProfile(
        netuid=8,
        name="Vanta",
        category="Quant & Prop Trading",
        tier="proven",
        thesis="Ex-Taoshi: segnali quant e prop trading decentralizzato. Owner cut 0% su eTAO.",
        revenue_note="$750K-$1M/anno da clienti esterni + buyback Alpha.",
    ),
    SubnetProfile(
        netuid=44,
        name="Score",
        category="Computer Vision & Sports AI",
        tier="proven",
        thesis="Computer vision e betting/sports analytics B2B con distribuzione wallet molto sana.",
        revenue_note="$1M-$2M/anno da clienti esterni.",
    ),
    SubnetProfile(
        netuid=120,
        name="Affine",
        category="Reasoning Mining & Orchestration",
        tier="proven",
        thesis="Orchestrazione RL multi-subnet; lanciato primo studio AI video pubblico su Bittensor.",
        revenue_note="Top 5 per quota emissioni di rete (~5%).",
    ),
    SubnetProfile(
        netuid=53,
        name="engy (EfficientFrontier)",
        category="Verified LLM Inference",
        tier="proven",
        thesis="Proof-of-Inference crittografica per LLM open-weights.",
        revenue_note="100% dei ricavi usati per buyback Alpha; forte accelerazione Q4 2026.",
    ),
    SubnetProfile(
        netuid=28,
        name="SayGM (gm)",
        category="Confidential LLM TEE",
        tier="proven",
        thesis="Marketplace LLM confidenziale basato su Trusted Execution Environments (TEE).",
        revenue_note="$2.5M-$3M/anno stimati; tra i migliori rapporti Revenue/MCap (~7%).",
    ),
    SubnetProfile(
        netuid=110,
        name="Green Compute",
        category="Green GPU Cloud",
        tier="proven",
        thesis="Cluster GPU UK alimentati al 100% da energie rinnovabili con API OpenAI-compatibile.",
        revenue_note="$1.2M/anno ricavi stimati + 10% revenue buyback.",
    ),
    SubnetProfile(
        netuid=41,
        name="Almanac",
        category="Prediction Market AI",
        tier="proven",
        thesis="Ex-Sportstensor: ricerca e intelligence per prediction markets; owner cut ridotto al 10%.",
        revenue_note="100% delle fee usate per buyback Alpha (~$300K/anno in crescita).",
    ),
]

# ==============================================================================
# 2. LE 10 SUBNET PIU' PROMETTENTI (Escluse le prime 10)
# ==============================================================================
PROMISING_SUBNETS: List[SubnetProfile] = [
    SubnetProfile(
        netuid=58,
        name="Attune",
        category="Robotics Simulation",
        tier="promising",
        thesis="Training di policy per robotica AI in simulazione; altissima attività GitHub e momentum.",
        revenue_note="Micro-cap (~$3M) con ~4% di emissioni; monitorare liquidità pool sottile.",
    ),
    SubnetProfile(
        netuid=107,
        name="Minos (Tiger Alpha)",
        category="Genomics & Biotech AI",
        tier="promising",
        thesis="Rilevamento mutazioni DNA e genomica computazionale.",
        revenue_note="Top 3 per emissioni (>5%) rispetto a MCap contenuta; monitorare concentrazione wallet.",
    ),
    SubnetProfile(
        netuid=56,
        name="Gradients",
        category="Distributed RLHF & Training",
        tier="promising",
        thesis="Infrastruttura di training distribuito Rayon Labs post-uscita Covenant.",
        revenue_note="Pool solida (~$11M) e Safety Screen superato.",
    ),
    SubnetProfile(
        netuid=3,
        name="Teutonic",
        category="Large Model Training",
        tier="promising",
        thesis="Subentrata sullo storico slot SN3 per addestramento distribuito di modelli giganti.",
        revenue_note="Bassa concentrazione wallet (~38%) e buona liquidità pool.",
    ),
    SubnetProfile(
        netuid=68,
        name="NOVA",
        category="Drug Discovery AI",
        tier="promising",
        thesis="AI verticale per la scoperta di nuove molecole farmaceutiche.",
        revenue_note="Unica biotech/pharma mid-cap con pool profonda (~$9M).",
    ),
    SubnetProfile(
        netuid=62,
        name="Ridges AI",
        category="Autonomous Coding Agents",
        tier="promising",
        thesis="Agenti software autonomi (>80% SWE-Bench), backata da DSV Fund.",
        revenue_note="Sconta recenti deflussi; ottima distribuzione holder (top-5 ~27%).",
    ),
    SubnetProfile(
        netuid=48,
        name="Quantum Compute",
        category="Quantum Simulation",
        tier="promising",
        thesis="Simulazione e accesso a calcolo quantistico on-demand.",
        revenue_note="Forte net inflow a 30 giorni e alto momentum.",
    ),
    SubnetProfile(
        netuid=15,
        name="ORO",
        category="Commerce Agent RL",
        tier="promising",
        thesis="Ambienti RL e benchmark (ShoppingBench) per agenti AI e-commerce.",
        revenue_note="Quota emissioni alta (~3.4%) rispetto alla capitalizzazione.",
    ),
    SubnetProfile(
        netuid=90,
        name="KubeTEE",
        category="Confidential Kubernetes",
        tier="promising",
        thesis="Orchestrazione confidential computing TEE multi-cluster su Kubernetes.",
        revenue_note="Micro-cap con quasi il 5% di emissioni e inflow positivi.",
    ),
    SubnetProfile(
        netuid=117,
        name="everyframe.studio",
        category="AI Video Craft",
        tier="promising",
        thesis="Generazione e craft video AI con split eTAO personalizzati e volumi molto elevati.",
        revenue_note="Forte ricambio volumi/pool e forte trazione community.",
    ),
]

# Extra ad alta convinzione per ricerche rapide
EXTRA_WATCHLIST: List[SubnetProfile] = [
    SubnetProfile(50, "Synth", "Synthetic Financial Data", "extra", "Previsioni probabilistiche prezzi crypto/finanza.", "Ottimo rapporto ricavi/MCap."),
    SubnetProfile(71, "Leadpoet", "B2B Lead Intelligence", "extra", "AI lead generation B2B finanziata da SubConnect.", "ARR 3x in 2 mesi."),
    SubnetProfile(124, "Swarm", "Autonomous Drones", "extra", "Piloti AI per droni autonomi.", "Safety screen superato."),
    SubnetProfile(75, "Hippius", "Decentralized Storage", "extra", "Storage DePIN S3-compatibile.", "Mid-cap solida con Safety ✓."),
    SubnetProfile(93, "Bitcast", "Creator Ad Network", "extra", "Marketing network decentralizzato.", "Buyback attivo ~64% ricavi."),
]

ALL_CURATED_MAP: Dict[int, SubnetProfile] = {
    s.netuid: s for s in (PROVEN_SUBNETS + PROMISING_SUBNETS + EXTRA_WATCHLIST)
}
PROVEN_NETUIDS = [s.netuid for s in PROVEN_SUBNETS]
PROMISING_NETUIDS = [s.netuid for s in PROMISING_SUBNETS]


# ==============================================================================
# 3. MAPPA ETF / ETP / TRUST SU TAO (Europa & USA)
# ==============================================================================
@dataclass(frozen=True)
class EtfProduct:
    ticker: str
    yahoo_candidates: List[str]  # suffissi borsa da tentare su Yahoo Finance
    name: str
    issuer: str
    region: str
    currency: str
    isin: str
    ter_pct: float
    staking_included: bool
    tao_per_share_approx: float  # utile come riferimento indicativo se disponibile
    notes: str


TAO_ETFS: List[EtfProduct] = [
    EtfProduct(
        ticker="STAO",
        yahoo_candidates=["STAO.PA", "STAO.SW", "STAO.ST"],
        name="Safello Bittensor Staked TAO ETP",
        issuer="DDA / Safello",
        region="Europa (SIX / Euronext / Nasdaq ST)",
        currency="EUR",
        isin="DE000A4APQY4",
        ter_pct=1.49,
        staking_included=True,
        tao_per_share_approx=0.0,
        notes="100% fisico + Staking Yield accumulato nel NAV.",
    ),
    EtfProduct(
        ticker="ATAO",
        yahoo_candidates=["ATAO.AS", "ATAO.PA", "ATAO-USD.AS"],
        name="21Shares Bittensor ETP",
        issuer="21Shares",
        region="Europa (Euronext Amsterdam / Paris)",
        currency="USD",
        isin="CH1495416971",
        ter_pct=2.50,
        staking_included=False,
        tao_per_share_approx=0.0,
        notes="100% garantito fisicamente in cold storage.",
    ),
    EtfProduct(
        ticker="VIRTAO",
        yahoo_candidates=["VIRTAO.ST"],
        name="Virtune Bittensor ETP",
        issuer="Virtune AB",
        region="Europa (Nasdaq Stockholm)",
        currency="SEK",
        isin="SE0027098484",
        ter_pct=1.95,
        staking_included=False,
        tao_per_share_approx=0.0,
        notes="100% fisico, scambiato in Corone Svedesi (SEK).",
    ),
    EtfProduct(
        ticker="VTAO",
        yahoo_candidates=["VTAO.ST"],
        name="Valour Bittensor SEK",
        issuer="Valour Inc.",
        region="Europa (Spotlight Stock Market)",
        currency="SEK",
        isin="CH1213604619",
        ter_pct=1.90,
        staking_included=False,
        tao_per_share_approx=0.0,
        notes="Certificato sintetico (non collateralizzato fisicamente).",
    ),
    EtfProduct(
        ticker="GTAO",
        yahoo_candidates=["GTAO"],
        name="Grayscale Bittensor Trust",
        issuer="Grayscale",
        region="USA (OTCQX -> S-1 NYSE Arca pending)",
        currency="USD",
        isin="US38963B1008",
        ter_pct=2.50,
        staking_included=False,
        tao_per_share_approx=0.0,
        notes="Scambia OTC con possibile premio/sconto sul NAV; in attesa conversione Spot ETF.",
    ),
]