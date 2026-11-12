import sys
import os
import argparse
import webbrowser
import time

# Hack para asegurar que el directorio actual sea visible para importaciones
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Reconfigurar salida estándar para UTF-8 si es posible (evita errores de codificación con caracteres unicode del AST)
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from compiler import compilar
from server import run_server

def run_cli_mode(texto):
    print("=" * 60)
    print(" COMPILADOR ARITMÉTICO (PLY) - MODO CLI")
    print("=" * 60)
    r = compilar(texto)
    if 'lines' not in r:
        print(r.get('message')); sys.exit(1)
    for l in r['lines']:
        print(f"\n[Línea {l['line']}] {l['text']}")
        print("  [1] Léxico :", ", ".join(f"{t['type']}({t['value']})" for t in l['tokens']))
        for e in l['errors']:
            print(f"  ERROR ({e['phase']}): {e['message']}")
            print("   " + l['text']); print("   " + " " * e['position'] + "^")
        if l['ast']:
            print("  [2] Sintáctico (AST anotado con tipos):")
            print("\n".join("      " + x for x in l['ast_ascii'].splitlines()))
        if l['status'] == 'ok':
            print(f"  [3] Semántico: valor = {l['valor']}  (tipo {l['tipo']})")
    print("\nTabla de símbolos:")
    print(f"  {'Lexema':<8}{'Tipo':<8}{'Ámbito':<8}{'Dir':<6}{'Valor':<10}{'Decl':<6}Refs")
    for f in r['symbol_table']:
        print(f"  {f['lexema']:<8}{f['tipo']:<8}{f['ambito']:<8}{f['direccion']:<6}{str(f['valor']):<10}{f['linea_decl']:<6}{f['lineas_ref']}")
    sys.exit(0 if r['status'] == 'success' else 1)

def main():
    parser = argparse.ArgumentParser(description="Simulador de Compilador Aritmético USB")
    parser.add_argument('--cli', type=str, help="Ejecutar en consola con el programa dado (usa \\n para varias líneas).")
    parser.add_argument('--file', type=str, help="Ejecutar en consola leyendo un archivo de texto (una instrucción por línea).")
    parser.add_argument('--web', action='store_true', help="Iniciar en modo interfaz web (por defecto).")
    parser.add_argument('--port', type=int, default=8000, help="Puerto para el servidor web (por defecto: 8000).")
    
    args = parser.parse_args()
    
    if args.file:
        run_cli_mode(open(args.file, encoding='utf-8').read())
    elif args.cli:
        run_cli_mode(args.cli.replace('\\n', '\n'))
    else:
        # Iniciar modo web por defecto
        # Abrir el navegador en un hilo ligero
        url = f"http://localhost:{args.port}"
        print(f"Iniciando interfaz interactiva en: {url}")
        
        # Pequeño truco para abrir el navegador un segundo después de lanzar el servidor
        # (Así el servidor ya está listo para recibir la petición)
        def open_browser():
            time.sleep(1.0)
            webbrowser.open(url)
            
        import threading
        threading.Thread(target=open_browser, daemon=True).start()
        
        run_server(args.port)

if __name__ == '__main__':
    main()
