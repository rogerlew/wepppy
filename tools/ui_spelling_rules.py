"""House spelling for public WEPPcloud content."""

import re


PRODUCT = re.compile(r"(?<![\w/@.-])wepp[\s\-‐‑–]*cloud(?![\w/@]|\.[\w])", re.I)

# These pairs have the same scientific meaning in US and British usage.
# Omit ambiguous words such as "analyses" (also the US plural of "analysis").
US_SPELLING = {
    "centre": "center", "centres": "centers",
    "modelled": "modeled", "modelling": "modeling",
    "labelled": "labeled", "labelling": "labeling",
    "behaviour": "behavior", "behaviours": "behaviors",
    "honour": "honor", "honours": "honors",
    "colour": "color", "colours": "colors",
    "neighbour": "neighbor", "neighbours": "neighbors",
    "visualisation": "visualization", "normalisation": "normalization",
    "parameterisation": "parameterization",
}
# Include the unprefixed forms and all SI prefixes through quetta and quecto.
SI_PREFIXES = ("", *(
    "quetta ronna yotta zetta exa peta tera giga mega kilo hecto deka deci "
    "centi milli micro nano pico femto atto zepto yocto ronto quecto"
).split())
for prefix in (*SI_PREFIXES, "deca"):
    us_prefix = "deka" if prefix == "deca" else prefix
    for british, american in (("metre", "meter"), ("litre", "liter")):
        for plural in ("", "s"):
            US_SPELLING[prefix + british + plural] = us_prefix + american + plural

US_WORD = re.compile(r"(?<![\w/@.])(?:" + "|".join(US_SPELLING) + r")(?![\w/@]|\.[\w])", re.I)
# Preserve URLs and the journal's published title when present in a citation.
VERBATIM = re.compile(r"(?:https?://|www\.)\S+|\bEnvironmental Modelling & Software\b", re.I)


def spelling_findings(text):
    """Yield (match, rule, preferred spelling), retaining original offsets."""
    text = VERBATIM.sub(lambda match: " " * len(match[0]), text)
    for match in PRODUCT.finditer(text):
        if match[0] != "WEPPcloud":
            yield match, "product-name", "WEPPcloud"
    for match in US_WORD.finditer(text):
        replacement = US_SPELLING[match[0].lower()]
        if match[0].isupper():
            replacement = replacement.upper()
        elif match[0].istitle():
            replacement = replacement.capitalize()
        yield match, "us-spelling", replacement
