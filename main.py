# -*- coding: utf-8 -*-
"""
main.py — Interfaz de consola del analizador lexico de Paisascript.

Toda la logica de analisis vive en `lexer.py`; este archivo solo presenta.
Esa separacion es el requisito 15 del enunciado: el analizador sintactico
reutilizara `lexer.py` sin tocar una linea de esta interfaz.

Ejecutar:  python main.py
"""

from __future__ import annotations

import os
import sys
from collections import Counter

from ejemplos import EJEMPLOS
from lexer import Lexer, TipoToken


# =============================================================================
#  SOPORTE DE COLOR EN CONSOLA
# =============================================================================

def _preparar_consola() -> None:
    """Habilita secuencias ANSI en Windows y fuerza UTF-8 en la salida."""
    if os.name == "nt":
        try:
            import ctypes
            k = ctypes.windll.kernel32
            # 7 = STD_OUTPUT_HANDLE ; 0x0004 = ENABLE_VIRTUAL_TERMINAL_PROCESSING
            k.SetConsoleMode(k.GetStdHandle(-11), 7)
        except Exception:
            os.system("")  # respaldo: tambien activa el modo VT
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


R = "\033[0m"       # reset
NEGRITA = "\033[1m"
TENUE = "\033[2m"

# Un color por categoria lexica (requisito 12).
COLOR_CATEGORIA = {
    "RESERVADA":     "\033[1;95m",   # magenta brillante
    "TIPO":          "\033[1;96m",   # cian brillante
    "OPERADOR":      "\033[1;93m",   # amarillo brillante
    "LITERAL":       "\033[0;92m",   # verde
    "IDENTIFICADOR": "\033[0;97m",   # blanco
    "PUNTUACION":    "\033[0;90m",   # gris
    "FIN":           "\033[0;90m",
}
COLOR_ERROR = "\033[1;97;41m"        # blanco sobre rojo
COLOR_TITULO = "\033[1;96m"
COLOR_SUAVE = "\033[0;90m"

ANCHO = 78


def color_de(categoria: str) -> str:
    return COLOR_CATEGORIA.get(categoria, R)


# =============================================================================
#  UTILIDADES DE PRESENTACION
# =============================================================================

def titulo(texto: str) -> None:
    print()
    print(f"{COLOR_TITULO}{'=' * ANCHO}{R}")
    print(f"{COLOR_TITULO}  {texto}{R}")
    print(f"{COLOR_TITULO}{'=' * ANCHO}{R}")


def subtitulo(texto: str) -> None:
    print()
    print(f"{NEGRITA}{texto}{R}")
    print(f"{COLOR_SUAVE}{'-' * ANCHO}{R}")


# =============================================================================
#  1. VISUALIZACION GRAFICA — CODIGO FUENTE RESALTADO
# =============================================================================

def mostrar_codigo_resaltado(fuente: str, tokens, errores) -> None:
    """Reimprime el fuente pintando cada lexema con el color de su categoria.

    Las posiciones se reconstruyen a partir de (fila, columna) de cada token,
    que es justamente lo que se quiere demostrar: el lexer sabe exactamente
    donde empieza y termina cada pieza del texto.
    """
    subtitulo("1. CODIGO FUENTE SEGMENTADO EN TOKENS")

    lineas = fuente.split("\n")

    # Marcas por linea: (columna_inicio, lexema, color)
    marcas: dict[int, list] = {}
    for t in tokens:
        if t.tipo is TipoToken.FIN_ARCHIVO:
            continue
        marcas.setdefault(t.fila, []).append(
            (t.columna, t.lexema, color_de(t.categoria))
        )
    for e in errores:
        marcas.setdefault(e.fila, []).append(
            (e.columna, e.lexema, COLOR_ERROR)
        )

    for i, linea in enumerate(lineas, start=1):
        piezas = sorted(marcas.get(i, []))
        salida = []
        cursor = 0
        for columna, lexema, col in piezas:
            inicio = columna - 1
            if inicio < cursor:          # solapamiento defensivo
                continue
            salida.append(f"{COLOR_SUAVE}{linea[cursor:inicio]}{R}")
            salida.append(f"{col}{linea[inicio:inicio + len(lexema)]}{R}")
            cursor = inicio + len(lexema)
        salida.append(f"{COLOR_SUAVE}{linea[cursor:]}{R}")
        print(f"{COLOR_SUAVE}{i:>3} |{R} " + "".join(salida))


# =============================================================================
#  2. VISUALIZACION GRAFICA — FLUJO DE TOKENS
# =============================================================================

def mostrar_flujo_tokens(tokens) -> None:
    """Dibuja la secuencia de tokens como fichas etiquetadas."""
    subtitulo("2. FLUJO DE TOKENS  [ lexema | TIPO ]")

    utiles = [t for t in tokens if t.tipo is not TipoToken.FIN_ARCHIVO]
    linea_actual = ""
    largo = 0
    for t in utiles:
        ficha_txt = f"[ {t.lexema} | {t.tipo.name} ]"
        if largo + len(ficha_txt) + 1 > ANCHO and linea_actual:
            print(linea_actual)
            linea_actual, largo = "", 0
        col = color_de(t.categoria)
        linea_actual += f"{col}[ {t.lexema} {COLOR_SUAVE}|{R}{col} {t.tipo.name} ]{R} "
        largo += len(ficha_txt) + 1
    if linea_actual:
        print(linea_actual)


# =============================================================================
#  3. TABLA DE SIMBOLOS LEXICOS
# =============================================================================

def mostrar_tabla_simbolos(tokens) -> None:
    """Lexema, categoria (TipoToken), fila y columna de cada token."""
    subtitulo("3. TABLA DE SIMBOLOS LEXICOS")

    utiles = [t for t in tokens if t.tipo is not TipoToken.FIN_ARCHIVO]

    enc = f"{'#':>4}  {'LEXEMA':<24} {'TIPO DE TOKEN':<20} {'CATEGORIA':<14} {'FILA':>5} {'COL':>5}"
    print(f"{NEGRITA}{enc}{R}")
    print(f"{COLOR_SUAVE}{'-' * len(enc)}{R}")

    for n, t in enumerate(utiles, start=1):
        lexema = t.lexema if len(t.lexema) <= 24 else t.lexema[:21] + "..."
        col = color_de(t.categoria)
        print(f"{COLOR_SUAVE}{n:>4}{R}  {col}{lexema:<24}{R} "
              f"{t.tipo.name:<20} {COLOR_SUAVE}{t.categoria:<14}{R} "
              f"{t.fila:>5} {t.columna:>5}")

    print(f"{COLOR_SUAVE}{'-' * len(enc)}{R}")
    print(f"Total de tokens reconocidos: {NEGRITA}{len(utiles)}{R}")


# =============================================================================
#  4. IDENTIFICADORES DISTINTOS
# =============================================================================

def mostrar_identificadores(lexer: Lexer) -> None:
    resumen = lexer.resumen_identificadores()
    if not resumen:
        return
    subtitulo("4. IDENTIFICADORES DISTINTOS (germen de la tabla de simbolos)")
    enc = f"{'IDENTIFICADOR':<26} {'VECES':>6}  POSICIONES (fila:col)"
    print(f"{NEGRITA}{enc}{R}")
    print(f"{COLOR_SUAVE}{'-' * len(enc)}{R}")
    for nombre in sorted(resumen):
        pos = resumen[nombre]
        lista = ", ".join(f"{f}:{c}" for f, c in pos[:6])
        if len(pos) > 6:
            lista += ", ..."
        print(f"{color_de('IDENTIFICADOR')}{nombre:<26}{R} {len(pos):>6}  "
              f"{COLOR_SUAVE}{lista}{R}")


# =============================================================================
#  5. REPORTE DE ERRORES LEXICOS
# =============================================================================

def mostrar_errores(fuente: str, errores) -> None:
    subtitulo("5. REPORTE DE ERRORES LEXICOS")

    if not errores:
        print(f"\033[1;92mSin errores lexicos: toda la entrada se reconocio.{R}")
        return

    lineas = fuente.split("\n")
    print(f"{COLOR_ERROR} Se encontraron {len(errores)} error(es) "
          f"— el analisis NO se detuvo {R}")
    print()
    for n, e in enumerate(errores, start=1):
        print(f"{NEGRITA}Error {n}{R} — fila {NEGRITA}{e.fila}{R}, "
              f"columna {NEGRITA}{e.columna}{R}: {e.mensaje}")
        if 1 <= e.fila <= len(lineas):
            texto = lineas[e.fila - 1]
            print(f"   {COLOR_SUAVE}{e.fila:>3} |{R} {texto}")
            print(f"   {COLOR_SUAVE}    |{R} "
                  f"{' ' * (e.columna - 1)}\033[1;91m{'^' * max(1, len(e.lexema))}{R}")
        print()


# =============================================================================
#  6. RESUMEN POR CATEGORIA + LEYENDA
# =============================================================================

def mostrar_resumen(tokens, errores) -> None:
    subtitulo("6. RESUMEN POR CATEGORIA")

    utiles = [t for t in tokens if t.tipo is not TipoToken.FIN_ARCHIVO]
    cuenta = Counter(t.categoria for t in utiles)

    for categoria in ("RESERVADA", "TIPO", "OPERADOR", "LITERAL",
                      "IDENTIFICADOR", "PUNTUACION"):
        n = cuenta.get(categoria, 0)
        barra = "#" * min(n, 40)
        print(f"{color_de(categoria)}{categoria:<15}{R} {n:>4}  "
              f"{color_de(categoria)}{barra}{R}")

    print(f"{COLOR_ERROR}{'ERRORES':<15}{R} {len(errores):>4}  "
          f"\033[1;91m{'#' * min(len(errores), 40)}{R}")


def mostrar_leyenda() -> None:
    partes = [f"{color_de(c)}{c}{R}" for c in
              ("RESERVADA", "TIPO", "OPERADOR", "LITERAL",
               "IDENTIFICADOR", "PUNTUACION")]
    partes.append(f"{COLOR_ERROR}ERROR{R}")
    print(f"\n{COLOR_SUAVE}Leyenda de colores:{R} " + f"{COLOR_SUAVE} · {R}".join(partes))


# =============================================================================
#  ORQUESTACION
# =============================================================================

def analizar_y_reportar(fuente: str, encabezado: str = "") -> None:
    titulo(f"ANALISIS LEXICO — {encabezado}" if encabezado else "ANALISIS LEXICO")

    lexer = Lexer(fuente)
    tokens = lexer.tokenizar()
    errores = lexer.errores

    mostrar_leyenda()
    mostrar_codigo_resaltado(fuente, tokens, errores)
    mostrar_flujo_tokens(tokens)
    mostrar_tabla_simbolos(tokens)
    mostrar_identificadores(lexer)
    mostrar_errores(fuente, errores)
    mostrar_resumen(tokens, errores)


# =============================================================================
#  MENU
# =============================================================================

BANNER = r"""
  ____       _                     _       _
 |  _ \ __ _(_)___  __ _ ___  ___ | |_ ___(_)_ __  ___
 | |_) / _` | / __|/ _` / __|/ __|| __/ __| | '_ \/ __|
 |  __/ (_| | \__ \ (_| \__ \ (__ | || (__| | |_) \__ \
 |_|   \__,_|_|___/\__,_|___/\___| \__\___|_| .__/|___/
                                            |_|
        Analizador lexico  ·  destino: Gleam
"""


def leer_cadena_libre() -> str:
    print(f"\n{NEGRITA}Digite su codigo Paisascript.{R}")
    print(f"{COLOR_SUAVE}Termine escribiendo una linea con la palabra  fin  "
          f"(o Ctrl+Z / Ctrl+D){R}\n")
    lineas = []
    while True:
        try:
            linea = input()
        except EOFError:
            break
        if linea.strip().lower() == "fin":
            break
        lineas.append(linea)
    return "\n".join(lineas)


def menu_ejemplos() -> str | None:
    subtitulo("CADENAS PREDEFINIDAS")
    for i, (nombre, desc, _) in enumerate(EJEMPLOS, start=1):
        print(f"  {NEGRITA}{i}{R}. {nombre}")
        print(f"     {COLOR_SUAVE}{desc}{R}")
    print(f"  {NEGRITA}0{R}. Volver")

    op = input(f"\n{NEGRITA}Opcion: {R}").strip()
    if not op.isdigit() or not (1 <= int(op) <= len(EJEMPLOS)):
        return None
    nombre, _, codigo = EJEMPLOS[int(op) - 1]
    analizar_y_reportar(codigo, nombre)
    return nombre


def main() -> None:
    _preparar_consola()
    print(f"{COLOR_TITULO}{BANNER}{R}")

    while True:
        subtitulo("MENU PRINCIPAL")
        print(f"  {NEGRITA}1{R}. Analizar una cadena predefinida")
        print(f"  {NEGRITA}2{R}. Digitar una cadena libre")
        print(f"  {NEGRITA}3{R}. Analizar un archivo .paisa")
        print(f"  {NEGRITA}0{R}. Salir")

        try:
            op = input(f"\n{NEGRITA}Opcion: {R}").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if op == "1":
            menu_ejemplos()
        elif op == "2":
            fuente = leer_cadena_libre()
            if fuente.strip():
                analizar_y_reportar(fuente, "cadena digitada")
            else:
                print(f"{COLOR_SUAVE}No se digito nada.{R}")
        elif op == "3":
            ruta = input(f"{NEGRITA}Ruta del archivo: {R}").strip().strip('"')
            try:
                with open(ruta, "r", encoding="utf-8") as f:
                    analizar_y_reportar(f.read(), os.path.basename(ruta))
            except OSError as err:
                print(f"{COLOR_ERROR} No se pudo abrir el archivo: {err} {R}")
        elif op == "0":
            break
        else:
            print(f"{COLOR_SUAVE}Opcion no valida.{R}")

    print(f"\n{COLOR_TITULO}Listo pues. Hasta la proxima.{R}\n")


if __name__ == "__main__":
    main()
