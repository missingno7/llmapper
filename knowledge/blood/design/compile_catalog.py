"""Compile design-pattern catalog v1 from unsigned mines plus INTERPRETED labels.

The unsigned signatures are DERIVED. Names and roles here are INTERPRETED and
remain hypotheses until counterexamples split or retire them.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from bloodmap.patterns import attach_corpus_occurrences


def _pattern(
    pattern_id: str,
    *,
    status: str,
    scale: str,
    subject: str,
    population: str,
    match: dict[str, str],
    description: str,
    label: str,
    rationale: str,
    required_evidence: list[str],
    tags: list[str],
    counterexamples: list[dict] | None = None,
    confidence: str = "low",
) -> dict:
    return {
        "id": pattern_id,
        "status": status,
        "kind": "interpreted",
        "scale": scale,
        "subject": subject,
        "population": population,
        "match": match,
        "signature": match,
        "tags": tags,
        "description": description,
        "required_evidence": required_evidence,
        "confidence": confidence,
        "interpretation": {
            "status": "INTERPRETED",
            "label": label,
            "rationale": rationale,
        },
        "counterexamples": counterexamples or [],
        "occurrences": [],
    }


def templates() -> list[dict]:
    bb = "blood-bloodbath"
    return [
        _pattern(
            "pattern:spawn:open-hunting-cell",
            status="supported",
            scale="neighborhood",
            subject="spawn-neighborhood",
            population=bb,
            match={"sky": "1", "hops": "0", "exits": "3+", "field": "high", "sight": "high"},
            tags=["open-hunting-cell", "spawn"],
            description=(
                "A deathmatch start already sits in a large sky cell with many "
                "immediate portal choices and high local 2D sight."
            ),
            label="spawn already occupies a shared outdoor hunting cell",
            rationale=(
                "Recurs on BB6, BB8, BB9 (and variants on BB1/BB7). Area and peek "
                "bins vary; the stable relation is sky + zero hops + many exits + "
                "high field/sight."
            ),
            required_evidence=["spawn_neighborhood_report", "sky_ceiling"],
            confidence="medium",
            counterexamples=[{
                "claim_rejected": "outdoor hunting-cell spawn is concealed from other starts",
                "why": "BB6 hunting-cell starts have spawn-pair 2D clear fraction 1.0",
                "maps": ["BB6.MAP"],
            }],
        ),
        _pattern(
            "pattern:spawn:sky-porch-into-field",
            status="supported",
            scale="neighborhood",
            subject="spawn-neighborhood",
            population=bb,
            match={"sky": "1", "hops": "0", "exits": "1", "field": "high", "local": "large"},
            tags=["sky-porch", "spawn"],
            description=(
                "A small sky pad with a single exit whose reachable neighborhood "
                "is still a large field."
            ),
            label="small sky porch that already belongs to a large hunting field",
            rationale="BB6 has two 1-exit sky starts whose local reachable area matches the yards.",
            required_evidence=["spawn_neighborhood_report"],
            confidence="medium",
            counterexamples=[{
                "claim_rejected": "one exit means a closet spawn",
                "why": "local reachable area is large; the pad is a mouth, not a sealed room",
                "maps": ["BB6.MAP"],
            }],
        ),
        _pattern(
            "pattern:spawn:sky-constrained-alcove",
            status="hypothesis",
            scale="neighborhood",
            subject="spawn-neighborhood",
            population=bb,
            match={"sky": "1", "hops": "0", "local": "small"},
            tags=["sky-alcove", "spawn"],
            description="Sky start whose locally reachable area is small relative to the corpus median.",
            label="outdoor start in a constrained alcove rather than a hunting cell",
            rationale="Separates BB6's tiny-local sky start from the large-yard starts on the same map.",
            required_evidence=["spawn_neighborhood_report"],
            confidence="low",
        ),
        _pattern(
            "pattern:spawn:covered-hops-to-sky",
            status="supported",
            scale="neighborhood",
            subject="spawn-neighborhood",
            population=bb,
            match={"sky": "0", "hops": "2+"},
            tags=["covered-approach", "spawn"],
            description="Covered start that still reaches the largest sky component in a few portal hops.",
            label="covered spawn with a short approach into outdoor circulation",
            rationale="Recurs on BB1, BB2, BB7, BB8, BB9. Distinct from indoor-only maps with hops:none.",
            required_evidence=["spawn_neighborhood_report"],
            confidence="medium",
            counterexamples=[{
                "claim_rejected": "any covered spawn is a closet isolated from the match",
                "why": "hops 1–2+ still participate in the outdoor component; hops:none on BB3–BB5 is the indoor-only case",
                "maps": ["BB2.MAP", "BB3.MAP"],
            }],
        ),
        _pattern(
            "pattern:spawn:pairwise-2d-exposed",
            status="disputed",
            scale="neighborhood",
            subject="spawn-neighborhood",
            population=bb,
            match={"peek": "high", "sky": "1"},
            tags=["spawn-sight", "2d-limit"],
            description="Sky starts whose pairwise 2D sight to other starts is commonly clear.",
            label="2D spawn-to-spawn sight is open (not the same as 3D concealment)",
            rationale=(
                "BB6 is 28/28 clear including lower-Z depression starts. The sensor "
                "ignores height, so this cannot be read as 'no concealment'."
            ),
            required_evidence=["spawn_sight_report"],
            confidence="low",
            counterexamples=[{
                "claim_rejected": "high 2D peek means starts are unconcealed in play",
                "why": "2D rays ignore floor delta; BB6 lower-Z starts may be vertically offset from yard starts",
                "maps": ["BB6.MAP"],
            }, {
                "claim_rejected": "outdoor BloodBath starts are pairwise hidden",
                "why": "BB6 outdoor starts are pairwise 2D-visible; BB2 is the opposite extreme",
                "maps": ["BB6.MAP", "BB2.MAP"],
            }],
        ),
        _pattern(
            "pattern:route:all-sky-shortest-path",
            status="supported",
            scale="route",
            subject="route-exposure",
            population=bb,
            match={"seq": "S", "skyfrac": "high"},
            tags=["all-sky-route"],
            description="Shortest at-rest path from a start to the largest sky sector never samples cover.",
            label="spawn-to-field shortest path stays under sky",
            rationale="All eight BB6 routes and many BB8/BB9 routes. Also appears on BB1.",
            required_evidence=["route_exposure_report"],
            confidence="medium",
            counterexamples=[{
                "claim_rejected": "all-sky shortest path means the map has no interiors",
                "why": "BB6 has 151 covered sectors and 11 holed outdoor loops; the route sensor only walks start→largest sky",
                "maps": ["BB6.MAP"],
            }],
        ),
        _pattern(
            "pattern:route:cover-then-open",
            status="hypothesis",
            scale="route",
            subject="route-exposure",
            population=bb,
            match={"seq": "CS"},
            tags=["cover-to-open"],
            description="Shortest path samples cover first, then sky.",
            label="covered approach into open circulation",
            rationale="Recurs on BB2, BB7, BB8, BB9. Shade/Z bins vary; geometry alone is not a reveal.",
            required_evidence=["route_exposure_report"],
            confidence="low",
            counterexamples=[{
                "claim_rejected": "cover→open is a dramatic reveal",
                "why": "some CS routes are flat in Z and shade; they read as a doorway, not a staged reveal",
                "maps": ["BB1.MAP", "BB8.MAP"],
            }],
        ),
        _pattern(
            "pattern:route:open-cover-open",
            status="hypothesis",
            scale="route",
            subject="route-exposure",
            population=bb,
            match={"seq": "SCS"},
            tags=["through-mass"],
            description="Sky path interrupted by a covered sample, then sky again.",
            label="outdoor circulation interrupted by a covered mass",
            rationale="Appears on BB1 and BB2. Rare in the nine-map BloodBath set.",
            required_evidence=["route_exposure_report"],
            confidence="low",
        ),
        _pattern(
            "pattern:morph:rectangular-covered-cell",
            status="disputed",
            scale="local",
            subject="local-morphology",
            population=bb,
            match={"rect": "1", "convex": "1", "verts": "4", "sky": "0", "holes": "0"},
            tags=["orthogonal-cell", "construction-default"],
            description="Axis-aligned 4-vertex covered loop. The most common BloodBath local footprint.",
            label="rectangular covered cell (too common to imply a gameplay role)",
            rationale="202 samples on all 9 BB maps. Clustering geometry, not a reusable design relation.",
            required_evidence=["analyze_morphology"],
            confidence="high",
            counterexamples=[{
                "claim_rejected": "a rectangle is a room type (arena, closet, hub)",
                "why": "the same signature appears as storage, stairs, porches, and generic interiors",
                "maps": ["BB1.MAP", "BB6.MAP"],
            }],
        ),
        _pattern(
            "pattern:morph:irregular-covered-footprint",
            status="supported",
            scale="local",
            subject="local-morphology",
            population=bb,
            match={"rect": "0", "verts": "9+", "sky": "0", "fill": "loose"},
            tags=["irregular-footprint"],
            description="Non-rectangular covered loop with 9+ vertices and loose AABB fill.",
            label="irregular covered footprint as Blood's indoor architectural grain",
            rationale="Present on all 9 original BloodBath maps. Opposite of the rectangular default.",
            required_evidence=["analyze_morphology"],
            confidence="medium",
        ),
        _pattern(
            "pattern:morph:chamfered-irregular",
            status="supported",
            scale="local",
            subject="local-morphology",
            population=bb,
            match={"chamfer": "1+", "verts": "9+", "sky": "0"},
            tags=["chamfer"],
            description="High-vertex covered loop with chamfer-like corners.",
            label="chamfered irregular indoor mass",
            rationale="Eight of nine BloodBath maps. A local wall-chain motif, not a named room.",
            required_evidence=["analyze_morphology"],
            confidence="medium",
        ),
        _pattern(
            "pattern:morph:segmented-curve-chain",
            status="supported",
            scale="local",
            subject="local-morphology",
            population=bb,
            match={"curve": "1+", "sky": "0"},
            tags=["segmented-curve"],
            description="Covered loop containing a segmented-arc / curved-chain candidate.",
            label="segmented curve as a local masonry motif",
            rationale="Six BloodBath maps. Distinct from chamfers and from pure rectangles.",
            required_evidence=["analyze_morphology"],
            confidence="medium",
        ),
        _pattern(
            "pattern:morph:sky-host-with-holes",
            status="supported",
            scale="local",
            subject="local-morphology",
            population=bb,
            match={"sky": "1", "holes": "1+"},
            tags=["carved-mass", "outdoor-host"],
            description="Sky sector whose outer loop contains one or more holes.",
            label="outdoor host with carved building masses",
            rationale="BB6 has multiple holed sky loops; this is the footprint relation behind twin fortresses, not 'octagon'.",
            required_evidence=["analyze_morphology"],
            confidence="medium",
        ),
        _pattern(
            "pattern:vertical:storey-same-cover-into-larger",
            status="hypothesis",
            scale="route",
            subject="vertical-transition",
            population=bb,
            match={"step": "storey", "sky": "same", "into": "large"},
            tags=["height-change"],
            description="Walkable rest transition of about a storey within the same sky/cover class into a larger cell.",
            label="storey-scale height change into a larger same-cover cell",
            rationale="The single most common vertical signature on all 9 BB maps. Too frequent to mean 'overlook'.",
            required_evidence=["spatial.traversability"],
            confidence="low",
            counterexamples=[{
                "claim_rejected": "a storey delta is an overlook / sniper balcony",
                "why": "most samples are ordinary stairs or floor splits with no visibility or resource context",
                "maps": ["BB1.MAP", "BB6.MAP"],
            }],
        ),
        _pattern(
            "pattern:vertical:open-into-cover",
            status="supported",
            scale="route",
            subject="vertical-transition",
            population=bb,
            match={"sky": "open_to_cover"},
            tags=["enter-building"],
            description="Walkable transition from a sky sector into a covered sector.",
            label="leaving outdoor circulation into a covered mass",
            rationale="Rarer than same-sky steps. BB1, BB6, BB7. Often a descent on BB6.",
            required_evidence=["spatial.traversability", "ceiling_stat"],
            confidence="medium",
        ),
        _pattern(
            "pattern:vertical:cover-into-open",
            status="supported",
            scale="route",
            subject="vertical-transition",
            population=bb,
            match={"sky": "cover_to_open"},
            tags=["exit-building"],
            description="Walkable transition from cover into sky.",
            label="emerging from a covered mass into outdoor circulation",
            rationale="The reverse of open-into-cover. Needs route/resource context before calling it a reveal.",
            required_evidence=["spatial.traversability", "ceiling_stat"],
            confidence="medium",
        ),
        _pattern(
            "pattern:campaign-route:cover-then-open",
            status="supported",
            scale="route",
            subject="route-exposure",
            population="blood-campaign",
            match={"seq": "CS"},
            tags=["cover-to-open", "campaign-start"],
            description="Campaign start-to-sky shortest path samples cover first, then sky.",
            label="single-player start typically approaches outdoor space from cover",
            rationale=(
                "Dominant unsigned campaign route family (many E* maps). Not mixed with "
                "BloodBath statistics; BB6 is the opposite (all-sky shortest paths)."
            ),
            required_evidence=["route_exposure_report"],
            confidence="medium",
            counterexamples=[{
                "claim_rejected": "Blood maps generally spawn into outdoor hunting space",
                "why": "original campaign routes are mostly CS; original BloodBath BB6 is all-sky",
                "maps": ["E1M3.MAP", "BB6.MAP"],
            }],
        ),
        _pattern(
            "pattern:campaign-morph:rectangular-covered-cell",
            status="disputed",
            scale="local",
            subject="local-morphology",
            population="blood-campaign",
            match={"rect": "1", "convex": "1", "verts": "4", "sky": "0", "holes": "0"},
            tags=["orthogonal-cell", "construction-default"],
            description="Axis-aligned 4-vertex covered loop. The modal campaign footprint.",
            label="rectangular covered cell (campaign construction default)",
            rationale="3495 samples on 42 campaign maps. Same signature as BloodBath; still not a room role.",
            required_evidence=["analyze_morphology"],
            confidence="high",
        ),
        _pattern(
            "pattern:campaign-morph:irregular-covered-footprint",
            status="supported",
            scale="local",
            subject="local-morphology",
            population="blood-campaign",
            match={"rect": "0", "verts": "9+", "sky": "0", "fill": "loose"},
            tags=["irregular-footprint"],
            description="Non-rectangular covered 9+ vertex loops with loose AABB fill in campaign maps.",
            label="irregular covered footprint in original campaign architecture",
            rationale="Same relation as BloodBath, independently counted on E* maps.",
            required_evidence=["analyze_morphology"],
            confidence="medium",
        ),
        _pattern(
            "pattern:campaign-vertical:storey-same-cover-into-larger",
            status="hypothesis",
            scale="route",
            subject="vertical-transition",
            population="blood-campaign",
            match={"step": "storey", "sky": "same", "into": "large"},
            tags=["height-change"],
            description="Campaign storey-scale rest transitions within the same sky/cover class into a larger cell.",
            label="storey height change into a larger same-cover cell (campaign)",
            rationale="Very common; still insufficient for 'overlook' without visibility/resource context.",
            required_evidence=["spatial.traversability"],
            confidence="low",
        ),
    ]


def compile_v1(unsigned_paths: list[Path] | None = None) -> dict:
    catalog = {
        "$schema": "llmapper.design-pattern-catalog",
        "schema_version": 1,
        "id": "knowledge/blood/design/catalog-v1",
        "version": "v1",
        "status": "hypothesis",
        "kind": "derived+interpreted",
        "populations": ["blood-bloodbath", "blood-campaign"],
        "notes": [
            "Names are INTERPRETED after discrete signature discovery.",
            "Campaign maps are mined separately and are not mixed into these statistics.",
            "Generated and conversion maps are not evidence.",
            "A place may match several patterns.",
        ],
        "patterns": templates(),
    }
    paths = unsigned_paths or [
        REPO / "work" / "blood-pattern-unsigned-bloodbath.json",
        REPO / "work" / "blood-pattern-unsigned-campaign.json",
    ]
    for path in paths:
        unsigned = json.loads(path.read_text(encoding="utf-8"))
        attach_corpus_occurrences(catalog, unsigned, max_occurrences=24)
    catalog["pattern_count"] = len(catalog["patterns"])
    catalog["supported"] = sum(1 for item in catalog["patterns"] if item["status"] == "supported")
    catalog["disputed"] = sum(1 for item in catalog["patterns"] if item["status"] == "disputed")
    catalog["hypothesis"] = sum(1 for item in catalog["patterns"] if item["status"] == "hypothesis")
    return catalog


def corpus_summary(catalog: dict, unsigned_paths: list[Path]) -> dict:
    mines = []
    for path in unsigned_paths:
        if not path.exists():
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        by_subject = {}
        for candidate in payload.get("candidates") or []:
            by_subject.setdefault(candidate["subject"], {"candidates": 0, "samples": 0})
            by_subject[candidate["subject"]]["candidates"] += 1
            by_subject[candidate["subject"]]["samples"] += candidate["occurrence_count"]
        mines.append({
            "population": payload.get("population"),
            "maps_mined": payload.get("maps_mined"),
            "sample_count": payload.get("sample_count"),
            "candidate_count": len(payload.get("candidates") or []),
            "observe_errors": payload.get("observe_errors") or [],
            "medians": payload.get("medians"),
            "by_subject": by_subject,
        })
    return {
        "$schema": "llmapper.design-pattern-corpus-summary",
        "schema_version": 1,
        "catalog": catalog.get("id"),
        "catalog_version": catalog.get("version"),
        "pattern_count": catalog.get("pattern_count"),
        "supported": catalog.get("supported"),
        "hypothesis": catalog.get("hypothesis"),
        "disputed": catalog.get("disputed"),
        "mines": mines,
        "patterns": [
            {
                "id": item["id"],
                "status": item["status"],
                "population": item["population"],
                "subject": item["subject"],
                "occurrence_count": item.get("occurrence_count"),
                "map_count": item.get("map_count"),
                "maps": item.get("maps"),
                "interpretation": (item.get("interpretation") or {}).get("label"),
            }
            for item in catalog.get("patterns") or []
        ],
    }


def main() -> None:
    unsigned = [
        REPO / "work" / "blood-pattern-unsigned-bloodbath.json",
        REPO / "work" / "blood-pattern-unsigned-campaign.json",
    ]
    catalog = compile_v1(unsigned)
    out = ROOT / "catalog-v1.json"
    out.write_text(json.dumps(catalog, indent=2) + "\n", encoding="utf-8")
    summary = corpus_summary(catalog, unsigned)
    summary_path = REPO / "reports" / "blood-pattern-corpus-summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(
        f"wrote {out} patterns={catalog['pattern_count']} "
        f"supported={catalog['supported']} disputed={catalog['disputed']} "
        f"hypothesis={catalog['hypothesis']}"
    )
    print(f"wrote {summary_path}")
    for pattern in catalog["patterns"]:
        print(
            f"  {pattern['occurrence_count']:4d} maps={pattern['map_count']} "
            f"{pattern['status']:10s} {pattern['id']}"
        )


if __name__ == "__main__":
    main()
