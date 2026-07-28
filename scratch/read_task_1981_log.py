import os

log_path = "/Users/nb/.gemini/antigravity/brain/4977a979-cde7-4c64-993d-eb1f3f91ccb4/.system_generated/tasks/task-1981.log"
if os.path.exists(log_path):
    with open(log_path, 'r', encoding='utf-8') as f:
        print(f.read())
else:
    print(f"日志文件不存在: {log_path}")
