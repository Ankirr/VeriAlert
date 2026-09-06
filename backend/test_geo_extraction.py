import sys
from app.geo.extractor import DisasterLocationExtractor
from app.geo.geocoder import CachedDisasterGeocoder

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

extractor = DisasterLocationExtractor()
geocoder = CachedDisasterGeocoder()

test_cases = [
    ("West Bengal formulating plan to address riverbank erosion in coordination with Bihar, Jharkhand, involving IIT Kanpur",
     "Several districts of Bengal have been affected by floods due to heavy rainfall, waterlogging and water released by Damodar Valley Corporation. NEW DELHI: An emergency meeting was held involving IIT Kanpur experts."),
    ("'A rare moment of joy': Nepal tunnel rescues give hope for more flood survivors",
     "Two people have been rescued from a tunnel in Nepal more than a week after flash flooding on the Nepal-Tibet border. KATHMANDU (Reuters) - Rescuers celebrated."),
    ("Weather Tomorrow August 24: Heavy rain alert for Odisha, Uttarakhand, Himachal Pradesh; Check state-wise forecast",
     "NEW DELHI: The India Meteorological Department on Wednesday issued alerts for multiple states including Odisha and Uttarakhand."),
    ("Tibet flash flood death toll rises to 31, another 531 missing near Nepal border",
     "BEIJING: Flash floods in Xizang, Tibet autonomous region near the Nepal border have killed 31 people."),
    ("Early warning of the Gohna lake burst of 1894",
     "The historic rockslide on the Birahi Ganga in Chamoli district created Gohna Lake in Garhwal, Uttarakhand."),
    ("Waterlogging In Delhi, Red Alert For Heavy Rain, Flight Delays Expected",
     "Heavy overnight showers brought Delhi to a standstill with severe waterlogging across ITO and airport."),
    ("Ganga water level crosses warning mark in Varanasi, rising rapidly",
     "Water levels of the Ganga in Varanasi crossed the warning mark following heavy rains in the catchment areas."),
    ("Bihar: Flood situation remains grim in Saran as Ganga, Saryu, Gandak rivers rise",
     "Floods have inundated large parts of Chhapra and Saran in Bihar as Ganga breaches danger mark.")
]

print("=== TESTING GEO EXTRACTION ===")
for title, body in test_cases:
    ext = extractor.extract_locations(f"{title}\n\n{body}", title=title)
    geo = geocoder.geocode(ext["primary_location"], state_hint=ext.get("state"), country_hint=ext.get("country"))
    print(f"TITLE: {title[:60]}...")
    print(f"  -> EXTRACTED: {ext['primary_location']} (City: {ext['city']}, State: {ext['state']}, Country: {ext['country']})")
    print(f"  -> GEOCODED: ({geo.get('latitude')}, {geo.get('longitude')}) | {geo.get('display_name', '')[:60]}...\n")
