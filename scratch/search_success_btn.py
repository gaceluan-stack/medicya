import os

f = r"c:\Users\User\Documents\antigravity\proyecto app medic ya\app\templates\index.html"
print("Reading file:", f)
if os.path.exists(f):
    with open(f, "r", encoding="utf-8") as file:
        content = file.read()
    
    # search for success-whatsapp-btn and booking-success-modal
    print("Contains 'booking-success-modal':", "booking-success-modal" in content)
    print("Contains 'success-whatsapp-btn':", "success-whatsapp-btn" in content)
    
    # print lines matching success-whatsapp-btn or booking-success-modal
    lines = content.splitlines()
    for idx, line in enumerate(lines):
        if "booking-success-modal" in line or "success-whatsapp-btn" in line or "success-doctor-name" in line:
            print(f"Line {idx+1}: {line.strip()}")
else:
    print("Does not exist!")
