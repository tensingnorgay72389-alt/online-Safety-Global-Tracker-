# Regulator and ministry map

This note describes `config/regulators.yaml`. That file is a versioned, sourced map of online-safety, child-safety, platform, gaming and AI-service regulators and the relevant ministries, legislatures and gazettes in the priority markets, plus other markets evidenced in the instrument register or on official pages retrieved for this map. It is not a claim to have mapped every regulator on earth.

The map version is 2026-11-27. Official pages for this version were retrieved on 27 November 2026, 02:02 Hong Kong time (Asia/Hong_Kong, UTC+8).

A spokesperson is listed only when an official page retrieved for this map named that person in the stated role. A personal or institutional X handle is listed only when that official page clearly identified the handle. Roster leads that could not be re-verified against a retrieved official page were left off. Brand-mention watching is out of scope. Ministerial language such as "becomes law" is not enactment.

## How the pipeline uses the map

`ts-monitor run --since YYYY-MM-DD` loads the map, turns each scrape target into a catalogue source and merges those sources into `config/sources.yaml` by host and path. Pass `--skip-regulators` to use only `sources.yaml`. Pass `--regulators PATH` to load another map file.

`ts-monitor regulators` prints body and spokesperson counts. `--json` writes a machine-readable summary.

Fetch methods on scrape targets are `rss`, `official_page`, `html_index`, `newsroom` and `media_release_index`. RSS or official JSON is preferred where a source already lists it. Official newsroom and media-release indexes are parsed as HTML. Requests use a declared user-agent and a short timeout. A 403, 429, 404, timeout or connection failure is written to `out/inbox/fetch_errors.json`. That failure is not evidence that the page does not exist. The official URL stays in the map and remains a scrape target.

Ministerial media-release sources are never auto-apply eligible. Frozen dashboard vocabularies and the significance bar in `MONITORING.md` are unchanged.

The closed UK Department for Science, Innovation and Technology is recorded for provenance. Official GOV.UK text retrieved for this map states that the department existed until 2026 and that its responsibilities were split. It has no scrape targets.

## Counts

This version lists 53 bodies, 25 spokespersons named on official pages retrieved for the map, two personal X handles, four institutional X handles and 66 scrape targets. Of those bodies, 18 are regulators, 16 are ministries, 10 are legislatures or legislative boards, seven are gazettes, one is an executive office and one is a statutory commission.

Priority markets covered are the United States (federal, plus California, New York, Texas, Minnesota and Virginia, which already had official URLs in the source catalogue), the United Kingdom, the European Union, Australia, Singapore, India, Malaysia, Japan, Korea, Indonesia, Brazil, Canada, Mexico and Turkey. Additional bodies were added only where the register or a retrieved official page supplied evidence. Those additions are France (CNIL and Arcom), Greece (Hellenic Parliament), the United Arab Emirates (Cabinet and legislation site), Ireland (Coimisiún na Meán) and China (Cyberspace Administration of China).

## Sourced spokespersons

The 25 names below were taken from official pages retrieved on 27 November 2026, Hong Kong time. Where a handle is shown, that official page identified it. Where no handle is shown, no personal handle was listed on that page.

- Andrew N. Ferguson, Chairman of the Federal Trade Commission, official commissioners page, personal handle @AFergusonFTC and institutional handle @FTC
- Mark R. Meador, Commissioner, Federal Trade Commission, same official commissioners page, personal handle @MeadorFTC
- Lisa Nandy, Secretary of State for Digital, Culture, Media and Sport, official GOV.UK biography (appointed 20 July 2026). No personal handle was listed on that page.
- Henna Virkkunen, Executive Vice-President, Communications Networks, Content and Technology, official DG CONNECT leadership page. A dedicated biography URL returned HTTP 429 and was not used as a source. No personal handle is listed.
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
- Waldemar Gonçalves Ortunho Junior, Director-President, ANPD, official biography (modified 29 April 2026). The page describes a 2020-2026 mandate. No later official page extending or ending that mandate was retrieved for this map.
- Alexandre Freire, interim president of the Anatel Board of Directors, official Anatel news page published 6 November 2026 (assumed the interim presidency on 5 November 2026)
- Marc Miller, Minister of Canadian Identity and Culture and Minister responsible for Official Languages, official Canadian Heritage homepage, institutional handle @CdnHeritage
- Mélanie Joly, Minister of Industry and Minister responsible for Canada Economic Development for Quebec Regions, official ISED ministers page
- Evan Solomon, Minister of Artificial Intelligence and Digital Innovation and Minister responsible for the Federal Economic Development Agency for Southern Ontario, official ISED ministers page
- Marie-Laure Denis, President of the CNIL since 2 February 2019 (mandate renewed 30 January 2024), official CNIL biography, institutional handle listed as http://twitter.com/cnil
- Omar bin Sultan Al Olama, Minister of State for Artificial Intelligence, Digital Economy and Remote Work Applications, official UAE Cabinet page. The official page form of the name is used.
- Sinéad McSweeney, Online Safety Commissioner, Coimisiún na Meán, official appointment statement dated 17 November 2026, institutional handle @CNaM_ie on the official homepage
- John Evans, Digital Services Commissioner, Coimisiún na Meán, named on the same official appointment statement
- Zhuang Rongwen (庄荣文), Director of the Cyberspace Administration of China and Director of the State Internet Information Office, official CAC signed article dated 2 November 2026

## Official pages that could not be retrieved live

Eighty-six official URLs were requested from this environment for the map. Fifty-two were retrieved. Thirty-four were not. A failure is not evidence that the page does not exist. Each URL below is retained and remains a scrape target for the body.

Timed out:

- https://www.esafety.gov.au/
- https://www.esafety.gov.au/newsroom
- https://www.esafety.gov.au/newsroom/media-releases
- https://www.esafety.gov.au/about-us/about-the-commissioner
- https://www.acma.gov.au/
- https://www.acma.gov.au/authority
- https://minister.infrastructure.gov.au/wells
- https://minister.infrastructure.gov.au/wells/media-releases

HTTP 403:

- https://www.ofcom.org.uk/
- https://www.ofcom.org.uk/about-ofcom/structure-and-leadership/ofcom-board
- https://www.ofcom.org.uk/about-ofcom/what-we-do/contact-us
- https://www.ofcom.org.uk/online-safety/illegal-and-harmful-content/intimate-image-abuse-takedown
- https://ico.org.uk/
- https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/childrens-information/childrens-code-guidance-and-resources/
- https://bills.parliament.uk/
- https://www.commerce.gov/about/leadership
- https://www.fcc.gov/about/leadership
- https://www.congress.gov/
- https://leginfo.legislature.ca.gov/
- https://sso.agc.gov.sg/
- https://www.meity.gov.in/
- https://www.meity.gov.in/ministry/our-team
- https://peraturan.bpk.go.id/
- https://www.komdigi.go.id/
- https://www.hellenicparliament.gr/nomothetiko-ergo/psifisthenta-nomoschedia?law_id=97e0885f-30fe-45f3-bbe9-b4de0151a84f
- https://uaelegislation.gov.ae/en/legislations/4506

The official Digital Duty of Care bill homepage on parlinfo.aph.gov.au also returned HTTP 403 in an earlier official check used by this repository. It remains a scrape target in `config/sources.yaml` and in the Australia parliament entry.

HTTP 429:

- https://commission.europa.eu/about/organisation/college-commissioners/henna-virkkunen_en

HTTP 404 (URL retained as a previously cited official address, pending a later check):

- https://www.gov.br/mcom/pt-br/acesso-a-informacao/perguntas-frequentes/o-ministerio-das-comunicacoes/quem-e-o-ministro-das

Connection or transport error:

- https://capitol.texas.gov/
- https://egazette.gov.in/
- https://www.msit.go.kr/
- https://www.planalto.gov.br/
- https://www.arcom.fr/nous-connaitre/notre-institution/gouvernance
- https://u.ae/en/information-and-services/social-affairs/Priority-groups/children/Childrens-digital-safety

The official Komdigi portal at https://portal.komdigi.go.id/ was retrieved. The www.komdigi.go.id address was the one that returned 403.

## Names and handles left unverified

The morning-desk roster was used only as a lead. The following roster names or titles were not copied into the map, because an official leadership page was not retrieved, or the retrieved official page did not name the person.

- Anika Wells, Julie Inman Grant and Nerida O'Loughlin (Australian ministerial and regulator pages timed out)
- Ofcom board or executive names from the roster, including Ian Cheshire, Melanie Dawes and Oliver Griffiths (official Ofcom pages returned 403)
- ICO leadership (official pages returned 403)
- Howard Lutnick, Brendan Carr and other US Commerce, FCC, NTIA or NIST roster leads (official leadership pages returned 403). The FCC is still listed as a body, with no spokesperson.
- MeitY team names, including Ashwini Vaishnaw (official MeitY pages returned 403)
- A Japanese Ministry of Internal Affairs and Communications minister (the official soumu.go.jp homepage was retrieved and did not name a minister in the text used for this map)
- A Brazilian Minister of Communications (the dedicated "who is the minister" URL returned 404, and the retrieved MCom homepage did not clearly name the minister)
- An Indonesian Komdigi minister (the official portal was retrieved and did not name a minister). A name was not inferred from a headline that used the office title only.
- Fahmi Fadzil (a name was not inferred from an MCMC photo-gallery slug)
- PDPC leadership (the official homepage was retrieved and did not name a commissioner)
- Arcom leadership (the official governance page could not be retrieved)
- Other MDDI political office holders named on the official holders page besides Josephine Teo, who is listed as the minister

The following roster handles were not copied, because no retrieved official page identified them. A handle was never inferred from a name pattern.

- @lisanandy (Lisa Nandy is listed, without a personal handle)
- @HennaVirkkunen (Henna Virkkunen is listed, without a personal handle)
- @OmarSAlolama (Omar bin Sultan Al Olama is listed, without a personal handle)
- @howardlutnick, @BrendanCarrFCC, @IMDAsg, @AnikaWells, @eSafetyOffice, @Ofcom, @MCMC_RASMI, @digital_jpn, @MIC_JAPAN, @kemkomdigi and @anatelgovbr

## Markets and bodies not invented

The following gaps were left explicit. No official URL was invented to fill them.

- Vietnam has two instruments in the register snapshot. No official government URL was sourced for this map, so no Vietnamese body or scraper was added.
- The register has state instruments for Arkansas, Florida, Maryland, Nebraska, Utah and Vermont. Those rows did not carry an official homepage in the snapshot used for this map, so no body entry was added.
- No official homepage for a Malaysian communications ministry was established, so only the Malaysian Communications and Multimedia Commission is listed.
- An official eSafety GOSRN release used as a monitoring fixture mentions Germany's federal network agency. No official homepage for that agency was retrieved for this map, so no German body was added.
- The India Online Gaming Authority and the Singapore Online Safety Commission are named in official register instruments. They are listed as bodies. No separate official homepage was invented for either of them. Their scrape targets point at the official parent statute or rules URL already cited in the register.

## Bodies by jurisdiction

United States: Federal Trade Commission, United States Congress, Federal Communications Commission, California Legislature, New York Governor, Texas Legislature, Minnesota Revisor of Statutes, Virginia Legislative Information System.

United Kingdom: Ofcom, Information Commissioner's Office, Department for Digital, Culture, Media and Sport, closed Department for Science, Innovation and Technology (no scrape targets), UK Parliament.

European Union: DG CONNECT, European AI Office, European Commission spokespersons service, EUR-Lex, Commission Directorate-General for Migration and Home Affairs.

Australia: eSafety Commissioner, Australian Communications and Media Authority, Minister for Communications, Australian Parliament (including the Digital Duty of Care bill homepage).

Singapore: Ministry of Digital Development and Information, Infocomm Media Development Authority, Personal Data Protection Commission, Online Safety Commission (statute citation only), Singapore Statutes Online.

India: Ministry of Electronics and Information Technology, Online Gaming Authority of India (named in official rules, no separate homepage), eGazette.

Malaysia: Malaysian Communications and Multimedia Commission, including the official press-release index.

Japan: Digital Agency, Ministry of Internal Affairs and Communications.

Korea: Korea Media and Communications Commission, Ministry of Science and ICT, National Assembly legislative opinion portal.

Indonesia: Ministry of Communication and Digital Affairs (official portal), Peraturan BPK.

Brazil: Ministry of Communications, ANPD, Anatel, Presidência da República (planalto.gov.br).

Canada: Canadian Heritage, Innovation, Science and Economic Development Canada, Parliament of Canada (including the official LEGISinfo page for Bill C-34).

Mexico: Diario Oficial de la Federación / SIDOF.

Turkey: mevzuat.gov.tr.

France: CNIL, Arcom.

Greece: Hellenic Parliament.

United Arab Emirates: UAE Cabinet, uaelegislation.gov.ae.

Ireland: Coimisiún na Meán.

China: Cyberspace Administration of China.

Each entry in the YAML records jurisdiction, body type, official name, official homepage where one was sourced, newsroom or media-release URL, bill or consultation board URL where one exists, key spokespersons with role and sourced official URL, fetch method and a retrieval note for this run.
