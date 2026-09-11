import urllib.request

url = "https://medic-ya.onrender.com/static/js/map.js"
try:
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as response:
        content = response.read().decode('utf-8')
        
    print(f"File size: {len(content)} bytes")
    print("Contains 'selectedBookingSlots':", "selectedBookingSlots" in content)
    print("Contains 'todayStr':", "todayStr" in content)
    
    # Print the lines around selectBookingSlot
    lines = content.splitlines()
    for idx, line in enumerate(lines):
        if "function selectBookingSlot" in line:
            print("\nFound selectBookingSlot:")
            for i in range(max(0, idx - 5), min(len(lines), idx + 20)):
                print(f"{i+1}: {lines[i]}")
except Exception as e:
    print("Error:", e)
