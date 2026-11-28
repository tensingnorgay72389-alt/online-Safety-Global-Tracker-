# Regulator and ministry map

This note describes `config/regulators.yaml`. That file is a versioned, sourced map of online-safety, child-safety, platform, gaming and AI-service regulators and the relevant ministries, official newsrooms, national legislatures (including houses of representatives), official bill trackers, parliamentary records and named key spokespersons. Other markets are included only where the instrument register or an official page retrieved for this map supplied evidence. It is not a claim to have mapped every regulator on earth.

The map version is 2026-11-27-legislature-sea. Official pages for this expansion were retrieved on 27 November 2026, 02:50 Hong Kong time (Asia/Hong_Kong, UTC+8). Earlier official retrievals for the first version of the map were made at 02:02 Hong Kong time the same day.

A spokesperson is listed only when an official page retrieved for this map named that person in the stated role. A personal or institutional X handle is listed only when that official page clearly identified the handle. Roster leads that could not be re-verified against a retrieved official page were left off. Brand-mention watching is out of scope. Ministerial language such as "becomes law" is not enactment.

## Live tracker

This backend is built to update the working 2026 Trust and Safety instrument register, which is the live tracker for this project:

https://cursor.com/canvas/store-ebf3ffb9-7e41-4683-935a-adf799982e56/6246d529-8c4f-4535-9f6a-670da7b635fa

The repository does not edit that Page automatically. The published Global Trust and Safety Dashboard is a vocabulary and visual reference only. It is not this tracker: https://patriciayyzhai.github.io/global-trust-safety-dashboard/

## How the pipeline uses the map

`ts-monitor run --since YYYY-MM-DD` loads the map, turns each scrape target into a catalogue source and merges those sources into `config/sources.yaml` by host and path. The weekday fetch then keeps official sources whose jurisdiction is in the approved priority market set, plus the existing Timor-Leste legislative source. Official targets for other jurisdictions remain in the map and are not requested. Pass `--skip-regulators` to use only `sources.yaml`. Pass `--regulators PATH` to load another map file.

`ts-monitor regulators` prints body and spokesperson counts. `--json` writes a machine-readable summary.

Fetch methods on scrape targets are `rss`, `official_page`, `html_index`, `newsroom` and `media_release_index`. RSS or official JSON is preferred where a source already lists it. Official newsroom and media-release indexes are parsed as HTML. Requests use a declared user-agent and a short timeout. A 403, 429, 404, timeout or connection failure is written to `out/inbox/fetch_errors.json`. That failure is not evidence that the page does not exist. The official URL stays in the map and remains a scrape target.

Ministerial media-release sources and official legislative records of political comments (`legislative_record`) are never auto-apply eligible. Frozen dashboard vocabularies and the significance bar in `MONITORING.md` are unchanged.

The closed UK Department for Science, Innovation and Technology is recorded for provenance. Official GOV.UK text retrieved for an earlier version of this map states that the department existed until 2026 and that its responsibilities were split. It has no scrape targets.

## Counts

This version lists 108 bodies, 28 spokespersons named on official pages retrieved for the map, two personal X handles, five institutional X handles and 175 scrape targets. Of those bodies, 40 are legislatures or legislative boards, 32 are regulators, 26 are ministries, eight are gazettes, one is an executive office and one is a statutory commission. After deduplication against `config/sources.yaml` and the weekday market gate, `ts-monitor run` adds 142 net new official targets. The nine official targets for Greece, China, the United Arab Emirates and the five United States state pages remain in the map and are not requested on that run.

## Legislatures, bills in drafting and politician comments

Official lower and upper houses, bill trackers and parliamentary records are mapped so that proposed bills, bills in drafting or consultation and on-the-record comments can be reviewed. Those records come only from official legislative sources (Hansard, the Congressional Record, official debates, official bill and committee pages and official parliament newsrooms). Campaign websites and invented politician social accounts are not scraped.

A named politician is listed as a spokesperson only when an official page retrieved for this update named that person. On-the-record comments by members or ministers are captured as inbox items from `legislative_record` targets. Those items are never auto-applied to the register. Official bill and gazette pages remain eligible for auto-apply only when the classifier also finds a qualifying official instrument event.

Sourced legislature and bill-draft targets include the US House of Representatives, the US Senate, congress.gov, the official Congressional Record and federal bills collections on govinfo, UK bills, legislation.gov.uk, Hansard and the official House of Commons and House of Lords pages, the European Parliament, its Legislative Observatory, the Official Journal on EUR-Lex, the Australian Parliament bill and Hansard pages, the House of Commons of Canada, the Senate of Canada and LEGISinfo, Lok Sabha and Rajya Sabha bill indexes on Digital Sansad, the Parliament of Singapore bills and Official Reports pages and official national parliament sites for Indonesia, Malaysia, Thailand, Brunei, Cambodia, Laos, Vietnam, Timor-Leste, Japan, Korea, Brazil, France, Germany, Ireland, Mexico and Turkey. Several of those official URLs could not be retrieved live from this environment and remain scrape targets.

## MCMC official URLs

The Malaysian Communications and Multimedia Commission entry now includes these official URLs, all on mcmc.gov.my and retrieved this run except where already listed:

- Homepage: https://www.mcmc.gov.my/
- Press releases (already present): https://www.mcmc.gov.my/en/media/press-releases
- Announcements: https://www.mcmc.gov.my/en/media/announcements
- Online Safety Act public consultation: https://www.mcmc.gov.my/en/onsa/resources/public-consultation
- Information papers and consultation papers: https://www.mcmc.gov.my/en/resources/reports/information-paper
- Legislation: https://www.mcmc.gov.my/en/legal/acts
- Online Safety Act under-16 page (already present): https://www.mcmc.gov.my/en/onsa/under-16
- Commission members (already present as the leadership source): https://www.mcmc.gov.my/en/about-us/commission-members

The official Ministry of Communications portal at https://www.komunikasi.gov.my/en/ and its public news index, the official Ministry of Digital site at https://www.digital.gov.my/ and https://www.digital.gov.my/en-GB/siaran and the official Parliament of Malaysia portal at https://www.parlimen.gov.my/ with its press-releases page were also added. The ministry portal returned only a short browser-fingerprint script from this environment. The parliament portal did not connect. Those official URLs are retained.

## Official Indian regulator, ministry and legislature URLs

Already present: MeitY homepage and team page, the Online Gaming Authority rules PDF cited in the register and egazette.gov.in (still a connection failure, still a target).

Added this run:

- TRAI homepage https://trai.gov.in/ (retrieved) and press releases https://www.trai.gov.in/notifications/press-release (retrieved)
- Ministry of Information and Broadcasting https://mib.gov.in/en (retrieved)
- CERT-In https://www.cert-in.org.in/ and press list https://www.cert-in.org.in/s2cMainServlet?pageid=PRESSLIST (connection failure, URLs retained)
- Data Protection Board of India https://dpbi.gov.in/ (HTTP 403, URL retained as the official portal identified by a 14 November 2026 Press Information Bureau release)
- MeitY press-release archive https://www.meity.gov.in/archives?page=press-release (HTTP 403, URL retained)
- Digital Sansad https://sansad.in/, Lok Sabha https://sansad.in/ls, Lok Sabha bills https://sansad.in/ls/legislation/bills and Rajya Sabha bills https://sansad.in/rs/legislation/bills (retrieved). The sansad.gov.in address and the Rajya Sabha homepage did not connect.

## Southeast Asia

Official T&S, communications, digital, media or legislative sources were added for every ASEAN member. Timor-Leste was added only because an official National Parliament page was retrieved.

- Brunei: AITI and Jabatan Majlis-Majlis Mesyuarat (both retrieved)
- Cambodia: Telecommunication Regulator of Cambodia and the National Assembly English site (retrieved). The official MPTC URL at https://www.mptc.gov.kh/ returned a "Request Rejected" page and is retained
- Indonesia: Komdigi portal and Peraturan BPK already in the map, plus the official DPR RI portal (retrieved)
- Laos: National Assembly (retrieved). No official communications-ministry URL was sourced this run
- Malaysia: MCMC, Ministry of Communications, Ministry of Digital and Parliament of Malaysia, as above
- Myanmar: Posts and Telecommunications Department (retrieved). The broader myanmar.gov.mm portal did not connect. No official parliament URL was added, because an official parliamentary homepage was not retrieved
- Philippines: House of Representatives, Senate, DICT, NTC and the Official Gazette (all official URLs returned HTTP 403 and are retained)
- Singapore: MDDI, IMDA, PDPC, Online Safety Commission and Singapore Statutes Online already in the map, plus the official Parliament, bills, Official Reports and press-release pages (retrieved)
- Thailand: National Assembly (retrieved). Official NBTC and MDES URLs returned HTTP 403 and are retained
- Vietnam: a request for www.mic.gov.vn redirected to the official Ministry of Science and Technology portal at https://mst.gov.vn/ (retrieved, including news and legal-document indexes and a posts and telecommunications news section). The National Assembly site at https://quochoi.vn/ could not be retrieved and is retained. No official URL was invented
- Timor-Leste: Parlamento Nacional (retrieved)

## European Union

EU-level official sources now include DG CONNECT, the European AI Office, the Commission spokespersons service, EUR-Lex and the Official Journal direct-access page, Home Affairs, the European Parliament and its Legislative Observatory, the Council of the European Union and its press page, the European Data Protection Supervisor and the European Data Protection Board. The Legislative Observatory, Official Journal page and EDPB were retrieved. The Parliament, Council and EDPS official URLs returned HTTP 403 and are retained.

Sourced EU member-state bodies, in addition to those already in the map (France CNIL and Arcom, Greece's parliament, Ireland's Coimisiún na Meán), are the German Bundestag and Bundesnetzagentur, Italy's AGCOM, Spain's CNMC, the Netherlands ACM, the Houses of the Oireachtas (bills and debates, retrieved, with the institutional handle @OireachtasNews listed on the official homepage) and the French Assemblée nationale and Sénat. Official URLs were not invented for other member states that were not sourced this run.

## Sourced spokespersons

The names below were taken from official pages retrieved for this map. Where a handle is shown, that official page identified it. Where no handle is shown, no personal handle was listed on that page. New names from this expansion are marked as added 27 November 2026, 02:50 Hong Kong time.

- Andrew N. Ferguson, Chairman of the Federal Trade Commission, official commissioners page, personal handle @AFergusonFTC and institutional handle @FTC
- Mark R. Meador, Commissioner, Federal Trade Commission, same official commissioners page, personal handle @MeadorFTC
- Arielle Roth, Assistant Secretary, National Telecommunications and Information Administration, official NTIA homepage (added this expansion)
- Lisa Nandy, Secretary of State for Digital, Culture, Media and Sport, official GOV.UK biography (appointed 20 July 2026). No personal handle was listed on that page
- Henna Virkkunen, Executive Vice-President, Communications Networks, Content and Technology, official DG CONNECT leadership page. A dedicated biography URL returned HTTP 429 and was not used as a source. No personal handle is listed
- Roberto Viola, Director-General, Communications Networks, Content and Technology, official DG CONNECT leadership page
- Lucilla Sioli, Director of the European AI Office, official Commission page dated 27 August 2026
- Paula Pinho, European Commission Chief Spokesperson, official spokespersons directory
- Thomas Regnier, Spokesperson (Tech Sovereignty, Defence, Space, Disinformation), official spokespersons directory
- Nika Blazevic, press officer (Tech Sovereignty), official spokespersons directory
- Patricia Poropat, press officer (Tech Sovereignty, Disinformation), official spokespersons directory
- Josephine Teo, Minister for Digital Development and Information and Minister-in-charge of Cybersecurity and Smart Nation Group, official MDDI political office holders page
- Ng Cher Pong, Chief Executive Officer, Infocomm Media Development Authority, official MDDI appointment release (CEO from 1 November 2025)
- Tan Sri Mohamad Salim Bin Fateh Din, Chairman of the Malaysian Communications and Multimedia Commission, official commission members page
- FURUKAWA Toshiharu, Minister for Digital Transformation, official Digital Agency English biography (last updated 29 September 2026)
- Jong-Cheol Kim (김종철), Chair, Korea Media and Communications Commission, official chair introduction page
- Waldemar Gonçalves Ortunho Junior, Director-President, ANPD, official biography (modified 29 April 2026). The page describes a 2020-2026 mandate. No later official page extending or ending that mandate was retrieved for this map
- Alexandre Freire, interim president of the Anatel Board of Directors, official Anatel news page published 6 November 2026 (assumed the interim presidency on 5 November 2026)
- Marc Miller, Minister of Canadian Identity and Culture and Minister responsible for Official Languages, official Canadian Heritage homepage, institutional handle @CdnHeritage
- Mélanie Joly, Minister of Industry and Minister responsible for Canada Economic Development for Quebec Regions, official ISED ministers page
- Evan Solomon, Minister of Artificial Intelligence and Digital Innovation and Minister responsible for the Federal Economic Development Agency for Southern Ontario, official ISED ministers page
- Marie-Laure Denis, President of the CNIL since 2 February 2019 (mandate renewed 30 January 2024), official CNIL biography, institutional handle listed as http://twitter.com/cnil
- Omar bin Sultan Al Olama, Minister of State for Artificial Intelligence, Digital Economy and Remote Work Applications, official UAE Cabinet page. The official page form of the name is used
- Sinéad McSweeney, Online Safety Commissioner, Coimisiún na Meán, official appointment statement dated 17 November 2026, institutional handle @CNaM_ie on the official homepage
- John Evans, Digital Services Commissioner, Coimisiún na Meán, named on the same official appointment statement
- Zhuang Rongwen (庄荣文), Director of the Cyberspace Administration of China and Director of the State Internet Information Office, official CAC signed article dated 2 November 2026
- Anil Kumar Lahoti, Chairman, Telecom Regulatory Authority of India, official TRAI homepage (added this expansion)
- Ashwini Vaishnaw, Cabinet Minister, Ministry of Information and Broadcasting, official MIB homepage (added this expansion)

## Official pages that could not be retrieved live in this expansion

A failure is not evidence that the page does not exist. Each official URL below is retained and remains a scrape target, except where a guessed path returned 404 and was discarded.

HTTP 403 included official newsrooms and legislatures for the FCC, Ofcom, the ICO, the US Senate, the US Department of Commerce, congress.gov, NTIA newsroom, UK House of Commons, House of Lords and Hansard, the European Parliament and Council and EDPS, the Australian Parliament bill and Hansard pages, the Philippine House, Senate, DICT, NTC and Official Gazette, Thailand's NBTC and MDES, MeitY press and homepage, dpbi.gov.in, Mexico's Senate and several pages already recorded as 403 in the first map run.

Connection or transport errors included the Parliament of Malaysia portal and press page, CERT-In, egazette.gov.in, sansad.gov.in, the Rajya Sabha homepage, mic.gov.vn, myanmar.gov.mm, assembly.go.kr and Mexico's Chamber of Deputies. https://quochoi.vn/ could not be retrieved (transport or certificate error). The official MPTC URL returned a "Request Rejected" page. The official Ministry of Communications portal at komunikasi.gov.my returned only a fingerprint reload script.

The official Bundesnetzagentur English homepage was retrieved after the bare domain path returned HTTP 404. A guessed NTIA `/news` path returned HTTP 404 and is not used. The official newsroom path linked from the NTIA homepage is the scrape target.

Pages recorded as not retrieved in the first map run (including eSafety and ACMA timeouts) remain in that state unless re-retrieved successfully in this expansion.

## Names and handles left unverified

The morning-desk roster was used only as a lead. Names and handles left off in the first map run remain unverified, including Anika Wells, Julie Inman Grant, Nerida O'Loughlin, Ofcom and ICO board leads, Howard Lutnick, Brendan Carr, MeitY team names from the roster (Ashwini Vaishnaw is now listed only for the Ministry of Information and Broadcasting, because that official homepage named him in that role, not because the MeitY team page was retrieved), a Japanese MIC minister, a Brazilian communications minister, a Komdigi minister, Fahmi Fadzil, PDPC leadership and Arcom leadership.

Handles still not copied and never inferred from a name pattern include @lisanandy, @HennaVirkkunen, @OmarSAlolama, @howardlutnick, @BrendanCarrFCC, @IMDAsg, @AnikaWells, @eSafetyOffice, @Ofcom, @MCMC_RASMI, @digital_jpn, @MIC_JAPAN, @kemkomdigi and @anatelgovbr.

No minister was listed for Malaysia's Ministry of Communications or Ministry of Digital, because a readable official leadership page did not name a current minister in the text used for this map.

## Markets and bodies not invented

- Laos has an official National Assembly page in the map. No official communications-ministry URL was sourced this run, so none was added.
- Myanmar has the official Posts and Telecommunications Department in the map. No official parliament URL was added, because an official parliamentary homepage was not retrieved.
- Other EU member states that were not sourced this run were not given invented regulators or legislatures.
- US state instruments for Arkansas, Florida, Maryland, Nebraska, Utah and Vermont still have no invented official homepages.
- A guessed Malaysian Hansard path was not added, because it was not taken from a retrieved official page.

Each entry in the YAML records jurisdiction, body type, official name, official homepage where one was sourced, newsroom or media-release URL, bill or consultation board URL where one exists, key spokespersons with role and sourced official URL, fetch method and a retrieval note for this run.
