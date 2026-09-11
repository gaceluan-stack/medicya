import os
import json
import urllib.request

config_path = os.path.expandvars(r"%APPDATA%\netlify\Config\config.json")
print("Reading Netlify config from:", config_path)

if not os.path.exists(config_path):
    print("Netlify config file does not exist!")
    exit(1)

try:
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
        
    token = config.get("users", {}).get("luis garcia", {}).get("auth", {}).get("token")
    if not token:
        # Fallback to get any token
        users = config.get("users", {})
        for user_data in users.values():
            token = user_data.get("auth", {}).get("token")
            if token:
                break
                
    if not token:
        # Check global ticket or token
        token = config.get("token")
        
    if not token:
        print("No Netlify access token found in config!")
        exit(1)
        
    print("Netlify token found successfully.")
    
    # Query details for medicya (a916ffbd-0ad8-42ad-8ff8-cba5d5984407)
    site_ids = ["a916ffbd-0ad8-42ad-8ff8-cba5d5984407", "7d906470-57b5-4b88-98d8-fe8c7140bf3c"]
    for site_id in site_ids:
        url = f"https://api.netlify.com/api/v1/sites/{site_id}"
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0',
            'Authorization': f'Bearer {token}'
        })
        try:
            with urllib.request.urlopen(req) as response:
                site_data = json.loads(response.read().decode('utf-8'))
            print(f"\n--- Site: {site_data.get('name')} ---")
            print(f"URL: {site_data.get('url')}")
            print(f"Git Repo: {site_data.get('build_settings', {}).get('repo_path')}")
            print(f"Branch: {site_data.get('build_settings', {}).get('branch')}")
            print(f"Build Command: {site_data.get('build_settings', {}).get('cmd')}")
            
            # Fetch latest deploys
            deploys_url = f"https://api.netlify.com/api/v1/sites/{site_id}/deploys"
            deploys_req = urllib.request.Request(deploys_url, headers={
                'User-Agent': 'Mozilla/5.0',
                'Authorization': f'Bearer {token}'
            })
            with urllib.request.urlopen(deploys_req) as deploys_response:
                deploys_data = json.loads(deploys_response.read().decode('utf-8'))
            print("Latest Deploys:")
            for d in deploys_data[:3]:
                print(f"  - ID: {d.get('id')}, State: {d.get('state')}, Commit: {d.get('commit_ref')[:7] if d.get('commit_ref') else 'N/A'}, Created: {d.get('created_at')}, Error: {d.get('error')}")
        except Exception as e:
            print(f"Error fetching site {site_id}: {e}")
            
except Exception as e:
    print("Global Error:", e)
