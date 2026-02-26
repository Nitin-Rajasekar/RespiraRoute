"""
RAG Knowledge Base for RespiraRoute.

Provides zone-specific and city-level context retrieved at inference time
to ground LLM anomaly explanations in local facts (pollution sources,
land use, topography) and CPCB/WHO health guidelines.
"""

# ── CPCB AQI Health Guidelines ───────────────────────────────────────
AQI_GUIDELINES = [
    {
        "range": (0, 50),
        "category": "Good",
        "health_impact": "Minimal impact. Air quality is satisfactory.",
        "advisory": "No restrictions. Ideal for outdoor activities.",
    },
    {
        "range": (51, 100),
        "category": "Moderate",
        "health_impact": "Minor breathing discomfort for sensitive individuals with lung disease.",
        "advisory": "Unusually sensitive people should consider limiting prolonged outdoor exertion.",
    },
    {
        "range": (101, 150),
        "category": "Unhealthy for Sensitive Groups",
        "health_impact": "Breathing discomfort for people with asthma, lung disease, elderly, and children.",
        "advisory": "Sensitive groups should limit prolonged outdoor exertion. General public OK.",
    },
    {
        "range": (151, 200),
        "category": "Unhealthy",
        "health_impact": "Breathing discomfort for most people. Serious health effects for sensitive groups.",
        "advisory": "Everyone should reduce prolonged outdoor exertion. Sensitive groups should avoid outdoor activity.",
    },
    {
        "range": (201, 300),
        "category": "Very Unhealthy",
        "health_impact": "Respiratory illness probable on prolonged exposure. Serious effects for sensitive groups.",
        "advisory": "Avoid prolonged outdoor activity. Wear N95 masks outdoors. Sensitive groups stay indoors.",
    },
    {
        "range": (301, 500),
        "category": "Hazardous",
        "health_impact": "Health warnings — everyone may experience serious health effects.",
        "advisory": "Avoid all outdoor activity. Keep windows closed. Use air purifiers indoors.",
    },
]

# ── City-Level Context ───────────────────────────────────────────────
CITY_CONTEXT = {
    "Delhi": (
        "Delhi sits in the Indo-Gangetic Plain, a low-lying basin that traps pollutants due to "
        "temperature inversions, especially in winter. Major sources include vehicular exhaust "
        "(11 million registered vehicles), construction dust, industrial emissions from NCR, "
        "and seasonal crop stubble burning from Punjab/Haryana (Oct–Nov). Calm winds and fog "
        "compound pollution events. Delhi consistently ranks among the world's most polluted capitals."
    ),
    "Mumbai": (
        "Mumbai's coastal geography means sea breezes typically help disperse pollutants, but "
        "the eastern suburbs and industrial belts see higher AQI. Vehicular emissions, port "
        "activities, and construction are primary sources. Monsoon season (Jun–Sep) dramatically "
        "improves air quality; post-monsoon and winter months are worst. High humidity can "
        "increase PM2.5 absorption."
    ),
    "Bangalore": (
        "Bangalore sits on the Deccan Plateau at ~920m elevation, which generally favours "
        "dispersion. However, rapid urbanisation has tripled traffic density over a decade. "
        "IT corridor zones see peak-hour vehicular pollution spikes. Low average wind speeds "
        "(3–8 km/h) reduce dispersion. Construction boom adds significant dust. The city has "
        "no major industry inside limits, so vehicles and construction dominate AQI."
    ),
    "Chennai": (
        "Chennai's coastal location provides natural ventilation, but the city has significant "
        "industrial activity in Guindy and Manali (north). Vehicular pollution is the primary "
        "urban AQI driver. Northeast monsoon (Oct–Dec) can bring both relief and trapping "
        "conditions. Industrial zones near the port and the Ennore area are chronic hotspots."
    ),
    "Kolkata": (
        "Kolkata has one of India's highest vehicle fleet densities and is surrounded by "
        "industrial clusters in Howrah and Durgapur. River valley geography limits dispersion "
        "during winter temperature inversions. Coal and biomass burning for cooking remains "
        "prevalent. The city historically records high PM10 from construction and unpaved roads."
    ),
    "Hyderabad": (
        "Hyderabad's rapid IT expansion has led to massive construction activity — a primary "
        "PM10 source. The city sits on a rocky plateau with moderate winds. HITEC City and "
        "Gachibowli see peak vehicular emissions during tech industry work hours. The old city "
        "(Charminar area) has dense traffic and traditional small industries. Granite quarrying "
        "in the periphery adds dust load."
    ),
    "Pune": (
        "Pune experiences distinct seasonal pollution patterns: winter inversions trap emissions, "
        "while the pre-monsoon dust storms add PM10. The Hinjewadi IT belt sees peak vehicle "
        "emissions. Hadapsar and Bhosari have industrial clusters. Pune's bowl-shaped topography "
        "surrounded by the Sahyadri ranges reduces wind dispersal in calm conditions."
    ),
    "Ahmedabad": (
        "Ahmedabad is one of India's most industrialised cities — textile mills, chemical plants, "
        "and dyeing units around Vatva and Naroda are major sources. Semi-arid climate means "
        "fugitive dust is a year-round problem. Low humidity and high temperatures drive ozone "
        "formation. SG Highway sees heavy vehicular load from satellite town commuters."
    ),
    "Jaipur": (
        "Jaipur's desert geography means fugitive dust from unpaved surfaces and construction "
        "is a dominant PM10 source. Vehicle fleet is growing rapidly. Sandstone quarrying and "
        "gem-polishing industries near the city add silica dust. Winter temperature inversions "
        "trap diesel exhaust. Rajasthan's dry climate means dust storms (andhi) can spike AQI "
        "dramatically within minutes."
    ),
    "Lucknow": (
        "Lucknow lies in the Indo-Gangetic Plain — prone to winter smog and temperature "
        "inversions similar to Delhi. Biomass burning for heating in peri-urban areas adds to "
        "winter AQI. Heavy vehicle traffic through the city centre and construction for "
        "infrastructure upgrades are year-round sources. Gomti riverbed dust contributes during "
        "dry months."
    ),
}

# ── Zone-Specific Context ────────────────────────────────────────────
ZONE_CONTEXT = {
    # Delhi
    "Connaught Place": "Central business district with extremely high footfall (~500k/day). Dense bus and auto-rickshaw traffic on radial roads. Surrounding underground construction for metro adds dust. Commercial generators active during power outages.",
    "Dwarka": "Planned residential suburb in southwest Delhi. Metro-connected but still high private vehicle use. Near IGI Airport — aviation fuel emissions and ground traffic contribute. Largely residential with lower industrial load than central Delhi.",
    "Anand Vihar": "One of Delhi's most polluted zones — major interstate bus terminal (ISBT) with thousands of diesel buses daily. Adjacent to UP border; goods trucks queue here. Rail yards add diesel particulates. Narrow streets trap exhaust.",
    "ITO": "Major arterial intersection in central Delhi. Extremely high through-traffic (government offices, courts, media hub). Yamuna riverbed dust blows in from the east during dry months. Construction along ring road adds PM10.",
    "Rohini": "Large planned residential district in northwest Delhi. High population density with significant two-wheeler and auto traffic. Nearby industrial areas in Mundka contribute on westerly winds. Cooler and calmer than south Delhi in winter.",
    # Mumbai
    "Bandra": "Upscale residential and commercial hub — sea breeze from the Arabian Sea generally helps, but the Bandra-Kurla Complex (BKC) office corridor generates peak-hour vehicular spikes. Construction of coastal road and metro contributes dust.",
    "Andheri": "Mumbai's largest suburb and commercial hub. SEEPZ industrial zone adds emissions. Proximity to the airport means low-altitude aircraft contribute to local NOx. One of the most congested arterials in the western suburbs.",
    "Colaba": "Southernmost tip of Mumbai — best natural ventilation of all city zones due to sea on three sides. Lower industrial load. Pollution mainly from tourist traffic and the busy navy/port areas. AQI spikes are rare and usually weather-driven.",
    "Worli": "Mixed residential-commercial zone on the western waterfront. Bandra-Worli Sea Link traffic adds vehicular load. Construction activity on the coastal road project has raised dust levels significantly over recent years.",
    "Powai": "IT and educational hub in eastern Mumbai. Surrounded by Sanjay Gandhi National Park — usually lower AQI than western suburbs. Hiranandani construction and Powai Lake evaporation can trap pollutants in the valley during calm nights.",
    # Bangalore
    "MG Road": "Bangalore's historic commercial spine — high footfall, dense bus/auto traffic, and restaurant/hotel generators. Narrow streets between tall buildings create canyon effect that traps exhaust. Metro construction in earlier years left residual dust.",
    "Whitefield": "Major IT corridor (TCS, SAP, IBM campuses) with 300k+ daily commuters. Vehicle-dominant commute pattern; limited public transport. Peak-hour AQI spikes are among the highest in Bangalore. Surrounded by peri-urban construction.",
    "Electronic City": "Bangalore's oldest IT hub (Infosys, Wipro HQ). Located on the southern periphery — fewer traffic signals, but high vehicle density on NICE Road. Industrial units in adjacent Bommasandra add periodic emissions.",
    "Koramangala": "Dense mixed-use neighbourhood — startups, restaurants, residential. High two-wheeler density. Poor road design causes idling traffic. Proximity to Sarjapur Road construction corridor adds dust. One of Bangalore's highest vehicular-density zones.",
    "Hebbal": "Northern gateway to Bangalore — major flyover interchange handles lakhs of vehicles daily. Proximity to Yelahanka Air Force Station. Hebbal lake provides some greenery but the outer ring road generates sustained exhaust load.",
    # Chennai
    "T Nagar": "Chennai's busiest commercial district — one of the highest retail footfalls in India. Dense bus terminus (CMBT nearby) and auto-rickshaw hub. Narrow streets trap diesel exhaust. Significant generator use during grid outages.",
    "Adyar": "Southern residential zone near the coast — Adyar river and Theosophical Society greenery improve local air. Generally lower AQI than central Chennai. Periodic construction projects along the ECR corridor add dust.",
    "Anna Nagar": "Planned residential grid with wider roads — better ventilation than T Nagar. High car ownership; significant private vehicle use. Proximity to CMBT and Koyambedu market (produce vehicles) raises vehicle density on the western edge.",
    "Guindy": "Industrial estate with automotive and engineering units — one of Chennai's highest industrial AQI contributors. Proximity to the airport adds aviation emissions. The IIT Madras campus buffer provides some green cover.",
    "Velachery": "Rapidly urbanising southern suburb. High construction activity for apartments raises PM10. Pallikaranai marshland nearby helps buffer; however, old landfill sites contribute methane and particulates.",
    # Kolkata
    "Park Street": "Kolkata's entertainment and commercial hub — dense vehicular traffic, restaurants, and hotel generators. Narrow colonial-era streets trap exhaust. High footfall adds to resuspension of road dust.",
    "Salt Lake": "Planned satellite township with wider roads — generally better dispersed than central Kolkata. IT sector offices generate peak-hour vehicle emissions. Proximity to the EKW wetlands provides some buffer.",
    "Howrah": "Major industrial and rail hub — Howrah Station has 600+ trains daily, contributing diesel exhaust. Steel foundries, jute mills, and chemical plants along the Hooghly river are chronic sources. Among Kolkata's most polluted zones.",
    "New Town": "Recently developed IT and residential zone (Rajarhat) — newer infrastructure but rapid construction activity raises dust significantly. Far from industrial zones; vehicular emissions dominate. Growing but still less congested than central Kolkata.",
    "Jadavpur": "Mixed residential-industrial zone in south Kolkata. Chemical industries and engineering workshops contribute. Jadavpur University area has some green cover. Traffic on EM Bypass adds vehicular load.",
    # Hyderabad
    "HITEC City": "Hyderabad's IT showpiece — Microsoft, Google, Facebook campuses. 200k+ peak-hour commuters; limited metro coverage means high car dependency. Construction of flyovers and office towers has been near-continuous for a decade.",
    "Secunderabad": "Major rail junction and cantonment area — diesel locomotive exhaust from Secunderabad station is a significant NOx source. Military establishments add some buffer greenery. Old commercial areas have dense bus/truck traffic.",
    "Gachibowli": "IT and financial district on the western edge — proximity to Hyderabad's outer ring road means heavy goods vehicle transit. University of Hyderabad campus provides green buffer. Construction near Financial District raises dust.",
    "Charminar": "Historic old city core — one of Hyderabad's most congested zones. Traditional industries (bangle-making, leather, biryani restaurants with coal fires). Narrow streets, minimal public transport, high two-wheeler density. Tourism traffic adds to load.",
    "Banjara Hills": "Upscale residential and commercial zone — high-end restaurants, hotels, hospitals. Relatively wider roads. Road No. 1 and 12 are major arterials. Large private vehicles (SUVs) dominate; fewer two-wheelers. Lower industrial load.",
    # Pune
    "Shivaji Nagar": "Pune's administrative and commercial centre — government offices, courts, and Deccan gymkhana. High bus and auto-rickshaw density. Older building stock with poor ventilation in congested pockets.",
    "Hinjewadi": "Pune's major IT park (Infosys, Wipro, TCS) — heavy peak-hour congestion on the Hinjewadi-Wakad corridor. Limited metro connectivity forces car dependency. Construction in Phases 2 and 3 adds significant dust.",
    "Kothrud": "Large residential suburb — relatively planned layout with some green cover. Growing vehicle density as population expands. Proximity to Chandni Chowk commercial area raises traffic. Generally lower AQI than eastern industrial Pune.",
    "Hadapsar": "Eastern Pune — mix of IT (Magarpatta City, SP Infocity) and traditional industries (Bhosari industrial belt nearby). High truck traffic on Solapur Road. One of Pune's faster-growing zones with significant construction dust.",
    "Viman Nagar": "Proximity to Pune Airport means aviation emissions and ground traffic contribute. IT offices (EON IT Park) generate peak-hour vehicular load. Rapidly developing residential zone with ongoing construction.",
    # Ahmedabad
    "SG Highway": "Satellite Gandhidham Highway — major arterial connecting Ahmedabad to satellite towns. High-speed vehicle corridor with significant particulate resuspension from arid road surfaces. Commercial development along the strip adds generators and vehicles.",
    "Maninagar": "Traditional residential and commercial zone in eastern Ahmedabad — denser and older than western areas. Proximity to Vatva industrial estate means industrial plumes on easterly winds. High two-wheeler and CNG auto density.",
    "Navrangpura": "Central Ahmedabad — educational institutions and commercial offices. Relatively better planned than eastern zones. Ellis Bridge traffic and BRTS corridor improve flow but add diesel particulates.",
    "Vastrapur": "Upscale residential zone near Vastrapur Lake — one of Ahmedabad's greener neighbourhoods. IIM Ahmedabad campus provides buffer. SG Highway traffic on the western edge is the primary AQI contributor.",
    "Chandkheda": "Northern suburb near Sabarmati and GIFT City — rapid development brings construction dust. Proximity to the Ahmedabad-Gandhinagar highway adds truck traffic. Some chemical and pharmaceutical units in the periphery.",
    # Jaipur
    "MI Road": "Jaipur's main commercial artery — high bus, auto, and tourist vehicle density. Sandstone construction dust from Pink City restoration projects. Gem and jewellery workshops use polishing compounds that add fine particulates.",
    "Malviya Nagar": "Southern residential suburb — growing IT presence (Mahindra World City nearby). Relatively newer development with wider roads. Marble and stone processing units in the outskirts add silica dust on southerly winds.",
    "Vaishali Nagar": "Large planned residential township in western Jaipur — high private car ownership. Proximity to Delhi-Jaipur highway means truck transit pollution. Arid surroundings contribute fugitive dust on windy days.",
    "Mansarovar": "One of Jaipur's largest residential areas — mix of middle-income housing and small commercial units. Significant two-wheeler density. Southern bypass construction adds dust. Cooler microclimate slightly reduces photochemical smog.",
    "C-Scheme": "Upscale administrative zone — embassies, government bungalows, and hotels. Rajasthan Secretariat traffic concentrated here. Better greenery than commercial zones. Primarily vehicular emissions from official convoys and private cars.",
    # Lucknow
    "Hazratganj": "Lucknow's historic commercial and cultural hub — dense footfall, auto-rickshaws, tourist buses. Old building fabric traps exhaust in narrow lanes. Proximity to the district courts adds official vehicle traffic. Key pollution hotspot.",
    "Gomti Nagar": "Modern planned township along the Gomti river — government and IT offices. Wider roads improve dispersal, but peak-hour traffic on Vibhuti Khand and Faizabad Road is heavy. Gomti riverbed dust blows in from the east in dry months.",
    "Aliganj": "Large residential suburb north of Lucknow — high population density, significant two-wheeler use. Proximity to Lucknow-Sitapur highway adds truck traffic at the edges. Local markets and small industries contribute.",
    "Indira Nagar": "Eastern Lucknow residential zone — growing commercial activity along Faizabad Road. Relatively newer development but rapid infill construction raises dust. Shopping malls and multiplexes generate generator exhaust during power cuts.",
    "Aminabad": "Dense old-city commercial zone — one of Lucknow's most congested markets. Narrow lanes, high vehicle density, street food vendors (coal/wood fires), and frequent power outages driving generator use. Among Lucknow's highest AQI zones.",
}


def retrieve_context(zone: str, city: str, aqi: int) -> str:
    """
    Retrieve relevant knowledge base entries for a given zone, city, and AQI level.
    Returns a formatted string ready for injection into an LLM prompt.
    """
    parts = []

    # 1. AQI guideline for this level
    guideline = next(
        (g for g in AQI_GUIDELINES if g["range"][0] <= aqi <= g["range"][1]),
        AQI_GUIDELINES[-1],
    )
    parts.append(
        f"CPCB Standard — {guideline['category']} (AQI {guideline['range'][0]}–{guideline['range'][1]}): "
        f"{guideline['health_impact']} Advisory: {guideline['advisory']}"
    )

    # 2. City-level context
    city_fact = CITY_CONTEXT.get(city)
    if city_fact:
        parts.append(f"City context ({city}): {city_fact}")

    # 3. Zone-specific context
    zone_fact = ZONE_CONTEXT.get(zone)
    if zone_fact:
        parts.append(f"Zone context ({zone}): {zone_fact}")

    return "\n\n".join(parts)
