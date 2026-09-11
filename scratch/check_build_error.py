import os
import json
import urllib.request

config_path = os.path.expandvars(r"%APPDATA%\netlify\Config\config.json")
try:
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
        
    token = config.get("users", {}).get("luis garcia", {}).get("auth", {}).get("token")
    if not token:
        users = config.get("users", {})
        for user_data in users.values():
            token = user_data.get("auth", {}).get("token")
            if token:
                break
                
    deploy_id = "6a8deef5a7ec8c0008705aec"
    url = f"https://api.netlify.com/api/v1/deploys/{deploy_id}"
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0',
        'Authorization': f'Bearer {token}'
    })
    
    with urllib.request.urlopen(req) as response:
        deploy_data = json.loads(response.read().decode('utf-8'))
        
    print(f"Deploy ID: {deploy_id}")
    print(f"State: {deploy_data.get('state')}")
    print(f"Error Message: {deploy_data.get('error_message')}")
    print(f"Log: {deploy_data.get('log_access_attributes')}")
    
except Exception as e:
    print("Error:", e)
