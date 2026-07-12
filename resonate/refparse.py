"""Human verse references -> USFM (dependency-free).

"What does John 3:16 say?"        -> [("John 3:16", "JHN.3.16")]
"Read me Philippians 4:6-7"       -> [("Philippians 4:6-7", "PHP.4.6-PHP.4.7")]
"Quote Psalm 23 verse 1"          -> [("Psalm 23:1", "PSA.23.1")]
"psalm 23"                        -> [("Psalm 23", "PSA.23")]        (whole chapter)

Why this exists: the Guide grounds itself on *emotional* beats, but people also ask
for Scripture BY NAME — the most basic request a Scripture guide gets. This module
lets any surface resolve an explicit reference to the same verified YouVersion
fetch the engine uses everywhere else (never model memory).
"""
from __future__ import annotations

import re

# canonical name -> USFM book code (all 66; order irrelevant)
_CANON = {
    "Genesis": "GEN", "Exodus": "EXO", "Leviticus": "LEV", "Numbers": "NUM",
    "Deuteronomy": "DEU", "Joshua": "JOS", "Judges": "JDG", "Ruth": "RUT",
    "1 Samuel": "1SA", "2 Samuel": "2SA", "1 Kings": "1KI", "2 Kings": "2KI",
    "1 Chronicles": "1CH", "2 Chronicles": "2CH", "Ezra": "EZR", "Nehemiah": "NEH",
    "Esther": "EST", "Job": "JOB", "Psalm": "PSA", "Proverbs": "PRO",
    "Ecclesiastes": "ECC", "Song of Solomon": "SNG", "Isaiah": "ISA",
    "Jeremiah": "JER", "Lamentations": "LAM", "Ezekiel": "EZK", "Daniel": "DAN",
    "Hosea": "HOS", "Joel": "JOL", "Amos": "AMO", "Obadiah": "OBA", "Jonah": "JON",
    "Micah": "MIC", "Nahum": "NAM", "Habakkuk": "HAB", "Zephaniah": "ZEP",
    "Haggai": "HAG", "Zechariah": "ZEC", "Malachi": "MAL",
    "Matthew": "MAT", "Mark": "MRK", "Luke": "LUK", "John": "JHN", "Acts": "ACT",
    "Romans": "ROM", "1 Corinthians": "1CO", "2 Corinthians": "2CO",
    "Galatians": "GAL", "Ephesians": "EPH", "Philippians": "PHP",
    "Colossians": "COL", "1 Thessalonians": "1TH", "2 Thessalonians": "2TH",
    "1 Timothy": "1TI", "2 Timothy": "2TI", "Titus": "TIT", "Philemon": "PHM",
    "Hebrews": "HEB", "James": "JAS", "1 Peter": "1PE", "2 Peter": "2PE",
    "1 John": "1JN", "2 John": "2JN", "3 John": "3JN", "Jude": "JUD",
    "Revelation": "REV",
}

# spoken/written aliases -> canonical (keys lowercase, no periods, single spaces)
_ALIASES = {
    "gen": "Genesis", "ex": "Exodus", "exod": "Exodus", "lev": "Leviticus",
    "num": "Numbers", "deut": "Deuteronomy", "dt": "Deuteronomy", "josh": "Joshua",
    "judg": "Judges", "1 sam": "1 Samuel", "2 sam": "2 Samuel",
    "1 kgs": "1 Kings", "2 kgs": "2 Kings", "1 chron": "1 Chronicles",
    "2 chron": "2 Chronicles", "neh": "Nehemiah", "esth": "Esther",
    "ps": "Psalm", "psa": "Psalm", "psalms": "Psalm", "prov": "Proverbs",
    "eccl": "Ecclesiastes", "song of songs": "Song of Solomon",
    "song": "Song of Solomon", "isa": "Isaiah", "jer": "Jeremiah",
    "lam": "Lamentations", "ezek": "Ezekiel", "dan": "Daniel", "hos": "Hosea",
    "obad": "Obadiah", "mic": "Micah", "nah": "Nahum", "hab": "Habakkuk",
    "zeph": "Zephaniah", "hag": "Haggai", "zech": "Zechariah", "mal": "Malachi",
    "matt": "Matthew", "mt": "Matthew", "mk": "Mark", "lk": "Luke",
    "jn": "John", "rom": "Romans", "1 cor": "1 Corinthians",
    "2 cor": "2 Corinthians", "gal": "Galatians", "eph": "Ephesians",
    "phil": "Philippians", "php": "Philippians", "col": "Colossians",
    "1 thess": "1 Thessalonians", "2 thess": "2 Thessalonians",
    "1 tim": "1 Timothy", "2 tim": "2 Timothy", "philem": "Philemon",
    "phlm": "Philemon", "heb": "Hebrews", "jas": "James", "1 pet": "1 Peter",
    "2 pet": "2 Peter", "rev": "Revelation",
}

_LOOKUP = {k.lower(): k for k in _CANON}
_LOOKUP.update(_ALIASES)

# longest names first so "1 corinthians" wins over "corinthians"-less partials
_NAME_RE = "|".join(sorted((re.escape(n) for n in _LOOKUP), key=len, reverse=True))
_REF_RE = re.compile(
    r"\b(" + _NAME_RE + r")\.?\s+(\d{1,3})"          # book + chapter
    r"(?:\s*:\s*(\d{1,3})|\s*,?\s+verses?\s+(\d{1,3}))?"  # :verse | "verse N"
    r"(?:\s*[-–—]\s*(\d{1,3}))?",                     # optional range end
    re.IGNORECASE,
)
_ROMAN = {"i": "1", "ii": "2", "iii": "3"}


def _normalise(text):
    # "I Peter 5:7" / "1st John" -> "1 peter 5:7" / "1 john"; drop abbrev periods
    t = re.sub(r"\b(i{1,3})\s+(?=[a-z])", lambda m: _ROMAN[m.group(1).lower()] + " ",
               text, flags=re.IGNORECASE)
    t = re.sub(r"\b([123])(?:st|nd|rd)\s+", r"\1 ", t, flags=re.IGNORECASE)
    return re.sub(r"[ \t]+", " ", t)


def find_references(text, limit=3):
    """All explicit references in free text, de-duplicated, in order of appearance.
    Returns [{"reference": "John 3:16", "usfm": "JHN.3.16"}, ...]."""
    out, seen = [], set()
    for m in _REF_RE.finditer(_normalise(text or "")):
        name, chap = _LOOKUP[re.sub(r"\s+", " ", m.group(1).lower()).strip()], m.group(2)
        verse = m.group(3) or m.group(4)
        end = m.group(5)
        code = _CANON[name]
        if verse:
            usfm = "%s.%s.%s" % (code, chap, verse)
            display = "%s %s:%s" % (name, chap, verse)
            if end and int(end) > int(verse):  # verse range within the chapter
                usfm += "-%s.%s.%s" % (code, chap, end)
                display += "-%s" % end
        else:
            if end:  # "Psalm 23-24" is a chapter range; keep just the first chapter
                pass
            usfm, display = "%s.%s" % (code, chap), "%s %s" % (name, chap)
        if usfm not in seen:
            seen.add(usfm)
            out.append({"reference": display, "usfm": usfm})
        if len(out) >= limit:
            break
    return out
