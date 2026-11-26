# Monitoring process

This note is the operating process for a human operator or a companion routine. The backend discovers and classifies Trust and Safety regulatory items. It does not itself update any dashboard.

## Daily (weekday) loop

1. Refresh the register snapshot in `data/register_snapshot.json` if patches were applied since the last run.
2. Run `ts-monitor run --since YYYY-MM-DD`, using the day after the previous successful window. On a machine without network access, pass `--file` and `--offline` to replay a Word-report-like JSON export or the fixtures.
3. Read `out/inbox/fetch_errors.json` if it exists. A 403 or a timeout is not evidence that the official page has disappeared. Retry later or open the URL in a browser. Do not invent a status from the failure.
4. Review `out/proposals/proposals.json` for the full set, including `news_only` items.
5. Review `out/significant/proposals.json` for candidates that the classifier marked both significant and auto-apply eligible.

Scheduled CI follows the same loop. `.github/workflows/monitor.yml` runs at 09:00 Hong Kong time, Monday to Friday, and uploads the `out/` artefacts. The workflow does not apply patches and does not edit a Page.

## How to apply `out/significant/` patches

A companion system or the operator should apply a significant patch only when all of the following hold:

- The proposal `action` is `new_instrument`, `status_change` or `milestone_add`. Never apply a `news_only` item to the register.
- `significant` is true and `auto_apply_eligible` is true and `rejected` is false and `vocabulary_flags` is empty.
- The first entry in `sources` is an official primary URL, and that URL still supports the proposed legal facts when checked at apply time.
- Names, dates and status in `epistemic.sourced_facts` are taken from that official URL. Category fields in `epistemic.category_judgement` (service types and obligation types) are analytical judgement and should be reviewed, not auto-copied without a sense check.
- No signed date or effective date is being invented. If those fields are null, leave them null.
- `instrument_kind` is not being upgraded to `enacted` or `in force` unless the official page lists Royal Assent or an equivalent signature, or the instrument is already an Act.

After a patch is applied out of band, copy the updated instrument list back into `data/register_snapshot.json`. The dashboard itself is updated out of band. This repository never writes to a Grok Bot Page.

## Significance bar

The bar is the Australia Online Safety Amendment (Digital Duty of Care) Bill 2026, official homepage `r7553`. As checked at 25 November 2026, 18:21 Hong Kong time, that page listed status Passed Both Houses and did not list Royal Assent. The correct register reading is status `passed`, `instrument_kind` still `bill`, `passed_date` 25 November 2026, no signed or effective date and a note that the instrument is not an Act and not in force.

A later official Royal Assent listing would be a significant auto-apply event. Until that official listing exists, do not upgrade the row because of a media release title such as "becomes law".

A consultation such as Ofcom's 25 November 2026 consultation on codes for a 48-hour intimate-image takedown duty may be added as a new row with `instrument_kind` set to `consultation`. It is significant only if the official consultation page is the source. It is not enactment of the Crime and Policing Act duty.

A GOSRN-style joint regulator statement, a CEO or senator statement with no bill and a brand mention with no instrument stay in the inbox as `news_only`. They are never auto-applied.

## Status discipline in one page

- A bill that has not passed the legislature stays `proposed`.
- Final legislative passage without signature or Royal Assent is `passed`, and `instrument_kind` stays `bill`.
- Royal Assent or equivalent signature may move `instrument_kind` to `enacted`. Do not invent an effective date.
- Commencement, once officially listed, may move status to `implementation_period` or `effective`.
- `enforced` is only for formal supervision, codes, investigations or penalties under that instrument.
- Guidance and consultations are not statutes. Use `instrument_kind` `guidance` or `consultation` beside an appropriate status such as `proposed` or `under_review`.
- Political deals, second-reading votes, committee recommendations and ministerial announcements are not enactment.

Use frozen labels only. The enums live in `config/vocabularies.yaml`. Any status, service type or obligation value that is not in those lists must be flagged and must not be applied.

## Ingesting historical Word reports

Export each report as JSON with a `report_title` and an `items` array. Each item should have a headline, outlet, date, URL and a one- or two-paragraph summary, plus an optional `section` field. Then run:

```bash
ts-monitor ingest --file path/to/report.json
ts-monitor propose
```

Items from a Tencent Mentions section are retained as `news_only` unless they also describe a regulatory instrument. There is no brand-mention scrape in this backend.

## Fetching

`config/sources.yaml` lists official and news endpoints, the fetch method (`rss`, `html_index` or `official_page`), the jurisdiction and whether a hit can ever be auto-applied. Only official sources can be auto-applied, and only when the classifier also finds a qualifying instrument event. News sources are for discovery.

Fetches use a short timeout and a declared user-agent. Optional environment variables are `TS_MONITOR_USER_AGENT` and `TS_MONITOR_HTTP_TIMEOUT`. An optional `CONGRESS_GOV_API_KEY` may be used later if Congress.gov HTML is not enough. Never commit a token.

## Provenance

Record fetch timestamps in Asia/Hong_Kong and in UTC. Every proposed legal fact needs an official URL. Do not invent a fact, quote, date, provision number or link.
