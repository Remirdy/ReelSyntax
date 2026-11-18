# Localization glossary

Keep these core domain terms consistent across interface catalogs (`locales/`), documentation (`docs/`), and format descriptions:

| English (`en`) | Turkish (`tr`) | German (`de`) | Meaning |
| --- | --- | --- | --- |
| `reel` / project | proje (`reel.json`) | Projekt (`reel.json`) | Frame-indexed declarative video project |
| `frame` | kare | Einzelbild / Frame | Canonical integer timeline unit |
| `format` | format | Format | Declarative prompt-to-video recipe (`format.json` + `FORMAT.md`) |
| `gate` (approval gate) | onay kapısı | Freigabestufe | Interactive or automated review checkpoint between steps |
| `pilot` | pilot kesit | Pilot-Ausschnitt | Short low-cost render slice reviewed before full rendering |
| `profile` (`draft` / `production` / `hero`) | render profili (`draft` / `production` / `hero`) | Render-Profil (`draft` / `production` / `hero`) | Quality and refinement level; literal CLI identifiers stay untranslated |
| `scene cache` | sahne önbelleği | Szenen-Cache | Content-addressed per-scene rendered output |
| `safe area` | güvenli alan | Schutzbereich | Margin clear of platform player overlays |
