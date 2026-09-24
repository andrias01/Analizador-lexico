"""
Módulo: parser_ll1.py
Descripción: Motor de Análisis Predictivo Descendente LL(1) mediante Pila.
Genera la traza paso a paso y construye el árbol de derivación sintáctica.

Recuperación de errores:
    El análisis NO se detiene en el primer error. Al detectar uno lo registra y
    se recupera para seguir analizando:
      - Terminal esperado que no coincide:
            * si el SIGUIENTE token sí coincide, el actual sobra y se descarta;
            * si no, se asume que el terminal faltó (se saca de la pila).
      - No terminal sin regla en la tabla M[X, a]:
            * si 'a' está en SIGUIENTE(X) o es un cierre que la pila aún espera,
              se omite X (se saca de la pila);
            * si no, se descarta 'a' y se reintenta (modo pánico).
    Para no llenar la salida de errores en cascada, por defecto se reporta a lo
    sumo un error por token de entrada (ver `un_error_por_token`).

Construcción paso a paso:
    Cada paso de la traza incluye además una clave "Arbol": una foto (dict)
    del árbol completo tal como va quedando justo después de esa acción. Con
    eso se puede mostrar, con botones de Siguiente/Anterior, cómo se va
    construyendo el árbol. Para no gastar tiempo/memoria de más en árboles
    grandes, esta foto se deja de grabar pasado LIMITE_PASOS_ARBOL (el
    análisis sigue normalmente; solo esa clave queda en None).
"""
from tabla_ll1 import generar_datos_completos_ll1, es_terminal

EPS = "ε"
LIMITE_PASOS_ARBOL = 4000  # tope de seguridad para no grabar árboles gigantes


def _nodo_a_dict(nodo):
    """Convierte un NodoArbol (y sus hijos) a un dict {'tipo','es_terminal','hijos'}."""
    if nodo is None:
        return None
    return {
        "tipo": nodo.valor,
        "es_terminal": nodo.tipo != "no_terminal",
        "hijos": [_nodo_a_dict(h) for h in nodo.hijos],
    }


class NodoArbol:
    """Estructura para los nodos del Árbol de Sintaxis Concreta (CST)."""
    def __init__(self, valor, tipo="no_terminal"):
        self.valor = valor
        self.tipo = tipo  # 'no_terminal', 'terminal', 'epsilon'
        self.hijos = []

    def agregar_hijo(self, nodo):
        self.hijos.append(nodo)


class ErrorSintacticoLL1(Exception):
    def __init__(self, mensaje, paso):
        super().__init__(f"Error en paso {paso}: {mensaje}")
        self.paso = paso


def obtener_simbolo_token(token):
    """Mapea el objeto token del lexer al símbolo terminal de la gramática."""

    # 1. Manejo del token EOF simulado interno de parser_ll1
    if getattr(token, "tipo", None) == "EOF":
        return "$"

    # 2. Manejo de los tokens reales del lexer (Enums)
    if hasattr(token.tipo, "name"):
        nombre_token = token.tipo.name

        # Traducir el fin de archivo nativo del lexer al símbolo de la gramática
        if nombre_token == "FIN_ARCHIVO":
            return "$"

        return nombre_token

    # 3. Respaldo
    return str(token.tipo)


def _mensaje_no_terminal(tabla_M, no_terminal, lookahead, encontrado, donde):
    """Mensaje de error cuando M[X, a] está vacía; lista lo esperado si es corto."""
    mensaje = (f"Token inesperado {encontrado}{donde}: "
               f"no hay regla en M[{no_terminal}, {lookahead}]")
    esperados = sorted(a for a, p in tabla_M.get(no_terminal, {}).items()
                       if p is not None and a != "$")
    if 0 < len(esperados) <= 8:
        mensaje += f" (se esperaba: {', '.join(esperados)})"
    return mensaje


# ==========================================
# ANÁLISIS PREDICTIVO
# ==========================================

def analisis_predictivo_multi(tokens, un_error_por_token=True):
    """
    Ejecuta el análisis de pila LL(1) sin detenerse en el primer error.

    Args:
        tokens: lista de tokens del lexer.
        un_error_por_token: si es True (por defecto) se reporta a lo sumo un
            error por token de entrada, para evitar errores en cascada. Con
            False se reportan todos los errores que detecte la recuperación.

    Retorna: (traza_pasos, raiz_arbol, es_valido, lista_de_errores)
    """
    primeros, siguientes, tabla_M, _ = generar_datos_completos_ll1()
    # No terminales que pueden derivar en vacío (ε está en su PRIMERO)
    anulables = {nt for nt, conjunto in primeros.items() if EPS in conjunto}
    # Tokens que solo pueden iniciar una declaración global (p. ej. 'hagale_pues').
    # Si aparecen dentro de un bloque es porque faltó cerrar algo: no se descartan,
    # así la siguiente función se analiza normalmente.
    solo_declaracion = (primeros.get("<declaracion>", set())
                        - primeros.get("<sentencia>", set()) - {EPS})

    # 1. Inicialización
    raiz = NodoArbol("<programa>")
    # La pila guarda tuplas: (Símbolo_Gramatical, Nodo_Asociado)
    pila = [("$", None), ("<programa>", raiz)]

    # Lista de tokens restantes (se asume que el lexer ya incluye un token EOF o lo simulamos)
    entrada = tokens.copy()
    if not entrada or entrada[-1].tipo != "EOF":
        # Clase dummy para simular el fin de cadena si el lexer no lo provee nativamente
        class TokenEOF:
            tipo = "EOF"
            lexema = "$"
            fila = -1
            columna = -1
        entrada.append(TokenEOF())

    traza = []
    errores = []
    paso = 1

    # Estado de la recuperación de errores
    consumidos = 0          # tokens consumidos hasta ahora (posición en la entrada)
    ultimo_error_en = -1    # posición en la que se registró el último error
    en_panico = False       # True mientras se descarta una racha de tokens

    def registrar(mensaje, en_eof, descarte=False):
        """Guarda el error salvo que sea una repetición en cascada."""
        nonlocal ultimo_error_en, en_panico
        if descarte:
            # Una racha de tokens descartados cuenta como un solo error
            if not en_panico:
                errores.append(mensaje)
            en_panico = True
        else:
            if (not un_error_por_token) or en_eof or consumidos != ultimo_error_en:
                errores.append(mensaje)
        ultimo_error_en = consumidos

    # 2. Ciclo principal del autómata de pila
    while len(pila) > 0:
        tope_simbolo, tope_nodo = pila.pop()
        token_actual = entrada[0]
        lookahead = obtener_simbolo_token(token_actual)

        en_eof = lookahead == "$"
        encontrado = "fin de archivo" if en_eof else f"'{token_actual.lexema}'"
        donde = "" if en_eof else f" en {token_actual.fila}:{token_actual.columna}"

        # Capturar el estado actual para la traza visual
        estado_pila = " ".join([s[0] for s in pila] + [tope_simbolo])
        estado_entrada = " ".join([obtener_simbolo_token(t) for t in entrada])
        accion = ""

        if tope_simbolo == "$":
            if en_eof:
                accion = "Aceptar: Fin de cadena" if not errores else "Fin de cadena (el análisis terminó con errores)"
                arbol_paso = (_nodo_a_dict(raiz) if len(traza) < LIMITE_PASOS_ARBOL else None)
                traza.append({"Paso": paso, "Pila": estado_pila, "Entrada": estado_entrada,
                              "Acción": accion, "Arbol": arbol_paso})
                break
            # Sobran tokens al final: se reporta y se descartan
            mensaje = f"Se esperaba fin de archivo, pero se encontró {encontrado}{donde}"
            registrar(mensaje, en_eof, descarte=True)
            accion = f"Error: {mensaje}. Recuperación: se descarta el token"
            entrada.pop(0)
            consumidos += 1
            pila.append(("$", None))

        elif es_terminal(tope_simbolo):
            if tope_simbolo == lookahead:
                accion = f"Hacer match: {tope_simbolo}"
                if tope_nodo:
                    tope_nodo.valor = f"{tope_simbolo} ({token_actual.lexema})"
                entrada.pop(0)  # Consumir token
                consumidos += 1
                en_panico = False

            elif not en_eof and len(entrada) > 1 and obtener_simbolo_token(entrada[1]) == tope_simbolo:
                # El token actual sobra: el siguiente es justo el esperado
                mensaje = f"Token inesperado {encontrado}{donde}; se esperaba '{tope_simbolo}'"
                registrar(mensaje, en_eof, descarte=True)
                accion = f"Error: {mensaje}. Recuperación: se descarta el token"
                entrada.pop(0)
                consumidos += 1
                pila.append((tope_simbolo, tope_nodo))  # reintentar el match

            else:
                # Se asume que el terminal esperado faltó
                mensaje = f"Se esperaba '{tope_simbolo}', se encontró {encontrado}{donde}"
                registrar(mensaje, en_eof)
                accion = f"Error: {mensaje}. Recuperación: se asume '{tope_simbolo}' faltante"
                if tope_nodo:
                    tope_nodo.valor = f"{tope_simbolo} (faltante)"
                en_panico = False

        else:  # Es un No-Terminal
            produccion = tabla_M.get(tope_simbolo, {}).get(lookahead)

            if produccion is None:
                # Terminales que el resto de la pila aún espera (cierres pendientes)
                pendientes = {sim for sim, _ in pila if sim != "$" and es_terminal(sim)}
                pendientes |= solo_declaracion

                if en_eof or lookahead in siguientes.get(tope_simbolo, ()) or lookahead in pendientes:
                    # El token pertenece al contexto: X no puede seguir, se omite X
                    if tope_simbolo in anulables:
                        # X puede ser vacío: el culpable es el terminal que falta
                        # después, que se reportará cuando llegue a la cima.
                        accion = f"Recuperación: {tope_simbolo} -> ε (el token no pertenece a {tope_simbolo})"
                    else:
                        mensaje = _mensaje_no_terminal(tabla_M, tope_simbolo, lookahead, encontrado, donde)
                        registrar(mensaje, en_eof)
                        accion = f"Error: {mensaje}. Recuperación: se omite {tope_simbolo}"
                    if tope_nodo:
                        tope_nodo.agregar_hijo(NodoArbol("<error>", "terminal"))
                    en_panico = False
                else:
                    # El token no tiene sentido aquí: se descarta y se reintenta X
                    mensaje = _mensaje_no_terminal(tabla_M, tope_simbolo, lookahead, encontrado, donde)
                    registrar(mensaje, en_eof, descarte=True)
                    accion = f"Error: {mensaje}. Recuperación: se descarta el token"
                    entrada.pop(0)
                    consumidos += 1
                    pila.append((tope_simbolo, tope_nodo))
            else:
                accion = f"Expandir: {tope_simbolo} -> " + " ".join(produccion)
                en_panico = False

                # Expansión de la producción y construcción del árbol
                if produccion == [EPS]:
                    nodo_eps = NodoArbol("ε", "epsilon")
                    tope_nodo.agregar_hijo(nodo_eps)
                else:
                    # Crear los hijos y apilarlos en orden INVERSO (LIFO)
                    hijos_creados = []
                    for sim in produccion:
                        tipo_n = "terminal" if es_terminal(sim) else "no_terminal"
                        nuevo_nodo = NodoArbol(sim, tipo_n)
                        hijos_creados.append(nuevo_nodo)
                        tope_nodo.agregar_hijo(nuevo_nodo)

                    # Apilar al revés para que el primero de la producción quede en el tope
                    for nodo in reversed(hijos_creados):
                        pila.append((nodo.valor, nodo))

        arbol_paso = (_nodo_a_dict(raiz) if len(traza) < LIMITE_PASOS_ARBOL else None)
        traza.append({"Paso": paso, "Pila": estado_pila, "Entrada": estado_entrada,
                      "Acción": accion, "Arbol": arbol_paso})
        paso += 1

    return traza, raiz, len(errores) == 0, errores


def analisis_predictivo(tokens):
    """
    Versión compatible con el frontend anterior.
    Retorna: (traza_pasos, raiz_arbol, es_valido, mensaje_error)
    donde mensaje_error contiene TODOS los errores (uno por línea, numerados).
    Para obtener la lista y contarlos use `analisis_predictivo_multi`.
    """
    traza, raiz, es_valido, errores = analisis_predictivo_multi(tokens)
    if len(errores) <= 1:
        mensaje = errores[0] if errores else ""
    else:
        mensaje = "\n\n".join(f"{i}. {e}" for i, e in enumerate(errores, 1))
    return traza, raiz, es_valido, mensaje
