"""Mine Blood's sound IDs, mapper-authored uses, and speech from the local game archive."""

from __future__ import annotations

import argparse
import json
import math
import re
import struct
import wave
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from bloodmap.corpus import campaign_maps
from bloodmap.format import read_map
from bloodmap.model import record_extra, record_fields
from bloodmap.shade_table import read_rff

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "reference/blood/SOUNDS.RFF"
SHELF = ROOT / "knowledge/blood/sounds.json"
PUBLISHED = ROOT / "work/briefs/sector_ambient_sfx.json"
WORK = ROOT / "work/sound-catalog"
SOURCE = "NBlood/source/blood/src/"
FORMAT_SOURCES = [
    SOURCE + "sound.h:33-41",
    SOURCE + "sfx.cpp:163-175",
    SOURCE + "sfx.cpp:232-247",
    SOURCE + "sound.cpp:55-76",
]
RATE_TABLE = (11025,) * 5 + (22050,) * 4 + (44100,) * 4
MODEL = "medium.en"

# Role names describe what the engine plays, including reversal.
SPRITE_SLOTS = {
    20: ("kSwitchToggle", {"data_1": "on", "data_2": "off"}),
    21: ("kSwitchOneWay", {"data_1": "on", "data_2": "off"}),
    22: ("kSwitchCombo", {"data_4": "turn"}),
    708: ("kGenSound", {"data_2": "repeat"}),
    709: ("kSoundSector", {"data_1": "start from off", "data_2": "end at on",
                           "data_3": "start from on", "data_4": "end at off"}),
    711: ("kSoundPlayer", {"data_1": "play to player"}),
}
USAGE_SOURCES = {
    "kSwitchToggle": SOURCE + "triggers.cpp:441-455",
    "kSwitchOneWay": SOURCE + "triggers.cpp:458-472",
    "kSwitchCombo": SOURCE + "triggers.cpp:475-489",
    "kGenSound": SOURCE + "triggers.cpp:2385-2387",
    "kSoundSector": SOURCE + "triggers.cpp:759-804",
    "kSoundPlayer": SOURCE + "triggers.cpp:617-625",
    "ambient sprite": SOURCE + "asound.cpp:120-161",
    "kMarkerPath": SOURCE + "triggers.cpp:1487,1640",
    "kWallGib": SOURCE + "triggers.cpp:714-737; " + SOURCE + "gib.cpp:227-241,501-502",
}
ARCHIVE_SOURCE = "reference/blood/SOUNDS.RFF"
FAQ_SOURCE = "https://rtcmsite.neocities.org/knowledge-base/library-online/blood-mapedit-map%20editing%20and%20effectsv2"
NAME_DESCRIPTIONS = {
    67: "Fan loop",
    100: "Door creak as the door starts to open or close",
    101: "Door opening",
    109: "Door sound",
    110: "Door moving",
    112: "Platform moving",
    115: "Train sound",
    117: "Small creaking door",
    119: "Sliding creak",
    121: "Sliding door",
    123: "Flush door",
    154: "Air door",
    204: "Attempt to operate a mechanism",
    205: "Mechanism in use",
    208: "Zippo lighter flick",
    210: "Switch breaking",
    264: "Looping hum",
    265: "Earth rumble",
    266: "Sine-wave tone",
    269: "Laughter",
    270: "Bell",
    271: "Owl call",
    478: "Tesla weapon zap",
    479: "Tesla weapon zap",
    495: "Acid impact",
    496: "Acid impact",
    707: "Breathing",
    720: "Submerging in water",
    803: "Footstep on stone",
    810: "Footstep in water",
    811: "Footstep in water",
    2006: "Bat sound",
    2202: "Pod squish",
    2400: "Fly buzzing",
    2401: "Fly sound",
    2450: "Fire pod closing",
    2451: "Fire pod collision",
    2452: "Fire pod explosion",
    2453: "Fire pod opening",
    2454: "Fire pod spitting",
    2470: "Pod closing",
    2471: "Pod collision",
    2472: "Pod explosion",
    2473: "Pod opening",
    2474: "Pod spitting",
    2475: "Pod spitting",
    2500: "Tentacle going down",
    2501: "Tentacle explosion",
    2502: "Tentacle sweeping",
    2503: "Tentacle coming up",
    9007: "Caleb transformation vocalization",
    9008: "Cultist transformation vocalization",
}
ENGINE_DESCRIPTIONS = {
    201: ("Teleporter activation", "triggers.cpp:1578"),
    300: ("Glass shattering on a gib wall", "gib.cpp:227-241,501-502"),
    461: ("Chant when the voodoo doll is drawn", "weapon.cpp:2611"),
    1103: ("Axe zombie spots the player", "ai.cpp:567"),
    1104: ("Axe zombie voice", "ai.cpp:570"),
    1200: ("Bloated butcher spots the player", "ai.cpp:607"),
    1201: ("Bloated butcher roaming voice", "ai.cpp:605"),
    3009: ("Caleb speaks when revived in multiplayer", "player.cpp:2658"),
    8000: ("Blue flag captured announcement", "player.cpp:1313"),
    8001: ("Red flag captured announcement", "player.cpp:1269"),
    8002: ("Red flag returned announcement", "player.cpp:1302"),
    8003: ("Blue flag returned announcement", "player.cpp:1258"),
    8004: ("Red flag dropped announcement", "player.cpp:2374"),
    8005: ("Blue flag dropped announcement", "player.cpp:2364"),
    8006: ("Red flag taken announcement", "player.cpp:1290"),
    8007: ("Blue flag taken announcement", "player.cpp:1246"),
    9008: ("Cultist morphing into a beast", "ai.cpp:1065"),
}
QUOTE_SOURCES = {
    3001: ("Army of Darkness (1992)",
           "https://thescriptsavant.com/movies/Army_Of_Darkness.pdf"),
    3003: ("Apocalypse Now (1979)",
           "https://cinephiliabeyond.org/wp-content/uploads/2015/04/Apocalypse-Now-1975.12.03.compressed.pdf"),
    3012: ("The Crow (1994)",
           "https://steamcommunity.com/sharedfiles/filedetails/?id=2524394088"),
    3027: ("The Raven, by Edgar Allan Poe",
           "https://www.gutenberg.org/ebooks/1065"),
    3060: ("Macbeth, Act 5, Scene 1",
           "https://www.folger.edu/explore/shakespeares-works/macbeth/read/5/1/"),
    4500: ("Jaws (1975)", "https://www.youtube.com/watch?v=qCzncv0ISaE"),
}

CREATURES = {
    "TCLT": "Tommy-gun cultist", "CULT": "Cultist", "AZOM": "Axe zombie",
    "CERB": "Cerberus", "GARG": "Flesh gargoyle", "SARG": "Stone gargoyle",
    "EEL": "Bone eel", "BAT": "Bat", "RAT": "Rat", "POD": "Pod",
}
CREATURE_ROLES = {
    "SPT": "spotting the player", "ROAM": "roaming", "ROM": "roaming",
    "PAN": "in pain", "PAIN": "in pain", "DIE": "dying", "GLO": "gloating",
    "FIR": "on fire",
}
CABAL_SOURCE = "https://blood-wiki.org/index.php/Cultist_Language"
# Where the screening decode is phonetically close to a documented Cabal line.
CABAL_FORMS = {
    "2001A": "Vorox esco marana!",
    "2001B": "Crudux cruo!",
    "2002Z": "Cruo crunatus durbe!",
    "2003A": "Maranax pallex!",
    "2004": "Maranax infirmux!",
    "2005": "Geroxe cruo!",
    "2006": "Cruo stragarana malaxos!",
    "2007": "En marana domus nava crunatus!",
    "2008Z": "Geroxe bibox malax!",
}
CABAL_SOUNDS = {59, 63, 461, *range(1003, 1013), *range(1021, 1025),
                *range(4003, 4013), *range(4021, 4025)}
EXTRA_SPEECH = {219, 220, 224, 267, 282, 283, 289, 743, 1032, 1103, 1104,
                1200, 1201, 3209, 3214, 3216, 4032,
                *range(7002, 7007)}
NONVERBAL = {269, 707, 711, 713, 716, 717, 719, 725, 726, 730, 735, 738, 740,
             1031, 1033, 1202, 3059, 4031, 4033, 4503, 4504, 4505, 4506,
             7000, 7001, 7007, 7008, 7009, 9007}
AUDIO_DESCRIPTIONS = {727: "Short scream", 735: "Laughter", 738: "Laughter",
                      739: "Laughter", 740: "Laughter", 741: "Laughter"}
UNRESOLVED_SPEECH = {219, 220, 267, 1201, 3211, 3214}
VERIFY_IDS = {1900, 2350, 2367, 742, 743, 3001, 3003, 3004, 3005, 3008, 3009, 3011,
              3012, 3018, 3020, 3027, 3028, 3029, 3050, 4003, 7002, 8000, 9007,
              10000, 11000}
EXTRA_VERIFY_IDS = {282, 283, 289, 350, 461, 1031, 1032, 1033, 1104, 1200, 1201,
                    1900, 1901, 2352, 2353, 2356, 3059, 3068, 3075, 3076, 3077,
                    3103, 3110, 3200, 3203, 3206, 3211, 3314, 3333, 3341, 4500,
                    4031, 4032, 4033, *range(8000, 8008)}
FAN_READINGS = {
    224: "Kill, kill, kill, kill.",
    282: "Tickets, please!",
    1104: "More brains!",
    1900: "I'll swallow your soul!",
    2352: "Kneel!",
    2353: "Kneel!",
    3016: "I've got a present for you.",
    3026: "Lambs to the slaughter.",
    3048: "Mmm, this is better than Kool-Aid.",
    3068: "Leftovers.",
    3075: "Whoa! Wrong car!",
    3076: "Oh, Ophelia!",
    3077: "Sleep, Ophelia.",
    3200: "Hello, may I speak to Mr. Jass? First name's Hugh.",
    3206: "You rang?",
}
ENGINE_READINGS = {
    8000: "Red captures the flag.",
    8002: "Red returns the flag.",
    8003: "Blue returns the flag.",
    8006: "Red flag stolen.",
}
NAME_READINGS = {
    "BONED": "Boned!",
    "CASTRA": "Castrated!",
    "DICED": "Diced!",
    "MINCMEAT": "Mincemeat!",
    "REAMED": "Reamed!",
    "RIPPED": "Ripped!",
    "SODOMIZ": "Sodomized!",
    "SPLATT": "Splattered!",
    "SQUASH": "Squashed!",
    "THROTTL": "Throttled!",
}


@dataclass(frozen=True)
class Sample:
    id: int
    name: str
    raw_name: str
    format: int
    pitch: int
    loop_start: int
    pcm: bytes | None

    @property
    def rate(self) -> int:
        return RATE_TABLE[self.format] if self.format < len(RATE_TABLE) else 11025

    @property
    def playback_rate(self) -> int:
        return (self.rate * self.pitch) >> 16

    @property
    def clip(self) -> tuple[str, int]:
        return self.raw_name, self.playback_rate


def read_samples(path: Path) -> dict[int, Sample]:
    """Join numbered SFX headers to case-insensitive, unsigned 8-bit mono RAW samples."""
    entries = read_rff(path)
    raw = {name.upper(): data for (kind, _, name), data in entries.items() if kind == "RAW"}
    samples = {}
    for (kind, ident, name), data in entries.items():
        if kind != "SFX":
            continue
        if ident in samples or len(data) < 21 or b"\0" not in data[20:]:
            raise ValueError(f"Invalid or duplicate SFX header {ident} ({name})")
        _, pitch, _, fmt, loop_start = struct.unpack_from("<5i", data)
        # PODSQUIS has an overlong RAW name in the shipped archive.
        raw_name = data[20:].split(b"\0", 1)[0].decode("ascii").upper()
        if fmt < 0 or pitch <= 0:
            raise ValueError(f"Invalid format or pitch in SFX {ident} ({name})")
        samples[ident] = Sample(ident, name, raw_name, fmt, pitch, loop_start, raw.get(raw_name))
    if not samples:
        raise ValueError(f"No SFX entries in {path}")
    return dict(sorted(samples.items()))


def map_sound_slots(disk):
    """Yield sound ID, role, field and indices for the campaign's sound-bearing records."""
    for index, sprite in enumerate(disk.sprites):
        extra = record_extra(sprite)
        if extra is None:
            continue
        fields = record_fields(sprite)
        sprite_type, sector = fields["type"], fields["sector"]
        if fields["status"] == 12 and extra["data_1"] < extra["data_2"]:
            kind, slots = "ambient sprite", {"data_3": "loop"}
        elif sprite_type == 15:
            kind, slots = "kMarkerPath", {"data_3": "departure", "data_4": "arrival"}
            sector = None  # The marker can be outside the moving sector.
        elif sprite_type == 709 and fields["status"] != 0:
            continue
        else:
            kind, slots = SPRITE_SLOTS.get(sprite_type, ("", {}))
        for field, role in slots.items():
            if extra[field] > 0:
                yield extra[field], kind, "sprite", index, field, role, sector

    # XWALL data selects a gib type. Only these nonzero types play a sound.
    for index, wall in enumerate(disk.walls):
        extra = record_extra(wall)
        if record_fields(wall)["type"] == 511 and extra and extra["data"] in (1, 12, 13):
            yield 300, "kWallGib", "wall", index, "data", "glass break", None


def campaign_uses(paths) -> dict[int, list[dict]]:
    """Count configured sound slots by type and role, with the first example of each."""
    uses = defaultdict(dict)
    for path in paths:
        disk = read_map(path)
        for ident, kind, obj, index, field, role, sector in map_sound_slots(disk):
            sector_type = (record_fields(disk.sectors[sector])["type"]
                           if sector is not None and 0 <= sector < len(disk.sectors) else None)
            group_type = sector_type if kind == "kSoundSector" and sector_type is not None else -1
            key = (kind, field, role, group_type)
            if key not in uses[ident]:
                example = {"map_index": f"{path.stem.upper()}:{index}", "record": obj}
                if sector_type is not None:
                    example["sector"] = sector
                    example["sector_type"] = sector_type
                uses[ident][key] = {"kind": kind, "field": field, "role": role,
                                    "count": 0, "example": example}
            uses[ident][key]["count"] += 1
    return {ident: [rows[key] for key in sorted(rows)] for ident, rows in uses.items()}


def read_published(path: Path) -> dict[int, list[dict]]:
    data = json.loads(path.read_text("utf-8"))
    descriptions = defaultdict(list)
    for row in data["sounds"]:
        descriptions[row["id"]].append(
            {"text": row["description"], "source": data["source"], "title": data["title"]})
    return descriptions


def published_from_shelf() -> dict[int, list[dict]]:
    return {int(i): [entry for entry in row["descriptions"] if entry["source"] == FAQ_SOURCE]
            for i, row in facts().items()}


def extract_wavs(samples: dict[int, Sample], directory: Path) -> dict[tuple[str, int], Path]:
    """Write one WAV for each distinct playable RAW and nominal 3D playback rate."""
    directory.mkdir(parents=True, exist_ok=True)
    clips = {}
    for ident, sample in samples.items():
        if not sample.pcm or sample.clip in clips:
            continue
        path = directory / f"{ident}.wav"
        with wave.open(str(path), "wb") as stream:
            stream.setparams((1, 1, sample.playback_rate, 0, "NONE", "not compressed"))
            stream.writeframes(sample.pcm)
        clips[sample.clip] = path
    return clips


def archive_description(sample: Sample) -> str:
    ident, name = sample.id, sample.name
    if ident in NAME_DESCRIPTIONS:
        return NAME_DESCRIPTIONS[ident]
    if not sample.raw_name:
        return "Silent footstep placeholder" if ident in (800, 801) else "Empty RAW reference"
    for prefix, creature in CREATURES.items():
        if name.startswith(prefix):
            role = name[len(prefix):].rstrip("0123456789")
            if role in CREATURE_ROLES:
                return f"{creature} {CREATURE_ROLES[role]}"
    if 4100 <= ident <= 4141:
        return f"Voice clip from the kill-line bank ({name})"
    if 4200 <= ident <= 4300:
        return f"Voice clip from the OMNI bank ({name})"
    if 4400 <= ident <= 4409:
        return "Multiplayer taunt"
    if 4500 <= ident <= 4548:
        return f"Voice clip from the 3000-series RAW bank ({name})"
    if 7000 <= ident <= 7009:
        return f"Innocent's distress call ({name})"
    if 8000 <= ident <= 8007:
        return "Capture-the-flag announcement"
    if 9000 <= ident <= 9017:
        return f"Beast sound ({name})"
    if 10000 <= ident <= 11001:
        return f"Small Caleb voice clip ({name})"
    return f"Archive sound {name}"


def engine_description(ident: int) -> tuple[str, str] | None:
    if ident in ENGINE_DESCRIPTIONS:
        return ENGINE_DESCRIPTIONS[ident]
    if 4003 <= ident <= 4006:
        return "Tommy-gun cultist spots the player", "ai.cpp:395"
    if 4008 <= ident <= 4012:
        return "Tommy-gun cultist roaming call", "ai.cpp:384"
    if 4400 <= ident <= 4409:
        return "Multiplayer taunt", "network.cpp:472,571"
    if 10000 <= ident <= 10005:
        return "Tiny Caleb combat vocalization", "aicaleb.cpp:90"
    if 11000 <= ident <= 11001:
        return "Tiny Caleb alerts to the player", "aicaleb.cpp:164"
    return None


def descriptions(sample: Sample, published: dict[int, list[dict]]) -> list[dict]:
    values = list(published.get(sample.id, []))
    engine = engine_description(sample.id)
    if engine:
        label, reference = engine
        values.append({"text": label, "source": SOURCE + reference, "title": "NBlood"})
    if sample.id in AUDIO_DESCRIPTIONS:
        values.append({"text": AUDIO_DESCRIPTIONS[sample.id],
                       "source": f"{ARCHIVE_SOURCE}:{sample.raw_name}.RAW",
                       "title": "Whisper vocalization reading"})
    if not values or sample.id in NAME_DESCRIPTIONS:
        values.append({"text": archive_description(sample),
                       "source": f"{ARCHIVE_SOURCE}:{sample.name}.SFX (ID {sample.id})",
                       "title": "Archive name (inferred description)"})
    return values


def whisper_rows(paths) -> dict[int, list[dict]]:
    """Load decoding candidates, starting with the archive-wide screening pass."""
    candidates = defaultdict(list)
    for path in paths:
        with path.open(encoding="utf-8") as stream:
            for line in stream:
                row = json.loads(line)
                for ident in row["ids"]:
                    candidates[ident].append(row)
    return candidates


def transcribe(samples: dict[int, Sample], clips: dict[tuple[str, int], Path],
               output: Path, device: str | None, threads: int,
               only: set[int] | None = None, context_seconds: int | None = None) -> None:
    """Write Whisper scores as JSONL, one row per distinct playback clip."""
    import numpy as np
    import torch
    import whisper
    from scipy.signal import resample_poly

    device = device or ("cuda" if torch.cuda.is_available() else "cpu")
    torch.set_num_threads(threads)
    if torch.get_num_interop_threads() != 1:
        torch.set_num_interop_threads(1)
    weights = Path.home() / ".cache/whisper" / f"{MODEL}.pt"
    model = whisper.load_model(str(weights), device=device).eval()
    positions = model.encoder.positional_embedding
    options = whisper.DecodingOptions(language="en", fp16=device == "cuda",
                                      without_timestamps=context_seconds is None, sample_len=36)
    timestamp_begin = whisper.tokenizer.get_tokenizer(False).timestamp_begin
    by_clip = defaultdict(list)
    for ident, sample in samples.items():
        if sample.clip in clips:
            by_clip[sample.clip].append(ident)
    keys = [key for key, ids in by_clip.items() if only is None or only.intersection(ids)]
    keys.sort(key=lambda key: (not any(3000 <= i < 3400 for i in by_clip[key]), by_clip[key][0]))
    batch_size = 4 if context_seconds == 30 else 8
    with output.open("w", encoding="utf-8") as stream, torch.inference_mode():
        for offset in range(0, len(keys), batch_size):
            batch = keys[offset:offset + batch_size]
            signals = []
            for key in batch:
                with wave.open(str(clips[key]), "rb") as wav:
                    rate = wav.getframerate()
                    pcm = wav.readframes(wav.getnframes())
                divisor = math.gcd(rate, 16000)
                signal = (np.frombuffer(pcm, np.uint8).astype(np.float32) - 128) / 128
                signals.append(resample_poly(signal, 16000 // divisor, rate // divisor))
            if context_seconds == 30:
                window = whisper.audio.N_FRAMES
                mels = [whisper.log_mel_spectrogram(whisper.pad_or_trim(signal))
                        for signal in signals]
            else:
                # A batched CPU screening pass uses the clip plus trailing silence.
                frames = math.ceil(max(map(len, signals)) / 160) + 180
                window = min(whisper.audio.N_FRAMES,
                             max(100 * (context_seconds or 6), frames + frames % 2))
                mels = [whisper.log_mel_spectrogram(signal, padding=whisper.audio.N_SAMPLES)
                        [:, :window] for signal in signals]
            model.encoder.positional_embedding = positions[:window // 2]
            results = model.decode(torch.stack(mels).to(device), options)
            for key, result in zip(batch, results):
                row = {"ids": by_clip[key], "text": result.text,
                       "avg_logprob": result.avg_logprob, "no_speech_prob": result.no_speech_prob,
                       "seconds": window / 100}
                if context_seconds is not None:
                    row["timestamps"] = [round((token - timestamp_begin) * .02, 2)
                                         for token in result.tokens if token >= timestamp_begin]
                stream.write(json.dumps(row) + "\n")
            stream.flush()
            print(f"Whisper {device}: {offset + len(batch)}/{len(keys)}", flush=True)


def words(text: str) -> list[str]:
    return re.findall(r"[\w']+", text.casefold())


def remove_repetition(text: str, duration: float) -> str:
    """Drop pathological looping of a phrase that cannot fit in the sample."""
    tokens = list(re.finditer(r"[\w']+", text))
    normalized = [token.group().casefold() for token in tokens]
    sentences = re.split(r"(?<=[.!?])\s+", text)
    if duration < 3.2 or len(tokens) > duration * 4 + 1:
        for size in range(1, len(tokens) // 2 + 1):
            if all(word == normalized[i % size] for i, word in enumerate(normalized)):
                if size > 3 or len(tokens) > max(3, duration * 4 + 1):
                    return text[:tokens[size].start()].strip(" ,")
        if len(sentences) > 1:
            first, second = words(sentences[0]), words(sentences[1])
            if len(second) >= 4 and (first == second or first[-len(second):] == second):
                return sentences[0]
    # A decoder sometimes gets stuck on its last sentence while there is only silence.
    while len(sentences) >= 3 and words(sentences[-1]) == words(sentences[-2]) == words(sentences[-3]):
        sentences.pop()
    return " ".join(sentences).strip()


def published_line(ident: int, rows: list[dict]) -> bool:
    return any(row["text"].lstrip().startswith('"') for row in rows) or ident in (
        702, 703, 704, 705, 742,
    )


def voice_kind(sample: Sample, fan_rows: list[dict]) -> str:
    ident, name = sample.id, sample.name
    if not sample.raw_name:
        return "silence"
    if name.startswith(("MUZAK", "MUSIC")) or ident in (3, 65):
        return "music"
    if ident in NONVERBAL:
        return "voice"
    if ident in CABAL_SOUNDS or ident in EXTRA_SPEECH:
        return "speech"
    if published_line(ident, fan_rows) or 8000 <= ident <= 8007 or 10000 <= ident <= 11001:
        return "speech"
    if 1 <= ident <= 67:
        return "ambient"
    if (name.startswith(("PLAY", "PAIN", "DIE")) or 3000 <= ident < 3400 or
            4100 <= ident <= 4548 or 4031 <= ident <= 4033 or 9000 <= ident <= 9011):
        return "voice"
    return "effect"


def refinement_ids(samples: dict[int, Sample], published: dict[int, list[dict]]) -> set[int]:
    extra = {724, 727, 741, 744, 1030, 1031, 1033, 1100, 1101, 1902, 2360, 4031, 4033, 9007}
    return {i for i, sample in samples.items() if sample.pcm and (
        voice_kind(sample, published.get(i, [])) == "speech" or
        4100 <= i < 4400 or 4500 <= i < 4600 or i in extra
    )}


def scored(row: dict, text: str) -> dict:
    return {
        "text": text,
        "model": f"Whisper {MODEL}",
        "confidence": round(math.exp(row["avg_logprob"]), 4),
        "no_speech_probability": round(row["no_speech_prob"], 4),
    }


def transcription(sample: Sample, kind: str, candidates: list[dict],
                  fan_rows: Sequence[dict] = ()) -> dict | None:
    if kind not in ("speech", "voice") or sample.pcm is None or sample.id in NONVERBAL:
        return None
    ident = sample.id
    # Retain a documented Cabal spelling only where a decoding supports the sounds.
    if ident in CABAL_SOUNDS:
        form = CABAL_FORMS.get(sample.raw_name)
        if form and candidates:
            row = candidates[-1]
            result = scored(row, form)
            result["text_source"] = CABAL_SOURCE
            result["language"] = "Cabal"
            return result
        return None
    if ident in UNRESOLVED_SPEECH:
        return None
    duration = len(sample.pcm) / sample.playback_rate
    if fan_rows and ident in FAN_READINGS:
        reading = FAN_READINGS[ident], fan_rows[0]["source"]
    elif ident in ENGINE_READINGS:
        reading = ENGINE_READINGS[ident], SOURCE + ENGINE_DESCRIPTIONS[ident][1]
    elif sample.raw_name in NAME_READINGS:
        reading = NAME_READINGS[sample.raw_name], f"{ARCHIVE_SOURCE}:{sample.raw_name}.RAW"
    else:
        reading = None
    for row in reversed(candidates):
        text = remove_repetition(row["text"], duration)
        tokens = words(text)
        if not tokens or len(tokens) > max(3, duration * 5.5 + 1):
            continue
        if re.fullmatch(r"(?:\[.*\]|\(.*\)|[?!.]+)", text):
            continue
        if all(word != "whoa" and re.fullmatch(r"(?:[aeiouwhm]+|(?:[ah]a?h[aeiou]*){2,})", word)
               for word in tokens):
            continue
        if kind == "voice" and (tokens in (["you"], ["i"], ["oh"], ["ah"], ["hey"]) or
                len(set(tokens)) == 1 and len(tokens) > 3):
            continue
        threshold = .60 if kind == "speech" else .40
        if row["no_speech_prob"] > threshold or row["avg_logprob"] < (-1.6 if reading else -1.0):
            continue
        timestamps = row.get("timestamps")
        if timestamps is not None and (
            len(timestamps) < 2 or timestamps[0] > duration or timestamps[-1] > duration + .65
        ):
            continue
        result = scored(row, text)
        if reading and words(text) != words(reading[0]):
            result.update(text=reading[0], text_source=reading[1], model_text=text)
        if timestamps:
            result["time_seconds"] = [timestamps[0], timestamps[-1]]
        return result
    return None


def build(samples: dict[int, Sample], maps, published: dict[int, list[dict]],
          candidates: dict[int, list[dict]]) -> dict:
    uses = campaign_uses(maps)
    rows = {}
    for ident, sample in samples.items():
        kind = voice_kind(sample, published.get(ident, []))
        best = transcription(sample, kind, candidates.get(ident, []), published.get(ident, []))
        size = len(sample.pcm) if sample.pcm is not None else None
        row = {
            "name": sample.name,
            "raw_name": sample.raw_name or None,
            "kind": "speech" if best else kind,
            "format": sample.format,
            "rate_hz": sample.rate,
            "playback_rate_hz": sample.playback_rate,
            "sample_count": size,
            "duration_seconds": round(size / sample.rate, 4) if size is not None else None,
            "playback_seconds": round(size / sample.playback_rate, 4) if size is not None else None,
            "loop": sample.loop_start >= 0,
            "loop_start_sample": sample.loop_start if sample.loop_start >= 0 else None,
            "descriptions": descriptions(sample, published),
            "campaign_uses": uses.get(ident, []),
        }
        if 3000 <= ident <= 3111 or 4400 <= ident <= 4548:
            row["speaker"] = "Caleb"
        elif 10000 <= ident <= 11001:
            row["speaker"] = "Tiny Caleb"
        if best:
            row["transcript"] = best
        elif kind == "speech":
            row["transcript_status"] = "unresolved" if size is not None else "missing sample"
        if ident in QUOTE_SOURCES:
            title, url = QUOTE_SOURCES[ident]
            row["quotation_source"] = {"title": title, "source": url}
        rows[str(ident)] = row
    return {
        "archive": ARCHIVE_SOURCE,
        "format_sources": FORMAT_SOURCES,
        "usage_sources": USAGE_SOURCES,
        "campaign_maps": len(maps),
        "whisper_screened": sum(bool(candidates.get(i)) for i in samples),
        "unresolved_campaign_ids": {str(i): uses[i] for i in sorted(uses.keys() - samples.keys())},
        "sounds": rows,
    }


@lru_cache(maxsize=1)
def facts() -> dict[str, dict]:
    """The checked-in shelf can be read without game files or Whisper."""
    if not SHELF.exists():
        return {}
    return json.loads(SHELF.read_text("utf-8"))["sounds"]


def show(ident: str) -> str:
    ident = str(int(ident)) if ident.isascii() and ident.isdigit() else ident
    row = facts().get(ident)
    if row is None:
        return f"No sound ID {ident} in the catalogue"
    lines = [f"SOUND {ident}  {row['name']}.SFX  [{row['kind']}]"]
    raw = row["raw_name"]
    if raw is None:
        lines.append("  empty RAW reference")
    elif row["sample_count"] is None:
        lines.append(f"  {raw}.RAW is missing from SOUNDS.RFF")
    else:
        lines.append(f"  {raw}.RAW  {row['duration_seconds']:.2f}s at {row['rate_hz']} Hz")
        if row["playback_rate_hz"] != row["rate_hz"]:
            lines.append(f"  nominal 3D play: {row['playback_seconds']:.2f}s at "
                         f"{row['playback_rate_hz']} Hz")
    lines.append(f"  loop start: sample {row['loop_start_sample']}" if row["loop"]
                 else "  loop: none configured in SFX header")
    if row.get("speaker"):
        lines.append(f"  speaker: {row['speaker']}")
    if transcript := row.get("transcript"):
        lines.append(f"  transcript: {transcript['text']} "
                     f"({transcript['model']}, "
                     f"confidence {transcript['confidence']:.2f}, "
                     f"no speech {transcript['no_speech_probability']:.2f})")
        if model_text := transcript.get("model_text"):
            lines.append(f"  model wording: {model_text}")
        if source := transcript.get("text_source"):
            lines.append(f"  wording source: {source}")
    elif status := row.get("transcript_status"):
        lines.append(f"  transcription: {status}")
    if quote := row.get("quotation_source"):
        lines.append(f"  quotation: {quote['title']} ({quote['source']})")
    for entry in row["descriptions"]:
        lines.append(f"  {entry['title']}: {entry['text']}  ({entry['source']})")
    uses = row["campaign_uses"]
    slots = sum(use["count"] for use in uses)
    lines.append(f"  campaign: {slots} sound slot{'s' if slots != 1 else ''}")
    for use in uses:
        example = use["example"]
        sector = (f", sector:{example['sector_type']}"
                  if use["kind"] == "kSoundSector" and "sector_type" in example else "")
        lines.append(f"    {use['kind']} {use['role']} ({use['field']}{sector}) x{use['count']}"
                     f"  e.g. {example['map_index']} {example['record']}")
    return "\n".join(lines)


def find(terms: list[str], limit: int = 12) -> list[str]:
    """Search descriptions, transcripts, names and speakers by whole words or inflections."""
    ignored = {"a", "an", "is", "the", "which", "what", "sound", "does", "say"}
    query = set(words(" ".join(terms)))
    query = query - ignored or query
    matches = []
    for ident, row in facts().items():
        labels = [entry["text"] for entry in row["descriptions"]]
        transcript = row.get("transcript", {}).get("text", "")
        text = " ".join([ident, row["name"], row["kind"], row.get("speaker", ""),
                         transcript, *labels])
        tokens = set(words(text))
        all_forms = tokens | {t.removesuffix("ing").removesuffix("s") for t in tokens}
        stems = {t.removesuffix("ing").removesuffix("s") for t in query}
        if not stems <= all_forms:
            continue
        matching_label = next((label for label in labels if stems <= {
            t.removesuffix("ing").removesuffix("s") for t in words(label)
        }), labels[0])
        excerpt = transcript if transcript and query.intersection(words(transcript)) else matching_label
        matches.append((len(query & tokens), int(ident),
                        f"  sound:{ident}  {row['name']}  [{row['kind']}]  {excerpt}"))
    return [line for _, _, line in sorted(matches, key=lambda hit: (-hit[0], hit[1]))[:limit]]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, default=ARCHIVE)
    parser.add_argument("--published", type=Path, default=PUBLISHED)
    parser.add_argument("--output", type=Path, default=SHELF)
    parser.add_argument("--work", type=Path, default=WORK)
    parser.add_argument("--transcribe", action="store_true", help="run archive-wide Whisper screening")
    parser.add_argument("--verify", nargs="+", type=int, metavar="ID",
                        help="redecode these IDs with the full 30-second Whisper context")
    parser.add_argument("--device", choices=("cpu", "cuda"))
    parser.add_argument("--threads", type=int, default=8)
    args = parser.parse_args(argv)
    samples = read_samples(args.archive)
    if args.published == PUBLISHED and not PUBLISHED.exists() and SHELF.exists():
        published = published_from_shelf()
    else:
        published = read_published(args.published)
    clips = extract_wavs(samples, args.work / "wav")
    screen = args.work / "whisper-cpu.jsonl"
    full = args.work / "whisper-full.jsonl"
    refined = args.work / "whisper-refined.jsonl"
    extra = args.work / "whisper-verified-extra.jsonl"
    if args.transcribe:
        transcribe(samples, clips, screen, args.device, args.threads)
        transcribe(samples, clips, refined, args.device, args.threads,
                   refinement_ids(samples, published), context_seconds=8)
    if args.verify or args.transcribe:
        transcribe(samples, clips, full, args.device, args.threads, set(args.verify or VERIFY_IDS),
                   context_seconds=30)
    if args.transcribe:
        transcribe(samples, clips, extra, args.device, args.threads, EXTRA_VERIFY_IDS,
                   context_seconds=30)
    candidates = whisper_rows(path for path in (screen, refined, full, extra) if path.exists())
    playable = {ident for ident, sample in samples.items() if sample.pcm}
    if playable - candidates.keys():
        parser.error(f"{len(playable - candidates.keys())} playable sound IDs need Whisper screening. "
                     "Run again with --transcribe.")
    data = build(samples, campaign_maps(), published, candidates)
    temporary = args.output.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(args.output)
    count = sum("transcript" in row for row in data["sounds"].values())
    print(f"{len(samples)} sound IDs, {len(clips)} playable clips, {count} transcripts, "
          f"{data['campaign_maps']} campaign maps -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
