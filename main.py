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

from compiler import Lexer, Parser, SemanticAnalyzer, LexicalError, SyntacticError
from server import run_server

def run_cli_mode(expression):
    print("=" * 60)
    print(" SIMULACIÓN DE COMPILADOR ARITMÉTICO - MODO CLI")
    print("=" * 60)
    print(f"Expresión de entrada: '{expression}'\n")

    # 1. Fase de Análisis Léxico
    print("[1] ANALIZADOR LÉXICO:")
    lexer = Lexer(expression)
    try:
        tokens = lexer.tokenize_all()
        print("Tokens generados exitosamente:")
        for t in tokens:
            if t.type != 'EOF':
                print(f"  - Tipo: {t.type:<18} | Valor: {repr(t.value):<10} | Posición: {t.position}")
            else:
                print(f"  - Tipo: {t.type:<18} | Valor: EOF        | Posición: {t.position}")
        print()
    except LexicalError as le:
        print("ERROR LÉXICO DETECTADO:")
        print(f"  Mensaje: {le.args[0]}")
        print(f"  Fórmula: {expression}")
        # Dibujar un puntero debajo de la posición del error
        puntero = " " * (le.position + 11) + "^"
        print(puntero)
        print("=" * 60)
        sys.exit(1)

    # 2. Fase de Análisis Sintáctico
    print("[2] ANALIZADOR SINTÁCTICO:")
    lexer_for_parser = Lexer(expression)
    parser = Parser(lexer_for_parser)
    try:
        ast_root = parser.parse()
        print("Árbol de Sintaxis Abstracta (AST) generado:")
        print(ast_root.to_ascii())
    except SyntacticError as se:
        print("ERROR SINTÁCTICO DETECTADO:")
        print(f"  Mensaje: {se.args[0]}")
        print(f"  Fórmula: {expression}")
        puntero = " " * (se.position + 11) + "^"
        print(puntero)
        print("=" * 60)
        sys.exit(1)

    # 3. Fase de Análisis Semántico
    print("[3] ANALIZADOR SEMÁNTICO BÁSICO:")
    try:
        analyzer = SemanticAnalyzer(ast_root)
        symbol_table, type_table = analyzer.analyze()
        
        # Mostrar Tabla de Símbolos
        print("Tabla de Símbolos:")
        print(f"  {'Símbolo (Valor)':<16} | {'Dirección (Simulada)':<20}")
        print("  " + "-" * 40)
        
        # Ordenar por dirección secuencial
        sorted_symbols = sorted(symbol_table.items(), key=lambda item: int(item[1].split('_')[1]))
        for symbol, addr in sorted_symbols:
            print(f"  {symbol:<16} | {addr:<20}")
        print()

        # Mostrar Tabla de Tipos
        print("Tabla de Tipos:")
        print(f"  {'Símbolo (Valor)':<16} | {'Tipo de Dato':<20}")
        print("  " + "-" * 40)
        for symbol, addr in sorted_symbols:
            print(f"  {symbol:<16} | {type_table[symbol]:<20}")
            
    except Exception as e:
        print(f"ERROR SEMÁNTICO DETECTADO: {str(e)}")
        print("=" * 60)
        sys.exit(1)

    print("=" * 60)
    print(" PROCESAMIENTO COMPLETADO EXITOSAMENTE")
    print("=" * 60)

def main():
    parser = argparse.ArgumentParser(description="Simulador de Compilador Aritmético USB")
    parser.add_argument('--cli', type=str, help="Ejecutar en consola con la expresión aritmética dada.")
    parser.add_argument('--web', action='store_true', help="Iniciar en modo interfaz web (por defecto).")
    parser.add_argument('--port', type=int, default=8000, help="Puerto para el servidor web (por defecto: 8000).")
    
    args = parser.parse_args()
    
    if args.cli:
        run_cli_mode(args.cli)
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
