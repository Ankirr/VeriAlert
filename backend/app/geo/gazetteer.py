"""
Regional Indian and Neighboring Transboundary Gazetteer.
Provides alias normalization, river basin mappings, and state/regional centroids.
"""
from typing import Dict, Any, Optional, Tuple

# Centroids for all Indian States & Union Territories (Lat, Lon)
STATE_CENTROIDS: Dict[str, Tuple[float, float]] = {
    "andhra pradesh": (15.9129, 79.7400),
    "arunachal pradesh": (28.2180, 94.7278),
    "assam": (26.2006, 92.9376),
    "bihar": (25.0961, 85.3131),
    "chhattisgarh": (21.2787, 81.8661),
    "goa": (15.2993, 74.1240),
    "gujarat": (22.2587, 71.1924),
    "haryana": (29.0588, 76.0856),
    "himachal pradesh": (31.1048, 77.1734),
    "jharkhand": (23.6102, 85.2799),
    "karnataka": (15.3173, 75.7139),
    "kerala": (10.8505, 76.2711),
    "madhya pradesh": (22.9734, 78.6569),
    "maharashtra": (19.7515, 75.7139),
    "manipur": (24.6637, 93.9063),
    "meghalaya": (25.4670, 91.3662),
    "mizoram": (23.1645, 92.9376),
    "nagaland": (26.1584, 94.5624),
    "odisha": (20.9517, 85.0985),
    "punjab": (31.1471, 75.3412),
    "rajasthan": (27.0238, 74.2179),
    "sikkim": (27.5330, 88.5122),
    "tamil nadu": (11.1271, 78.6569),
    "telangana": (18.1124, 79.0193),
    "tripura": (23.9408, 91.9882),
    "uttar pradesh": (26.8467, 80.9462),
    "uttarakhand": (30.0668, 79.0193),
    "west bengal": (22.9868, 87.8550),
    # Union Territories
    "delhi": (28.7041, 77.1025),
    "nct of delhi": (28.7041, 77.1025),
    "jammu and kashmir": (33.7782, 76.5762),
    "ladakh": (34.1526, 77.5771),
    "chandigarh": (30.7333, 76.7794),
    "puducherry": (11.9416, 79.8083),
    "andaman and nicobar islands": (11.7401, 92.6586),
    "lakshadweep": (10.5667, 72.6417),
    "dadra and nagar haveli and daman and diu": (20.4283, 72.8397),
    # Neighboring countries & transboundary regions
    "nepal": (28.3949, 84.1240),
    "bangladesh": (23.6850, 90.3563),
    "bhutan": (27.5142, 90.4336),
    "china": (35.8617, 104.1954),
    "tibet": (29.8556, 90.8750),
    "xizang": (29.8556, 90.8750),
    "lhasa": (29.6542, 91.1173),
    # Marine & special zones
    "bay of bengal": (15.0000, 88.0000),
    "arabian sea": (15.0000, 68.0000),
    "western rajasthan": (26.9157, 70.9083),
    "coastal karnataka": (12.9141, 74.8560),
    "bhotekoshi": (27.8772, 85.8922),
    "sindhupalchok": (27.8000, 85.7500),
    "melamchi": (27.8288, 85.5807),
    "damodar": (23.5000, 87.3000),
    "damodar valley": (23.5000, 87.3000),
    "bengal": (22.9868, 87.8550),
    "india": (20.5937, 78.9629)
}

# Regional / District / City to State / Country Aliases
REGIONAL_ALIASES: Dict[str, Dict[str, str]] = {
    # Delhi NCR & Landmarks
    "delhi": {"city": "Delhi", "state": "Delhi", "country": "India"},
    "new delhi": {"city": "New Delhi", "state": "Delhi", "country": "India"},
    "delhi ncr": {"city": "Delhi", "state": "Delhi", "country": "India"},
    "noida": {"city": "Noida", "state": "Uttar Pradesh", "country": "India"},
    "gurugram": {"city": "Gurugram", "state": "Haryana", "country": "India"},
    "gurgaon": {"city": "Gurugram", "state": "Haryana", "country": "India"},
    "ghaziabad": {"city": "Ghaziabad", "state": "Uttar Pradesh", "country": "India"},
    "faridabad": {"city": "Faridabad", "state": "Haryana", "country": "India"},
    "igi airport": {"city": "Delhi", "state": "Delhi", "country": "India"},
    "delhi airport": {"city": "Delhi", "state": "Delhi", "country": "India"},
    
    # Bihar vulnerable districts & cities
    "patna": {"city": "Patna", "state": "Bihar", "country": "India"},
    "gandhi ghat": {"city": "Patna", "state": "Bihar", "country": "India"},
    "saran": {"city": "Chhapra", "state": "Bihar", "country": "India"},
    "chhapra": {"city": "Chhapra", "state": "Bihar", "country": "India"},
    "darbhanga": {"city": "Darbhanga", "state": "Bihar", "country": "India"},
    "bhagalpur": {"city": "Bhagalpur", "state": "Bihar", "country": "India"},
    "muzaffarpur": {"city": "Muzaffarpur", "state": "Bihar", "country": "India"},
    "gaya": {"city": "Gaya", "state": "Bihar", "country": "India"},
    "supaul": {"city": "Supaul", "state": "Bihar", "country": "India"},
    "saharsa": {"city": "Saharsa", "state": "Bihar", "country": "India"},
    "madhubani": {"city": "Madhubani", "state": "Bihar", "country": "India"},
    "motihari": {"city": "Motihari", "state": "Bihar", "country": "India"},
    "purnia": {"city": "Purnia", "state": "Bihar", "country": "India"},
    "katihar": {"city": "Katihar", "state": "Bihar", "country": "India"},
    
    # Himachal Pradesh & Uttarakhand (Hill Calamities)
    "shimla": {"city": "Shimla", "state": "Himachal Pradesh", "country": "India"},
    "mandi": {"city": "Mandi", "state": "Himachal Pradesh", "country": "India"},
    "kullu": {"city": "Kullu", "state": "Himachal Pradesh", "country": "India"},
    "manali": {"city": "Manali", "state": "Himachal Pradesh", "country": "India"},
    "dharamshala": {"city": "Dharamshala", "state": "Himachal Pradesh", "country": "India"},
    "kinnaur": {"city": "Reckong Peo", "state": "Himachal Pradesh", "country": "India"},
    "dehradun": {"city": "Dehradun", "state": "Uttarakhand", "country": "India"},
    "chamoli": {"city": "Gopeshwar", "state": "Uttarakhand", "country": "India"},
    "joshimath": {"city": "Joshimath", "state": "Uttarakhand", "country": "India"},
    "kedarnath": {"city": "Kedarnath", "state": "Uttarakhand", "country": "India"},
    "badrinath": {"city": "Badrinath", "state": "Uttarakhand", "country": "India"},
    "rudraprayag": {"city": "Rudraprayag", "state": "Uttarakhand", "country": "India"},
    "uttarkashi": {"city": "Uttarkashi", "state": "Uttarakhand", "country": "India"},
    "rishikesh": {"city": "Rishikesh", "state": "Uttarakhand", "country": "India"},
    "haridwar": {"city": "Haridwar", "state": "Uttarakhand", "country": "India"},
    "nainital": {"city": "Nainital", "state": "Uttarakhand", "country": "India"},
    
    # Assam & Northeast (Brahmaputra / Landslides)
    "guwahati": {"city": "Guwahati", "state": "Assam", "country": "India"},
    "dibrugarh": {"city": "Dibrugarh", "state": "Assam", "country": "India"},
    "silchar": {"city": "Silchar", "state": "Assam", "country": "India"},
    "jorhat": {"city": "Jorhat", "state": "Assam", "country": "India"},
    "tezpur": {"city": "Tezpur", "state": "Assam", "country": "India"},
    "kaziranga": {"city": "Kaziranga", "state": "Assam", "country": "India"},
    "shillong": {"city": "Shillong", "state": "Meghalaya", "country": "India"},
    "cherrapunji": {"city": "Sohra", "state": "Meghalaya", "country": "India"},
    "gangtok": {"city": "Gangtok", "state": "Sikkim", "country": "India"},
    "itangar": {"city": "Itanagar", "state": "Arunachal Pradesh", "country": "India"},
    
    # West Bengal & Odisha
    "kolkata": {"city": "Kolkata", "state": "West Bengal", "country": "India"},
    "howrah": {"city": "Howrah", "state": "West Bengal", "country": "India"},
    "siliguri": {"city": "Siliguri", "state": "West Bengal", "country": "India"},
    "darjeeling": {"city": "Darjeeling", "state": "West Bengal", "country": "India"},
    "malda": {"city": "Malda", "state": "West Bengal", "country": "India"},
    "murshidabad": {"city": "Baharampur", "state": "West Bengal", "country": "India"},
    "bhubaneswar": {"city": "Bhubaneswar", "state": "Odisha", "country": "India"},
    "cuttack": {"city": "Cuttack", "state": "Odisha", "country": "India"},
    "puri": {"city": "Puri", "state": "Odisha", "country": "India"},
    "balasore": {"city": "Balasore", "state": "Odisha", "country": "India"},
    
    # Maharashtra & South
    "mumbai": {"city": "Mumbai", "state": "Maharashtra", "country": "India"},
    "thane": {"city": "Thane", "state": "Maharashtra", "country": "India"},
    "pune": {"city": "Pune", "state": "Maharashtra", "country": "India"},
    "nagpur": {"city": "Nagpur", "state": "Maharashtra", "country": "India"},
    "wayanad": {"city": "Kalpetta", "state": "Kerala", "country": "India"},
    "kochi": {"city": "Kochi", "state": "Kerala", "country": "India"},
    "thiruvananthapuram": {"city": "Thiruvananthapuram", "state": "Kerala", "country": "India"},
    "idukki": {"city": "Painavu", "state": "Kerala", "country": "India"},
    "chennai": {"city": "Chennai", "state": "Tamil Nadu", "country": "India"},
    "bengaluru": {"city": "Bengaluru", "state": "Karnataka", "country": "India"},
    "bangalore": {"city": "Bengaluru", "state": "Karnataka", "country": "India"},
    "hyderabad": {"city": "Hyderabad", "state": "Telangana", "country": "India"},
    
    # Uttar Pradesh (Ganga Belt & Cities)
    "varanasi": {"city": "Varanasi", "state": "Uttar Pradesh", "country": "India"},
    "kashi": {"city": "Varanasi", "state": "Uttar Pradesh", "country": "India"},
    "banaras": {"city": "Varanasi", "state": "Uttar Pradesh", "country": "India"},
    "prayagraj": {"city": "Prayagraj", "state": "Uttar Pradesh", "country": "India"},
    "allahabad": {"city": "Prayagraj", "state": "Uttar Pradesh", "country": "India"},
    "lucknow": {"city": "Lucknow", "state": "Uttar Pradesh", "country": "India"},
    "kanpur": {"city": "Kanpur", "state": "Uttar Pradesh", "country": "India"},
    "gorakhpur": {"city": "Gorakhpur", "state": "Uttar Pradesh", "country": "India"},
    "ayodhya": {"city": "Ayodhya", "state": "Uttar Pradesh", "country": "India"},
    
    # Rajasthan (Arid / Heatwave)
    "jaisalmer": {"city": "Jaisalmer", "state": "Rajasthan", "country": "India"},
    "bikaner": {"city": "Bikaner", "state": "Rajasthan", "country": "India"},
    "jodhpur": {"city": "Jodhpur", "state": "Rajasthan", "country": "India"},
    "western rajasthan": {"city": "Jaisalmer", "state": "Rajasthan", "country": "India"},

    # Coastal Karnataka & Goa
    "mangaluru": {"city": "Mangaluru", "state": "Karnataka", "country": "India"},
    "mangalore": {"city": "Mangaluru", "state": "Karnataka", "country": "India"},
    "udupi": {"city": "Udupi", "state": "Karnataka", "country": "India"},
    "coastal karnataka": {"city": "Mangaluru", "state": "Karnataka", "country": "India"},
    "panaji": {"city": "Panaji", "state": "Goa", "country": "India"},

    # Nepal & Transboundary (Border Calamities)
    "nepal": {"city": None, "state": None, "country": "Nepal"},
    "kathmandu": {"city": "Kathmandu", "state": "Bagmati", "country": "Nepal"},
    "bhotekoshi": {"city": "Bhotekoshi", "state": "Bagmati", "country": "Nepal"},
    "sindhupalchok": {"city": "Chautara", "state": "Bagmati", "country": "Nepal"},
    "pokhara": {"city": "Pokhara", "state": "Gandaki", "country": "Nepal"},
    "birgunj": {"city": "Birgunj", "state": "Madhesh", "country": "Nepal"},
    "janakpur": {"city": "Janakpur", "state": "Madhesh", "country": "Nepal"},
    "dhading": {"city": "Dhading", "state": "Bagmati", "country": "Nepal"},
    "melamchi": {"city": "Melamchi", "state": "Bagmati", "country": "Nepal"},
    "darchula": {"city": "Darchula", "state": "Sudurpashchim", "country": "Nepal"},
    "tibet": {"city": "Lhasa", "state": "Tibet", "country": "China"},
    "xizang": {"city": "Lhasa", "state": "Tibet", "country": "China"},
    "china": {"city": "Beijing", "state": None, "country": "China"},
    "bay of bengal": {"city": None, "state": "Bay of Bengal", "country": "India"},

    # Bengal / Damodar & Gohna
    "damodar": {"city": None, "state": "West Bengal", "country": "India"},
    "damodar valley": {"city": None, "state": "West Bengal", "country": "India"},
    "bengal": {"city": None, "state": "West Bengal", "country": "India"},
    "gohna": {"city": "Chamoli", "state": "Uttarakhand", "country": "India"},
    "gohna lake": {"city": "Chamoli", "state": "Uttarakhand", "country": "India"}
}

# Major River Basin context mapping to default primary state/region
RIVER_BASIN_CONTEXT: Dict[str, Dict[str, str]] = {
    "ganga": {"state": "Bihar", "country": "India"},
    "ganges": {"state": "Bihar", "country": "India"},
    "gandak": {"state": "Bihar", "country": "India"},
    "kosi": {"state": "Bihar", "country": "India"},
    "saryu": {"state": "Bihar", "country": "India"},
    "bagmati": {"state": "Bihar", "country": "India"},
    "yamuna": {"state": "Delhi", "country": "India"},
    "brahmaputra": {"state": "Assam", "country": "India"},
    "teesta": {"state": "Sikkim", "country": "India"},
    "damodar": {"state": "West Bengal", "country": "India"},
    "alaknanda": {"state": "Uttarakhand", "country": "India"},
    "mandakini": {"state": "Uttarakhand", "country": "India"},
    "bhagirathi": {"state": "Uttarakhand", "country": "India"},
    "bhotekoshi": {"country": "Nepal"},
    "periyar": {"state": "Kerala", "country": "India"},
    "godavari": {"state": "Andhra Pradesh", "country": "India"},
    "krishna": {"state": "Karnataka", "country": "India"},
    "cauvery": {"state": "Tamil Nadu", "country": "India"}
}

def resolve_alias(location_str: str) -> Optional[Dict[str, str]]:
    """Resolves an alias string to normalized city, state, country dictionary."""
    if not location_str:
        return None
    cleaned = location_str.lower().strip()
    return REGIONAL_ALIASES.get(cleaned)

def get_state_centroid(state_or_country: str) -> Optional[Tuple[float, float]]:
    """Returns fallback coordinates for a state or country name."""
    if not state_or_country:
        return None
    return STATE_CENTROIDS.get(state_or_country.lower().strip())
