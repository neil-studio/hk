#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import http.server
import socketserver

PORT = 8000
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.join(BASE_DIR, "web")
CONFIG_PATH = os.path.join(BASE_DIR, "config_admin.json")

class ThreadingHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True

class SandboxHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        # 默认将静态目录定位到 web 文件夹
        super().__init__(*args, directory=WEB_DIR, **kwargs)

    def do_GET(self):
        # 兼容处理带版本戳的 /data.json?v=...
        if self.path.startswith('/data.json'):
            json_file = os.path.join(WEB_DIR, "data.json")
            if os.path.exists(json_file):
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                with open(json_file, 'rb') as f:
                    self.wfile.write(f.read())
                return
            else:
                self.send_error(404, "data.json not found")
                return

        # 获取配置接口
        if self.path == '/api/config':
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            if os.path.exists(CONFIG_PATH):
                with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                    self.wfile.write(f.read().encode('utf-8'))
            else:
                default_config = {
                    "focus_project": "",
                    "featured_projects": [],
                    "projects_data": {}
                }
                self.wfile.write(json.dumps(default_config, ensure_ascii=False).encode('utf-8'))
        else:
            # 执行默认静态文件处理
            super().do_GET()

    def do_POST(self):
        # 保存配置接口
        if self.path == '/api/save-config':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data.decode('utf-8'))
                
                with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                print("配置已成功持久化写入磁盘。")

                fetch_script = os.path.join(BASE_DIR, "fetch_floorplans.py")
                if os.path.exists(fetch_script):
                    import subprocess
                    print("检测到配置保存，正在静默运行 fetch_floorplans.py 抓取户型图...")
                    subprocess.run(["python3", fetch_script], cwd=BASE_DIR)

                build_script = os.path.join(BASE_DIR, "build_web.py")
                if os.path.exists(build_script):
                    import subprocess
                    print("检测到配置保存，正在自动运行 build_web.py 重建元数据...")
                    subprocess.run(["python3", build_script], cwd=BASE_DIR)
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json; charset=utf-8')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success"}, ensure_ascii=False).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

if __name__ == '__main__':
    httpd = ThreadingHTTPServer(("", PORT), SandboxHTTPRequestHandler)
    print("="*60)
    print(f"香港一手新盘一站通 - 测试版本地多线程服务已成功启动!")
    print(f"用户浏览端: http://localhost:{PORT}")
    print(f"管理员配置端: http://localhost:{PORT}/admin.html")
    print("="*60)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n服务器已安全停止。")
