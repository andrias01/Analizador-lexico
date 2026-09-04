# -*- coding: utf-8 -*-
"""
lexer.py — Analizador lexico de Paisascript.

Modulo INDEPENDIENTE de la interfaz: no imprime nada ni lee de consola.
Expone tres cosas y nada mas:

    TipoToken   enumeracion de las categorias lexicas del lenguaje
    Token       lexema + tipo + fila + columna (+ valor semantico)
    Lexer       la clase que convierte texto en una lista de Token

El analizador sintactico descendente recursivo del proyecto podra
consumir `Lexer(fuente).tokenizar()` sin modificar una sola linea de este
archivo. Por eso el manejo de errores no aborta: los errores se acumulan
en `Lexer.errores` y el recorrido continua con el siguiente caracter.

Lenguaje destino del compilador: Gleam.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List


# =============================================================================
#  CATEGORIAS LEXICAS
# =============================================================================

class TipoToken(Enum):
    """Categorias de token de Paisascript.

    El prefijo del nombre determina la categoria general (ver `categoria`),
    que es lo que la capa de presentacion usa para elegir el color.
    """

    # --- Palabras reservadas: declaraciones y E/S ---------------------------
    KW_DECLARACION = auto()      # pille_pues      -> let
    KW_LECTURA = auto()          # escuche_pues    -> erlang.get_line
    KW_IMPRESION = auto()        # hable_pues      -> io.println
    KW_FUNCION = auto()          # hagale_pues     -> pub fn
    KW_FIN_FUNCION = auto()      # ya_quedo        -> }
    KW_RETORNAR = auto()         # entregue_pues   -> expresion final

    # --- Palabras reservadas: estructuras de control ------------------------
    KW_SI = auto()               # si_acaso        -> case
    KW_ENTONCES = auto()         # entonces_pues   -> True  ->
    KW_SINO = auto()             # sino_pues       -> False ->
    KW_FIN_SI = auto()           # asi_quedo       -> }
    KW_MIENTRAS = auto()         # mientras_que    -> recursion de cola
    KW_HACER = auto()            # dele_pues       -> {
    KW_FIN_MIENTRAS = auto()     # hasta_ahi       -> }
    KW_PARA = auto()             # pa_cada         -> list.range
    KW_DESDE = auto()            # desde
    KW_HASTA = auto()            # hasta
    KW_PASO = auto()             # de_a
    KW_FIN_PARA = auto()         # listo_pues      -> }
    KW_PILLEMOS = auto()         # pillemos        -> case
    KW_FLECHA = auto()           # pa_que_lleve    -> ->

    # --- Palabras reservadas: tipos -----------------------------------------
    KW_TIPO_ENTERO = auto()      # numerito        -> Int
    KW_TIPO_REAL = auto()        # quebradito      -> Float
    KW_TIPO_CADENA = auto()      # cuento          -> String
    KW_TIPO_BOOLEANO = auto()    # siono           -> Bool

    # --- Operadores logicos y de comparacion con nombre ---------------------
    OP_Y = auto()                # y_tambien       -> &&
    OP_O = auto()                # o_que           -> ||
    OP_NO = auto()               # nanai           -> !
    OP_IGUAL = auto()            # igualito        -> ==
    OP_DISTINTO = auto()         # distinto        -> !=

    # --- Literales ----------------------------------------------------------
    LIT_VERDADERO = auto()       # sizas           -> True
    LIT_FALSO = auto()           # naranjas        -> False
    NUM_ENTERO = auto()          # 42              -> Int
    NUM_REAL = auto()            # 3.1416          -> Float
    CADENA_LITERAL = auto()      # "hola"          -> String

    # --- Identificadores ----------------------------------------------------
    IDENTIFICADOR = auto()

    # --- Operadores simbolicos ----------------------------------------------
    OP_POTENCIA = auto()         # **              -> int.power / float.power
    OP_MULT = auto()             # *               -> *  |  *.
    OP_DIV = auto()              # /               -> /  |  /.
    OP_MODULO = auto()           # %               -> %
    OP_SUMA = auto()             # +               -> +  |  +.
    OP_RESTA = auto()            # -               -> -  |  -.
    OP_CONCAT = auto()           # <>              -> <>
    OP_MAYOR_IGUAL = auto()      # >=
    OP_MENOR_IGUAL = auto()      # <=
    OP_MAYOR = auto()            # >
    OP_MENOR = auto()            # <
    OP_ASIGNACION = auto()       # =

    # --- Puntuacion ---------------------------------------------------------
    PAR_ABRE = auto()            # (
    PAR_CIERRA = auto()          # )
    LLAVE_ABRE = auto()          # {
    LLAVE_CIERRA = auto()        # }
    COMA = auto()                # ,
    COMODIN = auto()             # _               -> _

    # --- Centinela para el analizador sintactico ----------------------------
    FIN_ARCHIVO = auto()

    @property
    def categoria(self) -> str:
        """Categoria general del token, derivada del prefijo del nombre.

        La usa la capa de presentacion para asignar colores. Se calcula del
        nombre para que agregar un token nuevo no obligue a tocar ninguna
        tabla aparte.
        """
        n = self.name
        if n.startswith("KW_TIPO_"):
            return "TIPO"
        if n.startswith("KW_"):
            return "RESERVADA"
        if n.startswith("OP_"):
            return "OPERADOR"
        if n.startswith(("LIT_", "NUM_", "CADENA_")):
            return "LITERAL"
        if n == "IDENTIFICADOR":
            return "IDENTIFICADOR"
        if n == "FIN_ARCHIVO":
            return "FIN"
        return "PUNTUACION"


# =============================================================================
#  TABLA DE PALABRAS RESERVADAS
# =============================================================================
# Se resuelven por diccionario y no por orden en la expresion regular: el
# lexer reconoce primero un identificador completo (maximal munch) y luego
# consulta esta tabla. Asi `pille_puesX` es un identificador y no la palabra
# reservada `pille_pues` seguida de `X`, sin depender de trucos con \b.

PALABRAS_RESERVADAS = {
    # Declaraciones y E/S
    "pille_pues":    TipoToken.KW_DECLARACION,
    "escuche_pues":  TipoToken.KW_LECTURA,
    "hable_pues":    TipoToken.KW_IMPRESION,
    "hagale_pues":   TipoToken.KW_FUNCION,
    "ya_quedo":      TipoToken.KW_FIN_FUNCION,
    "entregue_pues": TipoToken.KW_RETORNAR,
    # Control
    "si_acaso":      TipoToken.KW_SI,
    "entonces_pues": TipoToken.KW_ENTONCES,
    "sino_pues":     TipoToken.KW_SINO,
    "asi_quedo":     TipoToken.KW_FIN_SI,
    "mientras_que":  TipoToken.KW_MIENTRAS,
    "dele_pues":     TipoToken.KW_HACER,
    "hasta_ahi":     TipoToken.KW_FIN_MIENTRAS,
    "pa_cada":       TipoToken.KW_PARA,
    "desde":         TipoToken.KW_DESDE,
    "hasta":         TipoToken.KW_HASTA,
    "de_a":          TipoToken.KW_PASO,
    "listo_pues":    TipoToken.KW_FIN_PARA,
    "pillemos":      TipoToken.KW_PILLEMOS,
    "pa_que_lleve":  TipoToken.KW_FLECHA,
    # Tipos
    "numerito":      TipoToken.KW_TIPO_ENTERO,
    "quebradito":    TipoToken.KW_TIPO_REAL,
    "cuento":        TipoToken.KW_TIPO_CADENA,
    "siono":         TipoToken.KW_TIPO_BOOLEANO,
    # Operadores con nombre
    "y_tambien":     TipoToken.OP_Y,
    "o_que":         TipoToken.OP_O,
    "nanai":         TipoToken.OP_NO,
    "igualito":      TipoToken.OP_IGUAL,
    "distinto":      TipoToken.OP_DISTINTO,
    # Literales booleanos
    "sizas":         TipoToken.LIT_VERDADERO,
    "naranjas":      TipoToken.LIT_FALSO,
}


# =============================================================================
#  ESTRUCTURAS DE SALIDA
# =============================================================================

@dataclass(frozen=True)
class Token:
    """Un token reconocido, con su posicion exacta en el texto fuente."""

    tipo: TipoToken
    lexema: str
    fila: int          # 1-based
    columna: int       # 1-based
    valor: object = None   # int / float / str ya convertido; None si no aplica

    @property
    def categoria(self) -> str:
        return self.tipo.categoria

    def __str__(self) -> str:
        return f"{self.tipo.name}('{self.lexema}') @ {self.fila}:{self.columna}"


@dataclass(frozen=True)
class ErrorLexico:
    """Un error lexico localizado. Nunca detiene el analisis."""

    lexema: str
    fila: int
    columna: int
    mensaje: str

    def __str__(self) -> str:
        return (f"Error lexico en fila {self.fila}, columna {self.columna}: "
                f"{self.mensaje} -> '{self.lexema}'")


# =============================================================================
#  EL ANALIZADOR
# =============================================================================

# Clases de caracteres para identificadores. El enunciado (2.1) exige admitir
# tildes y la letra n con virgulilla. Gleam solo acepta ASCII, asi que el
# generador de codigo de la entrega final los transliterara.
_MINUSCULAS = "a-záéíóúüñ"
_MAYUSCULAS = "A-ZÁÉÍÓÚÜÑ"
_ID_INICIO = f"[{_MINUSCULAS}_]"
_ID_RESTO = f"[{_MINUSCULAS}{_MAYUSCULAS}0-9_]"


class Lexer:
    """Convierte codigo fuente Paisascript en una lista de Token.

    Uso tipico:

        lexer = Lexer(codigo)
        tokens = lexer.tokenizar()
        for e in lexer.errores:
            print(e)

    Estrategia: una sola expresion regular alternada con grupos nombrados,
    recorrida con `re.finditer`. Como Python devuelve la PRIMERA alternativa
    que casa (no la mas larga), el orden de `_ESPECIFICACION` es significativo:
    los operadores de dos caracteres van antes que los de uno (** antes que *,
    <> y <= antes que <), y NUM_REAL antes que NUM_ENTERO.
    """

    # El orden de esta lista ES la tabla de prioridades del analizador.
    _ESPECIFICACION = [
        # Se descartan, pero deben casar antes que los operadores: // seria
        # dos divisiones si no estuviera aqui arriba.
        ("COMENTARIO",       r"//[^\n]*"),
        ("ESPACIOS",         r"[ \t\r\n]+"),

        # Literales numericos. El real primero: si no, 3.14 seria 3 . 14.
        ("NUM_REAL",         r"\d+\.\d+"),
        ("NUM_ENTERO",       r"\d+"),

        # Cadena bien formada; despues, la cadena sin cerrar como error.
        ("CADENA_LITERAL",   r'"(?:[^"\\\n]|\\.)*"'),
        ("CADENA_ABIERTA",   r'"(?:[^"\\\n]|\\.)*'),

        # Identificadores y palabras reservadas (se separan por diccionario).
        ("IDENTIFICADOR",    _ID_INICIO + _ID_RESTO + r"*"),
        # Empieza en mayuscula: no es un identificador valido de Paisascript
        # (Gleam reserva la mayuscula inicial para los constructores de tipo).
        ("ID_MAYUSCULA",     f"[{_MAYUSCULAS}]" + _ID_RESTO + r"*"),

        # Tres o mas asteriscos seguidos no son un operador de Paisascript.
        # Va ANTES que OP_POTENCIA: si no, *** se partiria en ** y * y pasaria
        # inadvertido por el lexer (maximal munch sobre el asterisco).
        ("ASTERISCOS_INVALIDOS", r"\*{3,}"),

        # Lo mismo con los angulos: el unico par valido es <> (concatenacion).
        # Cualquier racha de tres o mas (>>>, <<<, <>>, <<>) y los pares >> y
        # << no son operadores del lenguaje. Va ANTES que OP_CONCAT, OP_MENOR
        # y OP_MAYOR para que la racha se lea completa y no en pedazos.
        # <> solo (dos caracteres) NO casa aqui y sigue siendo OP_CONCAT.
        ("ANGULOS_INVALIDOS", r"[<>]{3,}|>>|<<"),

        # Operadores de dos caracteres, antes que los de uno.
        ("OP_POTENCIA",      r"\*\*"),
        ("OP_CONCAT",        r"<>"),
        ("OP_MAYOR_IGUAL",   r">="),
        ("OP_MENOR_IGUAL",   r"<="),

        # Operadores de un caracter.
        ("OP_MULT",          r"\*"),
        ("OP_DIV",           r"/"),
        ("OP_MODULO",        r"%"),
        ("OP_SUMA",          r"\+"),
        ("OP_RESTA",         r"-"),
        ("OP_MAYOR",         r">"),
        ("OP_MENOR",         r"<"),
        ("OP_ASIGNACION",    r"="),

        # Puntuacion.
        ("PAR_ABRE",         r"\("),
        ("PAR_CIERRA",       r"\)"),
        ("LLAVE_ABRE",       r"\{"),
        ("LLAVE_CIERRA",     r"\}"),
        ("COMA",             r","),

        # Cualquier otra cosa: error lexico de un caracter.
        ("CARACTER_INVALIDO", r"."),
    ]

    _REGEX = re.compile(
        "|".join(f"(?P<{nombre}>{patron})" for nombre, patron in _ESPECIFICACION),
        re.DOTALL,
    )

    def __init__(self, fuente: str) -> None:
        self.fuente: str = fuente
        self.tokens: List[Token] = []
        self.errores: List[ErrorLexico] = []
        self._fila: int = 1
        self._columna: int = 1

    # -- API publica --------------------------------------------------------

    def tokenizar(self) -> List[Token]:
        """Analiza todo el fuente y devuelve la lista de tokens.

        Los errores NO interrumpen el recorrido: se registran en
        `self.errores` y el analisis sigue con el caracter siguiente
        (requisito 14 del enunciado).
        """
        self.tokens = []
        self.errores = []
        self._fila = 1
        self._columna = 1

        for m in self._REGEX.finditer(self.fuente):
            nombre = m.lastgroup
            lexema = m.group()
            fila, columna = self._fila, self._columna
            self._avanzar(lexema)

            if nombre in ("ESPACIOS", "COMENTARIO"):
                continue

            manejador = getattr(self, f"_t_{nombre}", None)
            if manejador is not None:
                manejador(lexema, fila, columna)
            else:
                # Operadores y puntuacion: el nombre del grupo coincide con
                # el del TipoToken, asi que no hace falta un caso por cada uno.
                self._emitir(TipoToken[nombre], lexema, fila, columna)

        self.tokens.append(
            Token(TipoToken.FIN_ARCHIVO, "", self._fila, self._columna)
        )
        return self.tokens

    @property
    def hubo_errores(self) -> bool:
        return bool(self.errores)

    def tokens_utiles(self) -> List[Token]:
        """Los tokens sin el centinela FIN_ARCHIVO (comodo para reportes)."""
        return [t for t in self.tokens if t.tipo is not TipoToken.FIN_ARCHIVO]

    def resumen_identificadores(self) -> dict:
        """Identificadores distintos y las posiciones donde aparecen.

        Es el germen de la tabla de simbolos que el analizador semantico de
        la entrega 3 llenara con tipo y alcance.
        """
        resumen: dict = {}
        for t in self.tokens:
            if t.tipo is TipoToken.IDENTIFICADOR:
                resumen.setdefault(t.lexema, []).append((t.fila, t.columna))
        return resumen

    # -- Manejadores de los grupos que necesitan logica extra ---------------

    def _t_IDENTIFICADOR(self, lexema: str, fila: int, columna: int) -> None:
        if lexema == "_":
            # El guion bajo suelto es el comodin del calce de patrones;
            # `_algo` en cambio si es un identificador corriente.
            self._emitir(TipoToken.COMODIN, lexema, fila, columna)
            return
        tipo = PALABRAS_RESERVADAS.get(lexema, TipoToken.IDENTIFICADOR)
        valor = None
        if tipo is TipoToken.LIT_VERDADERO:
            valor = True
        elif tipo is TipoToken.LIT_FALSO:
            valor = False
        self._emitir(tipo, lexema, fila, columna, valor)

    def _t_NUM_ENTERO(self, lexema: str, fila: int, columna: int) -> None:
        self._emitir(TipoToken.NUM_ENTERO, lexema, fila, columna, int(lexema))

    def _t_NUM_REAL(self, lexema: str, fila: int, columna: int) -> None:
        self._emitir(TipoToken.NUM_REAL, lexema, fila, columna, float(lexema))

    def _t_CADENA_LITERAL(self, lexema: str, fila: int, columna: int) -> None:
        # Se guarda el contenido sin comillas y con los escapes resueltos.
        crudo = lexema[1:-1]
        valor = re.sub(r"\\(.)", lambda m: {
            "n": "\n", "t": "\t", "r": "\r",
            "\\": "\\", '"': '"',
        }.get(m.group(1), m.group(1)), crudo)
        self._emitir(TipoToken.CADENA_LITERAL, lexema, fila, columna, valor)

    # -- Manejadores de error (registran y siguen) --------------------------

    def _t_CADENA_ABIERTA(self, lexema: str, fila: int, columna: int) -> None:
        self._error(lexema, fila, columna,
                    "literal de cadena sin comilla de cierre")

    def _t_ID_MAYUSCULA(self, lexema: str, fila: int, columna: int) -> None:
        self._error(lexema, fila, columna,
                    "un identificador debe empezar en minuscula o guion bajo")

    def _t_ASTERISCOS_INVALIDOS(self, lexema: str, fila: int, columna: int) -> None:
        self._error(lexema, fila, columna,
                    f"'{lexema}' no es un operador valido; use '*' para "
                    f"multiplicar o '**' para potencia")

    def _t_ANGULOS_INVALIDOS(self, lexema: str, fila: int, columna: int) -> None:
        self._error(lexema, fila, columna,
                    f"'{lexema}' no es un operador valido; use '<>' para "
                    f"concatenar y '<', '>', '<=', '>=' para comparar")

    def _t_CARACTER_INVALIDO(self, lexema: str, fila: int, columna: int) -> None:
        self._error(lexema, fila, columna,
                    f"caracter {lexema!r} no pertenece al alfabeto de Paisascript")

    # -- Internos -----------------------------------------------------------

    def _emitir(self, tipo: TipoToken, lexema: str, fila: int, columna: int,
                valor: object = None) -> None:
        self.tokens.append(Token(tipo, lexema, fila, columna, valor))

    def _error(self, lexema: str, fila: int, columna: int, mensaje: str) -> None:
        self.errores.append(ErrorLexico(lexema, fila, columna, mensaje))

    def _avanzar(self, lexema: str) -> None:
        """Actualiza fila y columna despues de consumir `lexema`."""
        saltos = lexema.count("\n")
        if saltos:
            self._fila += saltos
            self._columna = len(lexema) - lexema.rfind("\n")
        else:
            self._columna += len(lexema)


# =============================================================================
#  ATAJO DE CONVENIENCIA
# =============================================================================

def analizar(fuente: str):
    """Devuelve (tokens, errores) en una sola llamada."""
    lexer = Lexer(fuente)
    tokens = lexer.tokenizar()
    return tokens, lexer.errores


if __name__ == "__main__":
    # Auto-prueba minima. La interfaz de usuario esta en main.py.
    _tokens, _errores = analizar(
        'pille_pues numerito x = 10 % 3 ** 2\nhable_pues("ok" <> x) @'
    )
    for _t in _tokens:
        print(_t)
    for _e in _errores:
        print(_e)
