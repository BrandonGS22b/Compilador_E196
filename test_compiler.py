import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import unittest
from compiler import compilar


def una(texto):
    return compilar(texto)['lines'][0]


class TestCompilador(unittest.TestCase):
    def test_tokens_pdf3(self):
        l = una("x = (1 + 5) * 20 / 5")
        self.assertEqual([t['type'] for t in l['tokens']],
                         ['ID', 'EQUAL', 'LPAREN', 'NUMBER', 'PLUS', 'NUMBER', 'RPAREN',
                          'TIMES', 'NUMBER', 'DIVIDE', 'NUMBER'])
        self.assertEqual([t['position'] for t in l['tokens']][:3], [0, 2, 4])

    def test_variable_no_declarada_es_valida_lexicamente(self):
        l = una("y = 25 + (5 / 6) - 100 + w")
        self.assertEqual(len(l['tokens']), 13)
        self.assertEqual(l['status'], 'semantic_error')

    def test_todos_los_caracteres_ilegales(self):
        l = una("z = {23}{23}")
        self.assertEqual([e['char'] for e in l['errors']], ['{', '}', '{', '}'])
        self.assertEqual([e['char'] for e in una("w= 32 # 5")['errors']], ['#'])

    def test_evaluar_pdf2(self):
        r = compilar("Evaluar[1+1];\nEvaluar[1+1*2];\nEvaluar[-(1+1*6/3-5+7)];\n"
                     "Evaluar[-(1+1*6/3-5+1*-2)];\nEvaluar[-(1.6+1.45)];")
        self.assertEqual([l['valor'] for l in r['lines']], [2, 3, -5.0, 4.0, -3.05])
        self.assertEqual(r['status'], 'success')

    def test_precedencia_y_parentesis(self):
        self.assertEqual(una("2 + 3 * 4")['valor'], 14)
        self.assertEqual(una("(2 + 3) * 4")['valor'], 20)
        self.assertEqual(una("2 + 3 * 4")['ast']['short'], '+')

    def test_menos_unario(self):
        self.assertEqual(una("-5 + 3")['valor'], -2)
        self.assertEqual(una("2 * -3")['valor'], -6)

    def test_errores_sintacticos(self):
        for src in ["2 + * 3", "(2 + 3", "2 + 3)", "3 3", "10 +", "Evaluar 5", "= 4"]:
            self.assertEqual(una(src)['status'], 'syntax_error', src)

    def test_semantico_tipos_y_tabla(self):
        r = compilar("a = 4\nb = a * 2.5\nc = a / 2\nEvaluar[b + c]")
        t = {f['lexema']: f for f in r['symbol_table']}
        self.assertEqual((t['a']['tipo'], t['b']['tipo'], t['c']['tipo']), ('entero', 'real', 'real'))
        self.assertEqual([t['a']['direccion'], t['b']['direccion'], t['c']['direccion']], [0, 4, 12])
        self.assertEqual(t['a']['lineas_ref'], [2, 3])
        self.assertEqual(r['lines'][3]['valor'], 12.0)

    def test_errores_semanticos(self):
        self.assertIn('no declarado', una("Evaluar[j + 1]")['errors'][0]['message'])
        self.assertIn('cero', una("10 / 0")['errors'][0]['message'])

    def test_una_linea_con_error_no_detiene_las_demas(self):
        r = compilar("1 +\n2 + 2")
        self.assertEqual([l['status'] for l in r['lines']], ['syntax_error', 'ok'])

    def test_vacio(self):
        self.assertEqual(compilar("  \n")['status'], 'empty')


if __name__ == '__main__':
    unittest.main()
