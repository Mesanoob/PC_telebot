"""
knowledge.py — Smart knowledge retrieval for MCST bot.
Maps user questions to relevant knowledge sections.
Loads only what's needed to keep Gemini tokens lean.
"""

import os
import re

BASE = os.path.join(os.path.dirname(__file__), "knowledge")

# Each entry: (list of trigger keywords, filename)
SECTION_MAP = [
    (
        ["by-law", "bylaw", "rule", "pet", "parking", "noise", "behavio", "fine",
         "enforce", "breach", "ban", "prohibit", "floor", "garbage", "rubbish",
         "security", "satellite", "aircon", "air-con", "obstruct"],
        "smg10bylaws.txt",
    ),
    (
        ["agm", "annual general", "egm", "extraordinary", "quorum", "vote",
         "resolution", "special resolution", "ordinary resolution", "notice",
         "proxy", "motion", "agenda", "meeting"],
        "strata4proceedingsofageneralmeeting.txt",
    ),
    (
        ["agm prep", "prepare meeting", "notice of meeting", "prepare agm",
         "call meeting", "annual meeting prep"],
        "smg3preparationforageneralmeeting.txt",
    ),
    (
        ["council meeting", "council member", "council decision", "council minute",
         "mc council", "management council"],
        "smg5proceedingsofacouncilmeeting.txt",
    ),
    (
        ["dispute", "complaint", "stb", "strata title board", "mediation",
         "community mediation", "cmc", "sue", "legal action", "court",
         "tribunal", "appeal", "conflict", "neighbour", "neighbor"],
        "smg9disputeresolutions.txt",
    ),
    (
        ["renovation", "hack", "drill", "work hour", "working hour", "permit",
         "approval", "contractor", "alteration", "addition", "a&a",
         "structural", "bca", "waterproof", "tile", "ceiling"],
        "bca_guide14_carrying_out_works_in_lots.txt",
    ),
    (
        ["seepage", "leak", "water damage", "ceiling leak", "floor leak",
         "water ingress", "plumbing", "pipe burst", "damp", "moisture"],
        "bca_guide13_water_seepage.txt",
    ),
    (
        ["common property", "pool", "gym", "facility", "corridor", "lift",
         "car park", "carpark", "maintenance fee", "sinking fund",
         "conservancy", "common area", "lobby", "driveway", "rooftop",
         "playground", "bbq", "barbeque"],
        "bca_guide11_management_and_maintenance_of_common_property.txt",
    ),
    (
        ["facade", "exterior", "window", "balcony", "external wall",
         "awning", "railing", "cladding", "glass", "parapet"],
        "bca_guide12_management_and_maintenance_of_external_facades_and_exterior_features.txt",
    ),
    (
        ["motion", "write motion", "resolution type", "90 percent", "75 percent",
         "unanimous", "special resolution write", "how to write"],
        "bca_guide15_writing_a_motion_and_different_resolutions.txt",
    ),
    (
        ["managing agent", "ma ", " ma,", "property manager", "appoint agent",
         "agent duty", "agent contract", "agent fee", "terminate agent"],
        "smg6managingagent.txt",
    ),
    (
        ["handover", "developer handover", "first agm", "1st agm",
         "new development", "defect", "rectification"],
        "smg7developerhandoverafter1stagm.txt",
    ),
    (
        ["record", "document", "strata roll", "minute", "financial statement",
         "audit", "keep record", "store document"],
        "smg8maintainingmcrecords.txt",
    ),
    (
        ["role", "responsibility", "council duty", "sp duty", "subsidiary proprietor",
         "owner right", "tenant right", "occupier", "stakeholder"],
        "smg2roleandresponsibilityofstakeholders.txt",
    ),
    (
        ["what is mcst", "what is strata", "strata living", "concept", "overview",
         "how does condo work", "how mcst work"],
        "smg1conceptofstrataliving.txt",
    ),
]

# Always include a compact summary of the BMSMA key sections
BMSMA_SUMMARY = """
KEY BMSMA PROVISIONS (summary):
- MCST cannot impose fines; must apply to STB/court for enforcement.
- AGM required once per calendar year; 14 days written notice.
- Special resolution = 75% of share value; Ordinary = simple majority.
- Managing agent appointed by resolution; contract max 3 years renewable.
- Sinking fund minimum: 10% of annual budget or prescribed amount.
- STB can hear disputes on by-laws, common property, collective sales.
- Subsidiary proprietors must pay maintenance contributions on time.
- Exclusive use by-laws require special resolution and STB lodgement.
"""


def _score(query: str, keywords: list) -> int:
    q = query.lower()
    return sum(1 for kw in keywords if kw in q)


def get_relevant_knowledge(query: str, max_sections: int = 2) -> str:
    """Return the most relevant knowledge sections for a query."""
    scored = []
    for keywords, fname in SECTION_MAP:
        score = _score(query, keywords)
        if score > 0:
            scored.append((score, fname))

    # Sort by score descending, pick top N
    scored.sort(key=lambda x: -x[0])
    top = scored[:max_sections]

    if not top:
        # Fallback: load bylaws + disputes as most common topics
        top = [(0, "smg10bylaws.txt"), (0, "smg9disputeresolutions.txt")]

    sections = [BMSMA_SUMMARY]
    loaded = set()
    for _, fname in top:
        if fname in loaded:
            continue
        loaded.add(fname)
        path = os.path.join(BASE, fname)
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                sections.append(f.read())

    return "\n\n---\n\n".join(sections)
