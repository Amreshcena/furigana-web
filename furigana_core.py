"""
furigana_core.py — Word/phrase-level furigana generation for Japanese .srt files.

Converts kanji into the 漢字[かんじ] bracket format that Memento (and Migaku)
auto-parse to display furigana. Segments at the word/phrase level (not raw
tokenizer morphemes) so compound nouns and conjugated verb phrases come out
as one bracketed unit.
"""

import re
import threading

from sudachipy import tokenizer, dictionary
import jaconv

_TOK = None
_MODE = tokenizer.Tokenizer.SplitMode.C
_init_lock = threading.Lock()


def _tok():
    global _TOK
    if _TOK is None:
        with _init_lock:
            if _TOK is None:
                _TOK = dictionary.Dictionary().create()
    return _TOK


NOUN_LIKE = {'名詞', '接頭辞', '接尾辞', '形状詞'}
AUX_VERB = {'助動詞'}
KANJI_RE = re.compile(r'[\u4e00-\u9fff\u3005]')
SPACE_RE = re.compile(r'( +)')
ALREADY_BRACKETED_RE = re.compile(
    r'[\u4e00-\u9fff\u3005][\u4e00-\u9fff\u3005\u3040-\u309f\u30fc]*\[[\u3040-\u309f\u30fc]+\]'
)
MANUAL_RE = re.compile(r'([\u4e00-\u9fff\u3005]+)\(([\u3040-\u309f\u30fc]+)\)')


def has_kanji(s):
    return bool(KANJI_RE.search(s))


def is_number(m):
    pos = m.part_of_speech()
    return pos[0] == '名詞' and pos[1] == '数詞'


def is_bound_aux(m):
    pos = m.part_of_speech()
    return (pos[0] == '動詞' and pos[1] == '非自立可能') or (pos[0] == '形容詞' and pos[1] == '非自立可能')


def _chunk_tokens(morphs):
    chunks = []
    i, n = 0, len(morphs)
    while i < n:
        m = morphs[i]
        pos = m.part_of_speech()
        surfaces, readings = [m.surface()], [m.reading_form()]
        j = i + 1
        if is_number(m) or pos[0] == '空白':
            pass
        elif pos[0] in NOUN_LIKE and (pos[0] == '接頭辞' or has_kanji(m.surface())):
            while j < n:
                nm = morphs[j]
                npos = nm.part_of_speech()
                if npos[0] in NOUN_LIKE and not is_number(nm) and has_kanji(nm.surface()):
                    surfaces.append(nm.surface())
                    readings.append(nm.reading_form())
                    j += 1
                else:
                    break
        elif pos[0] in ('動詞', '形容詞'):
            while j < n:
                nm = morphs[j]
                npos = nm.part_of_speech()
                if npos[0] in AUX_VERB or is_bound_aux(nm):
                    surfaces.append(nm.surface())
                    readings.append(nm.reading_form())
                    j += 1
                elif (npos[0] == '助詞' and npos[1] == '接続助詞' and nm.surface() in ('て', 'で')
                      and j + 1 < n and (morphs[j + 1].part_of_speech()[0] in AUX_VERB
                                         or is_bound_aux(morphs[j + 1]))):
                    surfaces.append(nm.surface())
                    readings.append(nm.reading_form())
                    j += 1
                else:
                    break
        chunks.append((''.join(surfaces), ''.join(readings)))
        i = j
    return chunks


def _furigana_tokenize(text):
    out = []
    for surf, read in _chunk_tokens(_tok().tokenize(text, _MODE)):
        if has_kanji(surf):
            hira = jaconv.kata2hira(read)
            if hira and hira != surf:
                out.append(f"{surf}[{hira}]")
            else:
                out.append(surf)
        else:
            out.append(surf)
    return ''.join(out)


def furigana_segment(text):
    parts = SPACE_RE.split(text)
    out = []
    for part in parts:
        if part == '':
            continue
        if SPACE_RE.fullmatch(part):
            out.append(part)
        else:
            out.append(_furigana_tokenize(part))
    return ''.join(out)


def process_line(line):
    result = []
    last_end = 0
    combined_re = re.compile(f"({ALREADY_BRACKETED_RE.pattern})|({MANUAL_RE.pattern})")
    for m in combined_re.finditer(line):
        before = line[last_end:m.start()]
        result.append(furigana_segment(before))
        if m.group(1):
            result.append(m.group(1))
        else:
            kanji, reading = m.group(3), m.group(4)
            result.append(f"{kanji}[{reading}]")
        last_end = m.end()
    result.append(furigana_segment(line[last_end:]))
    return ''.join(result)


def is_text_line(line):
    s = line.strip()
    if s == '':
        return False
    if s.isdigit():
        return False
    if '-->' in s:
        return False
    return True


def process_srt_text(srt_text: str) -> str:
    """Process a full .srt file's text content and return the furigana-annotated text."""
    lines = srt_text.splitlines(keepends=True)
    out_lines = []
    for line in lines:
        stripped = line.rstrip('\r\n')
        ending = line[len(stripped):] or '\n'
        if is_text_line(stripped):
            out_lines.append(process_line(stripped) + ending)
        else:
            out_lines.append(line if line.endswith(('\n', '\r')) else line + '\n')
    return ''.join(out_lines)


def warm_up():
    """Force dictionary load at process start instead of on first request."""
    _tok()
