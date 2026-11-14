"""Conservative ingredient presentation; source Markdown stays authoritative."""
import html
import re
from fractions import Fraction

FRACTIONS = dict(zip('½⅓⅔¼¾⅛⅜⅝⅞', ['1/2','1/3','2/3','1/4','3/4','1/8','3/8','5/8','7/8']))
NUMBER = r'(?:\d+\s+\d+/\d+|(?:\d+\s*)?[½⅓⅔¼¾⅛⅜⅝⅞]|\d+/\d+|\d+(?:[.,]\d+)?)'
PREFIX = r'(?:(?:about|approximately|approx\.?|a scant|less than|etwa|ungefähr|ca\.?|knapp|weniger als|juice of|saft von|insgesamt(?: etwa)?|laut Videobeschreibung etwa)\s+)?(?:≈\s*)?'
LEADING = re.compile(rf'^({PREFIX})({NUMBER})(?:\s*([–—-])\s*({NUMBER}))?(?=\s|$|%)', re.I)
CUP = r'(?:cups?|Tassen?)'
METRIC = rf'((?:(?:about|approximately|etwa|ungefähr)\s+)?{NUMBER}\s*(?:g|kg|ml|l))\b'
FDA = 'https://www.fda.gov/regulatory-information/search-fda-guidance-documents/guidance-industry-guidelines-determining-metric-equivalents-household-measures'


def normalize(text, cup_ml: float = 240):
    """Prefer archived source equivalents; cup fallback is volume, never mass."""
    text = re.sub(rf'{NUMBER}\s*°F\s*/\s*({NUMBER}\s*°C)', r'\1', text)
    # Counts and fixed pack contents are distinct: only the count will scale.
    text = re.sub(rf'((?:×\s*|Dose\s+à\s*)){NUMBER}\s*oz\s*/\s*(?:approximately|ungefähr|about|etwa)?\s*({NUMBER}\s*g)\b',
                  r'\1\2', text, flags=re.I)
    leading = re.match(rf'^({PREFIX})({NUMBER})\s+({CUP}|oz)\b\s*', text, re.I)
    if leading:
        rest = text[leading.end():]
        # Metric equivalents may precede or follow the ingredient description.
        equivalent = re.search(rf'\((?:laut (?:Video)?[Bb]eschreibung\s+)?{METRIC}(?:\s+according to[^)]*)?\)', rest, re.I)
        if equivalent:
            description = (rest[:equivalent.start()] + rest[equivalent.end():]).strip()
            return leading[1] + equivalent[1] + (' ' + description if description else '')
        slash = re.match(rf'/\s*{METRIC}\s*', rest, re.I)
        if slash:
            return leading[1] + slash[1] + ' ' + rest[slash.end():]
        if re.fullmatch(CUP, leading[3], re.I):
            volume = number(leading[2]) * cup_ml
            amount = format(volume, '.6g')
            return f'{leading[1]}≈ {amount} ml {rest}'.rstrip()
    # Redundant imperial equivalence is retained in provenance, not the main list.
    if re.match(rf'^{PREFIX}{NUMBER}\s*(?:g|kg|ml|l)\b', text, re.I):
        text = re.sub(rf'\s*\([^)]*\b(?:{CUP}|oz)\b[^)]*\)', '', text, flags=re.I)
    return text


def prepare(markdown, locale, render, cup_ml: float = 240):
    originals = []
    lines = []
    for line in markdown.splitlines():
        if line.startswith('- '):
            original = line[2:]
            normalized = normalize(original, cup_ml)
            if normalized != original:
                originals.append(original)
            line = '- ' + normalized
        lines.append(line)
    if not originals:
        return '\n'.join(lines), ''
    de = locale == 'de-CH'
    title = 'Originalmasse der Quelle' if de else 'Original source measurements'
    note = (f'Quellenseitige metrische Angaben haben Vorrang. Ohne solche Angaben: 1 cup ≈ {cup_ml:g} ml '
            '(redaktionelle Näherung für Koch- und Etikettenmasse, keine exakte US-Cup-Einheit). '
            'Nur Volumen, keine erfundenen Grammwerte für trockene Zutaten. Originalangaben bleiben unverändert.' if de else
            f'Source-provided metric equivalents take priority. Otherwise: 1 cup ≈ {cup_ml:g} ml '
            '(editorial cooking/label approximation, not an exact US customary cup). '
            'Volume only; no invented dry-ingredient gram conversions. Archived source amounts are unchanged.')
    reference = 'FDA: Haushaltsmasse und metrische Näherungen' if de else 'FDA household measures and metric approximations'
    provenance = (f'<details class="source-measurements" data-pagefind-ignore><summary>{title}</summary>'
                  f'<p>{note} <a href="{FDA}" rel="noopener noreferrer">{reference}</a>.</p><ul>'
                  + ''.join(f'<li>{render(text)}</li>' for text in originals) + '</ul></details>')
    return '\n'.join(lines), provenance


def number(token):
    for glyph, fraction in FRACTIONS.items():
        if glyph in token:
            return float(int(token[:-1] or '0') + Fraction(fraction))
    return float(sum((Fraction(part.replace(',', '.')) for part in token.split()), Fraction(0)))


def quantity_span(token):
    value = number(token)
    canonical = str(int(value)) if value.is_integer() else str(value)
    return f'<span data-quantity="{canonical}">{html.escape(token)}</span>'


def ingredient(text, render):
    # An explicitly missing unit is not a trustworthy scalable quantity.
    if re.search(r'\((?:unit not specified\b[^)]*|Einheit\b[^)]*\bnicht angegeben)\)', text, re.I):
        return render(text)
    match = LEADING.match(text)
    non_amount = r'\s*(?:%|°[CF]|(?:cm|mm|inches|Zoll|Glas|glass|handful|splash|Handvoll|Schuss|hours?|minutes?|seconds?|Stunden?|Minuten?|Sekunden?)\b|(?:ml|l|Liter)\s+(?:container|Behälter)\b)'
    if not match or re.match(non_amount, text[match.end():], re.I):
        return render(text)
    try:
        output = render(match[1]) + quantity_span(match[2])
        if match[4]:
            # Preserve original spacing and dash exactly for reset/no-JS.
            between = text[match.end(2):match.start(4)]
            output += render(between) + quantity_span(match[4])
        tail = text[match.end():]
        if re.match(r'\s*(?:cans?|packets?|packs?|cartons?|jars?|bottles?|Dosen?|Päckchen|Packung(?:en)?|Gläser|Flaschen)\b', tail, re.I):
            return output + render(tail)
        # Only explicit parenthetical total-weight equivalents; never per-pack sizes,
        # times, percentages, temperatures, or other numbers in ingredient prose.
        nested = re.compile(rf'\(((?:(?:about|approximately|etwa|ungefähr|laut Videobeschreibung etwa|insgesamt(?: etwa)?)\s+)?{NUMBER}(?:[–-]{NUMBER})?\s+g(?:\s+(?:total|leaves|Blätter|according to the video description))?(?:;\s*optional)?)\)', re.I)
        parts = []
        offset = 0
        for equivalent in nested.finditer(tail):
            parts.append(render(tail[offset:equivalent.start() + 1]))
            parts.append(ingredient(equivalent[1], render))
            parts.append(')')
            offset = equivalent.end()
        parts.append(render(tail[offset:]))
        return output + ''.join(parts)
    except (ValueError, ZeroDivisionError):
        return render(text)


def controls(slug, locale):
    de = locale == 'de-CH'
    label = 'Rezeptmenge' if de else 'Recipe multiplier'
    original = 'Originalrezept' if de else 'original recipe'
    reset = 'Zurücksetzen' if de else 'Reset'
    note = ('Nur angegebene Zutatenmengen ändern sich. Zubereitungsmengen, Zeiten, Temperaturen, Formen und Nährwerte bleiben beim Originalrezept. '
            'Bruchteile von Eiern müssen eventuell verquirlt und abgemessen werden. Unklare Mengen und weitere Zahlen im Text bleiben unverändert.' if de else
            'Only identified ingredient amounts change. Method quantities, times, temperatures, pans and nutrition remain at original scale. '
            'Fractional eggs may need beating and measuring. Ambiguous amounts and other numbers in prose stay unchanged.')
    return (f'<div id="recipe-scale" data-recipe-slug="{html.escape(slug, quote=True)}">'
            f'<div id="scale-controls" hidden role="group" aria-label="{label}" aria-describedby="scale-note">'
            f'<label for="scale-factor">{label}</label><div class="scale-inputs">'
            f'<input id="scale-factor" type="number" min="0.1" max="20" step="any" value="1" inputmode="decimal" aria-describedby="scale-note">'
            f'<span aria-hidden="true">×</span><button id="scale-reset" type="button">{reset}</button></div>'
            f'<label class="sr-only" for="scale-slider">{label} (0.25–4×)</label>'
            '<input id="scale-slider" type="range" min="0.25" max="4" step="0.25" value="1">'
            f'</div><p id="scale-status" aria-live="polite" aria-atomic="true" data-original="{original}">1× · {original}</p>'
            f'<p id="scale-note" class="scale-note">{note}</p></div>')


def method_notice(locale):
    note = ('Originalrezept: Mengen in der Zubereitung sind nicht skaliert; Zeiten, Temperaturen und Formen bleiben unverändert.' if locale == 'de-CH' else
            'Original scale: quantities in the method are not scaled; times, temperatures and pans remain unchanged.')
    return f'<p id="method-scale-note" class="scale-note">{note}</p>'
