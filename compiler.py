"""Compilador aritmético: léxico + sintáctico (PLY) + semántico.

Cada línea del programa es una instrucción:
    x = (1 + 5) * 20 / 5      asignación (declara/actualiza la variable)
    Evaluar[1 + 1];           evaluación (PDF 2)
    3 + 4                     expresión suelta
"""
import ply.lex as lex
import ply.yacc as yacc

RESERVADAS = {'Evaluar': 'EVALUAR'}
TOKENS = ('ID', 'NUMBER', 'DECIMAL', 'PLUS', 'MINUS', 'TIMES', 'DIVIDE',
          'LPAREN', 'RPAREN', 'EQUAL', 'LBRACKET', 'RBRACKET', 'SEMI', 'EVALUAR')
TAMANO = {'entero': 4, 'real': 8}   # bytes simulados para la dirección


class SemanticError(Exception):
    def __init__(self, message, position, line):
        super().__init__(message)
        self.position = position
        self.line = line


# =====================================================================
# Analizador léxico (PLY)
# =====================================================================
class Lexico:
    tokens = TOKENS
    t_PLUS = r'\+'
    t_MINUS = r'-'
    t_TIMES = r'\*'
    t_DIVIDE = r'/'
    t_LPAREN = r'\('
    t_RPAREN = r'\)'
    t_EQUAL = r'='
    t_LBRACKET = r'\['
    t_RBRACKET = r'\]'
    t_SEMI = r';'
    t_ignore = ' \t\r'

    def __init__(self):
        self.errores = []
        self.lexer = lex.lex(module=self, errorlog=lex.NullLogger())

    def t_DECIMAL(self, t):
        r'\d+\.\d+'
        t.value = float(t.value)
        return t

    def t_NUMBER(self, t):
        r'\d+'
        t.value = int(t.value)
        return t

    def t_ID(self, t):
        r'[A-Za-z_][A-Za-z_0-9]*'
        t.type = RESERVADAS.get(t.value, 'ID')
        return t

    def t_newline(self, t):
        r'\n+'
        t.lexer.lineno += len(t.value)

    def t_error(self, t):
        # Se registra y se continúa: así se reportan TODOS los caracteres ilegales.
        self.errores.append((t.value[0], t.lexpos, t.lexer.lineno))
        t.lexer.skip(1)

    def tokenizar(self, texto, linea):
        self.errores = []
        self.lexer.lineno = linea
        self.lexer.input(texto)
        toks = list(iter(self.lexer.token, None))
        return toks, list(self.errores)


# =====================================================================
# Nodos del AST (con atributos sintetizados: tipo y valor)
# =====================================================================
class Nodo:
    kind = 'stmt'

    def __init__(self, linea=0, pos=0):
        self.linea, self.pos = linea, pos
        self.tipo = None
        self.valor = None

    def etiqueta(self): return type(self).__name__
    def corto(self): return self.etiqueta()
    def hijos(self): return []

    def to_dict(self):
        return {'label': self.etiqueta(), 'short': self.corto(), 'kind': self.kind,
                'tipo': self.tipo, 'children': [h.to_dict() for h in self.hijos()]}

    def to_ascii(self, prefix="", last=True):
        txt = f"{prefix}{'└── ' if last else '├── '}{self.etiqueta()}"
        txt += f" : {self.tipo}\n" if self.tipo else "\n"
        nuevo = prefix + ("    " if last else "│   ")
        hs = self.hijos()
        for i, h in enumerate(hs):
            txt += h.to_ascii(nuevo, i == len(hs) - 1)
        return txt


class Num(Nodo):
    kind = 'num'
    def __init__(self, v, l, p): super().__init__(l, p); self.value = v
    def etiqueta(self): return f"Num({self.value})"
    def corto(self): return str(self.value)


class Var(Nodo):
    kind = 'var'
    def __init__(self, n, l, p): super().__init__(l, p); self.name = n
    def etiqueta(self): return f"Id({self.name})"
    def corto(self): return self.name


class BinOp(Nodo):
    kind = 'op'
    def __init__(self, op, a, b, l, p): super().__init__(l, p); self.op, self.left, self.right = op, a, b
    def etiqueta(self): return f"Op({self.op})"
    def corto(self): return self.op
    def hijos(self): return [self.left, self.right]


class Unary(Nodo):
    kind = 'op'
    def __init__(self, op, e, l, p): super().__init__(l, p); self.op, self.expr = op, e
    def etiqueta(self): return f"Neg({self.op})"
    def corto(self): return self.op
    def hijos(self): return [self.expr]


class Assign(Nodo):
    def __init__(self, n, e, l, p): super().__init__(l, p); self.name, self.expr = n, e
    def etiqueta(self): return f"Asignar({self.name})"
    def corto(self): return f"{self.name}="
    def hijos(self): return [self.expr]


class Evaluar(Nodo):
    def __init__(self, e, l, p): super().__init__(l, p); self.expr = e
    def etiqueta(self): return "Evaluar"
    def hijos(self): return [self.expr]


# =====================================================================
# Analizador sintáctico (PLY / yacc)
# =====================================================================
class Sintactico:
    tokens = TOKENS
    precedence = (
        ('left', 'PLUS', 'MINUS'),
        ('left', 'TIMES', 'DIVIDE'),
        ('right', 'UMINUS'),
    )
    start = 'linea'

    def __init__(self):
        self.error = None
        self.parser = yacc.yacc(module=self, write_tables=False, debug=False,
                                errorlog=yacc.NullLogger())

    def p_linea(self, p):
        '''linea : sentencia
                 | sentencia SEMI'''
        p[0] = p[1]

    def p_sentencia_asignacion(self, p):
        'sentencia : ID EQUAL expr'
        p[0] = Assign(p[1], p[3], p.lineno(1), p.lexpos(1))

    def p_sentencia_evaluar(self, p):
        'sentencia : EVALUAR LBRACKET expr RBRACKET'
        p[0] = Evaluar(p[3], p.lineno(1), p.lexpos(1))

    def p_sentencia_expr(self, p):
        'sentencia : expr'
        p[0] = p[1]

    def p_expr_binaria(self, p):
        '''expr : expr PLUS expr
                | expr MINUS expr
                | expr TIMES expr
                | expr DIVIDE expr'''
        p[0] = BinOp(p[2], p[1], p[3], p.lineno(2), p.lexpos(2))

    def p_expr_unaria(self, p):
        'expr : MINUS expr %prec UMINUS'
        p[0] = Unary('-', p[2], p.lineno(1), p.lexpos(1))

    def p_expr_grupo(self, p):
        'expr : LPAREN expr RPAREN'
        p[0] = p[2]

    def p_expr_numero(self, p):
        '''expr : NUMBER
                | DECIMAL'''
        p[0] = Num(p[1], p.lineno(1), p.lexpos(1))

    def p_expr_id(self, p):
        'expr : ID'
        p[0] = Var(p[1], p.lineno(1), p.lexpos(1))

    def p_error(self, p):
        if self.error is None:      # solo el primer error
            self.error = p if p else 'EOF'

    def analizar(self, texto, lexer):
        self.error = None
        arbol = self.parser.parse(texto, lexer=lexer)
        return (None if self.error is not None else arbol), self.error


# =====================================================================
# Tabla de símbolos + analizador semántico
# =====================================================================
class TablaSimbolos:
    def __init__(self):
        self.entradas = {}
        self.siguiente = 0

    def insertar(self, nombre, tipo, valor, linea):
        e = self.entradas.get(nombre)
        if e is None:
            self.entradas[nombre] = {'lexema': nombre, 'tipo': tipo, 'ambito': 'global',
                                     'direccion': self.siguiente, 'valor': valor,
                                     'linea_decl': linea, 'lineas_ref': []}
            self.siguiente += TAMANO[tipo]
        else:
            e['tipo'], e['valor'] = tipo, valor

    def buscar(self, nombre):
        return self.entradas.get(nombre)

    def eliminar(self, nombre):
        return self.entradas.pop(nombre, None)

    def referenciar(self, nombre, linea):
        refs = self.entradas[nombre]['lineas_ref']
        if linea not in refs:
            refs.append(linea)

    def filas(self):
        return [dict(e) for e in self.entradas.values()]


class AnalizadorSemantico:
    """Calcula los atributos sintetizados tipo y valor y comprueba la corrección semántica."""

    def __init__(self):
        self.tabla = TablaSimbolos()

    def visitar(self, n):
        getattr(self, 'v_' + type(n).__name__)(n)
        return n

    def v_Num(self, n):
        n.tipo = 'real' if isinstance(n.value, float) else 'entero'
        n.valor = n.value

    def v_Var(self, n):
        e = self.tabla.buscar(n.name)
        if e is None:
            raise SemanticError(f"Identificador no declarado: '{n.name}' en la línea {n.linea}, "
                                f"columna {n.pos + 1}.", n.pos, n.linea)
        self.tabla.referenciar(n.name, n.linea)
        n.tipo, n.valor = e['tipo'], e['valor']

    def v_Unary(self, n):
        self.visitar(n.expr)
        n.tipo, n.valor = n.expr.tipo, -n.expr.valor

    def v_BinOp(self, n):
        self.visitar(n.left)
        self.visitar(n.right)
        a, b = n.left.valor, n.right.valor
        if n.op == '/' and b == 0:
            raise SemanticError(f"División por cero en la línea {n.linea}, columna {n.pos + 1}.",
                                n.pos, n.linea)
        n.valor = {'+': a + b, '-': a - b, '*': a * b, '/': (a / b if b else 0)}[n.op]
        # '/' siempre produce real; el resto promueve a real si algún operando lo es
        n.tipo = 'real' if (n.op == '/' or 'real' in (n.left.tipo, n.right.tipo)) else 'entero'

    def v_Assign(self, n):
        self.visitar(n.expr)
        n.tipo, n.valor = n.expr.tipo, n.expr.valor
        self.tabla.insertar(n.name, n.tipo, n.valor, n.linea)

    def v_Evaluar(self, n):
        self.visitar(n.expr)
        n.tipo, n.valor = n.expr.tipo, n.expr.valor


# =====================================================================
# Orquestación
# =====================================================================
_lexico = _sintactico = None


def _limpio(v):
    return round(v, 10) if isinstance(v, float) else v


def _err(fase, msg, pos, linea, **extra):
    d = {'phase': fase, 'message': msg, 'position': pos, 'line': linea, 'column': pos + 1}
    d.update(extra)
    return d


def _procesar_linea(lx, ps, sem, texto, num):
    res = {'line': num, 'text': texto, 'status': 'ok', 'tokens': [], 'errors': [],
           'ast': None, 'ast_ascii': '', 'valor': None, 'tipo': None}
    toks, errs = lx.tokenizar(texto, num)
    res['tokens'] = [{'type': t.type, 'value': t.value, 'line': t.lineno, 'position': t.lexpos}
                     for t in toks]
    if errs:
        res['status'] = 'lexical_error'
        res['errors'] = [_err('Error léxico', f"Carácter ilegal '{c}' en la línea {l}, columna {p + 1}.",
                              p, l, char=c) for c, p, l in errs]
        return res

    arbol, error = ps.analizar(texto, lx.lexer)
    if arbol is None:
        res['status'] = 'syntax_error'
        if error == 'EOF' or error is None:
            res['errors'] = [_err('Error sintáctico', "La instrucción terminó inesperadamente "
                                  "(falta un operando o un cierre).", len(texto), num)]
        else:
            res['errors'] = [_err('Error sintáctico',
                                  f"Token inesperado '{error.value}' ({error.type}) en la línea "
                                  f"{num}, columna {error.lexpos + 1}.", error.lexpos, num)]
        return res

    try:
        sem.visitar(arbol)
        res['valor'], res['tipo'] = _limpio(arbol.valor), arbol.tipo
    except SemanticError as e:
        res['status'] = 'semantic_error'
        res['errors'] = [_err('Error semántico', e.args[0], e.position, e.line)]
    res['ast'] = arbol.to_dict()
    res['ast_ascii'] = arbol.to_ascii()
    return res


def compilar(texto):
    """Compila un programa (una instrucción por línea). Devuelve un dict serializable a JSON."""
    global _lexico, _sintactico
    if _lexico is None:
        _lexico, _sintactico = Lexico(), Sintactico()
    sem = AnalizadorSemantico()
    lineas = [_procesar_linea(_lexico, _sintactico, sem, l.rstrip('\r'), i)
              for i, l in enumerate((texto or '').split('\n'), 1) if l.strip()]
    if not lineas:
        return {'status': 'empty', 'message': 'Ingresa al menos una expresión.'}
    tabla = sem.tabla.filas()
    for f in tabla:
        f['valor'] = _limpio(f['valor'])
    ok = all(l['status'] == 'ok' for l in lineas)
    return {'status': 'success' if ok else 'error', 'lines': lineas,
            'symbol_table': tabla}
