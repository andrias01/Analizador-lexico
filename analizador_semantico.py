# -*- coding: utf-8 -*-
"""
Módulo: analizador_semantico.py
Descripción: Fase de ANÁLISIS SEMÁNTICO de Paisascript (Quiz 4 / Entrega 4).

Esta fase es INDEPENDIENTE del análisis sintáctico: recibe el CST (árbol de
derivación concreta) que produce `parser.Parser`, lo recorre con un visitor y
construye una tabla de símbolos. No modifica el parser ni depende de él más
allá de la forma del árbol.

Reglas semánticas implementadas (SEM-1 .. SEM-5, ver documento PDF):

  SEM-1  <sent_declaracion>
         Atributo sintetizado  type(expr).
         Restricción: si hay anotación de tipo, type(expr) == tipo declarado.
         Acción: comparar tipos, insertar el símbolo en el ámbito actual.

  SEM-2  <expr_primaria> (IDENTIFICADOR) y <sent_lectura>
         Restricción: todo identificador usado en una expresión debe estar
         declarado en el ámbito actual o en uno ancestro.
         Acción: consultar la tabla de símbolos (búsqueda de dentro hacia
         afuera). `escuche_pues(id)` declara/inicializa el identificador.

  SEM-3  <expr_aditiva>, <expr_multiplicativa>, <expr_unaria>, relacionales
         y lógicos.
         Restricción: los operandos aritméticos deben ser del mismo tipo
         (numerito o quebradito); '%' solo admite numerito; los operadores
         lógicos y las condiciones exigen siono.
         Acción: comparar los tipos sintetizados de ambos operandos.

  SEM-4  <sent_si>, <sent_mientras>
         Restricción: la condición debe ser de tipo siono.
         Acción: comprobar el tipo sintetizado de la expresión de control.

  SEM-5  <sent_llamada> y llamadas dentro de <expr_primaria>
         Restricción: la función debe existir, la aridad debe coincidir y
         cada argumento debe tener el tipo del parámetro formal.
         Acción: consultar la firma en la tabla de símbolos y comparar.

Recuperación de errores: cada violación se registra en `self.errores` y el
recorrido CONTINÚA. Las expresiones con error sintetizan el tipo especial
ERROR, que es compatible con cualquier otro tipo, para no generar errores en
cascada. Así se reportan todos los errores semánticos del programa en una
sola pasada, tal como exige el enunciado.

Uso:
    from analizador_semantico import AnalizadorSemantico
    analizador = AnalizadorSemantico(cst)
    errores = analizador.analizar()
    tabla = analizador.tabla
"""

from __future__ import annotations

# =============================================================================
#  TIPOS DEL LENGUAJE
# =============================================================================

# Tipos reales de Paisascript (se corresponden 1 a 1 con los de Gleam).
NUMERITO = "numerito"        # Int
QUEBRADITO = "quebradito"    # Float
CUENTO = "cuento"            # String
SIONO = "siono"              # Bool

# Tipos especiales del analizador (no son tipos del lenguaje fuente).
DESCONOCIDO = "desconocido"  # tipo aún no inferido (p. ej. escuche_pues)
ERROR = "error"              # expresión ya reportada: evita cascadas
VACIO = "vacio"              # función/procedimiento sin valor de retorno

TIPOS_NUMERICOS = {NUMERITO, QUEBRADITO}
TIPOS_VALIDOS = {NUMERITO, QUEBRADITO, CUENTO, SIONO}

# Mapa lexema -> tipo para los terminales de <tipo>.
_MAPA_TIPOS = {
    "numerito": NUMERITO,
    "quebradito": QUEBRADITO,
    "cuento": CUENTO,
    "siono": SIONO,
}

# Mapa token -> tipo (el lexer clasifica las palabras de tipo como KW_TIPO_*).
_MAPA_TOKENS_TIPO = {
    "KW_TIPO_ENTERO": NUMERITO,
    "KW_TIPO_REAL": QUEBRADITO,
    "KW_TIPO_CADENA": CUENTO,
    "KW_TIPO_BOOLEANO": SIONO,
}


# =============================================================================
#  ERROR SEMÁNTICO
# =============================================================================

class ErrorSemantico:
    """Violación de una regla semántica.

    Guarda todo lo que exige el enunciado: fila, columna, lexema y un mensaje
    descriptivo, además de la regla (SEM-x) que se violó.
    """

    def __init__(self, fila, columna, lexema, mensaje, regla=""):
        self.fila = fila
        self.columna = columna
        self.lexema = lexema
        self.mensaje = mensaje
        self.regla = regla

    def __str__(self):
        etiqueta = f"[{self.regla}] " if self.regla else ""
        return (
            f"Error Semántico en [Fila {self.fila}, Columna {self.columna}] "
            f"sobre '{self.lexema}': {etiqueta}{self.mensaje}"
        )

    def __repr__(self):
        return self.__str__()


# =============================================================================
#  TABLA DE SÍMBOLOS
# =============================================================================

class Simbolo:
    """Entrada de la tabla de símbolos.

    Atributos exigidos por el enunciado: tipo, valor/estado de inicialización
    y ámbito, además de la posición de la declaración (fila/columna).
    """

    def __init__(self, lexema, tipo, categoria, fila="?", columna="?",
                 ambito="global", inicializada=False, params=None,
                 tipo_retorno=None):
        self.lexema = lexema
        self.tipo = tipo                  # numerito | quebradito | cuento | siono | desconocido
        self.categoria = categoria        # variable | parametro | funcion | bucle | patron
        self.fila = fila
        self.columna = columna
        self.ambito = ambito
        self.inicializada = inicializada
        self.params = list(params or [])  # solo para funciones: lista de Simbolo
        self.tipo_retorno = tipo_retorno  # solo para funciones

    def como_fila(self):
        if self.categoria == "funcion":
            firma = ", ".join(f"{p.tipo} {p.lexema}" for p in self.params)
            detalle = f"({firma}) -> {self.tipo_retorno or DESCONOCIDO}"
        else:
            detalle = ""
        return {
            "Ámbito": self.ambito,
            "Lexema": self.lexema,
            "Tipo": self.tipo,
            "Categoría": self.categoria,
            "Fila": self.fila,
            "Columna": self.columna,
            "Inicializada": "sí" if self.inicializada else "no",
            "Detalle": detalle,
        }


class TablaSimbolos:
    """Pila de ámbitos. Cada bloque, función, `pa_cada` o `pillemos` abre uno."""

    def __init__(self):
        self.ambitos = [{}]
        self.nombres = ["global"]

    # --- Gestión de ámbitos ------------------------------------------------
    def abrir(self, nombre=None):
        self.ambitos.append({})
        self.nombres.append(nombre or f"bloque {len(self.ambitos)}")

    def cerrar(self):
        if len(self.ambitos) > 1:
            self.ambitos.pop()
            self.nombres.pop()

    @property
    def ambito_actual(self):
        return self.nombres[-1]

    # --- Operaciones sobre símbolos ---------------------------------------
    def declarar(self, simbolo):
        # Paisascript permite shadowing (como el `let` de Gleam): declarar en
        # el ámbito actual siempre es válido y oculta el enlace anterior.
        self.ambitos[-1][simbolo.lexema] = simbolo
        return simbolo

    def buscar(self, lexema):
        """Busca de dentro hacia afuera; devuelve el primer enlace visible."""
        for ambito in reversed(self.ambitos):
            if lexema in ambito:
                return ambito[lexema]
        return None

    def buscar_global(self, lexema):
        return self.ambitos[0].get(lexema)

    def filas(self):
        """Todas las entradas visibles/no visibles, para mostrar en la interfaz."""
        filas = []
        for nivel, ambito in enumerate(self.ambitos):
            for simbolo in ambito.values():
                fila = simbolo.como_fila()
                fila["Nivel"] = nivel
                filas.append(fila)
        return filas

    def __len__(self):
        return sum(len(a) for a in self.ambitos)


# =============================================================================
#  ANALIZADOR SEMÁNTICO (VISITOR SOBRE EL CST)
# =============================================================================

class AnalizadorSemantico:
    """Recorre el CST y valida las reglas SEM-1 a SEM-5."""

    def __init__(self, cst):
        self.cst = cst
        self.errores: list[ErrorSemantico] = []
        self.tabla = TablaSimbolos()
        self._pila_funciones = []   # contexto de retorno de la función actual
        self._pila_pillemos = []    # tipo de la expresión de cada `pillemos`
        self._contador_bloques = 0

    # ------------------------------------------------------------------
    #  Punto de entrada
    # ------------------------------------------------------------------
    def analizar(self):
        self._declarar_funciones(self.cst)
        self._visitar(self.cst)
        return self.errores

    # ------------------------------------------------------------------
    #  Utilidades de navegación del CST
    # ------------------------------------------------------------------
    @staticmethod
    def _hijos(nodo):
        return nodo.get("hijos", []) if isinstance(nodo, dict) else []

    @staticmethod
    def _nombre(nodo):
        """Etiqueta del no terminal sin ángulos ('<expr_o>' -> 'expr_o')."""
        if not isinstance(nodo, dict):
            return ""
        tipo = nodo.get("tipo", "")
        if tipo.startswith("<") and tipo.endswith(">"):
            return tipo[1:-1]
        return tipo

    @staticmethod
    def _es_eps(nodo):
        return AnalizadorSemantico._nombre(nodo) == "ε"

    @staticmethod
    def _token_tipo(nodo):
        if not isinstance(nodo, dict):
            return None
        if nodo.get("token_tipo"):
            return nodo["token_tipo"]
        return str(nodo.get("tipo", "")).split(" (", 1)[0]

    @staticmethod
    def _lexema(nodo):
        if not isinstance(nodo, dict):
            return ""
        if "lexema" in nodo:
            return nodo["lexema"]
        tipo = str(nodo.get("tipo", ""))
        if " (" in tipo and tipo.endswith(")"):
            return tipo[tipo.index(" (") + 2:-1]
        return ""

    def _pos(self, nodo):
        """Primera posición real (fila, columna, lexema) del subárbol."""
        if not isinstance(nodo, dict):
            return "?", "?", ""
        fila = nodo.get("fila")
        if fila not in (None, "?") and not nodo.get("hijos"):
            return fila, nodo.get("columna", "?"), nodo.get("lexema", "")
        for hijo in nodo.get("hijos", []):
            f, c, lex = self._pos(hijo)
            if f not in (None, "?"):
                return f, c, lex
        return "?", "?", ""

    def _error(self, nodo, mensaje, regla=""):
        fila, columna, lexema = self._pos(nodo)
        if not lexema:
            lexema = self._lexema(nodo)
        self.errores.append(ErrorSemantico(fila, columna, lexema, mensaje, regla))

    def _hijo_nt(self, nodo, nombre):
        for hijo in self._hijos(nodo):
            if self._nombre(hijo) == nombre:
                return hijo
        return None

    def _visitar(self, nodo):
        metodo = getattr(self, f"_v_{self._nombre(nodo)}", None)
        if metodo is not None:
            metodo(nodo)
        # Los nodos desconocidos / <error> / ε se ignoran: recuperación.

    # ------------------------------------------------------------------
    #  Tipos declarados
    # ------------------------------------------------------------------
    def _tipo_de_nodo(self, nodo):
        """Tipo declarado en <tipo>, <tipo_opcional> o <tipo_retorno>."""
        if not isinstance(nodo, dict):
            return DESCONOCIDO
        nombre = self._nombre(nodo)
        if nombre in ("tipo_opcional", "tipo_retorno"):
            for hijo in self._hijos(nodo):
                if nombre == "tipo_retorno" and self._nombre(hijo) == "tipo":
                    return self._tipo_de_nodo(hijo)
                if nombre == "tipo_opcional":
                    return self._tipo_de_nodo(hijo)
            return DESCONOCIDO
        if nombre == "tipo":
            for hijo in self._hijos(nodo):
                tipo = _MAPA_TIPOS.get(self._lexema(hijo))
                if tipo is None:
                    tipo = _MAPA_TOKENS_TIPO.get(self._token_tipo(hijo))
                if tipo:
                    return tipo
        for hijo in self._hijos(nodo):
            if self._es_eps(hijo):
                continue
            tipo = self._tipo_de_nodo(hijo)
            if tipo != DESCONOCIDO:
                return tipo
        return DESCONOCIDO

    # ------------------------------------------------------------------
    #  Recolección de firmas (pre-pasada para permitir llamadas adelantadas)
    # ------------------------------------------------------------------
    def _declarar_funciones(self, nodo):
        if self._nombre(nodo) == "def_funcion":
            self._registrar_funcion(nodo)
            return  # no hay funciones anidadas
        for hijo in self._hijos(nodo):
            self._declarar_funciones(hijo)

    def _registrar_funcion(self, nodo_def):
        hijos = self._hijos(nodo_def)
        if len(hijos) < 6:
            return
        nombre = self._lexema(hijos[1])
        if not nombre:
            return
        params_nodo = self._hijo_nt(nodo_def, "parametros")
        params = self._colectar_params(params_nodo)
        tipo_ret = self._tipo_de_nodo(self._hijo_nt(nodo_def, "tipo_retorno"))
        firma = [
            Simbolo(p_nombre, p_tipo, "parametro", p_leaf.get("fila", "?"),
                    p_leaf.get("columna", "?"), f"funcion {nombre}")
            for (p_nombre, p_tipo, p_leaf) in params
        ]
        self.tabla.ambitos[0][nombre] = Simbolo(
            nombre, "funcion", "funcion",
            hijos[1].get("fila", "?"), hijos[1].get("columna", "?"),
            "global", inicializada=True, params=firma, tipo_retorno=tipo_ret,
        )

    def _colectar_params(self, nodo):
        """Devuelve [(nombre, tipo, hoja_identificador)] de <parametros>."""
        resultado = []
        nombre = self._nombre(nodo)
        if nombre == "parametros":
            for hijo in self._hijos(nodo):
                resultado += self._colectar_params(hijo)
        elif nombre == "param_lista":
            h = self._hijos(nodo)
            if len(h) >= 3:
                resultado.append((self._lexema(h[1]), self._tipo_de_nodo(h[0]), h[1]))
                resultado += self._colectar_params(h[2])
        elif nombre == "param_resto" and not self._es_eps(nodo):
            h = self._hijos(nodo)
            if len(h) >= 4:
                resultado.append((self._lexema(h[2]), self._tipo_de_nodo(h[1]), h[2]))
                resultado += self._colectar_params(h[3])
        return resultado

    def _colectar_args(self, nodo):
        """Devuelve las <expresion> de <argumentos> en orden."""
        resultado = []
        nombre = self._nombre(nodo)
        if nombre == "argumentos":
            for hijo in self._hijos(nodo):
                resultado += self._colectar_args(hijo)
        elif nombre == "arg_lista":
            h = self._hijos(nodo)
            if h:
                resultado.append(h[0])
                if len(h) > 1:
                    resultado += self._colectar_args(h[1])
        elif nombre == "arg_resto" and not self._es_eps(nodo):
            h = self._hijos(nodo)
            if len(h) >= 3:
                resultado.append(h[1])
                resultado += self._colectar_args(h[2])
        return resultado

    # ------------------------------------------------------------------
    #  Programa, declaraciones y bloques
    # ------------------------------------------------------------------
    def _v_programa(self, nodo):
        for hijo in self._hijos(nodo):
            self._visitar(hijo)

    def _v_lista_declaraciones(self, nodo):
        for hijo in self._hijos(nodo):
            self._visitar(hijo)

    def _v_declaracion(self, nodo):
        for hijo in self._hijos(nodo):
            self._visitar(hijo)

    def _v_def_funcion(self, nodo):
        hijos = self._hijos(nodo)
        if len(hijos) < 8:
            return
        hoja_id = hijos[1]
        nombre = self._lexema(hoja_id)
        params = self._colectar_params(self._hijo_nt(nodo, "parametros"))
        retorno_anotado = self._tipo_de_nodo(self._hijo_nt(nodo, "tipo_retorno"))

        self.tabla.abrir(f"funcion {nombre}")
        for (p_nombre, p_tipo, p_leaf) in params:
            self.tabla.declarar(Simbolo(
                p_nombre, p_tipo, "parametro",
                p_leaf.get("fila", "?"), p_leaf.get("columna", "?"),
                self.tabla.ambito_actual, inicializada=True,
            ))

        contexto = {
            "nombre": nombre,
            "retorno_anotado": retorno_anotado,
            "retornos": [],
        }
        self._pila_funciones.append(contexto)
        self._visitar(self._hijo_nt(nodo, "bloque"))
        self._pila_funciones.pop()
        self.tabla.cerrar()

        # Inferencia del tipo de retorno cuando no hay anotación explícita.
        firma = self.tabla.buscar_global(nombre)
        if firma is not None:
            if retorno_anotado == DESCONOCIDO:
                tipos = [t for t in contexto["retornos"] if t not in (ERROR, DESCONOCIDO)]
                if tipos:
                    if any(t != tipos[0] for t in tipos):
                        self._error(hoja_id, f"La función '{nombre}' retorna tipos "
                                    f"inconsistentes: {', '.join(sorted(set(tipos)))}", "SEM-5")
                    else:
                        firma.tipo_retorno = tipos[0]
            elif not contexto["retornos"]:
                self._error(hoja_id, f"La función '{nombre}' declara retorno "
                            f"{retorno_anotado} pero no usa 'entregue_pues'", "SEM-5")

    def _v_bloque(self, nodo):
        self._contador_bloques += 1
        self.tabla.abrir(f"bloque {self._contador_bloques}")
        for hijo in self._hijos(nodo):
            self._visitar(hijo)
        self.tabla.cerrar()

    def _v_lista_sentencias(self, nodo):
        for hijo in self._hijos(nodo):
            self._visitar(hijo)

    def _v_sentencia(self, nodo):
        for hijo in self._hijos(nodo):
            self._visitar(hijo)

    # ------------------------------------------------------------------
    #  SEM-1: declaración y compatibilidad de tipos
    # ------------------------------------------------------------------
    def _v_sent_declaracion(self, nodo):
        hijos = self._hijos(nodo)
        if len(hijos) < 5:
            return
        hoja_id = hijos[2]
        nombre = self._lexema(hoja_id)
        tipo_declarado = self._tipo_de_nodo(hijos[1])
        tipo_expr = self._tipo_expr(hijos[4])

        if (tipo_declarado not in (DESCONOCIDO, ERROR)
                and tipo_expr not in (DESCONOCIDO, ERROR)
                and tipo_expr != tipo_declarado):
            self._error(
                hoja_id,
                f"Se declara '{nombre}' como {tipo_declarado}, pero la expresión "
                f"es de tipo {tipo_expr}",
                "SEM-1",
            )
            tipo_final = tipo_declarado
        else:
            tipo_final = tipo_declarado if tipo_declarado != DESCONOCIDO else tipo_expr
        if tipo_final == ERROR:
            # No se propaga el tipo de error a la tabla: evita cascadas.
            tipo_final = DESCONOCIDO

        self.tabla.declarar(Simbolo(
            nombre, tipo_final, "variable",
            hoja_id.get("fila", "?"), hoja_id.get("columna", "?"),
            self.tabla.ambito_actual, inicializada=True,
        ))

    # ------------------------------------------------------------------
    #  SEM-2: uso de identificadores y escuche_pues
    # ------------------------------------------------------------------
    def _v_sent_lectura(self, nodo):
        hijos = self._hijos(nodo)
        # escuche_pues "(" IDENTIFICADOR ")"
        hoja_id = next(
            (h for h in hijos if self._token_tipo(h) == "IDENTIFICADOR"), None
        )
        if hoja_id is None:
            return
        nombre = self._lexema(hoja_id)
        simbolo = self.tabla.buscar(nombre)
        if simbolo is None:
            # `escuche_pues(x)` declara x; su tipo se infiere por el uso.
            self.tabla.declarar(Simbolo(
                nombre, DESCONOCIDO, "variable",
                hoja_id.get("fila", "?"), hoja_id.get("columna", "?"),
                self.tabla.ambito_actual, inicializada=True,
            ))
        else:
            simbolo.inicializada = True

    # ------------------------------------------------------------------
    #  SEM-3 / SEM-4: expresiones y condiciones
    # ------------------------------------------------------------------
    def _v_sent_impresion(self, nodo):
        hijos = self._hijos(nodo)
        if len(hijos) >= 3:
            self._tipo_expr(hijos[2])

    def _v_sent_retornar(self, nodo):
        hijos = self._hijos(nodo)
        if len(hijos) < 2:
            return
        tipo = self._tipo_expr(hijos[1])
        if not self._pila_funciones:
            self._error(hijos[0], "'entregue_pues' solo puede usarse dentro de "
                        "una función", "SEM-5")
            return
        contexto = self._pila_funciones[-1]
        contexto["retornos"].append(tipo)
        esperado = contexto["retorno_anotado"]
        if (esperado not in (DESCONOCIDO, ERROR)
                and tipo not in (DESCONOCIDO, ERROR)
                and tipo != esperado):
            self._error(
                hijos[1],
                f"La función '{contexto['nombre']}' declara retorno {esperado}, "
                f"pero 'entregue_pues' devuelve {tipo}",
                "SEM-5",
            )

    def _v_sent_si(self, nodo):
        hijos = self._hijos(nodo)
        if len(hijos) < 5:
            return
        self._exigir_condicion(hijos[1], "si_acaso")
        self._visitar(hijos[3])   # <bloque> entonces
        self._visitar(hijos[4])   # <rama_sino>

    def _v_rama_sino(self, nodo):
        if self._es_eps(nodo):
            return
        for hijo in self._hijos(nodo):
            self._visitar(hijo)

    def _v_sent_mientras(self, nodo):
        hijos = self._hijos(nodo)
        if len(hijos) < 4:
            return
        self._exigir_condicion(hijos[1], "mientras_que")
        self._visitar(hijos[3])

    def _exigir_condicion(self, nodo_expr, construccion):
        tipo = self._tipo_expr(nodo_expr)
        if tipo not in (SIONO, ERROR, DESCONOCIDO):
            self._error(
                nodo_expr,
                f"La condición de '{construccion}' debe ser siono, pero es {tipo}",
                "SEM-4",
            )

    # ------------------------------------------------------------------
    #  SEM-3: operadores aritméticos, lógicos y relacionales
    # ------------------------------------------------------------------
    def _v_sent_para(self, nodo):
        hijos = self._hijos(nodo)
        if len(hijos) < 9:
            return
        # pa_cada ID desde <expr> hasta <expr> [de_a <expr>] dele_pues <bloque> listo_pues
        hoja_var = hijos[1]
        nombre_var = self._lexema(hoja_var)
        for indice, etiqueta in ((3, "desde"), (5, "hasta")):
            tipo = self._tipo_expr(hijos[indice])
            if tipo not in (NUMERITO, ERROR, DESCONOCIDO):
                self._error(
                    hijos[indice],
                    f"El límite '{etiqueta}' de 'pa_cada' debe ser numerito, "
                    f"pero es {tipo}",
                    "SEM-3",
                )
        paso = hijos[6]
        if not self._es_eps(paso):
            for hijo in self._hijos(paso):
                if self._nombre(hijo) == "expresion":
                    tipo = self._tipo_expr(hijo)
                    if tipo not in (NUMERITO, ERROR, DESCONOCIDO):
                        self._error(
                            hijo,
                            f"El paso 'de_a' debe ser numerito, pero es {tipo}",
                            "SEM-3",
                        )

        self.tabla.abrir(f"para {nombre_var}")
        self.tabla.declarar(Simbolo(
            nombre_var, NUMERITO, "bucle",
            hoja_var.get("fila", "?"), hoja_var.get("columna", "?"),
            self.tabla.ambito_actual, inicializada=True,
        ))
        self._visitar(self._hijo_nt(nodo, "bloque"))
        self.tabla.cerrar()

    def _v_sent_pillemos(self, nodo):
        hijos = self._hijos(nodo)
        if len(hijos) < 4:
            return
        tipo_expr = self._tipo_expr(hijos[1])
        self._pila_pillemos.append(tipo_expr)
        self._visitar(self._hijo_nt(nodo, "lista_casos"))
        self._pila_pillemos.pop()

    def _v_lista_casos(self, nodo):
        for hijo in self._hijos(nodo):
            self._visitar(hijo)

    def _v_lista_casos_resto(self, nodo):
        for hijo in self._hijos(nodo):
            self._visitar(hijo)

    def _v_caso(self, nodo):
        hijos = self._hijos(nodo)
        if len(hijos) < 3:
            return
        patron = hijos[0]
        tipo_patron, hoja_patron = self._tipo_patron(patron)
        tipo_expr = self._pila_pillemos[-1] if self._pila_pillemos else DESCONOCIDO

        if (tipo_patron not in (DESCONOCIDO, ERROR)
                and tipo_expr not in (DESCONOCIDO, ERROR)
                and tipo_patron != tipo_expr):
            self._error(
                patron,
                f"El patrón es de tipo {tipo_patron}, pero la expresión del "
                f"'pillemos' es de tipo {tipo_expr}",
                "SEM-3",
            )

        self.tabla.abrir("caso pillemos")
        if hoja_patron is not None and self._token_tipo(hoja_patron) == "IDENTIFICADOR":
            self.tabla.declarar(Simbolo(
                self._lexema(hoja_patron),
                tipo_expr if tipo_expr != ERROR else DESCONOCIDO,
                "patron",
                hoja_patron.get("fila", "?"), hoja_patron.get("columna", "?"),
                self.tabla.ambito_actual, inicializada=True,
            ))
        self._visitar(hijos[2])   # <cuerpo_caso>
        self.tabla.cerrar()

    def _tipo_patron(self, nodo_patron):
        for hoja in self._hijos(nodo_patron):
            tipo_token = self._token_tipo(hoja)
            lexema = self._lexema(hoja)
            if tipo_token == "NUM_ENTERO":
                return NUMERITO, hoja
            if tipo_token == "NUM_REAL":
                return QUEBRADITO, hoja
            if tipo_token == "CADENA_LITERAL":
                return CUENTO, hoja
            if tipo_token in ("LIT_VERDADERO", "LIT_FALSO") or lexema in ("sizas", "naranjas"):
                return SIONO, hoja
            if tipo_token == "COMODIN" or lexema == "_":
                return DESCONOCIDO, hoja
            if tipo_token == "IDENTIFICADOR":
                return DESCONOCIDO, hoja
        return DESCONOCIDO, None

    def _v_cuerpo_caso(self, nodo):
        for hijo in self._hijos(nodo):
            self._visitar(hijo)

    # ------------------------------------------------------------------
    #  SEM-5: llamadas
    # ------------------------------------------------------------------
    def _v_sent_llamada(self, nodo):
        hijos = self._hijos(nodo)
        if not hijos:
            return
        argumentos = self._hijo_nt(nodo, "argumentos")
        self._verificar_llamada(hijos[0], argumentos)

    def _v_sent_asignacion(self, nodo):
        # El parser tolera `x = expr` como recuperación, pero la gramática y el
        # modelo inmutable de Paisascript exigen `pille_pues` (shadowing).
        hijos = self._hijos(nodo)
        if not hijos:
            return
        self._error(
            hijos[0],
            f"Paisascript es inmutable: no se puede reasignar "
            f"'{self._lexema(hijos[0])}'. Use 'pille_pues' para crear un "
            f"enlace nuevo (shadowing)",
            "SEM-1",
        )
        for hijo in hijos[1:]:
            self._visitar(hijo)

    def _verificar_llamada(self, hoja_id, nodo_argumentos):
        nombre = self._lexema(hoja_id)
        firma = self.tabla.buscar_global(nombre) or self.tabla.buscar(nombre)
        argumentos = self._colectar_args(nodo_argumentos) if nodo_argumentos else []

        if firma is None or firma.categoria != "funcion":
            self._error(hoja_id, f"La función '{nombre}' no ha sido declarada", "SEM-5")
            for argumento in argumentos:
                self._tipo_expr(argumento)
            return ERROR

        esperados = firma.params
        if len(argumentos) != len(esperados):
            self._error(
                hoja_id,
                f"La función '{nombre}' espera {len(esperados)} argumento(s) "
                f"y se pasaron {len(argumentos)}",
                "SEM-5",
            )

        for indice, argumento in enumerate(argumentos):
            tipo_arg = self._tipo_expr(argumento)
            if indice >= len(esperados):
                continue
            parametro = esperados[indice]
            if (tipo_arg not in (DESCONOCIDO, ERROR)
                    and parametro.tipo not in (DESCONOCIDO, ERROR)
                    and tipo_arg != parametro.tipo):
                self._error(
                    argumento,
                    f"El argumento {indice + 1} ('{parametro.lexema}') de "
                    f"'{nombre}' debe ser {parametro.tipo}, pero se recibió {tipo_arg}",
                    "SEM-5",
                )
        return firma.tipo_retorno or DESCONOCIDO

    # ------------------------------------------------------------------
    #  Evaluación de expresiones: atributo sintetizado `type`
    # ------------------------------------------------------------------
    def _tipo_expr(self, nodo):
        nombre = self._nombre(nodo)

        if nombre == "expresion":
            hijos = self._hijos(nodo)
            return self._tipo_expr(hijos[0]) if hijos else DESCONOCIDO

        if nombre in ("expr_o", "expr_y", "expr_igualdad", "expr_relacional",
                      "expr_concat", "expr_aditiva", "expr_multiplicativa",
                      "expr_potencia"):
            hijos = self._hijos(nodo)
            if len(hijos) < 2:
                return self._tipo_expr(hijos[0]) if hijos else DESCONOCIDO
            tipo_izq = self._tipo_expr(hijos[0])
            return self._cadena(nombre, tipo_izq, hijos[1])

        if nombre == "expr_unaria":
            hijos = self._hijos(nodo)
            if len(hijos) == 2:
                operador = self._lexema(hijos[0])
                tipo = self._tipo_expr(hijos[1])
                if operador == "nanai":
                    if tipo not in (SIONO, ERROR, DESCONOCIDO):
                        self._error(hijos[1], f"'nanai' exige un operando siono, "
                                    f"pero es {tipo}", "SEM-3")
                        return ERROR
                    return SIONO
                # "-" unario
                if tipo not in (NUMERITO, QUEBRADITO, ERROR, DESCONOCIDO):
                    self._error(hijos[1], f"El operador '-' exige un operando "
                                f"numerito o quebradito, pero es {tipo}", "SEM-3")
                    return ERROR
                return tipo
            return self._tipo_expr(hijos[0]) if hijos else DESCONOCIDO

        if nombre == "expr_primaria":
            return self._tipo_primaria(nodo)

        # <error>, <sufijo_id>, ε u otro nodo inesperado
        return DESCONOCIDO

    def _cadena(self, nivel, tipo_izq, nodo_p):
        """Recorre la cola derecha `A' ::= op B A' | e` de cada nivel."""
        if not isinstance(nodo_p, dict) or self._es_eps(nodo_p):
            return tipo_izq
        hijos = self._hijos(nodo_p)
        if len(hijos) < 2:
            return tipo_izq
        operador = self._lexema(hijos[0])
        tipo_der = self._tipo_expr(hijos[1])
        resultado = self._aplicar(nivel, operador, tipo_izq, tipo_der, hijos[0])
        resto = hijos[2] if len(hijos) > 2 else None
        return self._cadena(nivel, resultado, resto)

    def _aplicar(self, nivel, operador, izq, der, nodo_op):
        if ERROR in (izq, der):
            return ERROR

        if nivel == "expr_o" or nivel == "expr_y":
            return self._logica(operador, izq, der, nodo_op)

        if nivel == "expr_igualdad":
            if not self._compatibles(izq, der):
                self._error(nodo_op, f"No se pueden comparar valores de tipo "
                            f"{izq} y {der} con '{operador}'", "SEM-3")
                return ERROR
            return SIONO

        if nivel == "expr_relacional":
            return self._relacional(operador, izq, der, nodo_op)

        if nivel == "expr_concat":
            validos = TIPOS_NUMERICOS | {CUENTO, DESCONOCIDO}
            if izq not in validos or der not in validos:
                invalido = izq if izq not in validos else der
                self._error(nodo_op, f"El operador '<>' no admite valores de "
                            f"tipo {invalido}", "SEM-3")
                return ERROR
            return CUENTO

        if nivel == "expr_multiplicativa":
            if operador == "%":
                return self._entero(operador, izq, der, nodo_op)
            return self._aritmetica(operador, izq, der, nodo_op)

        # expr_aditiva y expr_potencia
        return self._aritmetica(operador, izq, der, nodo_op)

    @staticmethod
    def _compatibles(izq, der):
        return ERROR in (izq, der) or DESCONOCIDO in (izq, der) or izq == der

    def _logica(self, operador, izq, der, nodo_op):
        for tipo in (izq, der):
            if tipo not in (SIONO, DESCONOCIDO, ERROR):
                self._error(nodo_op, f"El operador '{operador}' exige operandos "
                            f"siono, pero se recibió {tipo}", "SEM-3")
                return ERROR
        return SIONO

    def _relacional(self, operador, izq, der, nodo_op):
        if izq == DESCONOCIDO or der == DESCONOCIDO:
            return SIONO
        if izq not in TIPOS_NUMERICOS or der not in TIPOS_NUMERICOS:
            self._error(nodo_op, f"El operador '{operador}' exige operandos "
                        f"numeritos o quebraditos, pero se recibieron {izq} y {der}",
                        "SEM-3")
            return ERROR
        if izq != der:
            self._error(nodo_op, f"No se pueden comparar '{izq}' con '{der}' "
                        f"usando '{operador}'", "SEM-3")
            return ERROR
        return SIONO

    def _aritmetica(self, operador, izq, der, nodo_op):
        if DESCONOCIDO in (izq, der):
            conocido = der if izq == DESCONOCIDO else izq
            return conocido if conocido in TIPOS_NUMERICOS else DESCONOCIDO
        if izq not in TIPOS_NUMERICOS or der not in TIPOS_NUMERICOS:
            self._error(nodo_op, f"El operador '{operador}' exige operandos "
                        f"numerito o quebradito, pero se recibieron {izq} y {der}",
                        "SEM-3")
            return ERROR
        if izq != der:
            self._error(nodo_op, f"No se pueden mezclar '{izq}' y '{der}' con "
                        f"'{operador}': Gleam no convierte implícitamente entre "
                        f"numerito y quebradito", "SEM-3")
            return ERROR
        return izq

    def _entero(self, operador, izq, der, nodo_op):
        if DESCONOCIDO in (izq, der):
            return NUMERITO
        if izq != NUMERITO or der != NUMERITO:
            self._error(nodo_op, f"El operador '{operador}' solo admite "
                        f"numerito, pero se recibieron {izq} y {der}", "SEM-3")
            return ERROR
        return NUMERITO

    def _tipo_primaria(self, nodo):
        hijos = self._hijos(nodo)
        if not hijos:
            return DESCONOCIDO

        # "(" <expresion> ")"
        if len(hijos) == 3 and self._token_tipo(hijos[0]) == "PAR_ABRE":
            return self._tipo_expr(hijos[1])

        hoja = hijos[0]
        tipo_token = self._token_tipo(hoja)
        lexema = self._lexema(hoja)

        if tipo_token == "NUM_ENTERO":
            return NUMERITO
        if tipo_token == "NUM_REAL":
            return QUEBRADITO
        if tipo_token == "CADENA_LITERAL":
            return CUENTO
        if tipo_token in ("LIT_VERDADERO", "LIT_FALSO") or lexema in ("sizas", "naranjas"):
            return SIONO

        if tipo_token == "IDENTIFICADOR":
            sufijo = hijos[1] if len(hijos) > 1 else None
            if self._es_llamada(sufijo):
                argumentos = self._hijo_nt(sufijo, "argumentos")
                return self._verificar_llamada(hoja, argumentos)
            return self._tipo_variable(hoja)

        return DESCONOCIDO

    def _es_llamada(self, sufijo):
        if not isinstance(sufijo, dict):
            return False
        return any(self._token_tipo(h) == "PAR_ABRE" for h in self._hijos(sufijo))

    def _tipo_variable(self, hoja):
        nombre = self._lexema(hoja)
        simbolo = self.tabla.buscar(nombre)
        if simbolo is None:
            self._error(hoja, f"El identificador '{nombre}' no ha sido "
                        f"declarado en el ámbito actual ni en uno ancestro", "SEM-2")
            return ERROR
        if simbolo.categoria == "funcion":
            self._error(hoja, f"'{nombre}' es una función; para usarla debe "
                        f"escribirse '{nombre}(...)'", "SEM-2")
            return ERROR
        if not simbolo.inicializada:
            self._error(hoja, f"El identificador '{nombre}' se usa antes de "
                        f"ser inicializado", "SEM-2")
        return simbolo.tipo
