# -*- coding: utf-8 -*-
"""
chequeo_estructural.py — Verificacion RAPIDA de balanceo de bloques.

Esto NO es el analizador sintactico de la entrega 2. El parser real sera un
descendente recursivo completo, guiado por cada produccion de la gramatica
BNF (gramatica_BNF_Paisascript.txt), y detectara cualquier violacion de esa
gramatica. Esto es apenas una pasada extra sobre los tokens, tan simple como
emparejar parentesis, pensada para atrapar el error mas comun al escribir
Paisascript a mano: olvidar la palabra que cierra un bloque (asi_quedo,
hasta_ahi, listo_pues, ya_quedo) o dejar un parentesis o una llave sin cerrar.

Por diseno NO detecta:
  - errores de gramatica mas finos, como un "sino_pues" repetido o un
    "pa_cada" sin "desde"  (eso lo hara el parser de la entrega 2)
  - errores semanticos: tipos incompatibles, variables no declaradas,
    aridad incorrecta en una llamada  (eso lo hara el analizador semantico
    de la entrega 3)

El algoritmo es una pila: cada apertura se apila; cada cierre busca su
apertura correspondiente empezando por el tope. Es O(n) y sin retroceso,
exactamente como el emparejador de parentesis que se ensena en el curso.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from lexer import Token, TipoToken

# Cada apertura sabe cual es su cierre y como se llaman ambos lexemas.
_PARES = {
    TipoToken.KW_FUNCION:  (TipoToken.KW_FIN_FUNCION,  "ya_quedo"),
    TipoToken.KW_SI:       (TipoToken.KW_FIN_SI,       "asi_quedo"),
    TipoToken.KW_MIENTRAS: (TipoToken.KW_FIN_MIENTRAS, "hasta_ahi"),
    TipoToken.KW_PARA:     (TipoToken.KW_FIN_PARA,     "listo_pues"),
    TipoToken.PAR_ABRE:    (TipoToken.PAR_CIERRA,      ")"),
    TipoToken.LLAVE_ABRE:  (TipoToken.LLAVE_CIERRA,    "}"),
}
# Tabla inversa: dado un tipo de cierre, cual es su apertura esperada.
_ABRE_ESPERADO = {cierre: abre for abre, (cierre, _) in _PARES.items()}


@dataclass(frozen=True)
class ErrorEstructural:
    """Un desbalance detectado: bloque sin cerrar o cierre sin apertura."""

    fila: int
    columna: int
    mensaje: str

    def __str__(self) -> str:
        return f"fila {self.fila}, columna {self.columna}: {self.mensaje}"


def verificar_balance(tokens: List[Token]) -> List[ErrorEstructural]:
    """Empareja aperturas y cierres con una pila; devuelve los desbalances.

    Cuando un cierre no coincide con el tope, se busca su apertura mas abajo
    en la pila: todo lo que quedo por encima de ese punto se reporta como
    "nunca se cerro", y se descarta junto con el emparejado. Asi un solo
    "asi_quedo" olvidado produce UN mensaje que senala exactamente el bloque
    abierto que quedo colgando, en vez de una cascada de errores derivados.
    """
    pila: List[Token] = []
    errores: List[ErrorEstructural] = []

    for t in tokens:
        if t.tipo in _PARES:
            pila.append(t)
            continue

        if t.tipo not in _ABRE_ESPERADO:
            continue  # token que no participa en el balanceo

        abre_esperado = _ABRE_ESPERADO[t.tipo]
        indice = None
        for i in range(len(pila) - 1, -1, -1):
            if pila[i].tipo is abre_esperado:
                indice = i
                break

        if indice is None:
            errores.append(ErrorEstructural(
                t.fila, t.columna,
                f"'{t.lexema}' aparece sin ningun bloque abierto que cerrar"))
            continue

        for huerfano in pila[indice + 1:]:
            _, cierre_esperado = _PARES[huerfano.tipo]
            errores.append(ErrorEstructural(
                huerfano.fila, huerfano.columna,
                f"'{huerfano.lexema}' nunca se cerro con '{cierre_esperado}' "
                f"(se encontro '{t.lexema}' en fila {t.fila}, columna "
                f"{t.columna} en su lugar)"))
        del pila[indice:]

    for abierto in pila:
        _, cierre_esperado = _PARES[abierto.tipo]
        errores.append(ErrorEstructural(
            abierto.fila, abierto.columna,
            f"'{abierto.lexema}' nunca se cerro con '{cierre_esperado}'"))

    return errores


if __name__ == "__main__":
    from lexer import Lexer

    _prueba = """
    hagale_pues f(numerito x) dele_pues
        si_acaso x > 0 entonces_pues
            hable_pues(x)
        // falta asi_quedo
    ya_quedo
    """
    _toks = Lexer(_prueba).tokenizar()
    for _e in verificar_balance(_toks):
        print(_e)
