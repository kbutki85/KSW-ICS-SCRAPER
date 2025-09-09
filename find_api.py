#!/usr/bin/env python3

import requests
import json
from urllib.parse import urlparse, parse_qs

URL = "https://www.laczynaspilka.pl/rozgrywki?season=e9d66181-d03e-4bb3-b889-4da848f4831d&leagueGroup=43da7ba1-b751-4295-814b-24bd37fd2d45&leagueId=5cc45e5f-744b-428c-b8af-cdefca38de29&enumType=Play&group=e5bc0d4f-1bc4-40f5-92f9-e55c859b5166&isAdvanceMode=false&genderType=Male"

# Parse URL parameters
parsed = urlparse(URL)
params = parse_qs(parsed.query)

# Extract key parameters
season = params.get('season', [''])[0]
league_group = params.get('leagueGroup', [''])[0]
league_id = params.get('leagueId', [''])[0]
group = params.get('group', [''])[0]

print(f"Season: {season}")
print(f"League Group: {league_group}")
print(f"League ID: {league_id}")
print(f"Group: {group}")

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Referer': URL
}

# Try different API endpoint patterns
api_endpoints = [
    f"https://www.laczynaspilka.pl/api/matches?seasonId={season}&leagueGroupId={league_group}",
    f"https://www.laczynaspilka.pl/api/fixtures?seasonId={season}&leagueGroupId={league_group}",
    f"https://www.laczynaspilka.pl/api/games?seasonId={season}&leagueGroupId={league_group}",
    f"https://www.laczynaspilka.pl/api/schedule?seasonId={season}&leagueGroupId={league_group}",
    f"https://www.laczynaspilka.pl/api/matches?season={season}&leagueGroup={league_group}",
    f"https://www.laczynaspilka.pl/api/matches?season={season}&leagueGroup={league_group}&group={group}",
    f"https://www.laczynaspilka.pl/api/rozgrywki/matches?season={season}&leagueGroup={league_group}",
    "https://www.laczynaspilka.pl/api/matches",
    "https://www.laczynaspilka.pl/api/fixtures",
    "https://www.laczynaspilka.pl/api/games",
]

for endpoint in api_endpoints:
    try:
        print(f"\nTrying: {endpoint}")
        response = requests.get(endpoint, headers=headers, timeout=10)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            content_type = response.headers.get('content-type', '')
            print(f"Content-Type: {content_type}")
            
            if 'json' in content_type:
                try:
                    data = response.json()
                    if isinstance(data, list):
                        print(f"JSON array with {len(data)} items")
                        if len(data) > 0:
                            print("First item keys:", list(data[0].keys()) if isinstance(data[0], dict) else "Not a dict")
                    elif isinstance(data, dict):
                        print("JSON object with keys:", list(data.keys()))
                    else:
                        print("JSON data type:", type(data))
                except:
                    print("Invalid JSON")
            else:
                print(f"Content length: {len(response.text)}")
                if len(response.text) < 500:
                    print("Content preview:", response.text[:200])
        else:
            print(f"Error response: {response.text[:200]}")
            
    except Exception as e:
        print(f"Error: {e}")

print("\n" + "="*50)
print("Checking for GraphQL endpoint...")

graphql_endpoint = "https://www.laczynaspilka.pl/graphql"
graphql_query = {
    "query": "{ matches { id home away date } }"
}

try:
    response = requests.post(graphql_endpoint, json=graphql_query, headers=headers, timeout=10)
    print(f"GraphQL Status: {response.status_code}")
    if response.status_code == 200:
        print("GraphQL Response:", response.json())
except Exception as e:
    print(f"GraphQL Error: {e}")
