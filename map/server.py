#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import http.server
import socketserver

PORT = 8080
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

try:
    ThreadingHTTPServer = http.server.ThreadingHTTPServer
except AttributeError:
    class ThreadingHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
        daemon_threads = True
        allow_reuse_address = True

class SandboxHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE_DIR, **kwargs)

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_POST(self):
        if self.path == '/api/save_coords':
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            try:
                import json
                data = json.loads(body.decode('utf-8'))
                coords_file = os.path.join(BASE_DIR, 'hk_project_coords.json')
                
                # Check if payload is single project update or full array
                if isinstance(data, dict) and 'name' in data:
                    with open(coords_file, 'r', encoding='utf-8') as f:
                        all_projects = json.load(f)
                    for i, p in enumerate(all_projects):
                        if p.get('name') == data.get('name'):
                            all_projects[i].update(data)
                            break
                    save_payload = all_projects
                elif isinstance(data, list):
                    save_payload = data
                else:
                    raise ValueError("Invalid payload format")

                with open(coords_file, 'w', encoding='utf-8') as f:
                    json.dump(save_payload, f, ensure_ascii=False, indent=2)

                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps({'status': 'ok', 'message': '坐标与路线已永久保存至 hk_project_coords.json'}).encode('utf-8'))
                print("💾 [API] 成功保存楼盘新坐标与步行路线至 hk_project_coords.json")
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps({'status': 'error', 'message': str(e)}).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

if __name__ == '__main__':
    # 允许命令行传入自定义端口
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        PORT = int(sys.argv[1])

    httpd = ThreadingHTTPServer(("", PORT), SandboxHTTPRequestHandler)
    print("=" * 64)
    print(f"🗺️  香港一手新盘沙盒地图 - 本地多线程服务器已启动！")
    print(f"📍 主入口 (全屏奢华悬浮版): http://localhost:{PORT}")
    print(f"   └─ 悬浮定版: http://localhost:{PORT}/test_layout_floating.html")
    print(f"   └─ 多维筛选: http://localhost:{PORT}/test_multi_filter_map.html")
    print(f"   └─ 仪表盘版: http://localhost:{PORT}/test_layout_dashboard.html")
    print(f"   └─ 管道流版: http://localhost:{PORT}/test_layout_pipeline.html")
    print(f"   └─ 分屏布局: http://localhost:{PORT}/test_layout_split.html")
    print(f"   └─ 对标布局: http://localhost:{PORT}/test_layout_benchmark.html")
    print("=" * 64)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n沙盒地图服务器已安全停止。")
