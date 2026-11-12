import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import unittest
from compiler import Lexer, Parser, SemanticAnalyzer, TokenType, LexicalError, SyntacticError

class TestCompiler(unittest.TestCase):

    def test_lexer_valid(self):
        text = " 10  + 20 * 300 / ( 5 - 2 ) "
        lexer = Lexer(text)
        tokens = lexer.tokenize_all()
        
        # Eliminar el EOF de la lista para comparar con facilidad
        token_types = [t.type for t in tokens if t.type != TokenType.EOF]
        expected_types = [
            TokenType.INT, TokenType.PLUS, TokenType.INT, TokenType.MUL,
            TokenType.INT, TokenType.DIV, TokenType.LPAREN, TokenType.INT,
            TokenType.MINUS, TokenType.INT, TokenType.RPAREN
        ]
        self.assertEqual(token_types, expected_types)
        
        # Verificar valores de los tokens enteros
        ints = [t.value for t in tokens if t.type == TokenType.INT]
        self.assertEqual(ints, [10, 20, 300, 5, 2])

    def test_lexer_invalid_char(self):
        text = "10 + 20a * 3"
        lexer = Lexer(text)
        with self.assertRaises(LexicalError) as ctx:
            lexer.tokenize_all()
        
        self.assertEqual(ctx.exception.position, 7)
        self.assertEqual(ctx.exception.char, 'a')

    def test_parser_precedence(self):
        # 2 + 3 * 4 debe ser 2 + (3 * 4)
        lexer = Lexer("2 + 3 * 4")
        parser = Parser(lexer)
        ast = parser.parse()
        
        # El nodo raíz debe ser '+'
        self.assertEqual(ast.op, '+')
        self.assertEqual(ast.left.value, 2)
        # El hijo derecho debe ser '*'
        self.assertEqual(ast.right.op, '*')
        self.assertEqual(ast.right.left.value, 3)
        self.assertEqual(ast.right.right.value, 4)

    def test_parser_parentheses(self):
        # (2 + 3) * 4
        lexer = Lexer("(2 + 3) * 4")
        parser = Parser(lexer)
        ast = parser.parse()
        
        # El nodo raíz debe ser '*'
        self.assertEqual(ast.op, '*')
        # El hijo izquierdo debe ser '+'
        self.assertEqual(ast.left.op, '+')
        self.assertEqual(ast.left.left.value, 2)
        self.assertEqual(ast.left.right.value, 3)
        self.assertEqual(ast.right.value, 4)

    def test_parser_syntax_error(self):
        lexer = Lexer("2 + * 3")
        parser = Parser(lexer)
        with self.assertRaises(SyntacticError):
            parser.parse()

    def test_semantic_analyzer(self):
        lexer = Lexer("10 + 20 * 10 - 5")
        parser = Parser(lexer)
        ast = parser.parse()
        
        analyzer = SemanticAnalyzer(ast)
        sym_table, type_table = analyzer.analyze()
        
        # Los operandos únicos son 5, 10, 20
        self.assertEqual(set(sym_table.keys()), {5, 10, 20})
        self.assertEqual(sym_table[5], "dir_1")
        self.assertEqual(sym_table[10], "dir_2")
        self.assertEqual(sym_table[20], "dir_3")
        
        for k in type_table:
            self.assertEqual(type_table[k], "entero")

if __name__ == '__main__':
    unittest.main()
