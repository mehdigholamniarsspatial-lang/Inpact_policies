from django import template

from policies import glossary

register = template.Library()


@register.filter
def humanise(value):
    return glossary.humanise(str(value or ""))


@register.filter
def pct(value, digits=0):
    if value is None:
        return "\u2013"
    return f"{value * 100:.{int(digits)}f}%"


@register.filter
def num(value, digits=2):
    if value is None:
        return "\u2013"
    return f"{value:,.{int(digits)}f}"


@register.filter
def split(value, sep=";"):
    return [v.strip() for v in str(value or "").split(sep) if v.strip()]


@register.filter
def get(d, key):
    try:
        return d.get(key)
    except AttributeError:
        return None


@register.filter
def sector_color(sector):
    return glossary.SECTORS.get(sector, ("#777777", ""))[0]


@register.filter
def mech_color(mech):
    return glossary.MECHANISMS.get(mech, ("#777777", "", ""))[0]


@register.filter
def mech_label(mech):
    return glossary.MECHANISMS.get(mech, ("", humanise(mech), ""))[1]


@register.filter
def layer_label(layer):
    return glossary.LAYERS.get(layer, (humanise(layer), "", ""))[0]


@register.filter
def status_label(status):
    return glossary.STATUS.get(status, (humanise(status), ""))[0]


@register.filter
def effect_label(code):
    return {"expost_2024": "ex-post assessment, 2024", "exante_2025_WEM": "ex-ante projection for 2025, with existing measures",
            "exante_2030": "ex-ante projection for 2030", "not_quantified": "not quantified"}.get(code, humanise(code))
