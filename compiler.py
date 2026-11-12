import re

# =====================================================================
# Definición de Tokens
# =====================================================================
class TokenType:
    INT = 'ENTERO'
    PLUS = 'MAS'
    MINUS = 'MENOS'
    MUL = 'MULTIPLICACION'
    DIV = 'DIVISION'
    LPAREN = 'PARENTESIS_IZQ'
    RPAREN = 'PARENTESIS_DER'
    EOF = 'EOF'

class Token:
    def __init__(self, type_, value, position):
        self.type = type_
        self.value = value
        self.position = position  # Índice inicial en la cadena de texto

    def __repr__(self):
        return f"Token({self.type}, {repr(self.value)}, pos={self.position})"

    def to_dict(self):
        return {
            'type': self.type,
            'value': self.value,
            'position': self.position
        }


# =====================================================================
# Excepciones del Compilador
# =====================================================================
class LexicalError(Exception):
    def __init__(self, message, position, char):
        super().__init__(message)
        self.position = position
        self.char = char


class SyntacticError(Exception):
    def __init__(self, message, position, token):
        super().__init__(message)
        self.position = position
        self.token = token


# =====================================================================
# Analizador Léxico (Lexer)
# =====================================================================
class Lexer:
    def __init__(self, text):
        self.text = text
        self.pos = 0
        self.current_char = self.text[0] if len(self.text) > 0 else None

    def advance(self):
        self.pos += 1
        if self.pos > len(self.text) - 1:
            self.current_char = None
        else:
            self.current_char = self.text[self.pos]

    def skip_whitespace(self):
        while self.current_char is not None and self.current_char.isspace():
            self.advance()

    def integer(self):
        start_pos = self.pos
        result = ''
        while self.current_char is not None and self.current_char.isdigit():
            result += self.current_char
            self.advance()
        return Token(TokenType.INT, int(result), start_pos)

    def get_next_token(self):
        while self.current_char is not None:
            if self.current_char.isspace():
                self.skip_whitespace()
                continue

            if self.current_char.isdigit():
                return self.integer()

            if self.current_char == '+':
                token = Token(TokenType.PLUS, '+', self.pos)
                self.advance()
                return token

            if self.current_char == '-':
                token = Token(TokenType.MINUS, '-', self.pos)
                self.advance()
                return token

            if self.current_char == '*':
                token = Token(TokenType.MUL, '*', self.pos)
                self.advance()
                return token

            if self.current_char == '/':
                token = Token(TokenType.DIV, '/', self.pos)
                self.advance()
                return token

            if self.current_char == '(':
                token = Token(TokenType.LPAREN, '(', self.pos)
                self.advance()
                return token

            if self.current_char == ')':
                token = Token(TokenType.RPAREN, ')', self.pos)
                self.advance()
                return token

            # Error Léxico: Carácter no permitido
            char = self.current_char
            pos = self.pos
            self.advance()
            raise LexicalError(
                f"Carácter no válido '{char}' encontrado en la posición {pos}.",
                pos,
                char
            )

        return Token(TokenType.EOF, None, self.pos)

    def tokenize_all(self):
        tokens = []
        lexer_clone = Lexer(self.text)
        while True:
            token = lexer_clone.get_next_token()
            tokens.append(token)
            if token.type == TokenType.EOF:
                break
        return tokens


# =====================================================================
# Nodos del Árbol de Sintaxis Abstracta (AST)
# =====================================================================
class AST:
    def to_dict(self):
        raise NotImplementedError()

    def to_ascii(self, prefix="", is_last=True):
        raise NotImplementedError()


class NumNode(AST):
    def __init__(self, token):
        self.token = token
        self.value = token.value

    def __repr__(self):
        return f"NumNode({self.value})"

    def to_dict(self):
        return {
            'type': 'Num',
            'value': self.value,
            'position': self.token.position
        }

    def to_ascii(self, prefix="", is_last=True):
        marker = "└── " if is_last else "├── "
        return f"{prefix}{marker}Num({self.value})\n"


class BinOpNode(AST):
    def __init__(self, left, op_token, right):
        self.left = left
        self.op_token = op_token
        self.op = op_token.value
        self.right = right

    def __repr__(self):
        return f"BinOpNode({self.left}, {self.op}, {self.right})"

    def to_dict(self):
        return {
            'type': 'BinOp',
            'op': self.op,
            'position': self.op_token.position,
            'left': self.left.to_dict(),
            'right': self.right.to_dict()
        }

    def to_ascii(self, prefix="", is_last=True):
        marker = "└── " if is_last else "├── "
        result = f"{prefix}{marker}Op({self.op})\n"
        
        # Preparar prefijo para los hijos
        new_prefix = prefix + ("    " if is_last else "│   ")
        
        # Dibujar hijos
        result += self.left.to_ascii(new_prefix, is_last=False)
        result += self.right.to_ascii(new_prefix, is_last=True)
        
        return result


# =====================================================================
# Analizador Sintáctico (Parser)
# =====================================================================
class Parser:
    def __init__(self, lexer):
        self.lexer = lexer
        self.current_token = self.lexer.get_next_token()

    def error(self, message):
        raise SyntacticError(message, self.current_token.position, self.current_token)

    def consume(self, token_type):
        if self.current_token.type == token_type:
            self.current_token = self.lexer.get_next_token()
        else:
            self.error(f"Se esperaba token {token_type}, pero se obtuvo {self.current_token.type}")

    def factor(self):
        """factor : INT | LPAREN expr RPAREN"""
        token = self.current_token
        if token.type == TokenType.INT:
            self.consume(TokenType.INT)
            return NumNode(token)
        elif token.type == TokenType.LPAREN:
            self.consume(TokenType.LPAREN)
            node = self.expr()
            if self.current_token.type != TokenType.RPAREN:
                self.error("Falta paréntesis de cierre ')'")
            self.consume(TokenType.RPAREN)
            return node
        else:
            self.error(f"Se esperaba un número o un paréntesis de apertura, pero se encontró '{token.value or token.type}'")

    def term(self):
        """term : factor ((MUL | DIV) factor)*"""
        node = self.factor()

        while self.current_token.type in (TokenType.MUL, TokenType.DIV):
            token = self.current_token
            if token.type == TokenType.MUL:
                self.consume(TokenType.MUL)
            elif token.type == TokenType.DIV:
                self.consume(TokenType.DIV)
            node = BinOpNode(left=node, op_token=token, right=self.factor())

        return node

    def expr(self):
        """expr : term ((PLUS | MINUS) term)*"""
        node = self.term()

        while self.current_token.type in (TokenType.PLUS, TokenType.MINUS):
            token = self.current_token
            if token.type == TokenType.PLUS:
                self.consume(TokenType.PLUS)
            elif token.type == TokenType.MINUS:
                self.consume(TokenType.MINUS)
            node = BinOpNode(left=node, op_token=token, right=self.term())

        return node

    def parse(self):
        node = self.expr()
        if self.current_token.type != TokenType.EOF:
            self.error(f"Carácter inesperado o fin de expresión no alcanzado. Token sobrante: {self.current_token}")
        return node


# =====================================================================
# Analizador Semántico (SemanticAnalyzer)
# =====================================================================
class SemanticAnalyzer:
    def __init__(self, ast):
        self.ast = ast
        self.symbol_table = {}
        self.type_table = {}

    def analyze(self):
        # Encontrar todos los operandos (números) únicos
        unique_numbers = sorted(list(self._collect_numbers(self.ast)))
        
        # Construir Tabla de Símbolos y de Tipos
        for i, num in enumerate(unique_numbers, start=1):
            addr = f"dir_{i}"
            self.symbol_table[num] = addr
            self.type_table[num] = "entero"
            
        return self.symbol_table, self.type_table

    def _collect_numbers(self, node):
        numbers = set()
        if isinstance(node, NumNode):
            numbers.add(node.value)
        elif isinstance(node, BinOpNode):
            numbers.update(self._collect_numbers(node.left))
            numbers.update(self._collect_numbers(node.right))
        return numbers
