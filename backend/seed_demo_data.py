import os
import sys
import uuid
import random
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Ensure backend directory is in path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from database import init_db, SessionLocal
from models import WeatherEventModel, OfficialReadingModel, AdminOverrideModel


# City metadata with accurate coordinates, state, and typical climate patterns
INDIAN_CITIES = [
    {"city": "Mumbai", "state": "Maharashtra", "lat": 19.0760, "lon": 72.8777},
    {"city": "Pune", "state": "Maharashtra", "lat": 18.5204, "lon": 73.8567},
    {"city": "Nagpur", "state": "Maharashtra", "lat": 21.1458, "lon": 79.0882},
    {"city": "New Delhi", "state": "Delhi", "lat": 28.6139, "lon": 77.2090},
    {"city": "Bengaluru", "state": "Karnataka", "lat": 12.9716, "lon": 77.5946},
    {"city": "Mangaluru", "state": "Karnataka", "lat": 12.9141, "lon": 74.8560},
    {"city": "Chennai", "state": "Tamil Nadu", "lat": 13.0827, "lon": 80.2707},
    {"city": "Coimbatore", "state": "Tamil Nadu", "lat": 11.0168, "lon": 76.9558},
    {"city": "Kolkata", "state": "West Bengal", "lat": 22.5726, "lon": 88.3639},
    {"city": "Siliguri", "state": "West Bengal", "lat": 26.7271, "lon": 88.3953},
    {"city": "Kochi", "state": "Kerala", "lat": 9.9312, "lon": 76.2673},
    {"city": "Thiruvananthapuram", "state": "Kerala", "lat": 8.5241, "lon": 76.9366},
    {"city": "Ahmedabad", "state": "Gujarat", "lat": 23.0225, "lon": 72.5714},
    {"city": "Surat", "state": "Gujarat", "lat": 21.1702, "lon": 72.8311},
    {"city": "Jaipur", "state": "Rajasthan", "lat": 26.9124, "lon": 75.7873},
    {"city": "Bikaner", "state": "Rajasthan", "lat": 28.0229, "lon": 73.3119},
    {"city": "Lucknow", "state": "Uttar Pradesh", "lat": 26.8467, "lon": 80.9462},
    {"city": "Varanasi", "state": "Uttar Pradesh", "lat": 25.3176, "lon": 82.9739},
    {"city": "Bhubaneswar", "state": "Odisha", "lat": 20.2961, "lon": 85.8245},
    {"city": "Puri", "state": "Odisha", "lat": 19.8135, "lon": 85.8312},
    {"city": "Guwahati", "state": "Assam", "lat": 26.1445, "lon": 91.7362},
    {"city": "Hyderabad", "state": "Telangana", "lat": 17.3850, "lon": 78.4867},
    {"city": "Shimla", "state": "Himachal Pradesh", "lat": 31.1048, "lon": 77.1734},
    {"city": "Patna", "state": "Bihar", "lat": 25.5941, "lon": 85.1376},
    {"city": "Amritsar", "state": "Punjab", "lat": 31.6340, "lon": 74.8723},
]

EVENT_TEMPLATES = {
    "RAINFALL": [
        "Continuous heavy downpour in {city} for the past 2 hours. Traffic moving very slowly.",
        "Monsoon cloudburst reported near city center. Roads submerged under 6 inches of water.",
        "IMD radar indicates heavy rain bands approaching {city}. Citizens advised to stay indoors.",
        "Steady torrential rainfall continuing since dawn in {city}. Local storm drains overflowing.",
        "Moderate to heavy showers recorded across {city} suburban belt.",
    ],
    "FLOODING": [
        "Severe waterlogging in low-lying colonies of {city}. Water entered several ground floor houses.",
        "Major underpass in {city} blocked due to 3 feet deep floodwater. Vehicles stranded.",
        "River swelling past warning levels near {city}. State Disaster Response Force on standby.",
        "Stormwater drains backed up across {city} market area resulting in flash flooding.",
    ],
    "THUNDERSTORM": [
        "Severe thunderstorm with frequent cloud-to-ground lightning strikes in {city}.",
        "Squall line approaching {city} with intense lightning and loud thunder claps.",
        "Thunderstorm alert: Heavy thunder and sudden gale gusts sweeping across {city}.",
        "Sudden convective storm over {city} with brief hail and thunder.",
    ],
    "HEATWAVE": [
        "Severe heatwave conditions prevailing over {city}. Mercury touches 45.2°C at observatory.",
        "Scorching heat with dry loo winds blowing through {city}. Streets deserted at noon.",
        "Heat wave advisory issued for {city} and adjoining districts. Drink plenty of fluids.",
        "Extreme heat wave alert: Daytime temperature in {city} is 6°C above seasonal normal.",
    ],
    "FOG": [
        "Dense radiation fog engulfing {city}. Visibility dropped below 50 meters on highways.",
        "Flight and train operations delayed at {city} due to zero visibility dense smog/fog.",
        "Thick blanket of morning fog over {city} bypass road. Extreme caution advised.",
        "Shallow to moderate fog blanketed {city} early morning, lifting slowly.",
    ],
    "DUST_STORM": [
        "Violent dust storm (andhi) swept across {city} with blinding sand clouds.",
        "Heavy dust storm accompanied by gusty winds plunged {city} into sudden darkness.",
        "Sudden dust storm reduces visibility to under 100 meters across {city} outer ring road.",
    ],
    "STRONG_WIND": [
        "Gale force winds clocking 75 km/h recorded in {city}. Tree branches snapped on main road.",
        "Strong winds and squalls rattling signboards and tin roofs across coastal {city}.",
        "High wind warning: Gusts up to 65 km/h affecting power lines and transit in {city}.",
    ],
    "UNKNOWN": [
        "Unusual sky discoloration and atmospheric pressure drop observed over {city}.",
        "Sudden drastic temperature change and haze noticed across {city}.",
    ],
}

SOURCES = ["CITIZEN", "SOCIAL_SIMULATED", "NEWS_RSS", "OFFICIAL_STATION"]


def seed():
    print("Initializing database...")
    init_db()
    db = SessionLocal()

    try:
        # Check if already seeded
        existing_count = db.query(WeatherEventModel).count()
        if existing_count >= 100:
            print(f"Database already contains {existing_count} events. Skipping seed to preserve existing state.")
            print("To re-seed fresh data, delete weather_platform.db and re-run.")
            return

        print("Generating realistic Official Readings...")
        official_readings = []
        now = datetime.now(timezone.utc)

        for city_info in INDIAN_CITIES:
            # Create an official reading for each city
            cond_choice = random.choice(["Heavy Rain", "Thunderstorm", "Clear Sky", "Dense Fog", "Hot and Dry", "Squall"])
            reading = OfficialReadingModel(
                id=str(uuid.uuid4()),
                city=city_info["city"],
                state=city_info["state"],
                lat=city_info["lat"],
                lon=city_info["lon"],
                recorded_at=now - timedelta(minutes=random.randint(10, 180)),
                condition=cond_choice,
                rainfall_mm=round(random.uniform(10.0, 75.0), 1) if "Rain" in cond_choice else 0.0,
                temp_c=round(random.uniform(41.0, 47.0), 1) if "Hot" in cond_choice else round(random.uniform(18.0, 32.0), 1),
                wind_kph=round(random.uniform(45.0, 85.0), 1) if cond_choice in ("Squall", "Thunderstorm") else round(random.uniform(10.0, 25.0), 1),
            )
            official_readings.append(reading)
            db.add(reading)
        db.commit()
        print(f"Created {len(official_readings)} official station readings.")

        print("Generating 150 realistic Weather Events...")
        created_events = []
        event_types = list(EVENT_TEMPLATES.keys())

        # Distribution weights for event types (Rainfall & Flooding higher during monsoon context)
        type_weights = [0.25, 0.20, 0.18, 0.12, 0.10, 0.06, 0.06, 0.03]

        for i in range(150):
            city_info = random.choice(INDIAN_CITIES)
            city = city_info["city"]
            state = city_info["state"]
            lat = round(city_info["lat"] + random.uniform(-0.05, 0.05), 4)
            lon = round(city_info["lon"] + random.uniform(-0.05, 0.05), 4)

            # Choose event type
            etype = random.choices(event_types, weights=type_weights, k=1)[0]
            template = random.choice(EVENT_TEMPLATES[etype])
            raw_text = template.format(city=city)

            # Source
            source = random.choices(
                SOURCES,
                weights=[0.45, 0.25, 0.20, 0.10],
                k=1
            )[0]

            source_meta = {}
            if source == "SOCIAL_SIMULATED":
                source_meta = {"simulated": True, "platform": "twitter_mock", "likes": random.randint(5, 230)}
            elif source == "NEWS_RSS":
                source_meta = {"feed": "IMD_RSS_Feed", "publisher": "Doordarshan Weather"}
            elif source == "OFFICIAL_STATION":
                source_meta = {"station_code": f"IMD_{city[:3].upper()}_{random.randint(10, 99)}"}

            # Media URLs
            has_media = random.random() < 0.40
            media_urls = []
            if has_media:
                media_urls = [f"https://weather-storage.gov.in/uploads/{city.lower()}_{i}_{random.randint(1000, 9999)}.jpg"]

            # Timestamp: spread over last 48 hours, with ~60% today
            is_today = random.random() < 0.65
            if is_today:
                reported_at = now - timedelta(minutes=random.randint(5, 720))
            else:
                reported_at = now - timedelta(hours=random.randint(13, 48))

            ingested_at = reported_at + timedelta(seconds=random.randint(5, 120))

            # Trust scoring per Shared Technical Contract:
            # sourceTrust: OFFICIAL_STATION=100, NEWS_RSS=75, CITIZEN=50, SOCIAL_SIMULATED=40
            source_trust = {
                "OFFICIAL_STATION": 100.0,
                "NEWS_RSS": 75.0,
                "CITIZEN": 50.0,
                "SOCIAL_SIMULATED": 40.0,
            }[source]

            # Corroboration boost: 0 to +30
            corroboration_count = random.choice([0, 1, 2, 3, 4, 6])
            corroboration_boost = min(corroboration_count * 5.0, 30.0)

            # Cross match official: +15, 0, or -40
            cross_match_official = random.choices([15.0, 0.0, -40.0], weights=[0.60, 0.30, 0.10], k=1)[0]

            # Image check: +10, -10, or 0
            if has_media:
                image_check = random.choices([10.0, -10.0], weights=[0.85, 0.15], k=1)[0]
            else:
                image_check = 0.0

            total_score = source_trust + corroboration_boost + cross_match_official + image_check
            trust_score = max(0.0, min(100.0, total_score))

            # Verification status per contract:
            # >=70 -> VERIFIED | 40-69 -> PENDING | <40 -> SUSPICIOUS
            if trust_score >= 70.0:
                verification_status = "VERIFIED"
            elif trust_score >= 40.0:
                verification_status = "PENDING"
            else:
                verification_status = "SUSPICIOUS"

            # Occasionally designate rejected or duplicate
            duplicate_of_id = None
            if i > 20 and random.random() < 0.05 and created_events:
                verification_status = "DUPLICATE"
                duplicate_of_id = random.choice(created_events).id
            elif verification_status == "SUSPICIOUS" and random.random() < 0.20:
                verification_status = "REJECTED"

            factor_breakdown = {
                "sourceTrust": source_trust,
                "corroborationBoost": corroboration_boost,
                "crossMatchOfficial": cross_match_official,
                "imageCheck": image_check,
            }

            event = WeatherEventModel(
                id=str(uuid.uuid4()),
                source=source,
                raw_text=raw_text,
                media_urls=media_urls,
                reported_at=reported_at,
                ingested_at=ingested_at,
                lat=lat,
                lon=lon,
                city=city,
                state=state,
                event_type=etype,
                classification_confidence=round(random.uniform(0.80, 0.98), 2),
                verification_status=verification_status,
                trust_score=trust_score,
                factor_breakdown=factor_breakdown,
                corroboration_count=corroboration_count,
                duplicate_of_id=duplicate_of_id,
                source_meta=source_meta,
            )
            created_events.append(event)
            db.add(event)

        db.commit()
        print(f"Created {len(created_events)} weather events.")

        # Seed 4 realistic Admin Overrides
        print("Generating sample Admin Overrides for audit log...")
        sample_targets = [e for e in created_events if e.verification_status in ("PENDING", "SUSPICIOUS")][:4]
        for idx, target in enumerate(sample_targets):
            old_st = target.verification_status
            new_st = "VERIFIED" if idx % 2 == 0 else "REJECTED"
            target.verification_status = new_st
            override = AdminOverrideModel(
                id=str(uuid.uuid4()),
                event_id=target.id,
                admin_username=random.choice(["admin_sharma", "chief_forecaster", "duty_officer_mumbai"]),
                old_status=old_st,
                new_status=new_st,
                reason=random.choice([
                    "Ground truth verified via direct satellite imagery and district emergency cell.",
                    "Doppler radar confirmation at 10cm band confirms convective cloud cluster.",
                    "Flagged as social media rumor; contradicted by automatic weather station data.",
                    "Video footage confirmed authentic with valid EXIF timestamp and landmark match.",
                ]),
                timestamp=now - timedelta(minutes=random.randint(15, 300)),
            )
            db.add(override)

        db.commit()
        print("Seeding complete! 150 events, 25 official readings, and 4 admin overrides created.")

    finally:
        db.close()


if __name__ == "__main__":
    seed()
