# Locale Casing Transformation Table and Protected Units

| Locale | Input Sample | Correct All-Caps Output | Naive `.upper()` Bug | Correct Lowercase Output |
| --- | --- | --- | --- | --- |
| `tr` | `iyi ışık, şık çizgi` | `İYİ IŞIK, ŞIK ÇİZGİ` | `IYI IŞIK, ŞIK ÇIZGI` | `iyi ışık, şık çizgi` |
| `de` | `Straßengröße` | `STRASSENGRÖSSE` | `STRASSENGRÖSSE` (measure `+2` width!) | `straßengröße` |
| `fr` | `Écran d'accueil` | `ÉCRAN D'ACCUEIL` | Accent stripping if ASCII-folded | `écran d'accueil` |
| `es` | `Diseño útil` | `DISEÑO ÚTIL` | Missing `Ñ`/`Ú` in ASCII bitmap font | `diseño útil` |

Always measure pixel advance *after* applying the locale casing map and `unicodedata.normalize("NFC", s)`.
