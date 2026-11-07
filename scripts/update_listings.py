#!/usr/bin/env python3
"""Refresh README.md and listings.json from the live JobShift public radar.

Standard library only. Runs daily in GitHub Actions (see .github/workflows/update.yml).
Exits non-zero, leaving the files untouched, if the radar is down or returns too few
offers, so a stale or empty list is never published under today's date.
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

API_URL = "https://hirly-api-production.up.railway.app/api/public/alternances-2026"
RADAR_URL = "https://www.tryjobshift.com/alternances-2026"
UTM = "utm_source=github&utm_medium=repo&utm_campaign=alternances_2026"
ROOT = Path(__file__).resolve().parents[1]
MAX_ITEMS = 1500
PAGE_SIZE = 100
MIN_ITEMS = 50
ROWS_PER_SECTION = 40

SECTIONS = [
    ("tech", "💻 Tech, Data & IA (Développement, Data Science, Cybersécurité, Produit)"),
    ("finance", "🏦 Finance, Audit & Contrôle de Gestion"),
    ("marketing", "📣 Marketing, Digital, Communication & Growth"),
    ("commerce", "🤝 Commerce, Business Development & Achats"),
    ("ingenierie", "⚙️ Ingénierie, Industrie, Supply Chain & Aéronautique"),
    ("luxe", "✨ Luxe, Mode, Retail & Cosmétique"),
    ("rh", "👥 Ressources Humaines, Talent Acquisition & Juridique"),
]


def fetch_offers(opener=urllib.request.urlopen) -> Optional[List[Dict[str, Any]]]:
    rows: List[Dict[str, Any]] = []
    seen = set()
    cursor: Optional[str] = None
    while len(rows) < MAX_ITEMS:
        params = {"limit": str(PAGE_SIZE), "hide_cfa": "true"}
        if cursor:
            params["cursor"] = cursor
        request = urllib.request.Request(
            f"{API_URL}?{urllib.parse.urlencode(params)}",
            headers={"Accept": "application/json", "User-Agent": "jobshift-alternances-repo"},
        )
        try:
            with opener(request, timeout=60) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (OSError, ValueError, urllib.error.URLError):
            return None
        if not isinstance(payload, dict):
            return None
        for item in payload.get("items") or []:
            if not isinstance(item, dict):
                continue
            job_id = str(item.get("job_id") or "")
            if job_id and job_id not in seen and not item.get("is_cfa_or_school"):
                seen.add(job_id)
                rows.append(item)
        cursor = payload.get("next_cursor")
        if not payload.get("has_more") or not cursor:
            break
    return rows[:MAX_ITEMS]


def _badge_number(value: int) -> str:
    return f"{value:,}".replace(",", "_")


def _cell(value: Any) -> str:
    return str(value or "—").replace("|", "/").replace("\n", " ").strip() or "—"


def _is_stage(row: Dict[str, Any]) -> bool:
    return "stage" in str(row.get("contract_label") or "").lower()


def _row(row: Dict[str, Any], slug: str) -> str:
    company = _cell(row.get("company"))
    logo = row.get("company_logo")
    logo_html = (
        f'<img src="{logo}" width="18" height="18" align="absmiddle" /> ' if logo else ""
    )
    title = _cell(row.get("title"))
    contract = "💼 Stage" if _is_stage(row) else "🎓 Alternance"
    apply_url = row.get("selected_apply_url") or row.get("apply_url") or RADAR_URL
    query = urllib.parse.urlencode({"domain": slug, "q": f"{title} {company}"[:90]})
    auto_url = f"{RADAR_URL}?{query}&{UTM}"
    return (
        f"| {logo_html}**{company}** | {title} | {contract} | {_cell(row.get('city'))} | "
        f"[Postuler]({apply_url}) · [⚡ Auto-Apply]({auto_url}) |"
    )


def build_readme(rows: List[Dict[str, Any]], today: str) -> str:
    stages = sum(1 for row in rows if _is_stage(row))
    alternances = len(rows) - stages
    by_slug = {slug: [r for r in rows if r.get("domain_slug") == slug] for slug, _ in SECTIONS}
    lines = [
        '<div align="center">',
        "",
        "# 🇫🇷 Alternances & Stages France 2026 / 2027 (Sans CFA)",
        "",
        "### Le répertoire open-source des **vraies** offres d'Alternance et de Stage en France,"
        f" propulsé par [JobShift]({RADAR_URL}?{UTM})",
        "",
        f"[![Offres Actives](https://img.shields.io/badge/Offres_actives-{_badge_number(len(rows))}-2EC4B6?style=for-the-badge)]({RADAR_URL}?{UTM})",
        f"[![Alternances](https://img.shields.io/badge/Alternances-{_badge_number(alternances)}-2563eb?style=for-the-badge)]({RADAR_URL}?kind=alternance&{UTM})",
        f"[![Stages](https://img.shields.io/badge/Stages-{_badge_number(stages)}-7c3aed?style=for-the-badge)]({RADAR_URL}?kind=stage&{UTM})",
        f"[![Mise à jour](https://img.shields.io/badge/Mise_%C3%A0_jour-{today.replace('-', '--')}-111827?style=for-the-badge)]({RADAR_URL}?{UTM})",
        "",
        f"**[⚡ Ouvrir le Radar Interactif + Auto-Apply 1-Clic sur JobShift]({RADAR_URL}?{UTM})**",
        "",
        "</div>",
        "",
        "---",
        "",
        "## Pourquoi cette liste existe ?",
        "",
        "En France, la recherche d'alternance et de stage sur les jobboards classiques est polluée par"
        " des milliers de fausses annonces publiées par des écoles privées et des CFA en ligne qui"
        " cherchent à te vendre une formation plutôt qu'à te recruter dans une vraie entreprise.",
        "",
        "Inspiré du modèle américain de **SimplifyJobs** (`Summer2026-Internships`), ce dépôt maintenu"
        " par **[JobShift](https://github.com/Jobshift)** regroupe les offres publiées directement sur"
        " les sites carrières des entreprises (Workday, Greenhouse, Lever, SmartRecruiters, Teamtailor,"
        " Recruitee, Personio, Taleez, Flatchr) et sur **La Bonne Alternance**, avec un filtre strict qui"
        " exclut les écoles et CFA. **La liste est régénérée automatiquement chaque jour.**",
        "",
        "### Comment postuler 10x plus vite ?",
        "1. **Depuis ce GitHub** : clique sur **Postuler** pour ouvrir l'annonce officielle, ou sur"
        f" **⚡ Auto-Apply** pour candidater automatiquement avec ton CV adapté sur [JobShift]({RADAR_URL}?{UTM}).",
        f"2. **En lot** : ouvre le **[Radar Alternances & Stages sur JobShift]({RADAR_URL}?{UTM})**,"
        " filtre par ville, domaine ou grand groupe, sélectionne jusqu'à 50 offres et laisse"
        " l'Auto-Apply remplir les formulaires pour toi.",
        "",
        "## Sommaire par domaine",
        "",
    ]
    for slug, title in SECTIONS:
        lines.append(f"- [{title}](#{slug}) ({len(by_slug[slug])} offres)")
    lines += ["", "---", ""]
    for slug, title in SECTIONS:
        section_rows = by_slug[slug][:ROWS_PER_SECTION]
        lines += [
            f'<a id="{slug}"></a>',
            f"## {title}",
            "",
            f"👉 **[Voir toutes les offres {title} et postuler en 1 clic sur JobShift]"
            f"({RADAR_URL}?domain={slug}&{UTM})**",
            "",
        ]
        if section_rows:
            lines += [
                "| Entreprise | Poste | Contrat | Ville | Candidature |",
                "| :--- | :--- | :--- | :--- | :--- |",
                *(_row(row, slug) for row in section_rows),
            ]
        else:
            lines.append("_Aucune offre active dans ce domaine aujourd'hui._")
        lines.append("")
    lines += [
        "---",
        "",
        '<div align="center">',
        "  <b>Maintenu par l'équipe <a href=\"https://www.tryjobshift.com\">JobShift</a>"
        ' (<a href="https://github.com/Jobshift">@Jobshift</a>)</b><br/>',
        f"  <sub>{len(rows)} offres actives · Dernière mise à jour automatique : {today}</sub>",
        "</div>",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    rows = fetch_offers()
    if rows is None or len(rows) < MIN_ITEMS:
        count = 0 if rows is None else len(rows)
        print(f"Live radar unavailable or too small ({count} offers); nothing published.")
        return 1
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    (ROOT / "listings.json").write_text(
        json.dumps(rows, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (ROOT / "README.md").write_text(build_readme(rows, today), encoding="utf-8")
    print(json.dumps({"offers": len(rows), "date": today}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
