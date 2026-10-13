import sys
sys.path.insert(0, '.')
from lexer import Lexer
from generador_lalr1_completa import generar_tabla_lalr1_completa
from parser_lalr import generar_parser_lalr1

# Test specific cases
tests = [
    'pille_pues numerito x = 5 * 2',  # OP_MULT
    'pille_pues numerito x = 10 % 3',  # OP_MODULO
    'si_acaso x >= 5 entonces_pues hable_pues(1) asi_quedo',  # OP_MAYOR_IGUAL
    'pille_pues numerito x = 5 < 3',  # OP_MENOR
    'hable_pues(1)',  # PAR_CIERRA
]

resultado = generar_tabla_lalr1_completa()
parser = generar_parser_lalr1(resultado)

for code in tests:
    lexer = Lexer(code)
    tokens = lexer.tokenizar()
    print(f'Code: {code}')
    print(f'Tokens: {[(t.tipo.name, t.lexema) for t in tokens]}')
    ast, traza, es_valido, errores = parser.parse_con_pasos(tokens)
    status = '✅ OK' if es_valido else '❌ FAIL'
    print(f'{status}')
    if not es_valido:
        for e in errores:
            print(f'  Error: {e}')
    print()