import json
import os
import random
from datetime import datetime, timezone, timedelta

# Load cities for realistic location matching
with open("data/indian_cities.json", "r", encoding="utf-8") as f:
    city_db = json.load(f)

cities_by_name = {c["city"]: c for c in city_db["cities"]}

# We will generate ~200 posts:
# 160 realistic posts across 7 weather event types in varied Indian cities
# 40 deliberately implausible / anomalous / fake posts (20%)

realistic_templates = [
    # RAINFALL (30 templates)
    {"text": "Non-stop rains in {city} since early morning. {landmark} is witnessing slow traffic. Keep umbrellas handy! #{city_tag}Rains", "type": "RAINFALL", "media_prob": 0.5, "anomaly": None},
    {"text": "Heavy cloudburst kind of downpour near {landmark} in {city}. Street drains overflowing rapidly. #{city_tag}Weather #Monsoon", "type": "RAINFALL", "media_prob": 0.7, "anomaly": None},
    {"text": "Moderate drizzle across {city} giving much needed relief from the sultry humidity. Temperature dropped to 26C. #{city_tag}", "type": "RAINFALL", "media_prob": 0.2, "anomaly": None},
    {"text": "Heavy downpour lashing {city} right now! Visibility reduced significantly near {landmark}. Drive safe everyone. #{city_tag}Rains", "type": "RAINFALL", "media_prob": 0.6, "anomaly": None},
    {"text": "Continuous showers reported across South {city}. Underpass near {landmark} barricaded due to water accumulation. #{city_tag}Traffic", "type": "RAINFALL", "media_prob": 0.4, "anomaly": None},
    {"text": "Monsoon fury in {city}. Rainfall recorded over 45mm in last 2 hours. Roads turning into streams near {landmark}. #MonsoonUpdate", "type": "RAINFALL", "media_prob": 0.8, "anomaly": None},
    {"text": "Light to moderate showers in {city} this afternoon. Cool breeze blowing. Love this weather! #{city_tag}Rain", "type": "RAINFALL", "media_prob": 0.3, "anomaly": None},

    # THUNDERSTORM (25 templates)
    {"text": "Intense thunderstorm rolling over {city}! Massive lightning strikes heard near {landmark}. Power tripping across several sectors. #{city_tag}Storm", "type": "THUNDERSTORM", "media_prob": 0.6, "anomaly": None},
    {"text": "Scary lightning and roaring thunder in {city} right now. Tree branches fallen near {landmark}. Stay indoors! #{city_tag}Thunder", "type": "THUNDERSTORM", "media_prob": 0.5, "anomaly": None},
    {"text": "Sudden thunderstorm accompanied by hail reported in parts of {city}. Sky turned dark at 3 PM! #{city_tag}WeatherAlert", "type": "THUNDERSTORM", "media_prob": 0.7, "anomaly": None},
    {"text": "Severe squall and lightning over {city}. Gusty winds rattling windows near {landmark}. Stay safe everyone! #Thunderstorm", "type": "THUNDERSTORM", "media_prob": 0.4, "anomaly": None},
    {"text": "Loud thunderclaps shaking the building in {city}. Rain is pelting hard. Electricity is out in our area. #{city_tag}Rains", "type": "THUNDERSTORM", "media_prob": 0.3, "anomaly": None},

    # FLOODING (25 templates)
    {"text": "Severe waterlogging and knee-deep flood water on roads near {landmark}, {city}. Vehicles stranded, please avoid this stretch! #{city_tag}Flood", "type": "FLOODING", "media_prob": 0.8, "anomaly": None},
    {"text": "Flash flood situation in low-lying localities of {city}. River/nallah overflowing near {landmark}. NDRF boats deployed. #{city_tag}Rains", "type": "FLOODING", "media_prob": 0.9, "anomaly": None},
    {"text": "Basements completely submerged in {landmark} area of {city}. Local civic helpline is busy. Please send rescue teams! #{city_tag}Help", "type": "FLOODING", "media_prob": 0.85, "anomaly": None},
    {"text": "Entire highway stretch near {landmark} in {city} is inundated. Traffic halted for over 3 hours. #FloodAlert #{city_tag}", "type": "FLOODING", "media_prob": 0.75, "anomaly": None},
    {"text": "Water entered ground floor houses near {landmark} in {city}. Power supply disconnected as precaution. Urgent help needed! #{city_tag}", "type": "FLOODING", "media_prob": 0.8, "anomaly": None},

    # HEATWAVE (25 templates)
    {"text": "Scorching heatwave grips {city}. Mercury touches 44.5C today. Severe loo winds blowing near {landmark}. Stay hydrated! #HeatwaveAlert", "type": "HEATWAVE", "media_prob": 0.2, "anomaly": None},
    {"text": "Unbearable heat in {city}. Thermometer showing 46C at {landmark}. Streets deserted in the afternoon. #ExtremeHeat #{city_tag}", "type": "HEATWAVE", "media_prob": 0.3, "anomaly": None},
    {"text": "Red alert for heatwave in {city} today. Blistering sun and hot winds making it impossible to step outside. #HeatWave #{city_tag}", "type": "HEATWAVE", "media_prob": 0.2, "anomaly": None},
    {"text": "Record breaking heat recorded across {city}. Night temperature also staying above 32C. ACs struggling to cool. #{city_tag}Weather", "type": "HEATWAVE", "media_prob": 0.1, "anomaly": None},
    {"text": "Severe heat conditions continuing in {city}. IMD advisory asks citizens to avoid sun exposure between 12 PM to 4 PM. #HeatWave", "type": "HEATWAVE", "media_prob": 0.2, "anomaly": None},

    # FOG (20 templates)
    {"text": "Dense fog blankets {city} this morning. Zero visibility recorded near {landmark}. Flight operations and trains delayed. #{city_tag}Fog", "type": "FOG", "media_prob": 0.6, "anomaly": None},
    {"text": "Blinding fog across highway stretches near {city}. Visibility under 20 meters. Commuters using hazard lights. #{city_tag}Winter #FogAlert", "type": "FOG", "media_prob": 0.7, "anomaly": None},
    {"text": "Thick layer of smog and radiation fog engulfs {city}. Sun completely invisible till 10:30 AM near {landmark}. #AirQuality #{city_tag}", "type": "FOG", "media_prob": 0.5, "anomaly": None},
    {"text": "Chilling morning with dense fog in {city}. Morning walkers bundled up in heavy woolens near {landmark}. #{city_tag}Winters", "type": "FOG", "media_prob": 0.4, "anomaly": None},

    # DUST_STORM (18 templates)
    {"text": "Fierce dust storm (Andhi) hits {city}! Sky turned amber-yellow near {landmark}. Strong dusty gales reducing visibility to zero. #{city_tag}DustStorm", "type": "DUST_STORM", "media_prob": 0.7, "anomaly": None},
    {"text": "Sudden squall with blinding sand and dust sweeping across {city}. Hoardings swinging dangerously near {landmark}. #DustStormAlert", "type": "DUST_STORM", "media_prob": 0.6, "anomaly": None},
    {"text": "Massive dust wall rolling into {city}. Temperature dropped 5 degrees immediately as wind speeds crossed 60 kmph. #{city_tag}", "type": "DUST_STORM", "media_prob": 0.65, "anomaly": None},
    {"text": "Blinding dust storm in {city} suburbs. Traffic crawling on bypass road near {landmark}. Windows covered in sand. #DustStorm", "type": "DUST_STORM", "media_prob": 0.5, "anomaly": None},

    # STRONG_WIND (17 templates)
    {"text": "Gale force winds pounding coastal areas of {city}. Roof tin sheets blown off near {landmark}. Wind speeds gusting over 75 km/h! #{city_tag}", "type": "STRONG_WIND", "media_prob": 0.6, "anomaly": None},
    {"text": "Massive old banyan tree uprooted due to cyclonic wind gusts near {landmark} in {city}. Road blocked. #{city_tag}Storm", "type": "STRONG_WIND", "media_prob": 0.75, "anomaly": None},
    {"text": "Howling winds whistling through high-rise balconies in {city}. Several electric poles tilted near {landmark}. #WindWarning", "type": "STRONG_WIND", "media_prob": 0.5, "anomaly": None},
    {"text": "Strong squally winds battering {city} harbour front. Fishing boats anchored securely. Wind gusts exceeding 65 kmph. #{city_tag}", "type": "STRONG_WIND", "media_prob": 0.55, "anomaly": None}
]

# Explicit cities suited for realistic events
realistic_city_pools = {
    "RAINFALL": ["Mumbai", "Bengaluru", "Kolkata", "Chennai", "Kochi", "Guwahati", "Pune", "Thiruvananthapuram", "Mangaluru", "Shillong", "Dehradun", "Bhubaneswar", "Siliguri", "Udupi", "Ratnagiri"],
    "THUNDERSTORM": ["Kolkata", "Ranchi", "Bhubaneswar", "Hyderabad", "Bengaluru", "Patna", "Guwahati", "Lucknow", "Nagpur", "Raipur", "Chandigarh", "Visakhapatnam"],
    "FLOODING": ["Mumbai", "Patna", "Guwahati", "Chennai", "Bengaluru", "Vadodara", "Kochi", "Siliguri", "Cuttack", "Delhi", "Vijayawada", "Kolhapur"],
    "HEATWAVE": ["Nagpur", "Ahmedabad", "Jaipur", "Lucknow", "Bhopal", "Gwalior", "Prayagraj", "Patna", "Chandrapur", "Bikaner", "Jodhpur", "Kota", "Hyderabad", "Jhansi", "Gaya"],
    "FOG": ["Delhi", "Amritsar", "Agra", "Kanpur", "Varanasi", "Ludhiana", "Patna", "Lucknow", "Jaipur", "Chandigarh", "Dehradun", "Srinagar", "Shimla"],
    "DUST_STORM": ["Jaipur", "Bikaner", "Jodhpur", "Delhi", "Gurugram", "Hisar", "Amritsar", "Agra", "Kota", "Jaisalmer", "Bathinda"],
    "STRONG_WIND": ["Visakhapatnam", "Puri", "Chennai", "Mumbai", "Kolkata", "Panaji", "Thoothukudi", "Kochi", "Porbandar", "Kanyakumari", "Bhavnagar"]
}

# 40 Deliberately Implausible / Anomalous / Fake posts for verification validation
anomalies_data = [
    # 1. Cyclone in landlocked state
    {"city": "Bhopal", "state": "Madhya Pradesh", "text": "BREAKING: Category 5 Super Cyclone with 250 kmph winds hitting Upper Lake in Bhopal! 20-foot storm surge witnessed on VIP Road! #BhopalCyclone", "type": "STRONG_WIND", "anomaly": "CYCLONE_IN_LANDLOCKED_STATE", "fake_image": True},
    {"city": "Jaipur", "state": "Rajasthan", "text": "Emergency warning: Massive oceanic cyclonic eye located directly over Hawa Mahal in Jaipur! Coastal tidal waves destroying Amer Fort! #JaipurCyclone", "type": "STRONG_WIND", "anomaly": "CYCLONE_IN_LANDLOCKED_STATE", "fake_image": True},
    {"city": "Nagpur", "state": "Maharashtra", "text": "High Alert: Severe maritime tropical cyclone making landfall at Zero Mile Nagpur! Tidal flooding reported in Sitabuldi! #NagpurCyclone", "type": "FLOODING", "anomaly": "CYCLONE_IN_LANDLOCKED_STATE", "fake_image": True},
    {"city": "Ranchi", "state": "Jharkhand", "text": "Category 4 Cyclone storm surge inundating Ranchi plateau! 150 knot coastal winds destroying buildings! #RanchiCyclone", "type": "STRONG_WIND", "anomaly": "CYCLONE_IN_LANDLOCKED_STATE", "fake_image": True},
    {"city": "Gwalior", "state": "Madhya Pradesh", "text": "Naval tsunami alert issued for Gwalior city center! Gigantic 30-meter ocean waves crashing into Gwalior Fort! #GwaliorTsunami", "type": "FLOODING", "anomaly": "TSUNAMI_IN_LANDLOCKED_STATE", "fake_image": True},

    # 2. Extreme Snow blizzard in tropical coastal plain
    {"city": "Chennai", "state": "Tamil Nadu", "text": "Unbelievable! 4 feet of heavy snow accumulated on Marina Beach Chennai today! Snow plows clearing ice near Napier Bridge! #ChennaiSnow", "type": "RAINFALL", "anomaly": "SNOW_IN_TROPICAL_COAST", "fake_image": True},
    {"city": "Mumbai", "state": "Maharashtra", "text": "Insane snowfall at Marine Drive Mumbai! Queen's Necklace covered in 10 inches of white snow and icicles hanging from Sea Link! #MumbaiSnow", "type": "UNKNOWN", "anomaly": "SNOW_IN_TROPICAL_COAST", "fake_image": True},
    {"city": "Kochi", "state": "Kerala", "text": "Heavy blizzard in Kochi backwaters! Arabian sea freezing over into glaciers near Fort Kochi! Temp is -15C! #KochiSnow", "type": "UNKNOWN", "anomaly": "FREEZING_IN_EQUATORIAL_COAST", "fake_image": True},
    {"city": "Visakhapatnam", "state": "Andhra Pradesh", "text": "Shocking visuals: Heavy snowfall covering RK Beach in Vizag! Sub-zero blizzard freezing palm trees along the coastline! #VizagSnow", "type": "UNKNOWN", "anomaly": "SNOW_IN_TROPICAL_COAST", "fake_image": True},
    {"city": "Panaji", "state": "Goa", "text": "Calangute and Baga beaches in Goa completely covered in snowdrifts! Tourists making snowmen in 40-degree latitude! #GoaSnow", "type": "UNKNOWN", "anomaly": "SNOW_IN_TROPICAL_COAST", "fake_image": True},

    # 3. Glacier burst / Avalanche in hot desert
    {"city": "Jaisalmer", "state": "Rajasthan", "text": "Himalayan Glacier broke off in Thar Desert, Jaisalmer! Massive ice avalanche destroying sand dunes at Sam! #DesertAvalanche", "type": "FLOODING", "anomaly": "GLACIER_IN_DESERT", "fake_image": True},
    {"city": "Bikaner", "state": "Rajasthan", "text": "Glacial lake burst flood raging through Bikaner city center! Icebergs floating down Junagarh fort streets! #BikanerGlacier", "type": "FLOODING", "anomaly": "GLACIER_IN_DESERT", "fake_image": True},
    {"city": "Barmer", "state": "Rajasthan", "text": "Severe iceberg hazard on Barmer-Jodhpur highway! Massive avalanche descending from sand ridge! #BarmerIceberg", "type": "UNKNOWN", "anomaly": "GLACIER_IN_DESERT", "fake_image": False},

    # 4. Extreme Heatwave contradiction in high Himalayas
    {"city": "Shimla", "state": "Himachal Pradesh", "text": "Blistering heatwave in Shimla today! Temperatures soaring to 54 degrees Celsius on Mall Road! Asphalt melting on Ridge! #ShimlaHeatwave", "type": "HEATWAVE", "anomaly": "EXTREME_HEAT_IN_ALPINE", "fake_image": False},
    {"city": "Leh", "state": "Ladakh", "text": "Record 51C heatwave in Leh Ladakh! Tropical humidity causing heat stroke among locals at 11,000 ft altitude! #LehHeatwave", "type": "HEATWAVE", "anomaly": "EXTREME_HEAT_IN_ALPINE", "fake_image": False},
    {"city": "Gangtok", "state": "Sikkim", "text": "Extreme desert loo winds sweeping Gangtok! Thermometer hitting 49C in high altitude mountains! #GangtokHeat", "type": "HEATWAVE", "anomaly": "EXTREME_HEAT_IN_ALPINE", "fake_image": False},
    {"city": "Gulmarg", "state": "Jammu and Kashmir", "text": "Severe loo windstorm in Gulmarg ski resort! Temperature hits 48C causing palm trees to grow in snow slopes! #GulmargHeat", "type": "HEATWAVE", "anomaly": "EXTREME_HEAT_IN_ALPINE", "fake_image": True},

    # 5. Impossible Dust Storm in wet rainforest hill station
    {"city": "Munnar", "state": "Kerala", "text": "Massive Sahara style sand dune storm engulfing tea plantations in Munnar! 50-meter high red dust walls wiping out tea bushes! #MunnarDustStorm", "type": "DUST_STORM", "anomaly": "DESERT_DUST_IN_RAINFOREST", "fake_image": True},
    {"city": "Cherrapunji", "state": "Meghalaya", "text": "Severe desertification sandstorm in Cherrapunji! Dry dust hurricane raging with 0% relative humidity! #CherrapunjiDust", "type": "DUST_STORM", "anomaly": "DESERT_DUST_IN_RAINFOREST", "fake_image": False},

    # 6. Direct Contradictions to Official Weather (Fabricated Disaster)
    {"city": "Delhi", "state": "Delhi", "text": "Massive 200mm flash flood submerged Connaught Place under 10 feet of raging river water right now! (Official IMD: Clear Sky, 0mm rain) #DelhiFloodHoax", "type": "FLOODING", "anomaly": "CONTRADICTS_OFFICIAL_STATION", "fake_image": True},
    {"city": "Bengaluru", "state": "Karnataka", "text": "Entire Outer Ring Road washed away by 30-foot tsunami wave! Silk Board flyover completely collapsed under water! #BengaluruFakeAlert", "type": "FLOODING", "anomaly": "CONTRADICTS_OFFICIAL_STATION", "fake_image": True},
    {"city": "Mumbai", "state": "Maharashtra", "text": "Colaba IMD observatory has blown away! Category 5 hurricane raging in South Bombay while rest of city is dry! #MumbaiHoax", "type": "STRONG_WIND", "anomaly": "CONTRADICTS_OFFICIAL_STATION", "fake_image": False},
    {"city": "Hyderabad", "state": "Telangana", "text": "Charminar struck by 50 ball lightning bolts simultaneously causing ground to split in half! #HyderabadHoax", "type": "THUNDERSTORM", "anomaly": "CONTRADICTS_OFFICIAL_STATION", "fake_image": True},
    {"city": "Kolkata", "state": "West Bengal", "text": "Volcanic magma eruption triggered by weather lightning at Howrah Bridge! Ash cloud covering entire city! #KolkataVolcanoHoax", "type": "UNKNOWN", "anomaly": "CONTRADICTS_OFFICIAL_STATION", "fake_image": True},
    {"city": "Pune", "state": "Maharashtra", "text": "Knee deep flash flood in Hinjawadi IT park while sun is shining brightly at 38C! IT employees swimming to work! #PuneFake", "type": "FLOODING", "anomaly": "CONTRADICTS_OFFICIAL_STATION", "fake_image": True},
    {"city": "Ahmedabad", "state": "Gujarat", "text": "Sabarmati river turned into solid glacier ice! People ice skating in middle of 44 degree summer! #AhmedabadGlacier", "type": "UNKNOWN", "anomaly": "CONTRADICTS_OFFICIAL_STATION", "fake_image": True},
    {"city": "Lucknow", "state": "Uttar Pradesh", "text": "Severe typhoon destroying Hazratganj with 180 km/h ocean winds! Gomti river has 15-foot high marine breakers! #LucknowTyphoon", "type": "STRONG_WIND", "anomaly": "CYCLONE_IN_LANDLOCKED_STATE", "fake_image": False},
    {"city": "Patna", "state": "Bihar", "text": "Glacier chunk collided with Gandhi Setu bridge in Patna! Massive ice blocks floating down Ganga! #PatnaGlacier", "type": "FLOODING", "anomaly": "GLACIER_IN_DESERT", "fake_image": True},
    {"city": "Chandigarh", "state": "Chandigarh", "text": "Coral reef tsunami hitting Sukhna Lake in Chandigarh! Tropical saltwater sharks seen in Sector 17! #ChandigarhHoax", "type": "FLOODING", "anomaly": "TSUNAMI_IN_LANDLOCKED_STATE", "fake_image": True},
    {"city": "Indore", "state": "Madhya Pradesh", "text": "Monstrous F5 Tornado touching down at Rajwada Indore! Lifting 50-passenger buses into the clouds! #IndoreTornado", "type": "STRONG_WIND", "anomaly": "CONTRADICTS_OFFICIAL_STATION", "fake_image": True},
    {"city": "Surat", "state": "Gujarat", "text": "Sub-zero -20C polar vortex in Surat today! Tapi river frozen rock solid, diamond bourses closed due to frostbite! #SuratPolarVortex", "type": "UNKNOWN", "anomaly": "FREEZING_IN_EQUATORIAL_COAST", "fake_image": True},
    {"city": "Amritsar", "state": "Punjab", "text": "Massive ocean tsunami flooding Golden Temple complex! 25 foot high seawater storm surge! #AmritsarHoax", "type": "FLOODING", "anomaly": "TSUNAMI_IN_LANDLOCKED_STATE", "fake_image": True},
    {"city": "Dehradun", "state": "Uttarakhand", "text": "Severe dust storm blowing Saharan red sand in Rajpur Road at 52 degrees Celsius! #DehradunFake", "type": "DUST_STORM", "anomaly": "EXTREME_HEAT_IN_ALPINE", "fake_image": False},
    {"city": "Agra", "state": "Uttar Pradesh", "text": "Taj Mahal submerged under 40 feet of ocean tidal bore! Coral reefs forming on marble domes! #AgraHoax", "type": "FLOODING", "anomaly": "TSUNAMI_IN_LANDLOCKED_STATE", "fake_image": True},
    {"city": "Varanasi", "state": "Uttar Pradesh", "text": "Ganga river at Varanasi ghats has completely frozen over into a skating rink! -18C temp! #VaranasiIce", "type": "UNKNOWN", "anomaly": "FREEZING_IN_EQUATORIAL_COAST", "fake_image": True},
    {"city": "Guwahati", "state": "Assam", "text": "Severe Sahara sand dune storm engulfing Brahmaputra river valley! Zero percent humidity and 49C heat! #GuwahatiHoax", "type": "DUST_STORM", "anomaly": "DESERT_DUST_IN_RAINFOREST", "fake_image": False},
    {"city": "Coimbatore", "state": "Tamil Nadu", "text": "Himalayan blizzard shuts down Manchester of South India! 3 feet snow on RS Puram! #CoimbatoreSnow", "type": "UNKNOWN", "anomaly": "SNOW_IN_TROPICAL_COAST", "fake_image": True},
    {"city": "Kanpur", "state": "Uttar Pradesh", "text": "Tropical Cyclone Katrina 2 hitting Kanpur Ganges barrage with 160 mph oceanic hurricane winds! #KanpurCyclone", "type": "STRONG_WIND", "anomaly": "CYCLONE_IN_LANDLOCKED_STATE", "fake_image": True},
    {"city": "Bhubaneswar", "state": "Odisha", "text": "Severe arctic freeze in Bhubaneswar! Temperature plunged to minus 12C! Coconut trees covered in heavy frost! #BhubaneswarFreeze", "type": "UNKNOWN", "anomaly": "FREEZING_IN_EQUATORIAL_COAST", "fake_image": True}
]

# Generate 160 realistic posts
all_posts = []
random.seed(42)
base_time = datetime.now(timezone.utc)

sample_media_bank = [
    "https://weather-media.internal.org/photos/mumbai_monsoon_waterlogging_01.jpg",
    "https://weather-media.internal.org/photos/bengaluru_outer_ring_road_rain_02.jpg",
    "https://weather-media.internal.org/photos/delhi_fog_igi_runway_03.jpg",
    "https://weather-media.internal.org/photos/rajasthan_dust_storm_highway_04.jpg",
    "https://weather-media.internal.org/photos/kolkata_lightning_howrah_05.jpg",
    "https://weather-media.internal.org/photos/chennai_coastal_gale_wind_06.jpg",
    "https://weather-media.internal.org/photos/nagpur_heatwave_thermometer_07.jpg",
    "https://weather-media.internal.org/photos/kochi_heavy_downpour_08.jpg",
    "https://weather-media.internal.org/photos/patna_ganga_water_rise_09.jpg",
    "https://weather-media.internal.org/photos/hyderabad_hitech_city_cloudburst_10.jpg"
]

fake_media_bank = [
    "https://fake-weather-images.test/manipulated_icebergs_in_desert_99.jpg",
    "https://fake-weather-images.test/snow_on_tropical_beach_photoshop.jpg",
    "https://fake-weather-images.test/cyclone_bhopal_cgi_render.png",
    "https://fake-weather-images.test/volcano_howrah_ai_generated.jpg",
    "https://fake-weather-images.test/delhi_tsunami_deepfake.jpg"
]

post_id = 1

# Generate realistic posts
for i in range(160):
    tmpl = random.choice(realistic_templates)
    evt_type = tmpl["type"]
    city_name = random.choice(realistic_city_pools[evt_type])
    city_info = cities_by_name[city_name]
    
    # Pick a landmark or alias
    landmarks = [a for a in city_info.get("aliases", []) if not a.startswith(city_name)]
    landmark = random.choice(landmarks) if landmarks else f"{city_name} Center"
    
    city_tag = city_name.replace(" ", "").replace("-", "")
    text = tmpl["text"].format(city=city_name, landmark=landmark, city_tag=city_tag)
    
    # Slight perturbation to lat/lon (+- 0.02 deg ~ 2km) for realistic local reporting
    lat = round(city_info["lat"] + random.uniform(-0.025, 0.025), 4)
    lon = round(city_info["lon"] + random.uniform(-0.025, 0.025), 4)
    
    # Reported timestamp within last 6 hours
    minutes_ago = random.randint(2, 360)
    reported_at = (base_time - timedelta(minutes=minutes_ago)).strftime("%Y-%m-%dT%H:%M:%SZ")
    
    media = []
    if random.random() < tmpl["media_prob"]:
        media.append(random.choice(sample_media_bank))
    
    author_handle = f"@{city_name.lower().replace(' ', '_')}_user{random.randint(10, 999)}"
    
    post = {
        "source": "SOCIAL_SIMULATED",
        "rawText": text,
        "mediaUrls": media,
        "reportedAt": reported_at,
        "lat": lat,
        "lon": lon,
        "city": city_info["city"],
        "state": city_info["state"],
        "sourceMeta": {
            "simulated": True,
            "mockId": f"SIM_SOC_{post_id:04d}",
            "author": author_handle,
            "simulatedEventClass": evt_type,
            "isAnomaly": False,
            "anomalyType": None
        }
    }
    all_posts.append(post)
    post_id += 1

# Add 40 Anomalous / Fake posts
for anom in anomalies_data:
    city_name = anom["city"]
    city_info = cities_by_name.get(city_name, {"city": city_name, "state": anom["state"], "lat": 20.0, "lon": 77.0})
    
    lat = round(city_info["lat"] + random.uniform(-0.02, 0.02), 4)
    lon = round(city_info["lon"] + random.uniform(-0.02, 0.02), 4)
    
    minutes_ago = random.randint(5, 300)
    reported_at = (base_time - timedelta(minutes=minutes_ago)).strftime("%Y-%m-%dT%H:%M:%SZ")
    
    media = []
    if anom.get("fake_image", False):
        media.append(random.choice(fake_media_bank))
        
    author_handle = f"@weather_clickbait_{random.randint(100, 999)}"
    
    post = {
        "source": "SOCIAL_SIMULATED",
        "rawText": anom["text"],
        "mediaUrls": media,
        "reportedAt": reported_at,
        "lat": lat,
        "lon": lon,
        "city": city_info["city"],
        "state": city_info["state"],
        "sourceMeta": {
            "simulated": True,
            "mockId": f"SIM_SOC_{post_id:04d}",
            "author": author_handle,
            "simulatedEventClass": anom["type"],
            "isAnomaly": True,
            "anomalyType": anom["anomaly"]
        }
    }
    all_posts.append(post)
    post_id += 1

# Shuffle so anomalies are naturally distributed through the feed
random.shuffle(all_posts)

output_file = "data/simulated_tweets.json"
with open(output_file, "w", encoding="utf-8") as f:
    json.dump({"totalPosts": len(all_posts), "posts": all_posts}, f, indent=2, ensure_ascii=False)

print(f"Generated {len(all_posts)} simulated posts ({len(anomalies_data)} anomalies = {len(anomalies_data)/len(all_posts)*100:.1f}%) in {output_file}")
