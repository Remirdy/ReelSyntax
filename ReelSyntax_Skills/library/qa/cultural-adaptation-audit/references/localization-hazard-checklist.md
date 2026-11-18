# Localization Hazard and Cultural Audit Checklist

| Hazard Category | Flagged Pattern | Safe Localized Replacement |
| --- | --- | --- |
| Ambiguous date | `04/09/26`, `4/9` | `9 Apr 2026` / `9 Nisan 2026` / `9. April 2026` / `2026-04-09` |
| 12-hour clock in EU/TR | `4:00 PM`, `9 AM` | `16:00` (`de`/`fr`/`es`/`pt`), `16.00` (`tr`) |
| Imperial units in generic copy | `98°F`, `5 lbs`, `10 ft` | `37 °C`, `2,3 kg`, `3 m` |
| Hardcoded English UI chrome | `STEP 1`, `BEFORE / AFTER` | `ADIM 01`, `ÖNCE / SONRA` (`tr`); `SCHRITT 01`, `VORHER / NACHHER` (`de`) |
| Season-month coupling | `"Warm January?"` / `"Summer in June"` | Name the month or condition directly (`"In June"`, `"On hot days"`) |
