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

## Automation

Two GitHub Actions keep this file trustworthy without anyone touching it:

- **Validate** (`validate.yml`) — every push and PR runs
  `scripts/validate.py`: schema, unique keys, known exchange shapes,
  sane weekend rules. A broken file can't land on `main`, which is what
  the app fetches.
- **Auto-update** (`auto-update.yml`) — Thursdays 13:00 UTC,
  `scripts/update_from_wa7bnm.py` reads the
  [WA7BNM Contest Calendar](https://www.contestcalendar.com) RSS feed
  (a rolling 8-day window — every contest passes through it the week
  before it runs) and compares each listed contest's actual weekend
  with the one our rule predicts. Confirmed drift is fixed and
  committed automatically; anything ambiguous (weekday starts, dates
  that aren't a full weekend) opens an issue instead of guessing. The
  app picks up committed fixes within days.

Dates in the app always compute locally from the weekend rules — this
repo only changes when a sponsor actually moves a contest.
