import urllib.request
import json

url = "https://api.netlify.com/api/v1/sites/a916ffbd-0ad8-42ad-8ff8-cba5d5984407/deploys"
try:
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode('utf-8'))
        
    print(f"Total deploys: {len(data)}")
    for d in data[:5]:
        print(f"ID: {d.get('id')}, State: {d.get('state')}, Branch: {d.get('branch')}, Context: {d.get('context')}, Created: {d.get('created_at')}")
except Exception as e:
    print("Error:", e)
