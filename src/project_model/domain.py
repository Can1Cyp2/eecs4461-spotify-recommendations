# reads the songs and listening sets, then calculates their similarity:
from collections import Counter
from dataclasses import dataclass
from fractions import Fraction
import csv
import json
from pathlib import Path
import re

NUMERIC = ("bpm", "duration_seconds", "release_year")
SCENARIOS = ("aligned", "half_different", "contrasting")
WEIGHTS = (Fraction(0), Fraction(1, 4), Fraction(1, 2), Fraction(3, 4), Fraction(1))
#these weights for the five characteristics stay fixed, only the balance between the two profiles changes:
FEATURE_WEIGHTS = {
    "genre": Fraction(50, 100), "bpm": Fraction(15, 100),
    "release_year": Fraction(20, 100), "duration_seconds": Fraction(10, 100),
    "key": Fraction(5, 100),
}
DEFAULT_GENRE_GROUPS = {
    "rock": "Rock", "alt rock": "Rock", "pop": "Pop", "pop rock": "Pop Rock",
    "electronic": "Electronic", "jazz": "Jazz", "hip hop": "Hip Hop",
}
SOURCE_FIELDS = ("title", "artist", "genre", "bpm", "key", "duration_seconds", "release_year")


@dataclass(frozen=True)
class Track:
    # stores one songs metadata from the catalogue:
    track_id: str
    title: str
    artist: str
    genre: str
    bpm: Fraction
    key: str
    duration_seconds: Fraction
    release_year: int
    evidence_status: str
    version: str = ""
    work_id: str = ""


@dataclass(frozen=True)
class Profile:
    # summarizes ten songs as genre/key proportions and average numeric values:
    ids: tuple
    genre_mix: dict
    key_mix: dict
    means: dict


def normalize_genre(label, groups=None):
    # removes extra spaces and groups the genre names listed above:
    label = " ".join(str(label).split())
    if not label:
        raise ValueError("Missing genre")
    aliases = dict(DEFAULT_GENRE_GROUPS)
    for raw, canonical in (groups or {}).items():
        raw = " ".join(str(raw).split()).casefold()
        canonical = " ".join(str(canonical).split())
        if not raw or not canonical:
            raise ValueError("Empty genre grouping")
        aliases[raw] = DEFAULT_GENRE_GROUPS.get(canonical.casefold(), canonical.casefold().title())
    # keeps other genres separate, ignoring differences in capitalization:
    return aliases.get(label.casefold(), label.casefold().title())

def normalize_key(label):
    # puts equivalent key names in the same format, (ex. Db major becomes C# major):
    label = " ".join(str(label).split())
    match = re.fullmatch(r"([a-g])\s*([#b♯♭]?)\s*(major|minor|maj|min)", label, re.I)
    if not match:
        raise ValueError(f"Key must identify a note and major/minor mode: {label!r}")
    note, accidental, mode = match.groups()
    pitch = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}[note.upper()]
    if accidental in ("#", "♯"):
        pitch += 1
    elif accidental.casefold() in ("b", "♭"):
        pitch -= 1
    canonical = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")[pitch % 12]
    return canonical + " " + ("major" if mode.casefold() in ("major", "maj") else "minor")


def number(value, field, track_id):
    # reads a positive number as a fraction so rounding does not affect the ranking:
    try:
        result = Fraction(str(value).strip())
    except (ValueError, ZeroDivisionError) as e:
        raise ValueError(f"Invalid finite {field} for {track_id}: {value!r}") from e
    if result <= 0:
        raise ValueError(f"{field} must be positive for {track_id}")
    return result

def dataset_status(tracks):
    # checks that made-up song metadata is not mixed with metadata for real songs:
    statuses = {t.evidence_status for t in tracks}
    if statuses == {"synthetic"}:
        return "synthetic"
    if "synthetic" in statuses:
        raise ValueError("Do not mix synthetic and real track metadata in a catalogue")
    return "real_metadata"

def load_inputs(data_dir):
    # reads the catalogue and checks the data needed for all five characteristics:
    data_dir = Path(data_dir)
    with (data_dir / "catalogue.csv").open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    groups_path = data_dir / "genre_groups.json"
    groups = json.loads(groups_path.read_text(encoding="utf-8")) if groups_path.exists() else {}
    if not isinstance(groups, dict):
        raise ValueError("genre_groups.json must map original genre names to the names used for scoring")
    if normalize_genre("Pop Rock", groups) == normalize_genre("Rock", groups):
        raise ValueError("Pop Rock and Rock must stay separate for scoring")
    if normalize_genre("Pop Rock", groups) == normalize_genre("Pop", groups):
        raise ValueError("Pop and Pop Rock must stay separate for scoring")
    if normalize_genre("Alt Rock", groups) != normalize_genre("Rock", groups):
        raise ValueError("Alt Rock must be grouped with Rock for scoring")
    tracks = []
    for row in rows:
        row = {k: (v or "").strip() for k, v in row.items() if k is not None}
        track_id = row.get("track_id", "")
        for field in ("track_id", "title", "artist", "genre", "key", "evidence_status"):
            if not row.get(field):
                raise ValueError(f"Missing {field} for {track_id or 'a catalogue row'}")
        row["genre"] = normalize_genre(row["genre"], groups)
        row["key"] = normalize_key(row["key"])
        row["bpm"] = number(row.get("bpm", ""), "bpm", track_id)
        row["duration_seconds"] = number(row.get("duration_seconds", ""), "duration_seconds", track_id)
        year = number(row.get("release_year", ""), "release_year", track_id)
        if year.denominator != 1:
            raise ValueError(f"release_year must be an integer for {track_id}")
        row["release_year"] = int(year)
        if row["evidence_status"] not in ("synthetic", "observed", "inferred"):
            raise ValueError(f"Unknown evidence status for {track_id}")
        try:
            track = Track(**row)
        except TypeError as e:
            raise ValueError(f"Unsupported/missing catalogue columns: {e}") from e
        tracks.append(track)

    # checks that the catalogue has 90 different songs, with one version of each song:
    ids = {t.track_id for t in tracks}
    if len(tracks) != 90 or len(ids) != 90:
        raise ValueError("Expected 90 songs, each with a different track_id")
    if len({(t.title.casefold(), t.artist.casefold()) for t in tracks}) != 90:
        raise ValueError("Duplicate song title/artist pair; keep one identified version")
    work_ids = [t.work_id for t in tracks if t.work_id]
    if len(work_ids) != len(set(work_ids)):
        raise ValueError("Duplicate work_id; keep one identified version per song")
    status = dataset_status(tracks)

    # checks that each listening set has ten songs from the catalogue:
    config = json.loads((data_dir / "profiles.json").read_text(encoding="utf-8"))
    if config.get("evidence_status") not in ("synthetic", "hypothetical"):
        raise ValueError("Listening sets must be labelled hypothetical or synthetic")
    if set(config["recent"]) != set(SCENARIOS):
        raise ValueError("Expected these recent-listening scenarios: aligned, half_different, contrasting")
    for name, members in [("established", config["established"]), *config["recent"].items()]:
        if len(members) != 10 or len(set(members)) != 10 or not set(members) <= ids:
            raise ValueError(f"{name}: expected ten different song IDs, all from the catalogue")
    # aligned shares ten songs with established taste, half different shares five, contrasting shares none:
    established = set(config["established"])
    for scenario, overlap in zip(SCENARIOS, (10, 5, 0)):
        if len(established & set(config["recent"][scenario])) != overlap:
            raise ValueError(f"{scenario}: expected {overlap} song IDs shared with established taste")
    # uses the full catalogue for the min/max scales, keeping them fixed for all runs:
    scales = {n: (min(getattr(t, n) for t in tracks), max(getattr(t, n) for t in tracks)) for n in NUMERIC}
    if status != "synthetic":
        design = config.get("profile_design", {})
        if design.get("selected_before_runs") is not True or not str(design.get("selection_reason", "")).strip():
            raise ValueError("profiles.json must confirm the listening sets were selected before running and explain why they were chosen")
        # checks that the recent sets differ in the characteristics described in my plan:
        for scenario, checks in profile_checks(tracks, config, scales).items():
            if scenario == "aligned":
                continue
            if not checks["key_distribution_differs"]:
                raise ValueError(f"{scenario}: recent listening must differ from established taste in musical keys")
            if scenario == "contrasting" and not (checks["genre_distribution_differs"] and checks["tempo_distribution_differs"]):
                raise ValueError("contrasting: recent listening must differ from established taste in both genre and tempo")
            if scenario == "half_different" and not (checks["genre_distribution_differs"] or checks["tempo_distribution_differs"]):
                raise ValueError("half_different: recent listening must differ from established taste in genre or tempo")
    return tracks, config, scales

def scaled(value, limits):
    # maps a numeric value to 0 to 1 using the catalogue minimum and maximum:
    low, high = limits
    return Fraction(value-low, high-low) if high != low else Fraction(0)

def make_profile(ids, by_id, scales):
    # summarizes a listening set, with each of its ten songs contributing equally:
    songs = [by_id[i] for i in ids]
    genre_mix = {genre: Fraction(count, len(songs)) for genre, count in Counter(t.genre for t in songs).items()}
    key_mix = {key: Fraction(count, len(songs)) for key, count in Counter(t.key for t in songs).items()}
    means = {
        name: sum((scaled(getattr(t, name), scales[name]) for t in songs), Fraction(0)) / len(songs)
        for name in NUMERIC
    }
    return Profile(tuple(ids), genre_mix, key_mix, means)

def components(track, profile, scales):
    # genre and key use the proportion of matching songs, numeric values use distance from the profile average:
    return {
        "genre": profile.genre_mix.get(track.genre, Fraction(0)),
        "key": profile.key_mix.get(track.key, Fraction(0)),
        **{n: 1 - abs(scaled(getattr(track, n), scales[n]) - profile.means[n]) for n in NUMERIC},
    }

def similarity(track, profile, scales):
    # combines the five matches using their fixed weights, returning a score from 0 to 1:
    matches = components(track, profile, scales)
    return sum((FEATURE_WEIGHTS[name] * match for name, match in matches.items()), Fraction(0))

def profile_checks(tracks, config, scales):
    # compares recent listening with established taste for the three scenario checks:
    by_id = {t.track_id: t for t in tracks}
    established = [by_id[i] for i in config["established"]]
    result = {}
    for scenario, ids in config["recent"].items():
        recent = [by_id[i] for i in ids]
        result[scenario] = {
            "overlap": len(set(config["established"]) & set(ids)),
            "eligible_count": 90 - len(set(config["established"]) | set(ids)),
            "genre_distribution_differs": Counter(t.genre for t in established) != Counter(t.genre for t in recent),
            "key_distribution_differs": Counter(t.key for t in established) != Counter(t.key for t in recent),
            "tempo_distribution_differs": Counter(t.bpm for t in established) != Counter(t.bpm for t in recent),
            "mean_bpm_difference": float(
                sum((t.bpm for t in recent), Fraction(0)) / 10
                - sum((t.bpm for t in established), Fraction(0)) / 10
            ),
        }
    return result

