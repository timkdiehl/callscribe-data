# callscribe-data

Hosted data for [CallScribe](https://github.com/timkdiehl/CallScribe), the
voice-first ham radio logging app.

## contest-catalog.json

The contest catalog the app refreshes from (Settings → Contesting →
Update Contest List). Entries map contest names onto the app's built-in
exchange shapes:

- `key` — stable identifier stamped on contest runs
- `name` / `shortName` — picker row and operate banner
- `cabrilloID` — the `CONTEST:` header contest robots expect
- `profileID` — one of the app's exchange shapes (`rst-serial`,
  `class-section`, `sweepstakes`, …); entries with unknown shapes are
  ignored by older builds
- `theySend`, `exchangeHint`, `exchangeExample` — plain-words coaching
- `schedule` — weekend rules: `{"month": 6, "ordinal": 4}` = 4th full
  weekend of June; `"ordinal": -1` = last full weekend. Dates compute
  in-app from these rules, so this file only changes when a sponsor
  moves a contest.

Bumping `version` above 1 tells old app builds to ignore the file
(schema break).

The canonical source is the app's built-in table — regenerate with:

```
CALLSCRIBE_DUMP_CATALOG=contest-catalog.json swift test --filter testDumpCatalogJSON
```
