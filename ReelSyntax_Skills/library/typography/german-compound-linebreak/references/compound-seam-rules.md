# German Morphological Seam Patterns and Break Priorities

1. **Priority 1 — Explicit hyphen or `­` soft hyphen** authored in localized copy.
2. **Priority 2 — Productive `Fugen-` suffixes** (`>= 4` chars left & right):
   - `-ungs-` (`Auflösungs-grenze`, `Verarbeitungs-zeit`)
   - `-heits-` / `-keits-` (`Sicherheits-prüfung`, `Geschwindigkeits-test`)
   - `-tions-` / `-itäts-` (`Produktions-plan`, `Qualitäts-kontrolle`)
   - `-schafts-` (`Wirtschafts-daten`)
3. **Priority 3 — Common head-noun boundaries** (`-frequenz`, `-steuerung`, `-kontrolle`, `-prüfung`, `-vergleich`, `-verbrauch`, `-analyse`, `-abgleich`, `-bereich`, `-schicht`).
4. **Fallback — Analytical rewrite**: replace `3`-stem monster noun with `Noun + Genitive/von` phrase (`"Prüfung der Farbkonsistenz"`).
