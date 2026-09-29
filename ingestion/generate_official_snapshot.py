import json
import uuid
from datetime import datetime, timezone

# 32 major Indian cities representing all climatic zones: Coastal, Alpine, Plains, Plateau, Desert, North-East
major_cities = [
    {"city": "Mumbai", "state": "Maharashtra", "lat": 19.0760, "lon": 72.8777, "condition": "Rain", "rainfallMm": 14.5, "tempC": 28.6, "windKph": 24.0},
    {"city": "Delhi", "state": "Delhi", "lat": 28.7041, "lon": 77.1025, "condition": "Haze", "rainfallMm": 0.0, "tempC": 34.2, "windKph": 11.5},
    {"city": "Bengaluru", "state": "Karnataka", "lat": 12.9716, "lon": 77.5946, "condition": "Clouds", "rainfallMm": 1.2, "tempC": 24.8, "windKph": 16.0},
    {"city": "Chennai", "state": "Tamil Nadu", "lat": 13.0827, "lon": 80.2707, "condition": "Clear", "rainfallMm": 0.0, "tempC": 32.5, "windKph": 18.2},
    {"city": "Kolkata", "state": "West Bengal", "lat": 22.5726, "lon": 88.3639, "condition": "Thunderstorm", "rainfallMm": 22.0, "tempC": 29.0, "windKph": 28.5},
    {"city": "Hyderabad", "state": "Telangana", "lat": 17.3850, "lon": 78.4867, "condition": "Clouds", "rainfallMm": 0.5, "tempC": 29.5, "windKph": 14.0},
    {"city": "Ahmedabad", "state": "Gujarat", "lat": 23.0225, "lon": 72.5714, "condition": "Clear", "rainfallMm": 0.0, "tempC": 38.4, "windKph": 12.0},
    {"city": "Pune", "state": "Maharashtra", "lat": 18.5204, "lon": 73.8567, "condition": "Rain", "rainfallMm": 8.0, "tempC": 25.5, "windKph": 15.0},
    {"city": "Jaipur", "state": "Rajasthan", "lat": 26.9124, "lon": 75.7873, "condition": "Clear", "rainfallMm": 0.0, "tempC": 37.0, "windKph": 13.5},
    {"city": "Lucknow", "state": "Uttar Pradesh", "lat": 26.8467, "lon": 80.9462, "condition": "Clouds", "rainfallMm": 0.0, "tempC": 33.8, "windKph": 9.0},
    {"city": "Kanpur", "state": "Uttar Pradesh", "lat": 26.4499, "lon": 80.3319, "condition": "Clouds", "rainfallMm": 0.0, "tempC": 34.0, "windKph": 10.0},
    {"city": "Nagpur", "state": "Maharashtra", "lat": 21.1458, "lon": 79.0882, "condition": "Clear", "rainfallMm": 0.0, "tempC": 41.2, "windKph": 14.0},
    {"city": "Indore", "state": "Madhya Pradesh", "lat": 22.7196, "lon": 75.8577, "condition": "Clear", "rainfallMm": 0.0, "tempC": 33.5, "windKph": 12.5},
    {"city": "Bhopal", "state": "Madhya Pradesh", "lat": 23.2599, "lon": 77.4126, "condition": "Clear", "rainfallMm": 0.0, "tempC": 34.5, "windKph": 11.0},
    {"city": "Visakhapatnam", "state": "Andhra Pradesh", "lat": 17.6868, "lon": 83.2185, "condition": "Clouds", "rainfallMm": 3.0, "tempC": 31.0, "windKph": 21.0},
    {"city": "Patna", "state": "Bihar", "lat": 25.5941, "lon": 85.1376, "condition": "Rain", "rainfallMm": 18.0, "tempC": 29.5, "windKph": 16.5},
    {"city": "Vadodara", "state": "Gujarat", "lat": 22.3072, "lon": 73.1812, "condition": "Clouds", "rainfallMm": 2.5, "tempC": 32.0, "windKph": 15.0},
    {"city": "Ludhiana", "state": "Punjab", "lat": 30.9010, "lon": 75.8573, "condition": "Clear", "rainfallMm": 0.0, "tempC": 35.0, "windKph": 8.5},
    {"city": "Agra", "state": "Uttar Pradesh", "lat": 27.1767, "lon": 78.0081, "condition": "Clear", "rainfallMm": 0.0, "tempC": 36.5, "windKph": 9.5},
    {"city": "Nashik", "state": "Maharashtra", "lat": 19.9975, "lon": 73.7898, "condition": "Rain", "rainfallMm": 6.5, "tempC": 26.0, "windKph": 17.0},
    {"city": "Varanasi", "state": "Uttar Pradesh", "lat": 25.3176, "lon": 82.9739, "condition": "Clouds", "rainfallMm": 0.0, "tempC": 33.0, "windKph": 10.0},
    {"city": "Srinagar", "state": "Jammu and Kashmir", "lat": 34.0837, "lon": 74.7973, "condition": "Clear", "rainfallMm": 0.0, "tempC": 18.5, "windKph": 6.0},
    {"city": "Amritsar", "state": "Punjab", "lat": 31.6340, "lon": 74.8723, "condition": "Clear", "rainfallMm": 0.0, "tempC": 34.8, "windKph": 8.0},
    {"city": "Ranchi", "state": "Jharkhand", "lat": 23.3441, "lon": 85.3096, "condition": "Thunderstorm", "rainfallMm": 15.0, "tempC": 27.2, "windKph": 22.0},
    {"city": "Guwahati", "state": "Assam", "lat": 26.1445, "lon": 91.7362, "condition": "Rain", "rainfallMm": 28.5, "tempC": 26.5, "windKph": 14.0},
    {"city": "Chandigarh", "state": "Chandigarh", "lat": 30.7333, "lon": 76.7794, "condition": "Clear", "rainfallMm": 0.0, "tempC": 33.0, "windKph": 10.0},
    {"city": "Shimla", "state": "Himachal Pradesh", "lat": 31.1048, "lon": 77.1734, "condition": "Clouds", "rainfallMm": 0.0, "tempC": 19.0, "windKph": 12.0},
    {"city": "Dehradun", "state": "Uttarakhand", "lat": 30.3165, "lon": 78.0322, "condition": "Rain", "rainfallMm": 11.0, "tempC": 26.0, "windKph": 13.0},
    {"city": "Kochi", "state": "Kerala", "lat": 9.9312, "lon": 76.2673, "condition": "Rain", "rainfallMm": 16.0, "tempC": 28.0, "windKph": 19.5},
    {"city": "Bhubaneswar", "state": "Odisha", "lat": 20.2961, "lon": 85.8245, "condition": "Thunderstorm", "rainfallMm": 19.5, "tempC": 29.8, "windKph": 25.0},
    {"city": "Panaji", "state": "Goa", "lat": 15.4909, "lon": 73.8278, "condition": "Rain", "rainfallMm": 12.0, "tempC": 29.0, "windKph": 22.5},
    {"city": "Thiruvananthapuram", "state": "Kerala", "lat": 8.5241, "lon": 76.9366, "condition": "Clouds", "rainfallMm": 4.5, "tempC": 28.5, "windKph": 17.0}
]

now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

readings = []
for item in major_cities:
    reading = {
        "id": str(uuid.uuid4()),
        "city": item["city"],
        "state": item["state"],
        "lat": item["lat"],
        "lon": item["lon"],
        "recordedAt": now_iso,
        "condition": item["condition"],
        "rainfallMm": item["rainfallMm"],
        "tempC": item["tempC"],
        "windKph": item["windKph"]
    }
    readings.append(reading)

with open("data/official_stations_snapshot.json", "w", encoding="utf-8") as f:
    json.dump({"totalStations": len(readings), "readings": readings}, f, indent=2, ensure_ascii=False)

print(f"Generated {len(readings)} official station snapshots in data/official_stations_snapshot.json")
