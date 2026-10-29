"""
Tagging tests: real archive headlines and what scripts/fetch_news.py must say about them.

Every row in HEADLINES is a headline from data/archive with its real outlet, and the topic,
operators, state, stage signal and cancelled flag that a careful reader would give it. The rows
were reviewed by hand on 2026-10-29; a rule change that breaks one is either a bug or a decision
to record in docs/DECISIONS.md. The smaller groups below pin down the tricky cases: names that
are also common words, future tense, cancellations that are not, organisation fields, project
name hints, and the topic and U.S. filters.

Run: python -m pytest -q tests
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import fetch_news as fn  # noqa: E402

GAZ, GEO = fn.load_gazetteer()


def tag(title, source="Test Outlet"):
    """Tag one headline the way the hourly run does. Returns the item, or None when it is dropped."""
    it = {"id": fn.make_id(title), "title": title, "source": source, "published": "2026-01-01T00:00:00+00:00"}
    return it if fn.tag_item(it, GAZ, GEO) else None


# (title, outlet, topic, operators, state, stage signal, cancelled)
HEADLINES = [
    ('Times Opinion: We can and should resist AI data centers in Chattanooga', 'Chattanooga Times Free Press', 'Analysis / Opinion', (), 'TN', None, False),
    ('Commentary: Thirsty AI data center runs into Florida community opposition', 'Florida Phoenix', 'Analysis / Opinion', (), 'FL', None, False),
    ('Laramie County commission unanimously approves massive AI data center', 'Wyoming Public Media', 'AI Infrastructure', (), 'WY', 'Announced', False),
    ("Elon Musk's xAI reportedly will spend $18B+ more on Nvidia chips for Colossus 2 data center", 'SiliconANGLE', 'AI Infrastructure', ('xAI',), None, None, False),
    ('Metro Nashville wants to seize the land earmarked for a data center near the zoo. Here’s what we know', 'WSMV', 'Analysis / Opinion', (), 'TN', None, False),
    ('Data centers in Minnesota: Why so many?', 'FOX 9 Minneapolis-St. Paul', 'Analysis / Opinion', (), 'MN', None, False),
    ('What’s the status of massive data centers in Colorado? Here’s what you need to know.', 'The Colorado Sun', 'Analysis / Opinion', (), 'CO', None, False),
    ("Washington's hydropower has created a data center boom. Some are concerned about its future.", 'NPR', 'Analysis / Opinion', (), 'WA', None, False),
    ('Data Centers Test Wyoming’s Promise Not To ‘Piss Away’ The Next Boom', 'Cowboy State Daily', 'Analysis / Opinion', (), 'WY', None, False),
    ('Editorial: Chicago needs a data center strategy, not another performative stunt', "Crain's Chicago Business", 'Analysis / Opinion', (), 'IL', None, False),
    ('What you need to know about the $40B Aligned Data Centers deal', 'Fierce Network', 'Analysis / Opinion', ('Aligned',), None, None, False),
    ('Circling Back: What Now for Quantum Loophole and the Quantum Frederick Data Center Campus?', 'Data Center Frontier', 'Analysis / Opinion', ('Quantum Loophole',), 'MD', None, False),
    ('CyrusOne wants to earn Texans’ trust amid data center boom', 'San Antonio Express-News', 'Analysis / Opinion', ('CyrusOne',), 'TX', None, False),
    ('Merrillville council extends data center moratorium by 6 months', 'Chicago Tribune', 'Cancelled / Blocked', (), 'IN', 'Cancelled / Blocked', True),
    ('Clackamas County commissioners approve 120-day pause on data center development', 'KGW', 'Cancelled / Blocked', (), 'OR', 'Cancelled / Blocked', True),
    ('Provo City Council denies zoning change for proposed data center', 'KSL', 'Cancelled / Blocked', (), 'UT', 'Cancelled / Blocked', True),
    ('Archbald unanimously denies zoning for hyperscale data center campus in borough', 'The Allegheny Front', 'Cancelled / Blocked', (), 'PA', 'Cancelled / Blocked', True),
    ('Data center moratorium passed by Inver Grove Heights City Council', 'FOX 9 Minneapolis-St. Paul', 'Cancelled / Blocked', (), 'MN', 'Cancelled / Blocked', True),
    ("Residents cheer as Tucson rejects Amazon's massive Project Blue data center campus in Arizona", 'Data Center Dynamics', 'Cancelled / Blocked', ('Amazon',), 'AZ', 'Cancelled / Blocked', True),
    ('Microsoft pauses some work at Mount Pleasant data center site', 'The Daily Reporter', 'Cancelled / Blocked', ('Microsoft',), 'WI', 'Cancelled / Blocked', True),
    ('Data center supporters and critics argue over future in Pittsburgh area', 'CBS News', 'Community', (), 'PA', None, False),
    ('Oldham County data center switches sites, reduces size amid local resistance', 'Louisville Public Media', 'Community', (), 'KY', None, False),
    ('Concern over big data centers is growing. Is Vermont likely to get one?', 'Vermont Public', 'Community', (), 'VT', None, False),
    ('Protesters call for moratorium on data centers in Virginia', 'WAVY.com', 'Community', (), 'VA', None, False),
    ('Spartanburg County data center lawsuit: Residents say $2.8B project was wrongly classified as ‘minor’ development', 'FOX Carolina News', 'Community', (), 'SC', None, False),
    ('Harford County Council introduces bill to pause data center development after community pushback', 'WMAR 2 News Baltimore', 'Community', (), 'MD', None, False),
    ('Indianapolis residents take Sabey data center fight to court after city approval', 'WTHR', 'Community', ('Sabey',), 'IN', 'Announced', False),
    ('Locals voice concerns over $1B York County data center as QTS reps meet face-to-face with residents', 'Post and Courier', 'Community', ('QTS',), 'SC', None, False),
    ('Data centers could be Texas construction’s bright star in 2026 and beyond', 'constructconnect.com', 'Construction', (), 'TX', None, False),
    ('New $16B natural gas generation hub being built in East Texas, data center to follow', 'The Center Square', 'Construction', (), 'TX', None, False),
    ('Amazon breaks ground on $10bn data center complex in Richmond County, North Carolina', 'Data Center Dynamics', 'Construction', ('Amazon',), 'NC', 'Under construction', False),
    ('CleanArc breaks ground on 900MW data center campus in Virginia', 'Data Center Dynamics', 'Construction', (), 'VA', 'Under construction', False),
    ('Groundbreaking in Irving for new data center', 'NBC 5 Dallas-Fort Worth', 'Construction', (), 'TX', 'Under construction', False),
    ('Aligned Data Centers breaks ground on $10B project at former coal plant site', 'The Business Journals', 'Construction', ('Aligned',), None, 'Under construction', False),
    ('Shreveport City Council welcomes $12 billion data center being built by Amazon', 'KSLA', 'Construction', ('Amazon',), 'LA', None, False),
    ('Talks underway for $10 billion data center and power plant north of Waco', 'The Waco Bridge', 'Deals / Investment', (), 'TX', None, False),
    ('BNY sells former data center facility north of Pittsburgh', 'The Business Journals', 'Deals / Investment', (), 'PA', None, False),
    ('Google to invest $40B in Texas data centers in major AI push', 'Fox Business', 'Deals / Investment', ('Google',), 'TX', None, False),
    ('The data center boom in North Texas is creating more jobs in electricity', 'WFAA', 'Economy / Jobs', (), 'TX', None, False),
    ('One Year In: Meta’s Richland Parish Data Center Supports Louisiana Economy With $875M In Contracts', 'Facebook', 'Economy / Jobs', ('Meta',), 'LA', None, False),
    ('Report: Illinois data center boom could create 121K jobs, generate $300M annual property tax revenue', 'MyStateline', 'Economy / Jobs', (), 'IL', None, False),
    ('Cities in Pinal County Take Different Paths on Data Centers as Jobs and Infrastructure Shape Economic Development Debate', 'Real Estate Daily News', 'Economy / Jobs', (), 'AZ', None, False),
    ('Data centers in Washtenaw County: Economic boon or environmental liability?', 'concentratemedia', 'Economy / Jobs', (), 'MI', None, False),
    ('Data centers create jobs in central Ohio, but not in ways you might expect', 'The Columbus Dispatch', 'Economy / Jobs', (), 'OH', None, False),
    ('Meta data center – how it went from economic development coup to project local residents rue', 'BG Independent News', 'Economy / Jobs', ('Meta',), None, None, False),
    ('Vantage Data Center opponents push misleading claims on jobs | Opinion', 'Milwaukee Journal Sentinel', 'Analysis / Opinion', ('Vantage',), 'WI', None, False),
    ("Hudspeth County residents demand answers on $15B data center's noise, water and power", 'KFOX', 'Environment', (), 'TX', None, False),
    ('Texas Data Center Developers Play Offense on Water, Claiming Huge Cuts in Usage', 'Inside Climate News', 'Environment', (), 'TX', None, False),
    ('Kentucky is welcoming a data center boom. But what are the environmental costs?', 'The Courier-Journal', 'Environment', (), 'KY', None, False),
    ('Microsoft sued over noise complaints at new Mount Pleasant data center facility', 'WPR', 'Environment', ('Microsoft',), 'WI', None, False),
    ('Nye County totally bans data centers in over-appropriated water basin', 'Nevada Current', 'Environment', (), 'NV', None, False),
    ('DNR cites flaws and gaps in environmental review of northeast Minnesota data center', 'Star Tribune', 'Environment', (), 'MN', None, False),
    ('Amazon Tests Lower-Carbon Aluminum in Ohio Data Center Build', 'Environment+Energy Leader', 'Environment', ('Amazon',), 'OH', None, False),
    ('Google addresses power and noise questions at Palo data center open house', 'KGAN', 'Environment', ('Google',), 'IA', None, False),
    ('Teachers and Local Businesses Win as Meta Expands Louisiana Data Center', 'Facebook', 'Expansion', ('Meta',), 'LA', 'Expansion', False),
    ('Microsoft Expands Global Data Center Capacity with 2 GW Data Center and Co-Located Power Facility in West Texas', 'Orrick', 'Expansion', ('Microsoft',), 'TX', 'Expansion', False),
    ('Facebook Data Center Expands to the South', 'Grow Omaha', 'Expansion', ('Meta',), None, 'Expansion', False),
    ('After months of debate, Antelope Data Center moves forward in southern Utah', 'The Salt Lake Tribune', 'General', (), 'UT', None, False),
    ('Effort to block Reno data center offers glimpse of increasingly thorny issue in Nevada', 'Nevada Current', 'General', (), 'NV', None, False),
    ('Haskell County to host 30 microreactors for Texas data centers', 'BigCountryHomepage.com', 'Power / Utility', (), 'TX', None, False),
    ("'Boomtown' near Austin considers data center project as it preps for more", 'The Business Journals', 'General', (), 'TX', None, False),
    ('Data center could move into site of former Indianapolis drive-in', 'wthr.com', 'General', (), 'IN', None, False),
    ('Stack Infrastructure puts another data center in the pipeline', 'The Real Deal', 'General', ('STACK',), None, None, False),
    ('APR Energy obtains approval for 800-acre natural gas powered data center in Pampa, Texas', 'Data Center Dynamics', 'Land Acquisition', (), 'TX', 'Announced', False),
    ('New 150-acre data center campus aims to attract big tech companies to Louisville', 'The Courier-Journal', 'Land Acquisition', (), 'KY', None, False),
    ('Virginia-based data center company tied to roughly 180-acre purchase in Bastrop County', 'The Business Journals', 'Land Acquisition', (), 'TX', None, False),
    ('Power plant for data center on 2,000 acres in Granbury goes to public hearing', 'Fort Worth Star-Telegram', 'Land Acquisition', (), 'TX', 'Announced', False),
    ('Cloverleaf targets 200-acre data center development in Michigan', 'Data Center Dynamics', 'Land Acquisition', (), 'MI', None, False),
    ('New Meta facility in Louisiana may require 10,000-acre solar farm', 'FOX 8 Local First', 'Land Acquisition', ('Meta',), 'LA', None, False),
    ('1,000-acre AWS data center campus under consideration in Montgomery County, Missouri', 'Data Center Dynamics', 'Land Acquisition', ('Amazon',), 'MO', None, False),
    ('Oregon city has lowest data center vacancy rate among big US markets', 'The Business Journals', 'Markets / Earnings', (), 'OR', None, False),
    ('Riley County Planning Director shares details on data center moratorium', 'WIBW', 'Policy / Permits', (), 'KS', 'Announced', False),
    ('Corning shares jump 4% after company strikes deal to power Amazon AI data centers in U.S.', 'CNBC', 'Markets / Earnings', ('Amazon',), None, None, False),
    ('Galaxy Digital Q3 Beats Estimates on AI Data-Center Push', 'Briefs Finance', 'Markets / Earnings', ('Galaxy Digital',), None, None, False),
    ('Data centers and natural gas power plant planned on 2,200 acres in Pittsylvania County, Virginia', 'Data Center Dynamics', 'New Announcement', (), 'VA', 'Announced', False),
    ('Mapping where the proposed big data center sites are in Pittsburgh - Pittsburgh Business Times', 'The Business Journals', 'New Announcement', (), 'PA', 'Announced', False),
    ('Proposed data center concerns residents of Michigan’s Frenchtown Township', 'Toledo Blade', 'New Announcement', (), 'MI', 'Announced', False),
    ('Ashville residents push back on proposed data center plans', '10TV', 'New Announcement', (), 'OH', 'Announced', False),
    ('Maquoketa residents protest proposed data center', 'WQAD', 'New Announcement', (), 'IA', 'Announced', False),
    ('Meta plans $1 billion AI data center in Beaver Dam', 'WTMJ', 'New Announcement', ('Meta',), 'WI', 'Announced', False),
    ('Google plans for new data center in LaGrange', '11Alive.com', 'New Announcement', ('Google',), 'GA', 'Announced', False),
    ('Wisconsin village’s plan commission approves rezoning for Microsoft data center', 'WPR', 'New Announcement', ('Microsoft',), 'WI', 'Announced', False),
    ('Microsoft begins hiring for Mount Pleasant data center that opens in 2026. Expansions coming', 'Milwaukee Journal Sentinel', 'Operations', ('Microsoft',), 'WI', None, False),
    ("Meta boasts company's dedication to community as Mesa Data Center goes online", 'ABC15 Arizona', 'Operations', ('Meta',), 'AZ', 'Operational', False),
    ('Colovore Opens Second 9MW High-Density, Liquid-Cooled Data Center in Santa Clara', 'Business Wire', 'Operations', (), 'CA', 'Operational', False),
    ('Microsoft opens the Fairwater data center in Mount Pleasant', 'Civic Media', 'Operations', ('Microsoft',), 'WI', 'Operational', False),
    ('American Tower opens Edge data center in Raleigh, North Carolina', 'Data Center Dynamics', 'Operations', (), 'NC', 'Operational', False),
    ('Meta goes live in Temple with $1.2 billion AI data center', 'KWTX', 'Operations', ('Meta',), None, 'Operational', False),
    ('Weather-related data center outage led to US TikTok issues, Oracle says', 'Austin American-Statesman', 'Operations', ('Oracle',), 'TX', None, False),
    ('Small northern New Mexico city postpones decision on data center moratorium', 'Source New Mexico', 'Policy / Permits', (), 'NM', None, False),
    ('Moratorium on data centers is pending in northwest Iowa county', 'Radio Iowa', 'Policy / Permits', (), 'IA', None, False),
    ('After Mills vetoes statewide pause, Maine towns move to halt data center projects locally', 'WGME', 'Policy / Permits', (), 'ME', None, False),
    ('Minneapolis data center pause heads back to City Council', 'MPR News', 'Policy / Permits', (), 'MN', None, False),
    ('Mercer County issues moratorium on data centers', 'KFYR-TV', 'Cancelled / Blocked', (), 'ND', 'Cancelled / Blocked', True),
    ('Commissioners approve zone change for Vantage Data Center south of Cheyenne', 'Wyoming Tribune Eagle', 'Policy / Permits', ('Vantage',), 'WY', 'Announced', False),
    ('Prince William supervisors approve VA 8/9 data center rezoning to extend Iron Mountain campus', 'InsideNoVa', 'Policy / Permits', ('Iron Mountain',), 'VA', 'Announced', False),
    ('Data center ban in southwest Ohio city must go before voters, says Ohio Supreme Court', 'The Statehouse News Bureau', 'Politics', (), 'OH', None, False),
    ('National political action committees pour money into Kansas data center politics', 'KSHB 41 Kansas City', 'Politics', (), 'KS', None, False),
    ('Union leader issues data center ultimatum to Kansas political candidates', 'The Topeka Capital-Journal', 'Politics', (), 'KS', None, False),
    ('Congressional hopeful Jake Johnson backs data center moratorium in southern Minnesota', 'Bring Me The News', 'Politics', (), 'MN', None, False),
    ('Pulaski County judge candidate warns against veto ahead of data center vote', 'thv11.com', 'Politics', (), 'AR', None, False),
    ('Trump criticizes New York data center moratorium', 'Reuters', 'Politics', (), 'NY', None, False),
    ('US hosting firm Patmos to convert former printing press in Kansas City into 100MW data center', 'Data Center Dynamics', 'Power / Utility', (), 'MO', None, False),
    ('Blakely to add a layer of data center regulations through electric company', 'Scranton Times-Tribune', 'Power / Utility', (), 'PA', None, False),
    ('Energy demand will outstrip supply in Virginia as data centers proliferate', 'Cardinal News', 'Power / Utility', (), 'VA', None, False),
    ('Ellison: Google’s Pine Island data center could cost Minnesotans millions for electricity', 'MPR News', 'Power / Utility', ('Google',), 'MN', None, False),
    ('Cheyenne to host massive AI data center using more electricity than all Wyoming homes combined', 'AP News', 'Power / Utility', (), 'WY', None, False),
    ('Google pushes data center growth with natural gas', 'Oklahoma Energy Today', 'Power / Utility', ('Google',), None, None, False),
]


@pytest.mark.parametrize("title,source,category,companies,state,stage,cancelled", HEADLINES, ids=[h[0][:60] for h in HEADLINES])
def test_archive_headline(title, source, category, companies, state, stage, cancelled):
    it = tag(title, source)
    assert it is not None, "dropped by the topic or U.S. filter"
    assert it["category"] == category
    assert tuple(it["companies"]) == companies
    assert it["state"] == state
    assert fn.guess_status(title) == stage
    assert fn.is_cancelled(title) == cancelled


def test_enough_archive_headlines_across_topics():
    assert len(HEADLINES) >= 80
    topics = {h[2] for h in HEADLINES}
    assert len(topics) >= 15, topics


# Names that are also common words only count with a qualifying word next to them.
GUARDED = [
    ("Stream files to build 48MW data center in Dallas, Texas", "Stream"),
    ("ComEd breaks ground on 260MW substation set to serve Stream data center in Elk Grove, Illinois", "Stream"),
    ("Prime opens 243K sf data center in Vernon leased to two AI firms", "Prime Data Centers"),
    ("Prime Data Centers looks to expand at McClellan Business Park", "Prime Data Centers"),
    ("Element Critical breaks ground on 10MW data center expansion in Houston, Texas", "Element Critical"),
    ("Edged tops out Phoenix data center in Arizona", "Edged"),
    ("Edged eyes 725MW data center campus in Pennsylvania", "Edged"),
    ("Galaxy Secures ERCOT Approval to Double Helios Data Center Power to 1.6 GW", "Galaxy Digital"),
    ("Galaxy Digital plans mega data center campus near Waco", "Galaxy Digital"),
    ("Lambda and Cologix launch Nvidia HGX B200 clusters in Columbus, Ohio", "Lambda"),
    ("Switch plans second data center expansion at pyramid campus in Kent County", "Switch"),
    ("Tract withdraws data center application after Chesterfield recommends against it", "Tract"),
]
NOT_ORGS = [
    "Expansion of Powhatan data center along Page Road denied by planning commission",
    "Data center proposed for 500-acre site in Page, Arizona",
    "Prime site: AWS announces U.S. 61 site for Vicksburg data center",
    "Suffolk approves temporary ban on data centers",
    "Redefine Your Data Center with New Cisco N9300 Series Smart Switch Innovations",
    "Who's behind 'Project Apollo'? New details revealed about Miami-Dade data center",
    "Wesco International completes acquisition of data-center service firm Ascent",
    "Data center stocks edged lower on Tuesday",
    "A stream of complaints about the data center",
]


@pytest.mark.parametrize("title,name", GUARDED)
def test_guarded_name_matches(title, name):
    assert name in fn.find_companies(title)


@pytest.mark.parametrize("title", NOT_ORGS)
def test_common_word_is_not_an_organisation(title):
    words = {"Page", "Prime", "Suffolk", "Switch", "Apollo", "Ascent", "Stream", "Edged", "Galaxy", "Element"}
    found = (fn.find_companies(title) + fn.find_orgs(fn.INVESTOR_RULES, title) + fn.find_orgs(fn.BUILDER_RULES, title)
             + fn.find_orgs(fn.SUPPLIER_RULES, title))
    assert not [f for f in found if f.split()[0] in words]


def test_meta_prometheus_is_not_prometheus_hyperscale():
    assert fn.find_companies("Prometheus Hyperscale details plans for Dallas data center campus") == ["Prometheus Hyperscale"]
    assert "Meta" in fn.find_companies("Meta's Prometheus supercluster in Ohio comes online")


# Stage signals: a stage word counts only when it is the project's present stage.
STAGES = [
    ("Planned $1.1B data center campus near Benbrook could break ground this summer", "Announced"),
    ("Meta’s mega data center in Kuna on track to be completed by 2025", None),
    ("Novva Secures $2B to Complete Utah Data Center Campus Construction", "Announced"),
    ("Microsoft begins hiring for Mount Pleasant data center that opens in 2026. Expansions coming", None),
    ("Will Vantage live up to jobs expectations when AI facility opens in Port Washington?", None),
    ("Massive Texas solar farm opens to power Google data centers", None),
    ("Data center supplier opens $7.4M factory in rural Orangeburg County", None),
    ("Flexential Completes Atlanta Data Center Purchase", None),
    ("Amazon completes its application for a data center in Walla Walla County", None),
    ("CBJ Newsmakers: First QTS data center buildings near completion", "Under construction"),
    ("Amazon opens $11 billion AI data center in rural Indiana as rivals race to break ground", "Operational"),
    ("Microsoft data centers coming to Heath, Hebron after groundbreaking", "Under construction"),
    ("$16 billion data center campus in Saline Township secures financing, construction underway", "Under construction"),
    ("Crusoe Announces Flagship Abilene Data Center is Live", "Operational"),
    ("OpenAI expands Oracle data center deal, says parts of Stargate 1 in Texas are operational", "Operational"),
    ("Google invests $1.5B to expand Jackson County data center", "Expansion"),
    ("AWS opens Richmond County, North Carolina data center", "Operational"),
    ("Meta begins construction of $10 billion Indiana data center to boost AI capabilities", "Under construction"),
]


@pytest.mark.parametrize("title,stage", STAGES)
def test_stage_signal(title, stage):
    assert fn.guess_status(title) == stage


# Cancelled / Blocked, and look-alikes that are not.
CANCELS = [
    ("Google officially withdraws plans for data center in Franklin Township", True),
    ("Tucson City Council rejects Project Blue data center amid intense community pressure", True),
    ("Cedar Hill imposes two-year moratorium on data centers", True),
    ("Mercer County issues moratorium on data centers", True),
    ("Amazon pulls back on plans for large data center in Becker", True),
    ("PSC votes against requiring Meta to reveal more about data center", False),
    ("Pond near Oracle, OpenAI data center construction site recovering after level drops", False),
    ("Fort Wayne city councilman withdraws proposal for data center task force in light of new proposal", False),
    ("Republican governor candidate Stacy Garrity calls for 'pause' on data center development", False),
    ("Maine groups join call for U.S. data center moratorium", False),
    ("Ohio Supreme Court blocks citizen-led data center referendum from appearing on ballot in Wilmington", False),
    ("Marana rejects referendums against Project Blue data center rezoning", False),
]


@pytest.mark.parametrize("title,cancelled", CANCELS)
def test_cancelled_flag(title, cancelled):
    assert fn.is_cancelled(title) == cancelled
    assert (fn.guess_status(title) == fn.CANCELLED) == cancelled


# Investors, builders, suppliers and utilities are separate from operators.
ORGS = [
    ("Apollo Global to Buy Builder of Large-Scale US Data Centers", "investors", "Apollo"),
    ("Meta plans $35bn data center fund, Apollo Global in talks to lead - report", "investors", "Apollo"),
    ("Walbridge breaks ground on $16B Stargate data center", "investors", "SoftBank"),
    ("Hut 8 partners with Jacobs for engineering, construction management services for West Feliciana data center", "builders", "Jacobs"),
    ("Carrier Plans $600 Million Texas Plant to Make Cooling Gear for AI Data Centers", "suppliers", "Carrier"),
    ("Vertiv shares jump 14 percent as data center earnings beat expectations", "suppliers", "Vertiv"),
    ("Entergy files for gas plants to serve Meta's Richland Parish data center", "utilities", "Entergy"),
]


@pytest.mark.parametrize("title,field,name", ORGS)
def test_organisation_fields(title, field, name):
    it = tag(title)
    assert it is not None
    assert name in it[field]
    assert name not in it["companies"]


def test_stargate_names_operators_and_investor():
    it = tag("Walbridge breaks ground on $16B Stargate data center")
    assert it["companies"] == ["Oracle", "OpenAI"] and it["investors"] == ["SoftBank"]


# Project names in headlines.
HINTS = [
    ("Plans for $17 billion ‘Project Sail’ data center proposed for Coweta County", "Project Sail"),
    ("Project Caprock Data Center Construction Begins in Hale County, Texas With First Facility", "Project Caprock"),
    ("Wildcat Ridge Data Center in Archbald to use huge amounts of power, water", "Wildcat Ridge Data Center"),
    ("Data center developer Stack Infrastructure expanding New Albany campus with 330,000-square-foot building", "New Albany campus"),
    ("Neighbors react to potential data center coming to Wood Haven Technology Park", "Wood Haven Technology Park"),
    ("Record $16B Data Center Project Advances in Michigan", None),
    ("Bulloch County Commissioners approve 90-Day Data Center Moratorium", None),
    ("Fleet Data Centers Raises $3.8 Billion to Build Out 230MW Data Center Campus in Texas", None),
    ("Project Profile: Reimagining U.S. Data Centers to Better Serve the Planet in San Jose", None),
]


@pytest.mark.parametrize("title,hint", HINTS)
def test_name_hint(title, hint):
    assert fn.name_hint(title) == hint


# The topic filter (about data centers) and the U.S. filter.
DROPPED = [
    ("Infineon unveils world’s thinnest silicon power wafers", "Data Center Dynamics"),
    ("Virgin Media O2 sells additional 8% stake in towers JV to Equitix", "Data Center Dynamics"),
    ("Eaton wins contract to install power infrastructure at NY Creates NanoFab research facility", "Test Outlet"),
    ("Silknet Breaks Ground on Georgia's First Tier III Certified Commercial Data Center", "BM.GE"),
    ("Brookfield plans to spend $10bn on a Swedish AI data center", "Test Outlet"),
    ("Wall Street's favorite data center stock", "Motley Fool"),
]


@pytest.mark.parametrize("title,source", DROPPED)
def test_dropped(title, source):
    assert tag(title, source) is None


def test_us_place_keeps_a_story_with_a_foreign_word():
    it = tag("Swiss firm buys Georgia data center site")
    assert it is not None and it["state"] == "GA"


def test_ambiguous_town_needs_a_state():
    # "Lansing" is in four states: it is placed only when the story or the outlet names one.
    assert tag("TeraWulf data center plan draws crowd in Lansing")["state"] is None
    assert tag("TeraWulf data center plan draws crowd in Lansing, New York")["state"] == "NY"


def test_outlet_home_state_is_a_last_resort():
    it = tag("County board approves data center rules", "WSMV")
    assert it["state"] == "TN" and it["location_precision"] == "source"
