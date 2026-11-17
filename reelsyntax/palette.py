import math


def hex_to_rgb(value: str) -> tuple[int, int, int]:
    clean = value.lstrip('#')
    return (int(clean[0:2], 16), int(clean[2:4], 16), int(clean[4:6], 16))


def rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    r, g, b = (max(0, min(255, int(round(c)))) for c in rgb)
    return f'#{r:02x}{g:02x}{b:02x}'


def srgb_channel_to_linear(u: float) -> float:
    u = max(0.0, min(1.0, u))
    return u / 12.92 if u <= 0.04045 else ((u + 0.055) / 1.055) ** 2.4


def linear_channel_to_srgb(v: float) -> float:
    v = max(0.0, min(1.0, v))
    return 12.92 * v if v <= 0.0031308 else 1.055 * (v ** (1.0 / 2.4)) - 0.055


def hex_to_linear(value: str) -> tuple[float, float, float]:
    r, g, b = hex_to_rgb(value)
    return (srgb_channel_to_linear(r / 255.0), srgb_channel_to_linear(g / 255.0), srgb_channel_to_linear(b / 255.0))


def linear_to_rgb8(lin: tuple[float, float, float], dither: float = 0.0) -> tuple[int, int, int]:
    return tuple(
        max(0, min(255, int(math.floor(linear_channel_to_srgb(c) * 255.0 + 0.5 + dither))))
        for c in lin
    )


def linear_rgb_to_oklab(r: float, g: float, b: float) -> tuple[float, float, float]:
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l_ = math.copysign(abs(l) ** (1.0 / 3.0), l)
    m_ = math.copysign(abs(m) ** (1.0 / 3.0), m)
    s_ = math.copysign(abs(s) ** (1.0 / 3.0), s)
    return (
        0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_,
        1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_,
        0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_,
    )


def oklab_to_linear_rgb(L: float, a: float, b: float) -> tuple[float, float, float]:
    l_ = L + 0.3963377774 * a + 0.2158037573 * b
    m_ = L - 0.1055613458 * a - 0.0638541728 * b
    s_ = L - 0.0894841775 * a - 1.2914855480 * b
    l, m, s = l_ * l_ * l_, m_ * m_ * m_, s_ * s_ * s_
    return (
        +4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
        -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
        -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s,
    )


def mix_oklab(hex_a: str, hex_b: str, t: float) -> tuple[int, int, int]:
    t = max(0.0, min(1.0, float(t)))
    la = linear_rgb_to_oklab(*hex_to_linear(hex_a))
    lb = linear_rgb_to_oklab(*hex_to_linear(hex_b))
    lin = oklab_to_linear_rgb(*(a + (b - a) * t for a, b in zip(la, lb)))
    return linear_to_rgb8(tuple(max(0.0, min(1.0, c)) for c in lin))


def _agx_curve(x: float) -> float:
    x = max(1e-6, x)
    ev = max(-10.0, min(6.5, math.log2(x)))
    u = (ev + 10.0) / 16.5
    u2 = u * u
    u4 = u2 * u2
    return (15.5 * u4 * u2 - 40.14 * u4 * u + 31.96 * u4 - 6.868 * u2 * u + 0.4298 * u2 + 0.1191 * u - 0.00232)


def agx_tonemap_linear(lin: tuple[float, float, float], exposure: float = 1.0, punch: float = 1.08) -> tuple[float, float, float]:
    r, g, b = (max(0.0, c * exposure) for c in lin)
    # Gamut-compressing inset before sigmoid prevents harsh primary hue shifts in highlights.
    ir = 0.842479062253094 * r + 0.0784335999999992 * g + 0.0792237451477643 * b
    ig = 0.0423282422610123 * r + 0.878468636469772 * g + 0.0791661274605434 * b
    ib = 0.0423756549057051 * r + 0.0784336 * g + 0.879142973793104 * b
    cr, cg, cb = (max(0.0, min(1.0, _agx_curve(c))) for c in (ir, ig, ib))
    if punch != 1.0:
        cr, cg, cb = (max(0.0, min(1.0, 0.5 + (c - 0.5) * punch)) for c in (cr, cg, cb))
    # Mild outset restoration while retaining highlight desaturation.
    or_ = 1.19687900512017 * cr - 0.0980208811401368 * cg - 0.0990297440797205 * cb
    og = -0.0528968517574562 * cr + 1.15190312990417 * cg - 0.0989611768448433 * cb
    ob = -0.0529716355144438 * cr - 0.0980434501171241 * cg + 1.15107367264116 * cb
    return (max(0.0, min(1.0, or_)), max(0.0, min(1.0, og)), max(0.0, min(1.0, ob)))


def relative_luminance(rgb: tuple[int, int, int]) -> float:
    r, g, b = (srgb_channel_to_linear(c / 255.0) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(rgb_a: tuple[int, int, int], rgb_b: tuple[int, int, int]) -> float:
    la, lb = relative_luminance(rgb_a), relative_luminance(rgb_b)
    bright, dark = (la, lb) if la >= lb else (lb, la)
    return (bright + 0.05) / (dark + 0.05)
