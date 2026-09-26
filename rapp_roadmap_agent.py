"""
RappRoadmap — pull your north star from the global RAPP roadmap, over the hydra.

Drop this into any brainstem's agents/ and it can fetch the ecosystem roadmap (kody-w/
rapp-roadmap) from whichever hydra head is reachable, to keep a north star locally —
which phase the ecosystem is in, what the medium is, and where a given situation fits.
Caches current RAPP/1 guidance locally, so it keeps its north star even fully offline
(degrade-to-cache). Retired or malformed guidance is refused, not silently migrated.
The roadmap is static data on the global CDN; this never relies on an API we don't own.

Actions: north_star · phase (current or by name) · guidance (situation -> phase/hero) ·
         hero_use_cases · refresh. See https://github.com/kody-w/rapp-roadmap.
"""
from http.client import HTTPException
import json
import logging
import os
import re
import time
import urllib.request

from agents.basic_agent import BasicAgent

OWNER, REPO = "kody-w", "rapp-roadmap"
HEADS = [
    f"https://raw.githubusercontent.com/{OWNER}/{REPO}/main",
    f"https://cdn.jsdelivr.net/gh/{OWNER}/{REPO}@main",
    f"https://raw.githack.com/{OWNER}/{REPO}/main",
]
HEADS = [h for h in os.environ.get("FRAME_HEADS", "").split(",") if h.strip()] + HEADS
CACHE = os.path.expanduser("~/.brainstem/.roadmap_cache.json")
LOG = logging.getLogger(__name__)


def _validate_roadmap(rm):
    if not isinstance(rm, dict):
        raise ValueError("roadmap must be a JSON object")
    active = {
        key: value for key, value in rm.items()
        if not (
            key in ("architecture", "grounding")
            and isinstance(value, dict)
            and value.get("status") == "historical"
        )
    }
    if re.search(r"\brapp-(?:frame|egg)/[0-9]", json.dumps(active)):
        raise ValueError("roadmap contains retired frame/egg guidance")
    medium = rm.get("the_medium")
    if (
        not isinstance(medium, str)
        or not re.search(r"\brapp/1(?![-\w./])", medium)
        or not re.search(r"\brapp/1-egg(?![-\w./])", medium)
    ):
        raise ValueError("roadmap lacks current RAPP/1 frame/egg guidance")
    return rm


def _cached_roadmap():
    try:
        with open(CACHE, encoding="utf-8") as cache:
            stored = json.load(cache)
        if not isinstance(stored, dict):
            raise ValueError("roadmap cache must be a JSON object")
        return _validate_roadmap(stored.get("roadmap"))
    except FileNotFoundError:
        return None
    except (OSError, ValueError) as exc:
        LOG.warning("Ignoring unusable roadmap cache: %s", exc)
        return None


def _fetch():
    for base in HEADS:
        try:
            req = urllib.request.Request(f"{base}/roadmap.json", headers={"User-Agent": "rapp-roadmap"})
            with urllib.request.urlopen(req, timeout=8) as r:
                rm = _validate_roadmap(json.loads(r.read()))
        except (OSError, ValueError, HTTPException) as exc:
            LOG.warning("Skipping roadmap head %s: %s", base, exc)
            continue
        try:
            with open(CACHE, "w", encoding="utf-8") as cache:
                json.dump({"at": time.time(), "head": base, "roadmap": rm}, cache)
        except OSError as exc:
            LOG.warning("Could not cache current roadmap: %s", exc)
        return rm, base
    rm = _cached_roadmap()
    if rm is not None:
        return rm, "cache (offline)"
    return None, None


class RappRoadmapAgent(BasicAgent):
    def __init__(self):
        self.name = "RappRoadmap"
        self.metadata = {
            "name": self.name,
            "description": ("Pull the global RAPP ecosystem roadmap (your north star) from the hydra. "
                            "action=north_star | the_medium | phase (optional `name`) | guidance (pass a `situation`) | "
                            "hero_use_cases | refresh. Offline-resilient (cached)."),
            "parameters": {"type": "object", "properties": {
                "action": {"type": "string", "enum": ["north_star", "the_medium", "phase", "guidance", "hero_use_cases", "refresh"]},
                "situation": {"type": "string", "description": "for guidance: what you're trying to do"},
                "name": {"type": "string", "description": "for phase: a phase name fragment (else the current phase)"},
            }, "required": ["action"]},
        }
        super().__init__(name=self.name, metadata=self.metadata)

    def system_context(self):
        rm = _cached_roadmap()
        ns = (rm or {}).get("north_star")
        return f"North star (RAPP roadmap): {ns}" if ns else ""

    def perform(self, **kwargs):
        action = (kwargs.get("action") or "north_star").strip()
        rm, head = _fetch()
        if rm is None:
            return json.dumps({"ok": False, "error": "no current roadmap available from any head or cache"})
        if action == "north_star":
            return json.dumps({"north_star": rm.get("north_star"), "via": head})
        if action == "the_medium":
            return json.dumps({"the_medium": rm.get("the_medium"), "via": head})
        if action == "hero_use_cases":
            return json.dumps({"hero_use_cases": rm.get("hero_use_cases", []), "via": head})
        if action == "phase":
            phases = rm.get("phases", [])
            name = (kwargs.get("name") or "").lower()
            ph = next((p for p in phases if name in p.get("title", p.get("name", "")).lower()), None) if name else (phases[0] if phases else None)
            return json.dumps({"phase": ph, "via": head})
        if action == "guidance":
            sit = (kwargs.get("situation") or "").lower()
            words = {w for w in sit.replace(",", " ").split() if len(w) > 3}
            best, score = None, 0
            for p in rm.get("phases", []):
                hay = (p.get("title", p.get("name", "")) + " " + p.get("theme", "") + " "
                       + " ".join(p.get("items", p.get("objectives", []))) + " "
                       + p.get("hero_use_case", "")).lower()
                s = sum(1 for w in words if w in hay)
                if s > score:
                    best, score = p, s
            return json.dumps({"situation": kwargs.get("situation"), "north_star": rm.get("north_star"),
                               "fits_phase": (best or {}).get("title", (best or {}).get("name")),
                               "theme": (best or {}).get("theme"),
                               "items": (best or {}).get("items", (best or {}).get("objectives", [])),
                               "hero_use_case": (best or {}).get("hero_use_case"), "via": head})
        return json.dumps({"ok": True, "refreshed_from": head, "north_star": rm.get("north_star")})
