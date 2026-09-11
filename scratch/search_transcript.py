import os

log_path = r"C:\Users\User\.gemini\antigravity\brain\82f11ddf-4618-4217-bacf-0d5e2b83a997\.system_generated\logs\transcript.jsonl"
print("Reading log from:", log_path)

if not os.path.exists(log_path):
    print("Log file does not exist!")
    exit(1)

try:
    with open(log_path, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f):
            if "netlify" in line.lower():
                print(f"Line {idx+1}: {line[:300]}...")
except Exception as e:
    print("Error:", e)
