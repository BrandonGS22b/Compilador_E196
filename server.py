import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import http.server
import json
import urllib.parse
from compiler import compilar

# Directorio base absoluto para que Vercel y local encuentren los archivos
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

PORT = 8000

class handler(http.server.BaseHTTPRequestHandler):
    
    def log_message(self, format, *args):
        # Deshabilitar logs ruidosos en consola
        pass

    def do_GET(self):
        # Enrutar la raíz directamente a index.html en la raíz del proyecto
        path = self.path
        if path == '/' or path == '/index.html':
            filepath = os.path.join(BASE_DIR, 'index.html')
            self.serve_file(filepath, 'text/html')
        else:
            filename = os.path.basename(path)
            filepath = os.path.join(BASE_DIR, filename)
            
            if os.path.exists(filepath) and os.path.isfile(filepath):
                ext = os.path.splitext(filename)[1].lower()
                content_type = 'text/plain'
                if ext == '.html':
                    content_type = 'text/html'
                elif ext == '.css':
                    content_type = 'text/css'
                elif ext == '.js':
                    content_type = 'text/javascript'
                elif ext == '.png':
                    content_type = 'image/png'
                elif ext == '.jpg' or ext == '.jpeg':
                    content_type = 'image/jpeg'
                self.serve_file(filepath, content_type)
            else:
                self.send_error(404, "File Not Found")

    def do_POST(self):
        if self.path == '/api/compile':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')
            
            try:
                data = json.loads(post_data)
                expression = data.get('expression', '')
            except Exception:
                self.send_json({'status': 'error', 'message': 'JSON inválido'}, 400)
                return

            response_data = self.compile_expression(expression)
            self.send_json(response_data)
        else:
            self.send_error(404, "Not Found")

    def serve_file(self, filepath, content_type):
        try:
            with open(filepath, 'rb') as f:
                content = f.read()
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.send_error(500, f"Error interno: {str(e)}")

    def send_json(self, data, status_code=200):
        try:
            response_content = json.dumps(data).encode('utf-8')
            self.send_response(status_code)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(response_content)))
            self.end_headers()
            self.wfile.write(response_content)
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(f"Error serializando JSON: {str(e)}".encode('utf-8'))

    def compile_expression(self, expression):
        try:
            return compilar(expression)
        except Exception as e:
            return {'status': 'error', 'message': f'Error interno del compilador: {e}'}

def run_server(port=PORT):
    server_address = ('', port)
    httpd = http.server.HTTPServer(server_address, handler)
    print(f"Servidor web local ejecutándose en http://localhost:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor web detenido.")
        httpd.server_close()