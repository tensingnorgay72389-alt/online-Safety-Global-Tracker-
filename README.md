# T&S regulatory monitor

This repository is a Trust and Safety regulatory monitoring backend. It captures bills, consultations, enacted rules, statutory codes, official investigations, penalties and court decisions on minors, age assurance, content moderation, harmful content, addictive design, gaming and AI services. It classifies each item against frozen Global Trust and Safety Dashboard vocabularies and writes typed JSON register patches.

Significant draft bills and official status changes are marked for automatic application by a human operator or a companion routine. The significance bar is Australia's Digital Duty of Care Bill 2026 as recorded on the official bill homepage. Passage through both Houses without Royal Assent is a significant status change to `passed`. The instrument remains a `bill`. It is not an Act and not in force.

This repository does not edit any Grok Bot Page or any other external dashboard. It produces verified, typed JSON that can be applied out of band after an official-source check.

## Dashboard

The static site in `dashboard/` is this repository's Global Trust and Safety Dashboard. It covers the 158-market heatmap, the market database, the regulations register and a browser-local score and wording editor. `.github/workflows/deploy-pages.yml` builds it with Node 20 and publishes `dashboard/dist` to GitHub Pages on every push to `main`:

https://tensingnorgay72389-alt.github.io/online-Safety-Global-Tracker-/

The weekday monitor does not write into that site. Python files under `src/` and `tests/` are unchanged by the dashboard.

## Live tracker

This backend is built to update the working 2026 Trust and Safety instrument register, which is the live tracker for this project:

https://cursor.com/canvas/store-ebf3ffb9-7e41-4683-935a-adf799982e56/6246d529-8c4f-4535-9f6a-670da7b635fa

The repository does not edit that Page automatically. It writes typed JSON patches that can be applied out of band after an official-source check.

The register uses published category labels and visual conventions from the Global Trust and Safety Dashboard vocabularies as a reference. That published dashboard is a vocabulary and visual reference only. It is not this tracker: https://patriciayyzhai.github.io/global-trust-safety-dashboard/


## What is in scope

Priority markets are the United States (federal and notable states), the United Kingdom, the European Union and Australia, then Singapore, India, Malaysia, Japan, Korea, Indonesia, Brazil, Canada, Mexico and Turkey. The official map also covers all ASEAN member states and Timor-Leste where an official legislative source was retrieved. Additional EU institutions and sourced EU member-state bodies are included where official URLs were sourced. Official legislatures, bill trackers and parliamentary records are included so that proposed and drafting-stage bills and on-the-record political comments can be reviewed. Precedent-setting developments in other markets are also recorded.

Out of scope are brand mention watching (including a dedicated Tencent Mentions scrape), general cybersecurity, data protection with no online-safety hook, AI industrial policy, election campaigning except where the item is about platform rules, AI content or enforcement, campaign websites and invented politician social accounts. Official legislative records of member or minister comments are collected but are never auto-applied. Political or company statements that do not change an instrument's legal status stay in the inbox.

## Install and test

Python 3.11 or later is required.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

The equivalent without a virtual environment is `pip install -e ".[dev]"` followed by `pytest`.

## Commands

`ts-monitor run --since YYYY-MM-DD` fetches curated sources, classifies items and writes the inbox, all proposals and the significant subset.

To replay Word-report-like JSON or the included fixtures without touching the network:

```bash
ts-monitor run --since 2026-11-24 \
  --file tests/fixtures/inbox/all_required.json \
  --register tests/fixtures/register_pre_ddoc_passage.json \
  --offline \
  --out /tmp/ts-monitor-out
```

`ts-monitor ingest --file PATH` loads a Word-report-like JSON file or a directory of fixture items into `out/inbox/`.

`ts-monitor match` rematches the written inbox against the register snapshot.

`ts-monitor propose` emits patches only, reading the written inbox (or `--file`).

`ts-monitor regulators` prints the regulator map counts. Add `--json` for a machine-readable summary.

`ts-monitor run` also fetches the official newsroom, media-release, bill and consultation pages listed in `config/regulators.yaml`, unless `--skip-regulators` is set. Pass `--regulators PATH` to use another map file.

Useful flags are `--register`, `--sources`, `--regulators`, `--skip-regulators` and `--out`.

## Regulator and ministry map

`config/regulators.yaml` is a versioned, sourced map of online-safety, child-safety, platform, gaming and AI-service regulators and the relevant ministries, legislatures and gazettes in the priority markets. Other markets are included only where the instrument register or an official page retrieved for this map supplied evidence. The map is not a claim to have mapped every regulator on earth.

As of 27 November 2026, 02:50 Hong Kong time (Asia/Hong_Kong, UTC+8) the map lists 108 bodies, 28 spokespersons named on official pages retrieved for the map, two personal X handles, five institutional X handles and 175 scrape targets. A name or handle is listed only when an official page retrieved for this map named that person or identified that handle. Roster leads that could not be re-verified were left off.

Official pages that returned 403, 429 or 404, timed out or failed to connect are still listed and still have scraper targets. Those failures are recorded. They are not treated as evidence that the page does not exist.

See `docs/REGULATOR-MAP.md` for the full list, the official pages that could not be retrieved live from this environment and the names and handles left unverified.

## Outputs

`out/inbox/` holds normalised news items, official items and any fetch errors.

`out/proposals/` holds every typed proposal, including `news_only` items.

`out/significant/` holds the subset with `significant` set to true that is also eligible for automatic application. A companion system should apply only this folder, and only after confirming the official URL still supports the patch.

Each proposal is deterministic JSON. It includes `action` (`new_instrument`, `status_change`, `milestone_add` or `news_only`), an instrument id or a proposed id, `fields`, `previous_values` where relevant, `significant`, `confidence`, `sources` (official URL first), `fetched_at` in ISO 8601 with a timezone, `fetched_at_utc`, `notes` and an `epistemic` mark. The epistemic mark distinguishes sourced facts (names, dates and status) from category judgement (service types and obligation types). The backend does not invent scores and does not recompute dashboard market severity scores.

## Status discipline

Distinguish enacted law, bills, guidance, consultations, committee recommendations, political deals, second-reading votes, lawsuits and research papers. Do not treat the latter items as enactment.

A political deal or a second-reading vote is not enactment. Passed Both Houses without Royal Assent (or equivalent signature) is not an Act and not in force. Ministerial language such as "becomes law" is not Royal Assent. Record what the official instrument page actually lists.

Consultations may be proposed as new rows with `instrument_kind` set to `consultation` and a status of `proposed` or `under_review`. They are not a final code and not the enactment of the underlying statutory duty.

## Significance and auto-apply

`significant` is true only when an official primary source supports one of the following:

1. A new national or regional bill, act, decree, regulation or statutory code on online safety, child safety, AI chatbots, platform duties, age assurance or duty of care is introduced.
2. An official status change to such an instrument. This includes passage through a house, final passage, signature or Royal Assent, commencement, material amendment, injunction, repeal or a formal enforcement action. A named investigation opening is recordable but is not enactment.
3. A material official update to an instrument already in `data/register_snapshot.json`.

Never auto-apply on ministerial or political statements alone, regulator-network joint statements without a binding instrument, company comments, academic papers, news analysis or brand mentions. Those may be stored in the inbox as `news_only` items.

If an official page returns 403 or times out, the failure is recorded in `out/inbox/fetch_errors.json`. That failure is not evidence that the page does not exist. Do not auto-apply on press copy alone.

## Weekday workflow

`.github/workflows/monitor.yml` runs tests and then `ts-monitor run` at 09:00 Hong Kong time on weekday mornings (01:00 UTC, cron `0 1 * * 1-5`). Artefacts are uploaded. The workflow does not edit an external dashboard. If a Congress.gov API token is ever needed, set the repository secret `CONGRESS_GOV_API_KEY` and expose it as that environment variable. Never commit tokens.

## Register snapshot

`data/register_snapshot.json` is a snapshot of the current instrument register. The operator should refresh it after applying patches. It is not live dashboard state.

One snapshot row, `US-NY-WARN-2025`, is recorded with status `enacted`, which is not a frozen RegulationStatus value. Review that row against official chaptered text before any later patch overwrites it.

This project uses the published Global Trust and Safety Dashboard category labels. The site in `dashboard/` is maintained here.

## Secrets

Do not add credentials, client-advisory wording or internal briefing material to this repository.
