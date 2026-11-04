# -*- coding: utf-8 -*-
"""
Módulo: test_semantico.py
Descripción: Pruebas automáticas de la fase de análisis semántico (Entrega 4).

Ejecutar:  python test_semantico.py

No depende de Streamlit ni de pandas: solo del lexer, el parser y el
analizador semántico.
"""

from pathlib import Path

from lexer import Lexer
from parser import Parser
from analizador_semantico import AnalizadorSemantico

RAIZ = Path(__file__).parent


def analizar(codigo):
    """Devuelve (errores_sintacticos, errores_semanticos, tabla)."""
    tokens = Lexer(codigo).tokenizar()
    cst, _, errores_sint = Parser(tokens).parse_con_pasos()
    analizador = AnalizadorSemantico(cst)
    errores_sem = analizador.analizar()
    return errores_sint, errores_sem, analizador.tabla


def _casos_de(errores):
    return [e.regla for e in errores]


def main():
    fallos = 0
    total = 0

    # ------------------------------------------------------------------
    # Caso 1: programa sin errores (léxico, sintáctico y semántico)
    # ------------------------------------------------------------------
    total += 1
    codigo = (RAIZ / "ejemplos_prueba" / "1_sin_errores.txt").read_text(encoding="utf-8")
    errs_sint, errs_sem, tabla = analizar(codigo)
    if errs_sint or errs_sem:
        fallos += 1
        print("FALLO caso 1 (1_sin_errores.txt)")
        print("  sintácticos:", errs_sint)
        print("  semánticos :", [str(e) for e in errs_sem])
    else:
        print("OK   caso 1  — 1_sin_errores.txt: ningún error (5 símbolos, "
              f"{len(tabla.filas())} entradas)")

    # ------------------------------------------------------------------
    # Caso 2: los cuatro errores semánticos esperados
    # ------------------------------------------------------------------
    total += 1
    codigo = (RAIZ / "ejemplos_prueba" / "3_error_semantico.txt").read_text(encoding="utf-8")
    errs_sint, errs_sem, _ = analizar(codigo)
    esperado = ["SEM-1", "SEM-3", "SEM-2", "SEM-5"]
    obtenido = _casos_de(errs_sem)
    if errs_sint or obtenido != esperado:
        fallos += 1
        print("FALLO caso 2 (3_error_semantico.txt)")
        print("  esperado:", esperado)
        print("  obtenido:", obtenido)
        for e in errs_sem:
            print("   ", e)
    else:
        print("OK   caso 2  — 3_error_semantico.txt: 4 errores "
              "[SEM-1, SEM-3, SEM-2, SEM-5] con fila/columna/lexema")

    # ------------------------------------------------------------------
    # Caso 3: recuperación — varios errores en el mismo programa
    # ------------------------------------------------------------------
    total += 1
    codigo = r'''
hagale_pues f(numerito a) pa_que_lleve siono dele_pues
    entregue_pues a
ya_quedo

pille_pues numerito x = 1
pille_pues cuento y = x
si_acaso x entonces_pues
    hable_pues("no")
asi_quedo

pa_cada i desde "a" hasta 10 dele_pues
    hable_pues(i)
listo_pues

pillemos x {
    1 pa_que_lleve hable_pues("uno")
    "dos" pa_que_lleve hable_pues("dos")
}

pille_pues numerito w = f("hola")
'''
    errs_sint, errs_sem, _ = analizar(codigo)
    reglas = set(_casos_de(errs_sem))
    if errs_sint or not {"SEM-1", "SEM-3", "SEM-4", "SEM-5"} <= reglas or len(errs_sem) < 6:
        fallos += 1
        print("FALLO caso 3 (recuperación)")
        print("  sintácticos:", errs_sint)
        print("  semánticos :", [str(e) for e in errs_sem])
    else:
        print(f"OK   caso 3  — recuperación: {len(errs_sem)} errores semánticos "
              f"reportados en una sola pasada ({sorted(reglas)})")

    # ------------------------------------------------------------------
    # Caso 4: shadowing y ámbitos anidados válidos
    # ------------------------------------------------------------------
    total += 1
    codigo = r'''
pille_pues numerito x = 1
si_acaso sizas entonces_pues
    pille_pues numerito x = 2
    hable_pues(x)
asi_quedo
hable_pues(x)

hagale_pues doble(numerito n) pa_que_lleve numerito dele_pues
    entregue_pues n * 2
ya_quedo
hable_pues(doble(x))
'''
    errs_sint, errs_sem, _ = analizar(codigo)
    if errs_sint or errs_sem:
        fallos += 1
        print("FALLO caso 4 (shadowing/ámbitos)")
        print("  sintácticos:", errs_sint)
        print("  semánticos :", [str(e) for e in errs_sem])
    else:
        print("OK   caso 4  — shadowing y ámbitos anidados sin errores")

    print()
    if fallos:
        print(f"RESULTADO: {fallos}/{total} prueba(s) fallaron.")
        raise SystemExit(1)
    print(f"RESULTADO: {total}/{total} pruebas superadas.")


if __name__ == "__main__":
    main()
