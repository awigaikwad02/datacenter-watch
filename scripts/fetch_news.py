#!/usr/bin/env python3
"""
The Rack Report: feed updater.

Pulls the Google News RSS searches and Google Alerts RSS feeds listed in
data/feeds.json, cleans and dedupes the headlines, tags each one with a
category, detects place names, and writes:

  data/news.json                the feed shown on index.html
  data/registry.json            permanent project registry (scripts/registry.py):
                                curated projects plus projects detected from
                                headlines, never trimmed
  projects/<id>/index.html      one static page per visible project
  sitemap.xml                   the six site pages plus the project pages
  data/status.json              a short report of the run
  data/archive/YYYY-MM.json     permanent monthly archive; headlines are only
                                ever appended, never trimmed or deleted
  data/archive/index.json       months available and item counts

The site covers the United States only: stories that are clearly about
another country are dropped, and every kept story is tagged with the U.S.
states it mentions. Headlines must be about data centers (see is_on_topic),
sources in data/feeds.json "blocked_sources" are dropped, and related
headlines are grouped with a shared cluster_id.

Run locally:  python scripts/fetch_news.py
Re-tag the existing files without fetching:  python scripts/fetch_news.py --no-fetch
Test offline against a saved RSS file, writing somewhere else:
  python scripts/fetch_news.py --sample scripts/sample_feed.xml --out /tmp/rack-test
GitHub Actions runs it on a schedule (see .github/workflows/update.yml).
"""

import argparse
import calendar
import shutil
import time
import hashlib
import html
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote_plus

import feedparser
import requests

from data_readme import readme

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
FEEDS_FILE = DATA / "feeds.json"
NEWS_FILE = DATA / "news.json"
STATUS_FILE = DATA / "status.json"
GAZ_FILE = Path(__file__).resolve().parent / "gazetteer.json"
ARCHIVE_DIR = DATA / "archive"
MONTH_RE = re.compile(r"^\d{4}-\d{2}$")

# How far back the hourly run accepts headlines from a feed and refills news.json from the archive.
NEWS_MAX_AGE_DAYS = 90
# data/news.json keeps 90 days when that fits in NEWS_MAX_BYTES, otherwise the last 30 days.
# There is no item cap; older headlines live in data/archive/ and the Newsroom loads them on demand.
NEWS_WINDOW_DAYS = (90, 30)
NEWS_MAX_BYTES = int(2.5 * 1024 * 1024)
# Exit code for "Google is rate limiting us: skip this cycle and try again next hour".
EXIT_BACKOFF = 75
# Capacity figures above this are grid-wide totals ("474 GW of requests"), not one project.
MAX_PROJECT_MW = 20000
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; TheRackReport/1.0; +https://therackreport.org)"}
TIMEOUT = 25
FETCH_TRIES = 3          # retry 429 and 5xx responses with exponential backoff
CLUSTER_DAYS = 5         # related headlines must be this close in time
CLUSTER_STRONG = 0.5     # title-word Jaccard that clusters on its own
CLUSTER_WEAK = 0.3       # Jaccard that clusters with a shared city/county, or a shared company and state

# ---------------------------------------------------------------------------
# Classification rules. Order matters: the first rule that matches a headline
# becomes its primary category. Every matching rule is also kept as a tag.
# ---------------------------------------------------------------------------
# Cancellations and blocks are checked before everything else, so "Amazon drops
# data center plan" is never read as an announcement. CANCEL_NOT catches the
# opposite case: a vote against a moratorium or ban is not a blocked project.
CANCEL_PAT = (
    r"\b(drops|dropped|withdraw|withdraws|withdrew|withdrawn|scraps|scrapped|cancels|cancell?ed|abandons|abandoned|"
    r"(?:pulls|pulled) (?:out|back|the plug|plans?|its|application|proposal|request)|rejects|rejected|"
    r"denies|denied|blocks|blocked|halts|halted|pauses|paused|votes? down|voted down|votes? against|"
    r"voted against|court rules against|rules against|(?:puts?|putting|placed?) a pause|"
    r"moratorium (?:passed|passes|approved|adopted|enacted|extended|imposed)|"
    r"(?:pass|passes|passed|approve|approves|approved|adopts|adopted|enacts|enacted|extends|extended|extending|"
    r"expands|expanded|imposes|imposed|issues|issued|signs|signed|finalizes|finalized|starts|started) "
    r"(?:a |an |the )?(?:[\w$-]+ ){0,4}(?:moratoriums?|pause))\b")
CANCEL_RE = re.compile(CANCEL_PAT, re.I)
# Not a cancellation: proposals and calls for one, or a vote against a restriction rather than a project.
CANCEL_HEDGE = re.compile(
    r"\b(calls? for|called for|considers?|considering|weighs?|weighing|to debate|debates?|would|could|should|"
    r"to vote|vote on whether|set to|seeks?|urges?|pushes? for|proposal to|proposes?|wants?|won['’]t)\b", re.I)
CANCEL_NOT = re.compile(
    r"\b(?:votes? down|voted down|rejects?|rejected|denies|denied|blocks?|blocked|drops?|dropped|withdraws?|withdrew|"
    r"withdrawn|halts?|halted|pauses?|paused|votes? against|voted against|scraps?|scrapped|cancels?|cancell?ed)"
    r" (?:[\w$’'.,-]+ ){0,6}?(?:moratoriums?|bans?|freezes?|pauses?|restrictions?|ordinances?|regulations?|rules|guardrails|"
    r"limits|lawsuits?|suits?|challenges?|appeals?|petitions?|referendums?|opposition|tax(?:es)?|bills?|plan to|plan that|"
    r"meetings?|task force|study|studies|committee|hearings?|sessions?|votes?)\b|\b(?:blocks?|blocked) \w+ from\b|\b(?:rejects?|rejected) \$\d|"
    r"\b(?:votes?|voted|rules?|ruled) against (?:requiring|forcing|making|letting|allowing)\b|"
    r"\b(?:shares|stocks?|prices?|demand|revenue|profits?|levels?|ratings?|costs?|rates?) (?:drops?|dropped)\b", re.I)
CANCELLED = "Cancelled / Blocked"


def is_cancelled(title):
    """True when the headline reports a project cancelled or blocked (CANCEL_RE), unless it only
    proposes one (CANCEL_HEDGE) or is about a restriction, vote or share price instead
    (CANCEL_NOT).
    """
    return bool(CANCEL_RE.search(title)) and not CANCEL_HEDGE.search(title) and not CANCEL_NOT.search(title)


# Topic rules, checked in this order after Cancelled / Blocked; the first match wins and every
# match is kept as a tag. Rules near the top describe what is happening to a project; the later
# ones describe what the story is about (markets, the economy, the environment, a community, a
# government). Analysis / Opinion is a fallback for explainers, studies and columns. A headline that
# matches nothing is General; the health check keeps General under 10% and Policy / Permits under 20%.
CATEGORY_RULES = [
    # "Meta announces $10B data center in Richland Parish", "Massive data center could be coming to
    # Upstate New York town", "Potential data center eyed for former mill site"
    ("New Announcement",
     r"\b(announc\w*|plans?|planned|propos\w*|unveil\w*|to build|will build|eyes|eyeing|eyed|"
     r"selects?|chooses?|picks?|lands|secures?|launch\w*|new campus|mega|"
     r"(?:could be|is|are) coming|coming to|headed to|could be built|would be built|to be built|"
     r"potential|possible|would bring|wants to build|looks to build|to develop|would become)\b"),
    # "AWS breaks ground in Richmond County", "Data center being built near Abilene tops out"
    ("Construction",
     r"\b(break(s|ing)? ground|groundbreaking|ground-breaking|under construction|construction|"
     r"topping out|tops out|contractor|crews|build-?out|begins? building|starts? building|being built|"
     r"rising)\b"),
    # "QTS expands Fayetteville campus with second phase"
    ("Expansion",
     r"\b(expands?|expanding|expanded|expansion|adds|second phase|phase (2|ii|two)|"
     r"additional buildings?|more buildings)\b"),
    # "Developer buys 1,200 acres for data center campus", "Broker markets LeRay land for data center"
    ("Land Acquisition",
     r"(\b\d[\d,]*[- ]acres?\b|\bacres\b|\bparcels?\b|\bland (purchase|deal|sale|buy)\b|\b(buys?|bought|purchases?|"
     r"purchased|acquires?|acquired|markets|sells?|sold|being sold) (\w+ ){0,2}(land|site|property|acreage|farmland)\b|"
     r"\bsite acquisition\b)"),
    # "Google opens Mesa data center", "Outage at Ashburn data center", "Job fair for new data center"
    ("Operations",
     r"\b(opens|opened|officially open|now open|grand opening|goes live|went live|comes online|now online|"
     r"online|commissioned|energized|up and running|is live|now live|(?:is|are|now|fully) operational|activates|activated|"
     r"outages?|downtime|hiring|job fair|jobs fair|ribbon)\b"),
    # "Applied Digital shares jump on CoreWeave lease", "Equinix earnings beat", "Is the AI data center
    # boom a bubble?" Before Deals, so a stock story with a dollar figure is a market story.
    ("Markets / Earnings",
     r"\b(stocks?|shares (?:jump|jumped|rise|rose|fall|fell|drop|dropped|slide|slid|surge|surged|climb|climbed|sink|sank|"
     r"tumble|tumbled|soar|soared|gain|gained|pop|popped)|shares of|shareholders|earnings|quarterly|q[1-4]|(?<!tax )(?<!lost )revenue|profits?|"
     r"wall street|(?<!Wells Fargo )analysts?|(?:ai|tech|market|data center) bubble|bubble (?:fears?|talk|bursts?)|investors? (worry|fear|bet|cheer)|nasdaq|s&p|dow|market cap|"
     r"net absorption|vacancy|backlog|outlook|forecast)\b"),
    # "Blackstone buys AirTrunk", "$2.4B financing for Abilene campus", "Data center REIT signs lease"
    ("Deals / Investment",
     r"\b(acqui\w*|merger|buys?|bought|purchase\w*|invest\w*|funding|raises?|raised|financing|financed|loan|debt|"
     r"bonds?|reits?|lease[sd]?|leasing|joint venture|partnership|(?<!at )stake|ipo|valuation|billion|million|\$\s?\d|"
     r"m&a|sells?|sold|sale)\b"),
    # "Data center could bring 300 jobs", "Tax revenue from data centers tops $1B in Loudoun",
    # "Data center boom pushes up land prices", "Louisiana's data center surge tests economic growth"
    ("Economy / Jobs",
     r"\b(jobs?|workers?|workforce|employment|employees|hires|economic\w*|economy|tax (revenue|base|dollars|bill)|"
     r"property tax\w*|revenue for|real estate|land (prices|values)|property values|home prices|housing|rents?|"
     r"windfall|payroll|wages?|training|apprentice\w*|small business\w*|tourism)\b"),
    # "Data center water use worries Tucson", "Neighbors say data center noise is unbearable",
    # "Report: data center diesel generators threaten air quality"
    ("Environment",
     r"\b(water|aquifers?|wells?|drought|wastewater|noise|noisy|hum|decibels?|air quality|air permit|pollut\w*|"
     r"emissions?|carbon|climate|environment\w*|wildlife|wetlands?|national parks?|diesel|generators?|"
     r"sustainab\w*|heat island|light pollution|health|pfas)\b"),
    # "Dominion seeks 5 GW for data centers", "Data centers drive up electric bills", "SMRs for data centers"
    ("Power / Utility",
     r"\b(power|grid|utilit(y|ies)|utility bills?|electric\w*|electricity rates?|energy|megawatts?|gigawatts?|\d+\s?[MG]W|"
     r"nuclear|(?:micro)?reactors?|smrs?|natural gas|gas plants?|gas-fired|power plants?|gas turbines?|turbines?|solar|wind|"
     r"batter(y|ies)|transmission|substations?|interconnection|demand|load|rates?|ratepayers?|blackout|cooling|coal)\b"),
    # "Chester residents protest data center", "Data center backlash grows in rural Georgia",
    # "Neighbors push back on Project Sail". Before Policy, so a community fight is not counted as policy.
    ("Community",
     r"\b(residents?|neighbou?rs?|neighbou?rhoods?|locals|backlash|push(es|ing|ed)? back|pushback|protest\w*|"
     r"opponents?|oppos\w*|opposition|fight\w*|fought|battle\w*|critics?|concerns?|worr\w*|petitions?|"
     r"anti-data|outcry|uproar|angry|anger|frustrat\w*|speak(s|ing)? out|spoke out|resistance|grassroots|"
     r"community|communities|town hall|open house|(public|community) (input|forum|meeting)s?|controvers\w*|"
     r"sparks?|draws?|divided|divides|divisive|defeat\w*|said no|says no|no data centers?|quality of life|farmers?|rural)\b"),
    # "Nvidia GPUs headed to Stargate site", "OpenAI's compute plans", "Hyperscalers race for AI capacity".
    # After Community: "AI" is in so many headlines that a fight over an "AI data center" is a community story.
    ("AI Infrastructure",
     r"\b(ai|a\.i\.|artificial intelligence|gpus?|nvidia|compute|computing|ai factor(y|ies)|supercomputers?|"
     r"hyperscal\w*|openai|microsoft|amazon|aws|google|alphabet|meta|oracle|xai|anthropic|stargate|crusoe|coreweave|cloud|"
     r"big tech|neoclouds?|chips?)\b"),
    # "Will a data center backlash help Talarico turn Texas blue?", "Candidates split on data centers"
    # Elections and party politics, before Policy / Permits so that topic stays about permits and rules.
    ("Politics",
     r"\b(elections?|electoral|midterms?|primary|primaries|candidates?|campaign\w*|voters|ballots?|"
     r"democrats?|republicans?|gop|g\.o\.p\.|dems?|partisan|bipartisan|trump|biden|harris|vance|white house|"
     r"congress\w*|politic\w*|polls|polling|governor['’]s race|races? for|runs? for|running for|seat)\b"),
    # "Planning commission recommends rezoning", "Indiana lawmakers file data center bill",
    # "County approves data center rules", "Judge sides with county in data center lawsuit"
    ("Policy / Permits",
     r"\b(zoning|rezon(e|es|ed|ing)|moratoriums?|ordinances?|permits?|permitting|planning (commission|board)|"
     r"board of supervisors|city council|county commission(ers?)?|public hearings?|hearings?|lawsuits?|referendums?|"
     r"tax (breaks?|incentives?|exemptions?|credits?)|incentives?|abatements?|approv\w*|green-?lights?|"
     r"bans?|banned|banning|pauses?|regulat\w*|regs|rules|restrictions?|crackdown|lawmakers?|legislat\w*|legislature|"
     r"senate|senators?|assembly|house bill|bills?|governor|gov|executive order|polic(?:y|ies)|"
     r"votes?|council\w*|commissioners?|supervisors|mayors?|officials|ndas?|transparency|"
     r"judges?|courts?|sues?|sued|appeals?|legal|federal|feds|epa|ferc|puc|psc|task force|"
     r"local control|agreements?|annex\w*|tif|pilot)\b"),
    # Fallback before General: explainers, studies, reports, columns and podcasts.
    # "What to know about the data center boom", "Opinion: Data centers are not the enemy",
    # "Report: Fairfax County leads state in data centers near homes"
    ("Analysis / Opinion",
     r"\b(opinion|op-ed|editorial|column|commentary|letters?|viewpoint|perspective|guest|"
     r"what (to|you|we) (know|need)|here['’]s|explain\w*|explainer|faq|q&a|how many|why|what|how|"
     r"study|studies|reports?|survey|analysis|research|data shows|finds|index|ranking|map|"
     r"podcast|video|watch|listen|interview|newsletter|the daily|weekly|roundup|recap|boom|race|rush|"
     r"growth|surge|explosion|future|era|age of)\b"),
]
COMPILED_RULES = [(name, re.compile(pat, re.I)) for name, pat in CATEGORY_RULES]

# Project detection: headline must be about a site and describe a stage.
PROJECT_WORDS = re.compile(r"\b(data\s?cent(er|re)s?|campus|hyperscale|facility|facilities)\b", re.I)
# Stage words, checked in this order; the first one that counts gives the headline's stage signal.
STATUS_RULES = [
    # "AWS breaks ground on Richmond County campus", "First QTS buildings near completion"
    ("Under construction",
     re.compile(r"\b(break(s|ing)? ground|groundbreaking|ground-breaking|under construction|"
                r"construction (begins|starts|underway|begun|started|kicks off)|begins? construction|"
                r"starts? construction|topping out|tops out|crews|near(s|ing)? completion)\b", re.I)),
    # "Google opens Mesa data center", "Meta's Kansas City campus comes online",
    # "Crusoe announces flagship Abilene data center is live", "OpenAI activates Stargate data center",
    # "Edged launches 26MW Kansas City data center"
    ("Operational",
     re.compile(r"\b(opens|opened|officially open|now open|grand opening|goes live|went live|is live|are live|now live|"
                r"comes online|came online|goes online|now online|(?:is|are|now|fully|becomes?|became|be) operational|in operation|up and running|"
                r"activates|activated|begins operations|starts operations|powers on|powered on|"
                r"launch(?:es|ed) (?:[\w$-]+ ){0,3}?(?:\d[\d,.]*\s?MW|data cent)|"
                r"completes?|completed|completion|commissioned|energized|ribbon)\b", re.I)),
    # "QTS expands Fayetteville campus with second phase"
    ("Expansion",
     re.compile(r"\b(expands?|expanding|expanded|expansion|adds|second phase|phase (2|ii|two)|"
                r"additional buildings?)\b", re.I)),
    # "Amazon plans $10B campus in Louisa County", "Board approves Project Sail rezoning"
    ("Announced",
     re.compile(r"\b(announc\w*|plans?|planned|planning|propos\w*|unveil\w*|to build|will build|eyes|eyeing|"
                r"selects?|chooses?|picks?|lands|secures?|approv\w*|acquires? (land|site)|"
                r"buys? (land|site|acres)|\d[\d,]* acres)\b", re.I)),
]
# A stage word does not count when it is still to come (fixed after the status audit,
# scripts/status_audit.py): "could break ground this summer", "plans to break ground",
# "on track to be completed by 2025", "$2B to complete Utah campus", "push xAI to complete",
# "will be operational in 2027", "jobs expectations when AI facility opens".
# "to build" and "plans" are themselves Announced words and "plans to expand" is an expansion
# announcement, so this test is not applied to Announced or Expansion.
STAGE_FUTURE = re.compile(r"\b(to|will|would|could|may|might|plans? to|planning to|aims? to|hopes? to|seeks? to|"
                          r"wants? to|set to|slated to|expected to|scheduled to|poised to|on track to|"
                          r"before|until|unless|if|when|once)\b\W*(\w+\W+){0,3}$", re.I)
# An opening or completion about something other than the data center or its construction:
# "Crusoe opens second Tulsa plant", "Texas solar farm opens to power Google data centers",
# "Flexential completes Atlanta data center purchase", "Amazon completes its application".
OPENS_OTHER = re.compile(r"\b(plant|factory|manufacturing|hub|solar|farm|wind|substation|office|headquarters|"
                         r"warehouse|store|school|training|recycling|pipeline|mine)s?\b", re.I)
COMPLETES_OTHER = re.compile(r"^\W*(?:[\w$.,'’-]+\W+){0,4}?(application|purchase|acquisition|sale|deal|financing|"
                             r"transaction|merger|review|study|annexation|agreement|rezoning|filing|survey|"
                             r"funding|offering|ipo|loan)\b", re.I)

# Organisations. Patterns are case-sensitive whole words. A name that is also a common word only
# matches with a qualifying next word (a "guard"): "Stream Data Centers" but not "a stream of",
# "Prime Data Centers" but not "prime location", "Galaxy Digital" but not "Galaxy", "Edged Data
# Centers" but not "edged out". Organisations fall in five fields on every headline:
#   companies   operators and developers: who owns or runs the data center (drives project matching)
#   investors   who finances or owns the operator ("Blackstone to buy AirTrunk")
#   builders    contractors, engineers and architects ("Mortenson breaks ground on ...")
#   suppliers   equipment and chip makers ("Vertiv to supply cooling for ...")
#   utilities   power companies and grid operators
# Only operators create projects; a headline naming only builders or suppliers can attach to a
# project that already exists at the same place (scripts/registry.py).
COMPANIES = [
    # Hyperscalers and AI labs. "Meta breaks ground on Hyperion in Richland Parish"
    ("Google", r"Google|Alphabet"),
    ("Microsoft", r"Microsoft|Azure|Fairwater"),
    ("Meta", r"Meta|Facebook|Hyperion|Prometheus(?! Hyperscale)"),
    ("Amazon", r"Amazon Web Services|Amazon|AWS|Project Rainier"),
    ("Oracle", r"Oracle|OCI"),
    ("OpenAI", r"OpenAI|ChatGPT"),
    ("xAI", r"xAI|Colossus"),
    ("Anthropic", r"Anthropic"),
    ("Apple", r"Apple"),
    ("IBM", r"IBM"),
    # GPU clouds and AI compute. "Nebius buys 79 acres in Birmingham"
    ("CoreWeave", r"CoreWeave"),
    ("Crusoe", r"Crusoe"),
    # Before the GPU clouds: in "Patmos announces Nebius as first tenant" the site is Patmos's.
    ("Patmos", r"Patmos"),
    ("Lambda", r"Lambda(?= (Labs|Inc|Cloud|AI|data|Data|leases|will|and|plans|Plans|files|Files|to|To|breaks|Breaks|opens|Opens|announces|Announces|launches|Launches|expands|Expands|tops|Tops|acquires|Acquires|secures|Secures|signs|Signs|raises|Raises|withdraws|Withdraws|completes|Completes|unveils|Unveils|in|wins|Wins|buys|Buys|sues|Sues|accuses|Accuses|fails|Fails|eyes|Eyes|pulls|Pulls|details|Details|planning|Planning|looks|Looks|loses|Loses|borrows|Borrows|deploys|Deploys)\b)|Lambda['’]s|(?<=operator )Lambda"),
    ("Nebius", r"Nebius"),
    ("Nscale", r"Nscale"),
    ("Fluidstack", r"Fluidstack|FluidStack"),
    ("Together AI", r"Together AI"),
    ("Poolside", r"Poolside"),
    ("Cerebras", r"Cerebras"),
    # Colocation and wholesale developers. "QTS files plans for Fayetteville campus"
    ("QTS", r"QTS"),
    ("Equinix", r"Equinix"),
    ("Digital Realty", r"Digital Realty"),
    ("Switch", r"Switch(?= (Inc|data cent|campus|Citadel|plans|Plans|files|Files|to|To|breaks|Breaks|opens|Opens|announces|Announces|launches|Launches|expands|Expands|tops|Tops|acquires|Acquires|secures|Secures|signs|Signs|raises|Raises|withdraws|Withdraws|completes|Completes|unveils|Unveils|in|wins|Wins|buys|Buys|sues|Sues|accuses|Accuses|fails|Fails|eyes|Eyes|pulls|Pulls|details|Details|planning|Planning|looks|Looks|loses|Loses|borrows|Borrows|deploys|Deploys)\b)|Switch['’]s|(?<=accuses )Switch|(?<=against )Switch|(?<=do )Switch"),
    ("CyrusOne", r"CyrusOne"),
    ("Compass Datacenters", r"Compass Data ?[Cc]enters"),
    ("Vantage", r"Vantage"),
    ("Aligned", r"Aligned Data Centers|Aligned(?= (Data|data))"),
    ("STACK", r"STACK Infrastructure|STACK|Stack(?= (Infrastructure|data cent|plans|Plans|files|Files|to|To|breaks|Breaks|opens|Opens|announces|Announces|launches|Launches|expands|Expands|tops|Tops|acquires|Acquires|secures|Secures|signs|Signs|raises|Raises|withdraws|Withdraws|completes|Completes|unveils|Unveils|in|wins|Wins|buys|Buys|sues|Sues|accuses|Accuses|fails|Fails|eyes|Eyes|pulls|Pulls|details|Details|planning|Planning|looks|Looks|loses|Loses|borrows|Borrows|deploys|Deploys)\b)"),
    ("EdgeCore", r"EdgeCore"),
    ("NTT", r"NTT"),
    ("Iron Mountain", r"Iron Mountain"),
    ("DataBank", r"DataBank"),
    ("Flexential", r"Flexential"),
    ("CoreSite", r"CoreSite"),
    ("Cologix", r"Cologix"),
    ("Centersquare", r"Centersquare|CenterSquare"),
    ("TierPoint", r"TierPoint"),
    ("H5 Data Centers", r"H5 Data Centers|H5(?= data cent)"),
    ("Element Critical", r"Element Critical"),
    ("1547 Critical Systems", r"1547 Critical Systems|1547 Realty|1547(?= (data|Data))"),
    ("DartPoints", r"DartPoints"),
    ("Evocative", r"Evocative"),
    ("Ascent", r"Ascent(?= (Data|data|Mission|Group)\b)"),
    ("Edged", r"Edged(?= (Data|data|US|Energy|plans|Plans|files|Files|to|To|breaks|Breaks|opens|Opens|announces|Announces|launches|Launches|expands|Expands|tops|Tops|acquires|Acquires|secures|Secures|signs|Signs|raises|Raises|withdraws|Withdraws|completes|Completes|unveils|Unveils|in|wins|Wins|buys|Buys|sues|Sues|accuses|Accuses|fails|Fails|eyes|Eyes|pulls|Pulls|details|Details|planning|Planning|looks|Looks|loses|Loses|borrows|Borrows|deploys|Deploys)\b)|Edged['’]s|(?<=for )Edged|EdgedEnergy"),
    ("Yondr", r"Yondr"),
    ("Corscale", r"Corscale"),
    ("Lincoln Rackhouse", r"Lincoln Rackhouse"),
    ("Chirisa", r"Chirisa"),
    ("Rowan Digital", r"Rowan Digital( Infrastructure)?"),
    ("Provident Data Centers", r"Provident Data Centers|Provident(?= (data|Data))"),
    ("Quantum Loophole", r"Quantum Loophole"),
    ("Prometheus Hyperscale", r"Prometheus Hyperscale"),
    ("Wyoming Hyperscale", r"Wyoming Hyperscale"),
    ("Lancium", r"Lancium"),
    ("Cloudburst", r"Cloudburst"),
    ("Digital Edge", r"Digital Edge"),
    # Added 2026-11-01 from data/operator_candidates.json (3+ headlines each) and by request.
    ("Beale Infrastructure", r"Beale Infrastructure|Beale(?= (moving|plans|withdraws|hopes|files|to|unveils|seeks)\b)"),
    ("DC Blox", r"DC Blox|DC BLOX"),
    ("Metrobloks", r"Metrobloks"),
    ("EdgeConneX", r"EdgeConneX"),
    ("Prologis", r"Prologis"),
    ("Oppidan", r"Oppidan"),
    ("TECfusions", r"TECfusions"),
    ("Karis", r"Karis Critical|Karis(?= (pitches|details|plans|data|Data)\b)"),
    ("RadiusDC", r"RadiusDC"),
    ("CleanArc", r"CleanArc"),
    ("Fleet Data Centers", r"Fleet Data Centers"),
    ("Blueprint", r"Blueprint Data Centers|Blueprint Projects"),
    ("Colovore", r"Colovore"),
    ("NorthMark", r"NorthMark"),
    ("Bit Digital", r"Bit Digital"),
    ("Digi Power X", r"Digi Power X"),
    ("Sequitor Edge", r"Sequitor Edge|Sequitor"),
    ("Atmosphere Data Centers", r"Atmosphere Data Centers"),
    ("Joule", r"Joule(?= (Capital|Partners|Power|and|,)\b)|Joule,"),
    ("Diode Ventures", r"Diode Ventures|Diode(?= (project|gets|plans|data|Data)\b)|(?<=bn )Diode"),
    ("Red Wolf", r"Red Wolf(?= (data|Data|campus|Campus|project|Project))"),
    ("Hunt Midwest", r"Hunt Midwest"),
    ("Applied Digital", r"Applied Digital"),
    ("Core Scientific", r"Core Scientific"),
    # Bitcoin miners turning sites into AI data centers. "TeraWulf to hold meeting on Lansing project"
    ("IREN", r"IREN|Iris Energy"),
    ("Cipher Mining", r"Cipher Mining|Cipher Digital|Cipher(?= (to|plans|signs|data|Data)\b)"),
    ("TeraWulf", r"TeraWulf"),
    ("Hut 8", r"Hut 8"),
    ("Galaxy Digital", r"Galaxy Digital|Galaxy(?=['’]s Helios| (plans|Plans|files|Files|to|To|breaks|Breaks|opens|Opens|announces|Announces|launches|Launches|expands|Expands|tops|Tops|acquires|Acquires|secures|Secures|signs|Signs|raises|Raises|withdraws|Withdraws|completes|Completes|unveils|Unveils|in|wins|Wins|buys|Buys|sues|Sues|accuses|Accuses|fails|Fails|eyes|Eyes|pulls|Pulls|details|Details|planning|Planning|looks|Looks|loses|Loses|borrows|Borrows|deploys|Deploys)\b)"),
    ("Riot Platforms", r"Riot Platforms|Riot(?= (Blockchain|to|plans)\b)"),
    ("MARA", r"MARA Holdings|MARA|Marathon Digital"),
    ("Bitdeer", r"Bitdeer"),
    ("CleanSpark", r"CleanSpark"),
    ("Soluna", r"Soluna"),
    # Energy-first and land developers. "Fermi America signs gas deal for Project Matador"
    ("Fermi America", r"Fermi America|Fermi(?! 2| nuclear| plant)|Project Matador"),
    ("Related Digital", r"Related Digital"),
    ("Tallgrass", r"Tallgrass"),
    ("Intersect Power", r"Intersect Power"),
    ("Tract", r"(?<=with )Tract|Tract(?=(['’]s| (Inc|Capital|data|Data|proposes|Proposes|campus|Campus|park|Park|lawsuit|plans|Plans|files|Files|to|To|breaks|Breaks|opens|Opens|announces|Announces|launches|Launches|expands|Expands|tops|Tops|acquires|Acquires|secures|Secures|signs|Signs|raises|Raises|withdraws|Withdraws|completes|Completes|unveils|Unveils|in|wins|Wins|buys|Buys|sues|Sues|accuses|Accuses|fails|Fails|eyes|Eyes|pulls|Pulls|details|Details|planning|Planning|looks|Looks|loses|Loses|borrows|Borrows|deploys|Deploys)\b))"),
    ("Hillwood", r"Hillwood"),
    ("PowerHouse", r"PowerHouse Data Centers|PowerHouse"),
    ("Sabey", r"Sabey Data Centers|Sabey"),
    ("T5", r"T5 Data Centers|T5"),
    ("Stream", r"Stream Data Centers|Stream Realty|Stream(?= (data|Data|plans|Plans|files|Files|to|To|breaks|Breaks|opens|Opens|announces|Announces|launches|Launches|expands|Expands|tops|Tops|acquires|Acquires|secures|Secures|signs|Signs|raises|Raises|withdraws|Withdraws|completes|Completes|unveils|Unveils|in|wins|Wins|buys|Buys|sues|Sues|accuses|Accuses|fails|Fails|eyes|Eyes|pulls|Pulls|details|Details|planning|Planning|looks|Looks|loses|Loses|borrows|Borrows|deploys|Deploys)\b)|(?<=serve )Stream"),
    ("Prime Data Centers", r"Prime Data Centers|Prime(?= (plans|Plans|files|Files|to|To|breaks|Breaks|opens|Opens|announces|Announces|launches|Launches|expands|Expands|tops|Tops|acquires|Acquires|secures|Secures|signs|Signs|raises|Raises|withdraws|Withdraws|completes|Completes|unveils|Unveils|in|wins|Wins|buys|Buys|sues|Sues|accuses|Accuses|fails|Fails|eyes|Eyes|pulls|Pulls|details|Details|planning|Planning|looks|Looks|loses|Loses|borrows|Borrows|deploys|Deploys)\b)"),
    ("Skybox", r"Skybox Datacenters|Skybox Data Centers|Skybox"),
    ("Novva", r"Novva Data Centers|Novva"),
]
# Named in data center headlines but never an operator here: context only, so a headline such as
# "De Soto OKs $3.1B data center project near new Panasonic plant" does not credit Panasonic.
CONTEXT_ONLY = {"Panasonic"}
# Code names that stand for several operators.
ALIASES = [("Stargate", ["OpenAI", "Oracle"])]
COMPANY_RULES = [(name, re.compile(r"(?<![\w-])(" + pat + r")(?![\w-])")) for name, pat in COMPANIES]
COMPANY_RULES += [(names, re.compile(r"(?<![\w-])" + a + r"(?![\w-])")) for a, names in ALIASES]
COMPANY_ORDER = {name: i for i, (name, _) in enumerate(COMPANIES)}

# Investors. "Blackstone's QTS ...", "DigitalBridge and SoftBank back Vantage"
INVESTORS = [
    ("Blackstone", r"Blackstone"),
    ("Brookfield", r"Brookfield(?! (County|Township|Zoo|Wisconsin|Illinois|Connecticut))"),
    ("KKR", r"KKR"),
    ("DigitalBridge", r"DigitalBridge"),
    ("Blue Owl", r"Blue Owl"),
    ("Macquarie", r"Macquarie"),
    ("BlackRock", r"BlackRock"),
    ("GIP", r"Global Infrastructure Partners|GIP"),
    ("Apollo", r"Apollo(?= (Global|Management|Funds|-backed|-managed|in talks|plans|Plans|files|Files|to|To|breaks|Breaks|opens|Opens|announces|Announces|launches|Launches|expands|Expands|tops|Tops|acquires|Acquires|secures|Secures|signs|Signs|raises|Raises|withdraws|Withdraws|completes|Completes|unveils|Unveils|in|wins|Wins|buys|Buys|sues|Sues|accuses|Accuses|fails|Fails|eyes|Eyes|pulls|Pulls|details|Details|planning|Planning|looks|Looks|loses|Loses|borrows|Borrows|deploys|Deploys)\b)|Apollo['’]s|(?<=by )Apollo|(?<=firm )Apollo"),
    ("Carlyle", r"Carlyle"),
    ("Stonepeak", r"Stonepeak"),
    ("Energy Capital Partners", r"Energy Capital Partners|ECP(?= (to|and|buys|acquires)\b)"),
    ("MGX", r"MGX"),
    ("SoftBank", r"SoftBank|Stargate"),
]
# Builders: general contractors, engineers and architects. "Mortenson breaks ground on ..."
BUILDERS = [
    ("Turner Construction", r"Turner Construction|Turner(?= (to build|builds|breaks ground|selected)\b)"),
    ("DPR Construction", r"DPR Construction|DPR"),
    ("Holder Construction", r"Holder Construction"),
    ("HITT", r"HITT"),
    ("Mortenson", r"Mortenson"),
    ("Clayco", r"Clayco"),
    ("Hensel Phelps", r"Hensel Phelps"),
    ("JE Dunn", r"JE Dunn|J\.E\. Dunn"),
    ("Whiting-Turner", r"Whiting-Turner"),
    ("Brasfield & Gorrie", r"Brasfield & Gorrie|Brasfield and Gorrie"),
    ("Gilbane", r"Gilbane"),
    ("Suffolk Construction", r"Suffolk Construction"),
    ("Fortis Construction", r"Fortis Construction"),
    ("Layton Construction", r"Layton Construction"),
    ("Balfour Beatty", r"Balfour Beatty"),
    ("Skanska", r"Skanska"),
    ("Fluor", r"Fluor"),
    ("Bechtel", r"Bechtel"),
    ("Kiewit", r"Kiewit"),
    ("Rosendin", r"Rosendin"),
    ("Burns & McDonnell", r"Burns & McDonnell|Burns and McDonnell"),
    ("Black & Veatch", r"Black & Veatch|Black and Veatch"),
    ("Jacobs", r"Jacobs Engineering|Jacobs Solutions|Jacobs(?= (to design|wins|selected)\b)|(?<=with )Jacobs|(?<=taps )Jacobs|(?<=hires )Jacobs"),
    ("AECOM", r"AECOM"),
    ("HDR", r"HDR(?= (Inc|Engineering|to|wins)\b)"),
    ("Corgan", r"Corgan"),
    ("Gensler", r"Gensler"),
    ("Page Southerland Page", r"Page Southerland Page|Page(?= (architects|Architects)\b)"),
    ("Syska Hennessy", r"Syska Hennessy|Syska"),
    ("kW Mission Critical", r"kW Mission Critical( Engineering)?"),
]
# Suppliers: power, cooling, generators and chips. "Vertiv shares jump on data center orders"
SUPPLIERS = [
    ("Vertiv", r"Vertiv"),
    ("Schneider Electric", r"Schneider Electric|Schneider(?= (to|and)\b)"),
    ("Eaton", r"Eaton(?! (County|Township|Rapids|Park))"),
    ("ABB", r"ABB"),
    ("Siemens", r"Siemens Energy|Siemens"),
    ("Caterpillar", r"Caterpillar"),
    ("Cummins", r"Cummins"),
    ("Rolls-Royce", r"Rolls-Royce"),
    ("GE Vernova", r"GE Vernova"),
    ("Bloom Energy", r"Bloom Energy|Bloom(?= (fuel cells|to supply)\b)"),
    ("Honeywell", r"Honeywell"),
    ("Johnson Controls", r"Johnson Controls"),
    ("Trane", r"Trane Technologies|Trane"),
    ("Carrier", r"Carrier Global|Carrier['’]s|Carrier(?= (and|Corp|Corporation|plans|Plans|files|Files|to|To|breaks|Breaks|opens|Opens|announces|Announces|launches|Launches|expands|Expands|tops|Tops|acquires|Acquires|secures|Secures|signs|Signs|raises|Raises|withdraws|Withdraws|completes|Completes|unveils|Unveils|in|wins|Wins|buys|Buys|sues|Sues|accuses|Accuses|fails|Fails|eyes|Eyes|pulls|Pulls|details|Details|planning|Planning|looks|Looks|loses|Loses|borrows|Borrows|deploys|Deploys)\b)"),
    ("Daikin", r"Daikin"),
    ("Nvidia", r"Nvidia|NVIDIA"),
    ("AMD", r"AMD"),
    ("Supermicro", r"Supermicro|Super Micro"),
    ("Dell", r"Dell Technologies|Dell(?! (Rapids|City))"),
    ("HPE", r"Hewlett Packard Enterprise|HPE"),
]


def _org_rules(pairs):
    """Compile (name, pattern) pairs into whole-word, case-sensitive regexes."""
    return [(name, re.compile(r"(?<![\w-])(" + pat + r")(?![\w-])")) for name, pat in pairs]


INVESTOR_RULES, BUILDER_RULES, SUPPLIER_RULES = _org_rules(INVESTORS), _org_rules(BUILDERS), _org_rules(SUPPLIERS)

# Utilities and grid operators, written to a separate "utilities" field.
# "Entergy files for gas plants to serve Meta", "ERCOT warns of data center load growth"
UTILITIES = [
    ("Entergy", r"Entergy"),
    ("Dominion Energy", r"Dominion Energy|Dominion"),
    ("Georgia Power", r"Georgia Power"),
    ("Southern Company", r"Southern Company|Southern Co\."),
    ("Duke Energy", r"Duke Energy|Duke's"),
    ("AEP", r"AEP|American Electric Power"),
    ("PSO", r"Public Service Company of Oklahoma|PSO"),
    ("SWEPCO", r"SWEPCO|Southwestern Electric Power"),
    ("Xcel Energy", r"Xcel Energy|Xcel"),
    ("Oncor", r"Oncor"),
    ("CenterPoint", r"CenterPoint Energy|CenterPoint"),
    ("PG&E", r"PG&E|Pacific Gas and Electric"),
    ("APS", r"APS|Arizona Public Service"),
    ("SRP", r"SRP|Salt River Project"),
    ("Tucson Electric Power", r"Tucson Electric Power|Tucson Electric|TEP"),
    ("NV Energy", r"NV Energy"),
    ("El Paso Electric", r"El Paso Electric"),
    ("Ameren", r"Ameren"),
    ("Evergy", r"Evergy"),
    ("OG&E", r"OG&E|Oklahoma Gas and Electric|Oklahoma Gas & Electric"),
    ("FirstEnergy", r"FirstEnergy"),
    ("PPL", r"PPL Electric|PPL"),
    ("Exelon", r"Exelon"),
    ("ComEd", r"ComEd|Commonwealth Edison"),
    ("Pepco", r"Pepco"),
    ("Consumers Energy", r"Consumers Energy"),
    ("DTE Energy", r"DTE Energy|DTE"),
    ("Alliant Energy", r"Alliant Energy|Alliant"),
    ("MidAmerican Energy", r"MidAmerican Energy|MidAmerican"),
    ("Portland General Electric", r"Portland General Electric|Portland General"),
    ("PacifiCorp", r"PacifiCorp|Rocky Mountain Power"),
    ("Idaho Power", r"Idaho Power"),
    ("Santee Cooper", r"Santee Cooper"),
    ("CPS Energy", r"CPS Energy"),
    ("Austin Energy", r"Austin Energy"),
    ("LG&E", r"LG&E|LG&E and KU|Louisville Gas and Electric"),
    ("LCRA", r"LCRA|Lower Colorado River Authority"),
    ("TVA", r"TVA|Tennessee Valley Authority"),
    ("PJM", r"PJM"),
    ("ERCOT", r"ERCOT"),
    ("MISO", r"MISO"),
]
UTILITY_RULES = _org_rules(UTILITIES)

# A headline is on topic when it names data centers, or a tracked company together with a site word.
ON_TOPIC_RE = re.compile(r"\b(data[\s-]?cent(er|re)s?|datacent(er|re)s?|hyperscal\w*|colocation|ai factor(y|ies)|supercomputers?|server farms?|data halls?|computing (site|campus|facility|facilities))\b", re.I)
SITE_RE = re.compile(r"\b(campus(es)?|facilit(y|ies)|sites?|megawatts?|gigawatts?|\d[\d,.]*\s?[MG]W)\b", re.I)


MW_RE = re.compile(r"(\d[\d,]*(?:\.\d+)?)\s?(?:MW|megawatts?)\b", re.I)
GW_RE = re.compile(r"(\d[\d,]*(?:\.\d+)?)\s?(?:GW|gigawatts?)\b", re.I)
MONEY_RE = re.compile(r"\$\s?(\d[\d,]*(?:\.\d+)?)\s?(billion|million|bn|b|m)\b", re.I)
# U.S.-only filter. A story is dropped when it names a non-U.S. place and no
# U.S. place, uses a foreign marker below, or comes from a foreign outlet.
FOREIGN_RE = re.compile(
    r"\b(data centres?|UK|U\.K\.|Britain|British|England|Europe|European|EU|India|Indian|China|Chinese|"
    r"Japan|Japanese|Korea|Korean|Australia|Australian|Canada|Canadian|Mexico|Mexican|Brazil|Brazilian|"
    r"Saudi|Emirati|Gulf|Africa|African|Asia|Asian|APAC|EMEA|LATAM|Indonesia|Malaysia|Malaysian|Thailand|"
    r"Vietnam|Philippines|Singapore|Ireland|Irish|Germany|German|France|French|Spain|Spanish|Italy|Italian|"
    r"Nordic|Norway|Norwegian|Sweden|Swedish|Finland|Finnish|Denmark|Danish|Dutch|Netherlands|Poland|Polish|"
    r"Belgium|Belgian|Austria|Austrian|Switzerland|Swiss|Portugal|Portuguese|Greece|Greek|Czech|Hungary|Hungarian|"
    r"Romania|Romanian|Iceland|Icelandic|Luxembourg|Estonia|Latvia|Lithuania|Croatia|Serbia|Bulgaria|Slovakia|"
    r"Israel|Israeli|Pakistan|"
    r"Bangladesh|Sri Lanka|Nepal|Kenya|Nigeria|Egypt|Morocco|Turkey|Russia|Russian|Ukraine|Kazakhstan|"
    r"Chile|Colombia|Argentina|Peru|New Zealand|Taiwan|Taiwanese|Hong Kong|Scotland|Scottish|Welsh|Wales|"
    r"Türkiye|Turkiye|Ankara|Istanbul|Lagos|Nairobi|Seoul|Tokyo|Mumbai|Jakarta|Bangkok|Manila|Hanoi|"
    r"Qatar|Kuwait|Oman|Bahrain|UAE|Abu Dhabi|Dubai|Telangana|Maharashtra|Tamil Nadu|Karnataka|Gujarat|"
    r"Uttar Pradesh|Andhra|Odisha|Kerala|Johor|Ontario|Quebec|Alberta|British Columbia|Nova Scotia|"
    r"New Brunswick|Saskatchewan|Manitoba|Cape Breton|Melbourne|Rs|crore|lakh|"
    r"[£€₹¥])(?![\w])", re.I)
FOREIGN_SOURCES = {
    "bbc news", "the guardian", "guardian", "telegraph", "irish times", "abc australia", "abc news (australia)",
    "abc news australia", "cbc news", "globe and mail", "the economic times", "the times of india", "straits times",
    "scmp", "south china morning post",
    "cbc", "cbc.ca", "global news", "ctv news", "the globe and mail", "toronto star", "financial post",
    "data centre magazine", "data centre solutions", "data centre review", "datacentre solutions",
    "computer weekly", "uktn", "the times", "the telegraph", "the independent", "bbc", "sky news",
    "the irish times", "silicon republic", "rte", "times of india", "the economic times", "economic times",
    "the hindu", "business standard", "moneycontrol", "mint", "livemint", "hindustan times", "ndtv",
    "the financial express", "financial express", "the new indian express", "deccan herald", "business today",
    "the straits times", "south china morning post", "the edge malaysia", "the star", "bernama",
    "the sydney morning herald", "the australian", "abc (australia)", "itnews", "the japan times",
    "nikkei asia", "the korea herald", "the korea times", "gulf news", "khaleej times", "arab news",
    "the national", "zawya", "techcentral", "businesstech", "mybroadband", "techcabal", "lusa",
    "nz herald", "rnz", "stuff", "beinsure", "capacity media", "w.media", "dcd asia", "datacenter forum", "bm.ge",
}
STATE_CODES = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR", "California": "CA", "Colorado": "CO",
    "Connecticut": "CT", "Delaware": "DE", "District of Columbia": "DC", "Florida": "FL", "Georgia": "GA",
    "Hawaii": "HI", "Idaho": "ID", "Illinois": "IL", "Indiana": "IN", "Iowa": "IA", "Kansas": "KS",
    "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD", "Massachusetts": "MA",
    "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS", "Missouri": "MO", "Montana": "MT",
    "Nebraska": "NE", "Nevada": "NV", "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM",
    "New York": "NY", "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK",
    "Oregon": "OR", "Pennsylvania": "PA", "Rhode Island": "RI", "South Carolina": "SC", "South Dakota": "SD",
    "Tennessee": "TN", "Texas": "TX", "Utah": "UT", "Vermont": "VT", "Virginia": "VA", "Washington": "WA",
    "West Virginia": "WV", "Wisconsin": "WI", "Wyoming": "WY",
}

TAG_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"\s+")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def log(msg):
    """Print a progress line immediately (the Actions log shows it as it happens)."""
    print(msg, flush=True)


CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f\u2028\u2029]")
INVISIBLE_RE = re.compile(r"[\u200b-\u200f\ufeff]")


def clean_text(s):
    """Plain text from feed markup: tags, entities and control or invisible characters removed."""
    if not s:
        return ""
    s = html.unescape(TAG_RE.sub(" ", s))
    return WS_RE.sub(" ", CONTROL_RE.sub(" ", INVISIBLE_RE.sub("", s))).strip()


def safe_link(url):
    """Only plain http(s) links are kept; javascript:, data: and anything else is dropped."""
    url = INVISIBLE_RE.sub("", CONTROL_RE.sub("", (url or "").strip()))
    return url if re.match(r"^https?://[^\s]+$", url, re.I) else ""


def norm_key(title):
    """The title reduced to lowercase letters and digits, so the same headline from two feeds dedupes."""
    return re.sub(r"[^a-z0-9]+", "", title.lower())


def make_id(title):
    """A headline's permanent id: the first 16 hex digits of the SHA-1 of its normalised title."""
    return hashlib.sha1(norm_key(title).encode("utf-8")).hexdigest()[:16]


def parse_dt(entry):
    """The entry's publication time as an aware UTC datetime, or None when the feed gives none."""
    for key in ("published_parsed", "updated_parsed"):
        st = entry.get(key)
        if st:
            try:
                return datetime.fromtimestamp(calendar.timegm(st), tz=timezone.utc)
            except Exception:
                pass
    return None


def load_json(path, default):
    """Read a JSON file, or return `default` when it is missing or unreadable (with a warning)."""
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            log(f"  warning: could not read {path.name}: {e}")
    return default


def google_news_url(query):
    """The Google News RSS search URL for a query, always in the U.S. edition (gl=US)."""
    return ("https://news.google.com/rss/search?q=" + quote_plus(query) +
            "&hl=en-US&gl=US&ceid=US:en")


# Per-run counts of feeds that failed, and of those whose last answer was HTTP 429 (rate limited).
FETCH_STATS = {"failed": 0, "rate_limited": 0}


def fetch_feed(url):
    """Fetch one feed, retrying 429 and 5xx responses (and network errors) with exponential backoff.

    Returns the parsed feed, or None after the last try fails. Failures are counted in FETCH_STATS
    so main() can tell "Google is rate limiting us" (back off) from an ordinary bad feed."""
    for attempt in range(1, FETCH_TRIES + 1):
        try:
            r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            if r.status_code == 429 or r.status_code >= 500:
                raise requests.HTTPError(f"HTTP {r.status_code}", response=r)
            r.raise_for_status()
            return feedparser.parse(r.content)
        except requests.RequestException as e:
            status = getattr(getattr(e, "response", None), "status_code", None)
            retryable = status is None or status == 429 or status >= 500
            if attempt < FETCH_TRIES and retryable:
                wait = 2 ** attempt
                log(f"  retry {attempt}/{FETCH_TRIES - 1} in {wait}s for {url[:70]}... ({e})")
                time.sleep(wait)
                continue
            log(f"  warning: fetch failed for {url[:90]}... ({e})")
            FETCH_STATS["failed"] += 1
            FETCH_STATS["rate_limited"] += status == 429
            return None


# ---------------------------------------------------------------------------
# Gazetteer / location detection
# ---------------------------------------------------------------------------
class Geo:
    """Everything location and source handling needs, loaded once per run."""

    def __init__(self, patterns, areas, source_states, blocked, ambiguous=None, cores=None, word_names=(), source_metros=None,
                 defaults=None, new_names=(), context_names=()):
        """Hold the compiled place data; see load_gazetteer."""
        self.patterns = patterns            # [(name, regex)] for cities, states, countries
        self.areas = areas                  # "Mason County" -> [candidates]
        self.ambiguous = ambiguous or {}    # "Lansing" -> [candidates in several states]
        self.source_states = source_states  # outlet name -> two-letter state
        self.blocked = blocked              # outlet names (lowercase) that are dropped
        self.cores = cores or {}            # metro core city -> metro ("Kansas City" -> "Kansas City")
        self.word_names = set(word_names)   # town names that are also English words ("Liberty")
        self.source_metros = source_metros or {}  # outlet -> metro, for outlets not named after the core city
        self.defaults = defaults or {}      # ambiguous name -> the well-known place it meant before ("Frederick" -> Maryland)
        self.new_names = set(new_names)     # suburb names added by gazetteer_metros.py (stricter rules, see find_locations)
        self.context_names = set(context_names)  # new suburb names another U.S. place shares: need metro or state context

    def metros_of_source(self, source):
        """The metro an outlet covers: listed in _source_metros, or its name contains a core city."""
        m = self.source_metros.get(source)
        if m:
            return {m}
        return {metro for core, metro in self.cores.items() if core in source}


# "Mason County", "St. Louis County", "Van Buren Township", "Richland Parish"
AREA_RE = re.compile(r"((?:(?:St\.|Saint|[A-Z][a-zA-Z'’-]+) )+)(County|Parish|Township)\b")
PRECISION_RANK = {"city": 4, "county": 3, "state": 2, "source": 1}


def entry_candidates(value):
    """A gazetteer value is one [lat, lon, level, display] entry or a list of them."""
    return value if value and isinstance(value[0], list) else [value]


def load_gazetteer():
    """Load scripts/gazetteer.json and data/feeds.json into (gaz, Geo): gaz maps a place name to
    its first entry; Geo holds the compiled place patterns (longest names first), the
    county/parish/township and ambiguous-town candidates, the outlets' home states and the
    blocked outlets.
    """
    doc = load_json(GAZ_FILE, {})
    raw = {k: v for k, v in doc.items() if not k.startswith("_")}
    areas, gaz, ambiguous = {}, {}, {}
    for k, v in raw.items():
        if re.search(r" (County|Parish|Township)$", k):
            areas[k] = entry_candidates(v)
        else:
            gaz[k] = entry_candidates(v)[0]
            if len(entry_candidates(v)) > 1:
                ambiguous[k] = entry_candidates(v)  # a town name found in several states
    patterns = []
    for n in sorted(gaz.keys(), key=len, reverse=True):
        if re.fullmatch(r"[A-Z]{2}", n):
            # Two-letter codes only count after a comma: "Abilene, TX"
            pat = re.compile(r"(?<=, )" + re.escape(n) + r"(?![A-Za-z])")
        else:
            # A hyphen may follow only as "-area" ("Kansas City-area data centers"); "New York-based" is a company's home.
            pat = re.compile(r"(?<![\w-])" + re.escape(n) + r"(?![\w])(?!-(?!area\b))")
        patterns.append((n, pat))
    cfg = load_json(FEEDS_FILE, {})
    source_states = {k: v for k, v in cfg.get("source_states", {}).items() if not k.startswith("_")}
    blocked = {s.strip().lower() for s in cfg.get("blocked_sources", []) if isinstance(s, str) and not s.startswith("#")}
    return gaz, Geo(patterns, areas, source_states, blocked, ambiguous, doc.get("_metro_cores", {}),
                    doc.get("_word_names", []), doc.get("_source_metros", {}), doc.get("_defaults", {}),
                    doc.get("_new_names", []), doc.get("_context_names", []))


def loc_from(entry, precision):
    """A gazetteer entry as a location dict (name, lat, lon, level, precision, country)."""
    lat, lon, level, display = entry[:4]
    country = entry[4] if len(entry) > 4 else ("US" if display.endswith(", US") else display.split(",")[-1].strip())
    if precision == "city" and re.search(r" (County|Parish), ", display):
        precision = "county"  # a landmark or split-state name that stands for a county ("KCI", "Kansas City, Kansas")
    loc = {"name": display, "lat": lat, "lon": lon, "level": level, "precision": precision, "country": country}
    if len(entry) > 5 and entry[5]:
        loc["metro"] = entry[5]
    return loc


# "near Kansas City", "outside Kansas City", "north of Kansas City", "Kansas City-area": the story
# is somewhere around the city, so the city itself is not where the project is.
VICINITY_BEFORE = re.compile(r"\b(?:just\s+)?(?:outside(?:\s+of)?|near|nearby|outskirts\s+of|suburbs?\s+of|suburban|"
                             r"(?:north|south|east|west|northeast|northwest|southeast|southwest)\s+of)\s+(?:the\s+)?$", re.I)
VICINITY_AFTER = re.compile(r"^(?:-area|\s+area\b|\s+metro\b|\s+region\b)", re.I)
# A suburb name followed by one of these is a street, a lake or an organisation: "Jones Road", "Savannah
# River Site", "Geronimo Power", "Oakland University".
NOT_A_TOWN_AFTER = re.compile(r"^\s*(?:&|Road|Rd\.?|Street|St\.|Avenue|Ave\.?|Boulevard|Blvd|Drive|Highway|Lake|River|Creek|"
                              r"Park|Township|Twp\.?|Power|Energy|Group|Capital|Partners|University|College|School|Act|Day|Hall|"
                              r"Center|Centre|Station|Mall|Plaza|Airport|Bank|Health|Hospital|Company|Co\.)\b")


# Capitalised words that may follow a town in a sentence-case headline ("Liberty City Council", "Olathe Planning Commission").
CIVIC_AFTER = {"City", "County", "Council", "Commission", "Planning", "Board", "Mayor", "Police", "Public", "Schools", "Chamber",
               "Village", "Town", "Area", "Zoning", "Data", "AI", "Missouri", "Kansas", "Mo", "Kan"} | set(STATE_CODES) | set(STATE_CODES.values())


def _suburb_in_context(name, text, start, end, sentence_case):
    """For a newly added suburb name: false when it is part of a longer name ("Daily Herald",
    "Western Macedonia", "Sen. Devine", "Spring Hope") or of a street or organisation ("Jones Road")."""
    before = text[:start].rstrip()
    prev = re.search(r"([A-Za-z.'’&-]+)$", before)
    if prev and before and before[-1] not in ":;,(—–-\"'‘“" and prev.group(1)[0].isupper() and not find_companies(prev.group(1)):
        return False
    after = text[end:]
    if NOT_A_TOWN_AFTER.match(after):
        return False
    nxt = re.match(r"\s+([A-Z][a-z]+)\b", after)
    return not (sentence_case and nxt and nxt.group(1) not in CIVIC_AFTER)


def _pick(cands, states, metros, default=None):
    """The one candidate in the story's metro, else the one in its states, else the name's default
    (the well-known place it meant before suburbs were added) when the story names no other state."""
    in_metro = [c for c in cands if len(c) > 5 and c[5] in metros]
    if len(in_metro) == 1:
        return in_metro[0]
    in_state = [c for c in (in_metro or cands) if state_of({"name": c[3]}) in states]
    if len(in_state) == 1:
        return in_state[0]
    if default and not in_state:
        d = next((c for c in cands if c[3] == default), None)
        if d and (not states or state_of({"name": d[3]}) in states):
            return d
    return None


def short_name(display):
    """'Kansas City, Missouri, US' -> 'Kansas City'."""
    return display.split(",")[0].strip()


def find_locations(text, gaz, geo, context_states=(), context_metros=()):
    """Places named in the text, most precise first.

    - Ambiguous county and town names ("Clay County", "Independence") are resolved to the one in
      the story's metro (from other places, or the outlet), else its state, else skipped.
    - A town name that is also an English word ("Liberty") only counts in a sentence-case headline.
    - A metro's core city named only as a reference point ("outside Kansas City", "Kansas City-area")
      is not a place of the story; its state is kept, with a note.
    - When a headline names a metro's core city and one of its suburbs or counties, the suburb or
      county wins ("Independence ... Kansas City" is Independence).
    """
    found, deferred, near = [], [], []
    work = text
    sentence_case = not title_case(text)
    # A city name inside "Richmond County" or "Van Buren Township" is not that city:
    # blank the matched county/parish/township names before looking for cities.
    for m in AREA_RE.finditer(text):
        words, kind = m.group(1).split(), m.group(2)
        for k in range(len(words), 0, -1):
            key = " ".join(words[-k:]) + " " + kind
            if key in geo.areas:
                start = m.end() - len(key)
                work = work[:start] + " " * len(key) + work[m.end():]
                break
    for name, pat in geo.patterns:
        if name not in work:  # cheap test first: most names are not in the headline
            continue
        m = pat.search(work)
        if not m:
            continue
        # A suburb name that does not stand for the town here leaves the text as it was, so a shorter
        # name inside it can still match ("How One Arizona City Blocked..." is Arizona).
        if name in geo.word_names and not sentence_case:
            continue
        if name in geo.new_names and not _suburb_in_context(name, text, m.start(), m.end(), sentence_case):
            continue
        # blank out the match so shorter names inside it do not re-match
        work = work[:m.start()] + (" " * (m.end() - m.start())) + work[m.end():]
        cands = geo.ambiguous.get(name) or [gaz[name]]
        is_city = cands[0][2] >= 3 and not re.search(r" (County|Parish), ", cands[0][3])
        # Only for a metro's core city: "near Boulder City" is close enough to Boulder City, but
        # "outside Atlanta" can be 40 miles from Atlanta.
        if is_city and name in geo.cores and (VICINITY_BEFORE.search(text[:m.start()]) or VICINITY_AFTER.match(text[m.end():])):
            near.append((name, cands))
            continue
        if name in geo.ambiguous or name in geo.context_names:
            deferred.append((name, cands))
        elif (name in geo.new_names and context_states and len(cands[0]) > 5
              and state_of({"name": cands[0][3]}) not in context_states and cands[0][5] not in context_metros):
            continue  # a suburb in another state and metro than the outlet's ("Bessemer City" from a Birmingham station)
        else:
            entry = gaz[name]
            found.append(loc_from(entry, "city" if entry[2] >= 3 else "state" if entry[2] == 2 else "country"))
    known_states = {state_of(f) for f in found} | set(context_states)
    known_metros = {f["metro"] for f in found if f.get("metro")} | set(context_metros)
    for name, cands in deferred:
        pick = _pick(cands, known_states, known_metros, geo.defaults.get(name))
        if pick:
            found.append(loc_from(pick, "city"))
            if len(pick) > 5 and pick[5]:
                known_metros.add(pick[5])
    for m in AREA_RE.finditer(text):
        words, kind = m.group(1).split(), m.group(2)
        for k in range(len(words), 0, -1):  # "Proposed Mason County" -> "Mason County"
            key = " ".join(words[-k:]) + " " + kind
            if key in geo.areas:
                cands = geo.areas[key]
                pick = cands[0] if len(cands) == 1 else _pick(cands, known_states | {state_of(f) for f in found}, known_metros)
                if pick:
                    found.append(loc_from(pick, "city" if kind == "Township" else "county"))
                break
    # A reference city gives only its state: "outside Kansas City" is somewhere in Missouri (or Kansas).
    for name, cands in near:
        pick = cands[0] if len(cands) == 1 else _pick(cands, known_states, known_metros)
        st = state_of({"name": pick[3]}) if pick else None
        state_name = next((n for n, c in STATE_CODES.items() if c == st), None)
        if state_name in gaz and not any(f["precision"] in ("city", "county") for f in found):
            loc = loc_from(gaz[state_name], "state")
            loc["note"] = f"near {name}"
            found.append(loc)
    # A metro suburb in another state than one the headline names is a same-named place, not this
    # one ("Antelope Data Center ... southern Utah" is not Antelope, California).
    named_states = {state_of(f) for f in found if f["precision"] == "state" and not f.get("note")}
    found = [f for f in found if not (f.get("metro") and f["precision"] == "city" and short_name(f["name"]) not in geo.cores
                                      and named_states and state_of(f) not in named_states)]
    # The metro's core city gives way to a suburb or county of the same metro.
    local = {f["metro"] for f in found if f.get("metro") and f["precision"] in ("city", "county")
             and short_name(f["name"]) not in geo.cores}
    found = [f for f in found if not (short_name(f["name"]) in geo.cores and f.get("metro") in local)]
    found.sort(key=lambda f: (-PRECISION_RANK.get(f["precision"], 0), -f["level"]))
    seen, out = set(), []
    for f in found:
        if f["name"] in seen:
            continue
        seen.add(f["name"])
        out.append(f)
    return out


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------
def country_of(loc):
    """The gazetteer's country code; older entries fall back to the display string."""
    return loc.get("country") or ("US" if loc["name"].endswith(", US") else loc["name"].split(",")[-1].strip())


def is_us(loc):
    """True for a location in the United States."""
    return country_of(loc) == "US"


def find_companies(text):
    """The operators named in the text, in COMPANIES order (aliases such as Stargate add several)."""
    found = set()
    for names, rx in COMPANY_RULES:
        if rx.search(text):
            found.update([names] if isinstance(names, str) else names)
    return sorted(found, key=lambda n: COMPANY_ORDER.get(n, 99))


def find_orgs(rules, text):
    """Names from one organisation list (utilities, investors, builders, suppliers) found in text."""
    return [name for name, rx in rules if rx.search(text)]


def find_utilities(text):
    """The utilities and grid operators named in the text."""
    return find_orgs(UTILITY_RULES, text)


def is_on_topic(text, companies):
    """True when the text is about data centers: it names one (ON_TOPIC_RE), or names a tracked
    operator together with a site word (campus, facility, megawatts).
    """
    return bool(ON_TOPIC_RE.search(text) or (companies and SITE_RE.search(text)))


def state_of(loc):
    """'Abilene, Texas, US' -> 'TX'; 'Washington, D.C., US' -> 'DC'."""
    parts = [p.strip() for p in loc["name"].split(",")]
    if "D.C." in parts or "DC" in parts:
        return "DC"
    for p in reversed(parts[:-1]):
        if p in STATE_CODES:
            return STATE_CODES[p]
    return None


def us_filter(item, all_locs, title_locs=()):
    """Return True when the story belongs on a U.S. site. A non-U.S. outlet needs
    a U.S. place or state in the title itself, not just in the description."""
    if item.get("source", "").strip().lower() in FOREIGN_SOURCES:
        return any(is_us(l) for l in title_locs)
    us_locs = [l for l in all_locs if is_us(l)]
    if us_locs:
        return True
    if any(not is_us(l) for l in all_locs):
        return False
    if FOREIGN_RE.search(item["title"]):
        return False
    return True


# Project names in headlines, used by the registry to match headlines about the same site and to
# name a record when no operator is known:
#   "Plans for $17 billion 'Project Sail' proposed for Coweta County" -> Project Sail
#   "Wildcat Ridge Data Center in Archbald to use huge amounts of power" -> Wildcat Ridge Data Center
#   "TeraWulf tops out latest data center at Lake Mariner campus"      -> Lake Mariner campus
#   "Mayor discusses potential data center at Wood Haven Technology Park" -> Wood Haven Technology Park
# Capital letters only mean a name in sentence-case headlines, so in Title Case Headlines only
# "Project X" counts. The plural "X Data Centers" is nearly always a company ("Fleet Data Centers
# raises $3.8B"), so only the singular names a site. Generic words ("New", "Massive"), a tracked
# operator alone ("Amazon Data Center") and a state alone are not names.
NAME_PROJECT_RE = re.compile(r"(?<!Center )(?<!Centre )(?<!Campus )\bProject ([A-Z][a-z]{2,}(?: [A-Z][a-z]{2,})?)\b")
# Sentence case only: "Independence AI data center", "the Wildcat Ridge data center".
NAME_SITE_LOWER_RE = re.compile(r"\b((?:[A-Z][\w'’&.-]+ ){1,3})(data cent(?:er|re))(?!s)\b")
NAME_SITE_RE = re.compile(r"\b((?:[A-Z][\w'’&.-]+ ){1,3})(Data Center|Data Centre|Datacenter|campus|Campus|Technology Park|Tech Park)(?!s)\b")
NAME_GENERIC = set("""A An The This That Proposed Planned Possible Potential Massive Huge Giant Big Biggest Largest Large Mega
Major Hyperscale Hyperscaler AI A.I. Artificial Intelligence Local County City Town Township State Rural Area Regional Future
Second Third First Next Another Its Their Our Your His Her Controversial Secret Mystery Data Center Centers Campus Campuses
Crypto Bitcoin Cloud Tech Technology Digital Gigawatt Billion Million Dollar Green Clean Solar Nuclear Gas Energy Power
U.S. US American National Federal Is Are Was Will Could Would Should Why How What Where When Who No Yes Not Latest
Residents Neighbors Officials Council Commission Board Opponents Critics Approves Approved Rejects Plans Plan Proposal
Says Said Pushes Coming Built Building Opens Opening Breaks Ground Moratorium Ban Rules Vote Votes Hearing Meeting
Inside Near At In On For To Of And With From By Over After Before About Amid Against Into Hosting College University School
Hospital Medical Office Corporate Headquarters HQ Edge Enterprise Colocation Wholesale Retail Modular Orbital Space
GW MW SF AB""".split())
# Words after "Project" that are not part of a name: "Project Caprock Data Center" is Project Caprock,
# and "Project Profile:" or "Project Manager" are not projects at all.
NAME_PROJECT_NOT = {"Advances", "Moves", "Gets", "Wins", "Faces", "Clears", "Draws", "Sparks", "Approved", "Rejected",
                    "Data", "Center", "Campus", "Site", "Plan", "Plans", "Proposal", "Update", "Updates", "Manager",
                    "Director", "Details", "Profile", "Spotlight", "Labor", "Management", "Resumes", "Begins",
                    "Starts", "Breaks", "Stalls", "Halts", "Paused", "Delayed", "Returns", "Head", "Lead"}


def title_case(title):
    """True for Headlines Written Like This, where capital letters say nothing about names."""
    words = [w for w in re.findall(r"[A-Za-z][\w'’-]*", title) if len(w) > 3]
    return bool(words) and sum(w[0].isupper() for w in words) / len(words) >= 0.6


def name_hint(title, places=None):
    """A project's own name in the headline ("Project Sail", "Wildcat Ridge Data Center"), or None.
    With places (the gazetteer), a lowercase "X data center" where X is only a place ("Kansas City
    data center") is not a name."""
    m = NAME_PROJECT_RE.search(title)
    if m:
        words = m.group(1).split()
        if words[0] not in NAME_GENERIC and words[0] not in NAME_PROJECT_NOT:
            return "Project " + (words[0] if words[-1] in NAME_PROJECT_NOT else m.group(1))
    lower = [(m, True) for m in NAME_SITE_LOWER_RE.finditer(title)] if places is not None and not title_case(title) else []
    for m, is_lower in [(m, False) for m in NAME_SITE_RE.finditer(title)] + lower:
        # Judge the case of the rest of the headline, not of the name itself.
        if title_case(title[:m.start()] + title[m.end():]):
            continue
        words = m.group(1).split()
        # Drop generic words and possessives in front: "the proposed Hermantown Data Center" -> "Hermantown Data Center"
        while words and (words[0] in NAME_GENERIC or words[0].endswith(("'s", "’s", "'", "’"))):
            words = words[1:]
        # "AI" may follow a name ("Independence AI data center") but is not a name by itself.
        if not words or any((w in NAME_GENERIC and not (w == "AI" and i > 0)) or w.endswith(("'s", "’s"))
                            for i, w in enumerate(words)) or not all(w[0].isupper() for w in words):
            continue
        if is_lower and " ".join(words) in places:
            continue
        name = " ".join(words)
        if name in STATE_CODES or find_companies(name) or find_companies(m.group(0)):
            continue
        kind = m.group(2)
        kind = "Data Center" if kind.lower().startswith(("data", "datacent")) else "campus" if kind.lower() == "campus" else kind
        return f"{name} {kind}"
    return None


def tag_item(item, gaz, geo):
    """(Re)compute topic, places, companies and figures. Returns False to drop the headline."""
    if item.get("source", "").strip().lower() in geo.blocked:
        return False
    text = item["title"] + " " + item.get("snippet", "") + " " + item.get("_desc", "")
    companies = find_companies(text)
    if not is_on_topic(text, companies):
        return False
    source_state = geo.source_states.get(item.get("source", ""))
    locs = find_locations(text, gaz, geo, [source_state] if source_state else (), geo.metros_of_source(item.get("source", "")))
    title_locs = find_locations(item["title"], gaz, geo) if item.get("source", "").strip().lower() in FOREIGN_SOURCES else ()
    if not us_filter(item, locs, title_locs):
        return False
    us_locs = [l for l in locs if is_us(l)]
    if not us_locs and source_state:
        # A local outlet with no place in the headline: use its home state, flagged as such
        name = next((n for n, c in STATE_CODES.items() if c == source_state), None)
        if name in gaz:
            us_locs = [loc_from(gaz[name], "source")]
    item["category"], item["tags"] = classify(item["title"])
    item["locations"] = us_locs[:3]
    states = [s for s in (state_of(l) for l in us_locs) if s]
    item["states"] = sorted(set(states))
    item["state"] = states[0] if states else None
    item["county"] = next((l["name"] for l in us_locs if l["precision"] == "county"), None)
    item["location_precision"] = us_locs[0]["precision"] if us_locs else None
    note = next((l["note"] for l in us_locs if l.get("note")), None)
    if note:
        item["location_note"] = note
    else:
        item.pop("location_note", None)
    item["companies"] = companies
    item["utilities"] = find_utilities(text)
    item["investors"] = find_orgs(INVESTOR_RULES, text)
    item["builders"] = find_orgs(BUILDER_RULES, text)
    item["suppliers"] = find_orgs(SUPPLIER_RULES, text)
    hint = name_hint(item["title"], gaz)
    if hint:
        item["name_hint"] = hint
    else:
        item.pop("name_hint", None)
    item.pop("capacity_mw", None)
    item.pop("investment_usd_b", None)
    item.update(extract_numbers(item["title"]))
    return True


# ---------------------------------------------------------------------------
# Clustering: one story told by several outlets
# ---------------------------------------------------------------------------
STOP = set("""a an and the of in on at to for by with from as is are be was were will has have had it its this that
these those new data center centers centre centres datacenter datacenters plan plans says say said could would
after over into about amid more than up out not no but or if he she they we you their our his her who what why how
county city state township parish us u.s""".split())


def title_words(title, source=""):
    """Title tokens without stopwords or the outlet's own name ("... - Reuters")."""
    drop = set(re.findall(r"[a-z0-9]+", source.lower()))
    return {w for w in re.findall(r"[a-z0-9$][a-z0-9$'.-]*", title.lower()) if len(w) > 2 and w not in STOP and w not in drop}


def jaccard(a, b):
    """Share of words two titles have in common (0 to 1), used for story clustering and matching."""
    return len(a & b) / len(a | b) if a and b else 0.0


def cluster_items(items):
    """Set cluster_id and cluster_title on every item. Two headlines published within
    CLUSTER_DAYS join when their title-word Jaccard is >= CLUSTER_STRONG, or >= CLUSTER_WEAK
    and they share a city or county, or >= CLUSTER_WEAK and they share a company and a
    state. Union-find lets clusters chain through intermediate headlines."""
    parent = {it["id"]: it["id"] for it in items}

    def find(x):
        """Union-find root of a headline id, with path halving."""
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def places(it):
        """The city and county names a headline is placed in."""
        return {l["name"] for l in it.get("locations", []) if l.get("precision") in ("city", "county")}

    rows = sorted(({"id": it["id"], "t": datetime.fromisoformat(it["published"]),
                    "w": title_words(it["title"], it.get("source", "")), "p": places(it),
                    "c": set(it.get("companies", [])), "s": set(it.get("states", []))} for it in items),
                  key=lambda r: r["t"])
    # Each root carries its cluster's states and places: two clusters that both name
    # places but none in common never merge, so a placeless headline cannot bridge them.
    geo = {r["id"]: (set(r["s"]), set(r["p"])) for r in rows}

    def conflict(ra, rb):
        """True when two clusters name different states, or different towns or counties, so
        they must not merge.
        """
        (sa, pa), (sb, pb) = geo[ra], geo[rb]
        return bool((sa and sb and not sa & sb) or (pa and pb and not pa & pb))

    window = timedelta(days=CLUSTER_DAYS)
    for i, a in enumerate(rows):
        for b in rows[i + 1:]:
            if b["t"] - a["t"] > window:
                break
            j = jaccard(a["w"], b["w"])
            if j < CLUSTER_WEAK:
                continue
            if j >= CLUSTER_STRONG or (a["p"] & b["p"]) or ((a["c"] & b["c"]) and (a["s"] & b["s"])):
                ra, rb = find(a["id"]), find(b["id"])
                if ra != rb and not conflict(ra, rb):
                    parent[rb] = ra
                    geo[ra] = (geo[ra][0] | geo[rb][0], geo[ra][1] | geo[rb][1])
    groups = {}
    for it in sorted(items, key=lambda x: x["published"]):
        groups.setdefault(find(it["id"]), []).append(it)
    for members in groups.values():
        # Named after the earliest headline so the id stays stable as stories join;
        # shown with the headline that has the most precise place, else the earliest.
        best = max(members, key=lambda m: PRECISION_RANK.get(m.get("location_precision"), 0))
        for it in members:
            it["cluster_id"] = members[0]["id"]
            it["cluster_title"] = best["title"]
    return len(groups)


# A headline the outlet itself labels as opinion is Analysis / Opinion whatever it is about:
# "Times Opinion: We can and should resist AI data centers", "Letter: City should take its time",
# "Vantage Data Center opponents push misleading claims on jobs | Opinion"
OPINION_LABEL = re.compile(r"^(?:[\w .]{0,20}\b)?(?:opinion|commentary|editorial|op-ed|letters?(?: to the editor)?|guest column|viewpoint|"
                           r"my turn|your turn|column)\s*[:|]|[|:-]\s*(?:opinion|commentary|editorial|op-ed)\s*$", re.I)


def classify(title):
    """(primary topic, every matching topic). Cancelled / Blocked first, then a labelled opinion,
    then CATEGORY_RULES in order; General when nothing matches."""
    tags = [name for name, rx in COMPILED_RULES if rx.search(title)]
    if OPINION_LABEL.search(title):
        tags = ["Analysis / Opinion"] + [t for t in tags if t != "Analysis / Opinion"]
    if is_cancelled(title):
        tags.insert(0, CANCELLED)
    primary = tags[0] if tags else "General"
    return primary, tags


NOT_INVESTMENT = re.compile(r"^\s*(?:in\s+)?(?:\w+\s+){0,2}(?:tax\b|incentives?|abatements?|subsid\w*|rebates?|credits?|"
                            r"fees?|fines?|settlements?)", re.I)


def extract_numbers(title):
    """Capacity (MW; GW converted) and investment (billions of dollars) stated in the title. A
    capacity above MAX_PROJECT_MW is dropped as a grid or statewide figure, not one project.
    """
    out = {}
    m = GW_RE.search(title)
    if m:
        out["capacity_mw"] = round(float(m.group(1).replace(",", "")) * 1000)
    else:
        m = MW_RE.search(title)
        if m:
            out["capacity_mw"] = round(float(m.group(1).replace(",", "")))
    # "$229 million in tax breaks for a $1.4 billion data center": a tax break is not the investment.
    m = next((x for x in MONEY_RE.finditer(title) if not NOT_INVESTMENT.match(title[x.end():])), None)
    if m:
        val = float(m.group(1).replace(",", ""))
        unit = m.group(2).lower()
        out["investment_usd_b"] = round(val if unit in ("billion", "bn", "b") else val / 1000, 3)
    if out.get("capacity_mw", 0) > MAX_PROJECT_MW:
        del out["capacity_mw"]
    return out


SCHEDULED = re.compile(r"\s+(?:in|by|this|next)\s+(?:early |late |mid-?|the )?(?:20\d\d|year|spring|summer|fall|autumn|winter|month|week|quarter)", re.I)


def stage_counts(status, m, title):
    """Whether one stage-word match describes the project's own present stage (see STAGE_FUTURE)."""
    before, after = title[:m.start()], title[m.end():]
    # "coming to Heath, Hebron after groundbreaking": a step right after "after" already happened.
    past = bool(re.search(r"\b(after|following|since)\W*$", before, re.I))
    if status not in ("Announced", "Expansion") and not past and STAGE_FUTURE.search(" ".join(before.split()[-4:]) + " "):
        return False
    # "data center that opens in 2026", "goes live by next year": a present-tense opening with a date is a schedule.
    if status == "Operational" and not m.group(0).lower().endswith("ed") and SCHEDULED.match(after):
        return False
    if status == "Operational":
        # The thing that opens is named just before or after the verb, or opens the headline.
        near = " ".join(before.split()[:3]) + " " + " ".join(before.split()[-3:]) + " " + " ".join(after.split()[:3])
        if OPENS_OTHER.search(near) or COMPLETES_OTHER.search(after):
            return False
    return True


def guess_status(title):
    """The stage a headline reports: Cancelled / Blocked, Under construction, Operational,
    Expansion, Announced, or None. The first rule with a match that counts wins, so in "Amazon
    opens Indiana campus as rivals race to break ground" the future "to break ground" is skipped
    and "opens" gives Operational."""
    if is_cancelled(title):
        return CANCELLED
    for status, rx in STATUS_RULES:
        if any(stage_counts(status, m, title) for m in rx.finditer(title)):
            return status
    return None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
# Fields the pages never read: kept in the archive, left out of data/news.json to keep it small.
NEWS_DROP_FIELDS = ("locations", "tags", "feed", "location_precision", "county", "cluster_title", "name_hint")


def slim(it):
    """A headline as written to data/news.json: no archive-only fields, no empty values, and the
    story's display headline marked with cluster_lead instead of repeating cluster_title."""
    out = {k: v for k, v in it.items() if k not in NEWS_DROP_FIELDS and v not in (None, [], "")}
    if it.get("cluster_title") == it.get("title"):
        out["cluster_lead"] = True
    return out


def entry_to_item(e, label, now, gaz, geo, max_age_days=NEWS_MAX_AGE_DAYS):
    """One RSS entry -> a tagged headline, or None when it is dropped (no title, unsafe link,
    too old, blocked source, off topic or outside the U.S.). The hourly run and
    scripts/backfill_news.py both use this, so every headline takes the same path."""
    raw_title = clean_text(e.get("title", ""))
    if not raw_title:
        return None
    source = ""
    src = e.get("source")
    if isinstance(src, dict):
        source = clean_text(src.get("title", ""))
    # Google News titles end with " - Source"
    title = raw_title
    if " - " in raw_title:
        head, _, tail = raw_title.rpartition(" - ")
        if (source and tail.strip().lower() == source.lower()) or (not source and len(tail) < 40):
            title = head.strip()
            source = source or tail.strip()
    link = safe_link(e.get("link", ""))
    if not link:
        return None
    dt = parse_dt(e) or now
    if max_age_days is not None and (now - dt).days > max_age_days:
        return None
    # Google News descriptions repeat the title and outlet; Alerts carry a real snippet.
    desc = clean_text(e.get("summary", "") or e.get("description", ""))
    snippet = desc[:300] if desc and not desc.startswith(title[:40]) else ""
    item = {
        "id": make_id(title),
        "title": title,
        "link": link,
        "source": source,
        "published": dt.isoformat(timespec="seconds"),
        "feed": label,
    }
    if snippet:
        item["snippet"] = snippet
    item["_desc"] = desc  # scanned for places and companies, never stored
    ok = tag_item(item, gaz, geo)
    item.pop("_desc", None)
    return item if ok else None


# ---------------------------------------------------------------------------
# Permanent archive
# ---------------------------------------------------------------------------
def archive_items(new_items, archive_dir):
    """Append headlines to data/archive/YYYY-MM.json by published month.

    Entries already in a month file are left exactly as they are; nothing is
    ever trimmed or deleted. Returns the number of headlines added.
    """
    archive_dir.mkdir(parents=True, exist_ok=True)
    # Ids are unique across the whole archive, not just within a month: a headline seen
    # again with another date stays where it was first archived.
    everywhere = set()
    for path in archive_dir.glob("*.json"):
        if MONTH_RE.match(path.stem):
            everywhere.update(x["id"] for x in load_json(path, {}).get("items", []))
    by_month = {}
    for it in new_items:
        month = it.get("published", "")[:7]
        if MONTH_RE.match(month):
            by_month.setdefault(month, []).append(it)
    added = 0
    for month, its in sorted(by_month.items()):
        path = archive_dir / (month + ".json")
        current = load_json(path, {}).get("items", [])
        known = {x["id"] for x in current}
        fresh = []
        for it in its:
            if it["id"] not in known and it["id"] not in everywhere:
                known.add(it["id"])
                everywhere.add(it["id"])
                fresh.append(it)
        if not fresh:
            continue
        items = current + fresh
        items.sort(key=lambda x: x["published"], reverse=True)
        path.write_text(json.dumps({"_readme": readme("archive month"), "month": month, "count": len(items), "items": items},
                                   ensure_ascii=False, indent=1), encoding="utf-8")
        added += len(fresh)
    write_archive_index(archive_dir)
    return added


def write_archive_index(archive_dir):
    """Rewrite data/archive/index.json: the months on disk with their headline counts, the total
    and the earliest date.
    """
    months = []
    for path in sorted(archive_dir.glob("*.json"), reverse=True):
        if not MONTH_RE.match(path.stem):
            continue
        items = load_json(path, {}).get("items", [])
        if not items:
            continue
        months.append({
            "month": path.stem, "count": len(items), "file": "data/archive/" + path.name,
            "earliest": min(x["published"] for x in items), "latest": max(x["published"] for x in items),
        })
    index = {
        "_readme": readme("archive index"),
        "total": sum(m["count"] for m in months),
        "earliest": min((m["earliest"] for m in months), default=None),
        "latest": max((m["latest"] for m in months), default=None),
        "months": months,
    }
    path = archive_dir / "index.json"
    old = load_json(path, {})
    old.pop("updated", None)
    if old == index:
        return  # nothing changed; keep the file (and git) quiet
    path.write_text(json.dumps(dict({"updated": datetime.now(timezone.utc).isoformat(timespec="seconds")}, **index),
                               ensure_ascii=False, indent=1), encoding="utf-8")


def parse_args():
    """Command-line options: --no-fetch, --sample RSS_FILE and --out DIR (see the module docstring)."""
    ap = argparse.ArgumentParser(description="Refresh data/news.json, data/registry.json and the project pages")
    ap.add_argument("--no-fetch", action="store_true", help="re-tag the stored items without fetching feeds")
    ap.add_argument("--sample", metavar="RSS_FILE", help="read this local RSS file instead of the network")
    ap.add_argument("--out", metavar="DIR", help="write the JSON files here instead of data/ (existing data/ files are read as the starting point)")
    return ap.parse_args()


def main():
    """One update run: fetch every feed, tag and cluster the headlines, archive them, write
    data/news.json, update the registry and project pages, and write data/status.json. Returns
    the exit code (0 ok, 1 no data, 75 rate limited).
    """
    args = parse_args()
    no_fetch = args.no_fetch
    news_out = Path(args.out) / NEWS_FILE.name if args.out else NEWS_FILE
    status_out = Path(args.out) / STATUS_FILE.name if args.out else STATUS_FILE
    archive_out = Path(args.out) / "archive" if args.out else ARCHIVE_DIR
    if args.out:
        Path(args.out).mkdir(parents=True, exist_ok=True)
        # Test runs start from a copy of the real archive and never touch it.
        if ARCHIVE_DIR.exists():
            shutil.copytree(ARCHIVE_DIR, archive_out, dirs_exist_ok=True)
    now = datetime.now(timezone.utc)
    cfg = load_json(FEEDS_FILE, {})
    gaz, geo = load_gazetteer()

    sources = []
    for f in cfg.get("google_news", []):
        if isinstance(f, dict) and f.get("query"):
            sources.append(("Google News: " + f.get("name", f["query"]), google_news_url(f["query"])))
    for url in cfg.get("google_alerts", []):
        if isinstance(url, str) and url.startswith("http"):
            sources.append(("Google Alerts", url))
    if no_fetch:
        sources = []
    if args.sample:
        sources = [("Sample: " + Path(args.sample).name, args.sample)]

    log(f"Fetching {len(sources)} feeds")
    fresh = {}
    raw_total = 0
    feeds_ok = 0
    for label, url in sources:
        parsed = feedparser.parse(Path(url).read_bytes()) if args.sample else fetch_feed(url)
        if not parsed:
            continue
        raw_total += len(parsed.entries)
        feeds_ok += bool(parsed.entries)
        n = 0
        for e in parsed.entries:
            item = entry_to_item(e, label, now, gaz, geo)
            if not item or item["id"] in fresh:
                continue
            fresh[item["id"]] = item
            n += 1
        log(f"  {label}: {n} items")
    # Rate limited on more than half the feeds: write nothing and let the caller retry next hour.
    if sources and FETCH_STATS["rate_limited"] * 2 > len(sources):
        log(f"BACKOFF: {FETCH_STATS['rate_limited']} of {len(sources)} feeds were rate limited (HTTP 429); "
            "leaving the data files unchanged for this cycle")
        return EXIT_BACKOFF
    if sources and raw_total == 0:
        log("ERROR: every feed returned zero items; leaving the data files unchanged")
        return 1

    # Merge with the existing news file so stories stay for NEWS_MAX_AGE_DAYS
    existing = load_json(NEWS_FILE, {}).get("items", [])
    merged = {it["id"]: it for it in existing if "id" in it}
    cutoff = now - timedelta(days=NEWS_MAX_AGE_DAYS)
    # Refill from the archive, so stories trimmed by an older, smaller limit come back
    for path in sorted(archive_out.glob("*.json")):
        if MONTH_RE.match(path.stem) and path.stem >= cutoff.strftime("%Y-%m"):
            for it in load_json(path, {}).get("items", []):
                if it["id"] not in merged and datetime.fromisoformat(it["published"]) >= cutoff:
                    merged[it["id"]] = dict(it)
    merged.update(fresh)
    # Re-tag stored stories too, so rule and gazetteer edits apply to old items
    kept = [it for it in merged.values() if tag_item(it, gaz, geo)]
    kept.sort(key=lambda it: it["published"], reverse=True)
    clusters = cluster_items(kept)
    log(f"Clusters: {len(kept)} headlines in {clusters} stories")

    # Every kept headline goes into the permanent archive before the recent file is trimmed
    added = archive_items(kept, archive_out)
    log(f"Archive: {added} new headlines added under {archive_out}")

    known = {it["id"] for it in existing}
    new_this_run = len([k for k in fresh if k not in known])
    # The longest window (90 days, then 30) whose file fits in NEWS_MAX_BYTES.
    for days in NEWS_WINDOW_DAYS:
        since = now - timedelta(days=days)
        items = [slim(it) for it in kept if datetime.fromisoformat(it["published"]) >= since]
        text = json.dumps({
            "_readme": readme("news.json"),
            "updated": now.isoformat(timespec="seconds"),
            "window_days": days,
            "count": len(items),
            "new_this_run": new_this_run,
            "items": items,
        }, ensure_ascii=False, separators=(",", ":"))
        if len(text.encode()) <= NEWS_MAX_BYTES or days == NEWS_WINDOW_DAYS[-1]:
            break
    news_out.write_text(text, encoding="utf-8")
    log(f"Wrote {news_out}: {len(items)} items, last {days} days, {len(text.encode()) / 1024:.0f} KB")

    # Permanent project registry: attach project-shaped headlines to records, apply
    # data/project_overrides.json, rebuild statuses, then the static project pages and sitemap.
    import registry
    reg_out = Path(args.out) / "registry.json" if args.out else registry.REGISTRY_FILE
    reg_in = reg_out if reg_out.exists() else registry.REGISTRY_FILE
    records = registry.update(kept, gaz, registry_in=reg_in, registry_out=reg_out, log=log,
                              rejects_out=Path(args.out) / "registry_rejects.json" if args.out else registry.REJECTS_FILE)
    registry.build_pages(records, out_dir=Path(args.out) / "projects" if args.out else registry.PAGES_DIR,
                         sitemap=Path(args.out) / "sitemap.xml" if args.out else registry.SITEMAP_FILE, log=log)

    # A small run report for the Methodology page.
    status_out.write_text(json.dumps({
        "_readme": readme("status.json"),
        "updated": now.isoformat(timespec="seconds"),
        "feeds_total": len(sources),
        "feeds_ok": feeds_ok,
        "items_total": len(items),
        "items_new": new_this_run,
    }, indent=1) + "\n", encoding="utf-8")
    log(f"Wrote {status_out}: {feeds_ok} of {len(sources)} feeds returned data, {new_this_run} new headlines")
    return 0


if __name__ == "__main__":
    sys.exit(main())
