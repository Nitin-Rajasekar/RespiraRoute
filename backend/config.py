"""Shared configuration for RespiraRoute backend."""

# ── Indian Cities with Sub-Zones ─────────────────────────────────
CITIES = {
    "Delhi": {
        "lat": 28.6139, "lng": 77.2090,
        "zones": {
            "Connaught Place": {"lat": 28.6315, "lng": 77.2167, "address": "Connaught Place, New Delhi, India"},
            "Dwarka": {"lat": 28.5921, "lng": 77.0460, "address": "Dwarka Sector 21, New Delhi, India"},
            "Anand Vihar": {"lat": 28.6469, "lng": 77.3164, "address": "Anand Vihar, East Delhi, India"},
            "ITO": {"lat": 28.6289, "lng": 77.2405, "address": "ITO, IP Estate, New Delhi, India"},
            "Rohini": {"lat": 28.7495, "lng": 77.0565, "address": "Rohini Sector 3, New Delhi, India"},
        },
    },
    "Mumbai": {
        "lat": 19.0760, "lng": 72.8777,
        "zones": {
            "Bandra": {"lat": 19.0596, "lng": 72.8295, "address": "Bandra West, Mumbai, Maharashtra, India"},
            "Andheri": {"lat": 19.1136, "lng": 72.8697, "address": "Andheri East, Mumbai, Maharashtra, India"},
            "Colaba": {"lat": 18.9067, "lng": 72.8147, "address": "Colaba Causeway, Mumbai, Maharashtra, India"},
            "Worli": {"lat": 19.0176, "lng": 72.8152, "address": "Worli Sea Face, Mumbai, Maharashtra, India"},
            "Powai": {"lat": 19.1176, "lng": 72.9060, "address": "Powai, Mumbai, Maharashtra, India"},
        },
    },
    "Bangalore": {
        "lat": 12.9716, "lng": 77.5946,
        "zones": {
            "MG Road": {"lat": 12.9758, "lng": 77.6045, "address": "MG Road, Bangalore, Karnataka, India"},
            "Whitefield": {"lat": 12.9698, "lng": 77.7500, "address": "Whitefield Main Road, Bangalore, Karnataka, India"},
            "Electronic City": {"lat": 12.8399, "lng": 77.6770, "address": "Electronic City Phase 1, Bangalore, Karnataka, India"},
            "Koramangala": {"lat": 12.9352, "lng": 77.6245, "address": "Koramangala 5th Block, Bangalore, Karnataka, India"},
            "Hebbal": {"lat": 13.0358, "lng": 77.5970, "address": "Hebbal Flyover, Bangalore, Karnataka, India"},
        },
    },
    "Chennai": {
        "lat": 13.0827, "lng": 80.2707,
        "zones": {
            "T Nagar": {"lat": 13.0418, "lng": 80.2341, "address": "T Nagar, Chennai, Tamil Nadu, India"},
            "Adyar": {"lat": 13.0012, "lng": 80.2565, "address": "Adyar, Chennai, Tamil Nadu, India"},
            "Anna Nagar": {"lat": 13.0850, "lng": 80.2101, "address": "Anna Nagar, Chennai, Tamil Nadu, India"},
            "Guindy": {"lat": 13.0067, "lng": 80.2206, "address": "Guindy, Chennai, Tamil Nadu, India"},
            "Velachery": {"lat": 12.9815, "lng": 80.2180, "address": "Velachery, Chennai, Tamil Nadu, India"},
        },
    },
    "Kolkata": {
        "lat": 22.5726, "lng": 88.3639,
        "zones": {
            "Park Street": {"lat": 22.5516, "lng": 88.3522, "address": "Park Street, Kolkata, West Bengal, India"},
            "Salt Lake": {"lat": 22.5800, "lng": 88.4179, "address": "Salt Lake City, Kolkata, West Bengal, India"},
            "Howrah": {"lat": 22.5958, "lng": 88.2636, "address": "Howrah Station, Howrah, West Bengal, India"},
            "New Town": {"lat": 22.5922, "lng": 88.4845, "address": "New Town, Rajarhat, Kolkata, West Bengal, India"},
            "Jadavpur": {"lat": 22.4990, "lng": 88.3697, "address": "Jadavpur, Kolkata, West Bengal, India"},
        },
    },
    "Hyderabad": {
        "lat": 17.3850, "lng": 78.4867,
        "zones": {
            "HITEC City": {"lat": 17.4435, "lng": 78.3772, "address": "HITEC City, Hyderabad, Telangana, India"},
            "Secunderabad": {"lat": 17.4399, "lng": 78.4983, "address": "Secunderabad Railway Station, Hyderabad, Telangana, India"},
            "Gachibowli": {"lat": 17.4401, "lng": 78.3489, "address": "Gachibowli, Hyderabad, Telangana, India"},
            "Charminar": {"lat": 17.3616, "lng": 78.4747, "address": "Charminar, Hyderabad, Telangana, India"},
            "Banjara Hills": {"lat": 17.4156, "lng": 78.4347, "address": "Banjara Hills Road No. 1, Hyderabad, Telangana, India"},
        },
    },
    "Pune": {
        "lat": 18.5204, "lng": 73.8567,
        "zones": {
            "Shivaji Nagar": {"lat": 18.5308, "lng": 73.8475, "address": "Shivaji Nagar, Pune, Maharashtra, India"},
            "Hinjewadi": {"lat": 18.5912, "lng": 73.7390, "address": "Hinjewadi IT Park, Pune, Maharashtra, India"},
            "Kothrud": {"lat": 18.5074, "lng": 73.8077, "address": "Kothrud, Pune, Maharashtra, India"},
            "Hadapsar": {"lat": 18.5089, "lng": 73.9260, "address": "Hadapsar, Pune, Maharashtra, India"},
            "Viman Nagar": {"lat": 18.5679, "lng": 73.9143, "address": "Viman Nagar, Pune, Maharashtra, India"},
        },
    },
    "Ahmedabad": {
        "lat": 23.0225, "lng": 72.5714,
        "zones": {
            "SG Highway": {"lat": 23.0300, "lng": 72.5100, "address": "SG Highway, Ahmedabad, Gujarat, India"},
            "Maninagar": {"lat": 22.9937, "lng": 72.6020, "address": "Maninagar, Ahmedabad, Gujarat, India"},
            "Navrangpura": {"lat": 23.0396, "lng": 72.5600, "address": "Navrangpura, Ahmedabad, Gujarat, India"},
            "Vastrapur": {"lat": 23.0365, "lng": 72.5290, "address": "Vastrapur, Ahmedabad, Gujarat, India"},
            "Chandkheda": {"lat": 23.1086, "lng": 72.5847, "address": "Chandkheda, Ahmedabad, Gujarat, India"},
        },
    },
    "Jaipur": {
        "lat": 26.9124, "lng": 75.7873,
        "zones": {
            "MI Road": {"lat": 26.9157, "lng": 75.7922, "address": "MI Road, Jaipur, Rajasthan, India"},
            "Malviya Nagar": {"lat": 26.8553, "lng": 75.8117, "address": "Malviya Nagar, Jaipur, Rajasthan, India"},
            "Vaishali Nagar": {"lat": 26.9120, "lng": 75.7260, "address": "Vaishali Nagar, Jaipur, Rajasthan, India"},
            "Mansarovar": {"lat": 26.8688, "lng": 75.7563, "address": "Mansarovar, Jaipur, Rajasthan, India"},
            "C-Scheme": {"lat": 26.9063, "lng": 75.7887, "address": "C-Scheme, Jaipur, Rajasthan, India"},
        },
    },
    "Lucknow": {
        "lat": 26.8467, "lng": 80.9462,
        "zones": {
            "Hazratganj": {"lat": 26.8498, "lng": 80.9465, "address": "Hazratganj, Lucknow, Uttar Pradesh, India"},
            "Gomti Nagar": {"lat": 26.8567, "lng": 80.9918, "address": "Gomti Nagar, Lucknow, Uttar Pradesh, India"},
            "Aliganj": {"lat": 26.8975, "lng": 80.9386, "address": "Aliganj, Lucknow, Uttar Pradesh, India"},
            "Indira Nagar": {"lat": 26.8772, "lng": 80.9912, "address": "Indira Nagar, Lucknow, Uttar Pradesh, India"},
            "Aminabad": {"lat": 26.8428, "lng": 80.9210, "address": "Aminabad, Lucknow, Uttar Pradesh, India"},
        },
    },
}

DEFAULT_CITY = "Delhi"

# Backward compatibility alias — used by custom_router
ZONES = CITIES[DEFAULT_CITY]["zones"]

# AQI category thresholds
AQI_CATEGORIES = [
    (50, "Good", "#22c55e"),
    (100, "Moderate", "#eab308"),
    (150, "Unhealthy for Sensitive", "#f97316"),
    (200, "Unhealthy", "#ef4444"),
    (300, "Very Unhealthy", "#a855f7"),
    (500, "Hazardous", "#7f1d1d"),
]

# Data stream settings
STREAM_INTERVAL_SECONDS = 120
DATA_FILE = "stream_data/zone_data.jsonl"

# Server
API_HOST = "0.0.0.0"
API_PORT = 8000
