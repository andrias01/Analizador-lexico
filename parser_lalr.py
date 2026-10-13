#!/usr/bin/env python3
"""Parser LALR(1) para PaisaScript.

Implementa un analizador sintáctico ascendente LALR(1) que utiliza
las tablas ACTION y GOTO generadas por generador_lalr1_completo.py.

Proporciona análisis paso a paso con traza de pilas y acciones.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional, List, Any, Union


# =============================================================================
# GRAMÁTICA BNF COMPLETA DE PAISCRIPT (basada en gramatica_BNF_completa.txt)
# Usa los nombres de tokens del LEXER (KW_DECLARACION, KW_LECTURA, etc.)
# =============================================================================

GRAMATICA_BNF = {
    # Programa y declaraciones
    "<programa>": [["<lista_declaraciones>"]],
    "<lista_declaraciones>": [["<declaracion>", "<lista_declaraciones>"], []],
    "<declaracion>": [["<def_funcion>"], ["<sentencia>"]],

    # Definición de funciones
    "<def_funcion>": [["KW_FUNCION", "IDENTIFICADOR", "PAR_ABRE", "<parametros>", "PAR_CIERRA", "<tipo_retorno>", "KW_HACER", "<bloque>", "KW_FIN_FUNCION"]],
    "<tipo_retorno>": [["KW_FLECHA", "<tipo>"], []],
    "<parametros>": [["<param_lista>"], []],
    "<param_lista>": [["<tipo>", "IDENTIFICADOR", "<param_resto>"]],
    "<param_resto>": [["COMA", "<tipo>", "IDENTIFICADOR", "<param_resto>"], []],
    "<tipo>": [["KW_TIPO_ENTERO"], ["KW_TIPO_REAL"], ["KW_TIPO_CADENA"], ["KW_TIPO_BOOLEANO"]],

    # Bloques y sentencias
    "<bloque>": [["<sentencia>", "<lista_sentencias>"]],
    "<lista_sentencias>": [["<sentencia>", "<lista_sentencias>"], []],

    "<sentencia>": [
        ["<sent_declaracion>"],
        ["<sent_lectura>"],
        ["<sent_impresion>"],
        ["<sent_si>"],
        ["<sent_mientras>"],
        ["<sent_para>"],
        ["<sent_pillemos>"],
        ["<sent_retornar>"],
        ["<sent_llamada>"]
    ],

    # Declaración / asignación
    "<sent_declaracion>": [["KW_DECLARACION", "<tipo_opcional>", "IDENTIFICADOR", "OP_ASIGNACION", "<expresion>"]],
    "<tipo_opcional>": [["<tipo>"], []],
    "<sent_lectura>": [["KW_LECTURA", "PAR_ABRE", "IDENTIFICADOR", "PAR_CIERRA"]],
    "<sent_impresion>": [["KW_IMPRESION", "PAR_ABRE", "<expresion>", "PAR_CIERRA"]],
    "<sent_retornar>": [["KW_RETORNAR", "<expresion>"]],

    # Llamada a función usada como sentencia
    "<sent_llamada>": [["IDENTIFICADOR", "PAR_ABRE", "<argumentos>", "PAR_CIERRA"]],

    # Condicional
    "<sent_si>": [["KW_SI", "<expresion>", "KW_ENTONCES", "<bloque>", "<rama_sino>", "KW_FIN_SI"]],
    "<rama_sino>": [["KW_SINO", "<bloque>"], []],

    # Repetición por condición (while)
    "<sent_mientras>": [["KW_MIENTRAS", "<expresion>", "KW_HACER", "<bloque>", "KW_FIN_MIENTRAS"]],

    # Repetición con variable de control (for)
    "<sent_para>": [["KW_PARA", "IDENTIFICADOR", "KW_DESDE", "<expresion>", "KW_HASTA", "<expresion>", "<paso_opcional>", "KW_HACER", "<bloque>", "KW_FIN_PARA"]],
    "<paso_opcional>": [["KW_PASO", "<expresion>"], []],

    # Calce de patrones (case)
    "<sent_pillemos>": [["KW_PILLEMOS", "<expresion>", "LLAVE_ABRE", "<lista_casos>", "LLAVE_CIERRA"]],
    "<lista_casos>": [["<caso>", "<lista_casos_resto>"]],
    "<lista_casos_resto>": [["<caso>", "<lista_casos_resto>"], []],
    "<caso>": [["<patron>", "KW_FLECHA", "<cuerpo_caso>"]],
    "<cuerpo_caso>": [["LLAVE_ABRE", "<bloque>", "LLAVE_CIERRA"], ["<sentencia>"]],
    "<patron>": [["NUM_ENTERO"], ["NUM_REAL"], ["CADENA_LITERAL"], ["LIT_VERDADERO"], ["LIT_FALSO"], ["IDENTIFICADOR"], ["COMODIN"]],

    # Expresiones LL1 (Niveles de precedencia)
    "<expresion>": [["<expr_o>"]],
    "<expr_o>": [["<expr_y>", "<expr_o_p>"]],
    "<expr_o_p>": [["OP_O", "<expr_y>", "<expr_o_p>"], []],
    "<expr_y>": [["<expr_igualdad>", "<expr_y_p>"]],
    "<expr_y_p>": [["OP_Y", "<expr_igualdad>", "<expr_y_p>"], []],
    "<expr_igualdad>": [["<expr_relacional>", "<expr_igualdad_p>"]],
    "<expr_igualdad_p>": [["OP_IGUAL", "<expr_relacional>", "<expr_igualdad_p>"], ["OP_DISTINTO", "<expr_relacional>", "<expr_igualdad_p>"], []],
    "<expr_relacional>": [["<expr_concat>", "<expr_relacional_p>"]],
    "<expr_relacional_p>": [["OP_MAYOR", "<expr_concat>", "<expr_relacional_p>"], ["OP_MENOR", "<expr_concat>", "<expr_relacional_p>"], ["OP_MAYOR_IGUAL", "<expr_concat>", "<expr_relacional_p>"], ["OP_MENOR_IGUAL", "<expr_concat>", "<expr_relacional_p>"], []],
    "<expr_concat>": [["<expr_aditiva>", "<expr_concat_p>"]],
    "<expr_concat_p>": [["OP_CONCAT", "<expr_aditiva>", "<expr_concat_p>"], []],
    "<expr_aditiva>": [["<expr_multiplicativa>", "<expr_aditiva_p>"]],
    "<expr_aditiva_p>": [["OP_SUMA", "<expr_multiplicativa>", "<expr_aditiva_p>"], ["OP_RESTA", "<expr_multiplicativa>", "<expr_aditiva_p>"], []],
    "<expr_multiplicativa>": [["<expr_potencia>", "<expr_multiplicativa_p>"]],
    "<expr_multiplicativa_p>": [["OP_MULT", "<expr_potencia>", "<expr_multiplicativa_p>"], ["OP_DIV", "<expr_potencia>", "<expr_multiplicativa_p>"], ["OP_MODULO", "<expr_potencia>", "<expr_multiplicativa_p>"], []],
    "<expr_potencia>": [["<expr_unaria>", "<expr_potencia_p>"]],
    "<expr_potencia_p>": [["OP_POTENCIA", "<expr_potencia>"], []],
    "<expr_unaria>": [["OP_NO", "<expr_unaria>"], ["OP_RESTA", "<expr_unaria>"], ["<expr_primaria>"]],

    "<expr_primaria>": [["PAR_ABRE", "<expresion>", "PAR_CIERRA"], ["NUM_ENTERO"], ["NUM_REAL"], ["CADENA_LITERAL"], ["LIT_VERDADERO"], ["LIT_FALSO"], ["IDENTIFICADOR", "<sufijo_id>"]],
    "<sufijo_id>": [["PAR_ABRE", "<argumentos>", "PAR_CIERRA"], ["ε"]],

    "<argumentos>": [["<arg_lista>"], ["ε"]],
    "<arg_lista>": [["<expresion>", "<arg_resto>"]],
    "<arg_resto>": [["COMA", "<expresion>", "<arg_resto>"], ["ε"]],
}


# =============================================================================
# AST Node Classes
# =============================================================================

@dataclass
class NodoAST:
    """Nodo del Árbol de Sintaxis Abstracta (AST)."""
    tipo: str                    # Tipo de nodo (ej: '<sentencia>', 'NUM_ENTERO', etc.)
    valor: Optional[str] = None  # Valor del token (para terminales)
    hijos: List['NodoAST'] = field(default_factory=list)
    token_original: Optional[Any] = None  # Token original del lexer (para terminales)
    
    def agregar_hijo(self, hijo: 'NodoAST') -> None:
        """Agrega un hijo al nodo."""
        self.hijos.append(hijo)
    
    def a_dict(self, _depth=0) -> dict:
        """Convierte el nodo a diccionario para serialización/visualización."""
        if _depth > 100:
            return {'tipo': self.tipo, 'valor': self.valor, 'hijos': ['<max_depth>']}
        return {
            'tipo': self.tipo,
            'valor': self.valor,
            'hijos': [h.a_dict(_depth + 1) for h in self.hijos]
        }
    
    def __str__(self) -> str:
        if self.valor is not None:
            return f"{self.tipo}({self.valor})"
        return self.tipo


def _rhs_legible(simbolos):
    """Parte derecha de una producción para mostrar en la traza.

    Las producciones ε se guardan como lista vacía (para que el reduce pase 0
    símbolos); aquí se muestran como 'ε' y el resto como 'A B C'.
    """
    return " ".join(simbolos) if simbolos else "ε"


# =============================================================================
# Tabla ACTION Construction
# =============================================================================

def _construir_tabla_action_estados(lalr_states, goto_by_nt, terminal_transitions, primeros, siguientes, gramatica, terminals):
    """
    Construye la tabla ACTION indexada por ESTADO (no por no-terminal).
    
    Args:
        lalr_states: lista de conjuntos de items LALR(1) por estado
        goto_by_nt: dict {no-terminal: {estado_origen: estado_destino}}
        terminal_transitions: dict {estado: {terminal: estado_destino}} - transiciones SHIFT para terminales
        primeros: dict {no-terminal: set(terminales)}
        siguientes: dict {no-terminal: set(terminales)}
        gramatica: dict {no-terminal: [producciones]}
        terminals: set de terminales
        
    Returns:
        action_table: dict {estado: {terminal: accion}}
        prod_list: lista de (no-terminal, produccion) para reduce
    """
    # Obtener non-terminales
    non_terminals = set(gramatica.keys())
    all_terminals = set(terminals)
    
    # Construir lista de producciones para reduce
    prod_list = []
    prod_to_num = {}
    for nt in sorted(gramatica.keys()):
        for prod in gramatica[nt]:
            # Normalizar producciones ε a tupla vacía
            prod_tuple = tuple(prod) if prod and prod != ['ε'] else ()
            prod_list.append((nt, prod_tuple))
    for i, (nt, p) in enumerate(prod_list):
        prod_to_num[(nt, p)] = i + 1
    
    # Inicializar tabla ACTION por estado
    action_table = {state_idx: {} for state_idx in range(len(lalr_states))}
    
    # Para cada estado, determinar acciones
    for state_idx, state in enumerate(lalr_states):
        # 1. SHIFT actions: usar terminal_transitions del generador
        # terminal_transitions ya contiene correctamente las transiciones SHIFT
        # calculadas directamente de los items del estado (símbolo en posición del punto)
        if state_idx in terminal_transitions:
            for term, target_state in terminal_transitions[state_idx].items():
                if term in all_terminals:
                    action_table[state_idx][term] = f"s{target_state}"
        
        # 2. REDUCE actions: items con punto al final
        for nt, rhs, dot, la in state:
            if dot == len(rhs):
                # Producción completada
                prod_key = (nt, tuple(rhs))
                if prod_key in prod_to_num:
                    prod_num = prod_to_num[prod_key]
                    # La lookahead válida es la que tiene el item (la) o los SIGUIENTES
                    lookaheads = set()
                    if la is not None and la != "ε" and la != "" and la in all_terminals:
                        lookaheads.add(la)
                    # También agregar SIGUIENTES del no-terminal
                    if nt in siguientes:
                        lookaheads.update(siguientes[nt] & all_terminals)
                    
                    for lookahead in lookaheads:
                        if lookahead not in action_table[state_idx]:
                            action_table[state_idx][lookahead] = f"r{prod_num}"
        
        # 3. ACCEPT action: en cualquier estado donde <programa> esté completado con lookahead $
        # El accept tiene prioridad sobre reduce cuando <programa> está completado
        for nt, rhs, dot, la in state:
            if nt == '<programa>' and dot == len(rhs) and la == '$':
                action_table[state_idx]['$'] = 'acc'
                break
        
        # Asegurar que FIN_ARCHIVO también acepte (token de fin de archivo del lexer)
        if '$' in action_table[state_idx] and action_table[state_idx]['$'] == 'acc':
            action_table[state_idx]['FIN_ARCHIVO'] = 'acc'

    return action_table, prod_list


class ParserLALR1:
    """Parser ascendente LALR(1) con traza paso a paso."""
    
    def __init__(self, action_table, goto_table, non_terminals, terminals, grammar, lalr_states_items=None):
        """Inicializa el parser.
        
        Args:
            action_table: dict {estado: {terminal: accion}}  # INDEXADO POR ESTADO
            goto_table: dict {no-terminal: {estado: estado_siguiente}}
            non_terminals: set o lista de non-terminales
            terminals: set o lista de terminals (incluyendo '$')
            grammar: dict {no-terminal: [lista de producciones]}
            lalr_states_items: lista de conjuntos de items LALR(1) por estado (opcional, para GOTO espontáneo)
        """
        self.action_table = action_table
        self.goto_table = goto_table
        self.non_terminals = non_terminals if isinstance(non_terminals, set) else set(non_terminals)
        self.terminals = terminals if isinstance(terminals, set) else set(terminals)
        self.grammar = grammar
        self.lalr_states_items = lalr_states_items
        
        # Contador de producciones para r{k}
        self.prod_count = 0
        self.productions_list = []
        self._construir_producciones()
    
    def _construir_producciones(self):
        """Construye la lista de producciones desde la gramática."""
        self.productions_list = []
        # Usar el mismo orden que _construir_tabla_action_estados: sorted non-terminals
        for nt in sorted(self.non_terminals):
            if nt in self.grammar:
                for prod in self.grammar[nt]:
                    # Normalizar producciones ε a lista vacía (pop 0 símbolos)
                    if not prod or prod == ['ε']:
                        self.productions_list.append((nt, []))
                    else:
                        self.productions_list.append((nt, prod))
        self.prod_count = len(self.productions_list)
    
    def _obtener_accion(self, estado_actual, simbolo_entrada):
        """Obtiene la acción de la tabla ACTION indexada por estado.
        
        Args:
            estado_actual: estado actual (entero, desde la cima de la pila)
            simbolo_entrada: símbolo de entrada actual
            
        Returns:
            str o None:acción ('s{n}', 'r{k}', 'acc') o None si no definida
        """
        # Helper to get string representation of token type
        def _get_str(tok):
            if hasattr(tok, 'tipo') and hasattr(tok.tipo, 'name'):
                return tok.tipo.name
            return str(tok)
        
        entry_str = _get_str(simbolo_entrada)
        
        # Tratar FIN_ARCHIVO como $ (EOF)
        if entry_str == 'FIN_ARCHIVO':
            entry_str = '$'
        
        # Buscar en la tabla ACTION por estado actual
        if estado_actual in self.action_table:
            if entry_str in self.action_table[estado_actual]:
                return self.action_table[estado_actual][entry_str]
        
        return None


    def parse_con_pasos(self, tokens):
        """Ejecuta el análisis LALR(1) y retorna la traza paso a paso con AST.
        
        Args:
            tokens: lista de tokens (tuples o objetos Token) a analizar
            
        Returns:
            tuple: (ast, traza, es_valido, errores)
            - ast: nodo raíz del árbol sintáctico (NodoAST)
            - traza: lista de dicts con {Paso, Accion, Pila, Entrada, Arbol}
            - es_valido: bool indicando si el análisis fue exitoso
            - errores: lista de mensajes de error
        """
        # Estado inicial: estado 0 con símbolo de entrada $ en la pila
        # La pila contiene tuplas (simbolo, estado)
        pila = [('$', 0)]  # (símbolo, estado)
        entrada = list(tokens) + ['$']  # Agregar EOF al final
        
        # Pila de nodos AST paralela a la pila de estados
        # Cada entrada en pila_nodos corresponde a una entrada en pila
        pila_nodos = [None]  # None para el símbolo inicial $
        
        traza = []

        def _registrar(datos):
            """Adjunta un paso a la traza guardando también los estados de la pila.

            Cada par de la pila es (símbolo, estado): el estado que se registra
            junto a un símbolo es el resultado de haber consumido ese símbolo.
            """
            datos['Estados'] = [s[1] for s in pila]
            traza.append(datos)

        paso = 0
        errores = []
        ast = None
        
        while True:
            paso += 1
            
            # Safety limit to prevent infinite loops
            if paso > 200:
                error_msg = f"Paso {paso}: Límite de pasos excedido (posible bucle infinito)"
                errores.append(error_msg)
                break
            
            # Obtener estado actual (de la cima de la pila) y símbolo de entrada
            estado_actual = pila[-1][1] if pila else 0
            simbolo_entrada = entrada[0] if entrada else None
            
            # Determinar acción usando el estado actual
            accion = self._obtener_accion(estado_actual, simbolo_entrada)
            
            # Para mensajes de error, obtener representación legible del tope de pila
            simbolo_pila = pila[-1][0] if pila else None
            
            if accion is None:
                error_msg = f"Paso {paso}: No hay definida acción para Estado[{estado_actual}] / Entrada[{simbolo_entrada}]"
                errores.append(error_msg)
                _registrar({
                    'Paso': paso,
                    'Acción': 'error',
                    'Pila': [s[0] for s in pila],
                    'Entrada': [e.tipo if hasattr(e, 'tipo') else str(e) for e in entrada],
                    'Arbol': pila_nodos[-1].a_dict() if pila_nodos[-1] else None,
                })
                break
            
            # Parsear la acción
            if accion.startswith('s'):
                # Shift: mover símbolo a pila y ir al nuevo estado
                numero_estado = accion[1:]  # Quitar 's'
                simbolo = simbolo_entrada
                pila.append((simbolo, int(numero_estado)))
                entrada = entrada[1:]  # Consumir entrada
                
                # Crear nodo hoja para el terminal
                if hasattr(simbolo, 'tipo') and hasattr(simbolo.tipo, 'name'):
                    nodo_hoja = NodoAST(
                        tipo=simbolo.tipo.name,
                        valor=simbolo.lexema if hasattr(simbolo, 'lexema') else str(simbolo),
                        token_original=simbolo
                    )
                else:
                    nodo_hoja = NodoAST(
                        tipo=str(simbolo),
                        valor=str(simbolo)
                    )
                pila_nodos.append(nodo_hoja)
                
                _registrar({
                    'Paso': paso,
                    'Acción': f'shift a estado {numero_estado}',
                    'Pila': [s[0] for s in pila],
                    'Entrada': [e.tipo if hasattr(e, 'tipo') else str(e) for e in entrada],
                    'Arbol': pila_nodos[-1].a_dict(),
                })
                
            elif accion.startswith('r'):
                # Reduce: reducir por producción r{k}
                prod_num = int(accion[1:])  # Número de producción (1-indexado)
                if prod_num < 1 or prod_num > self.prod_count:
                    error_msg = f"Paso {paso}: Número de producción inválido {prod_num}"
                    errores.append(error_msg)
                    _registrar({
                        'Paso': paso,
                        'Acción': f'reduce ERROR (prod {prod_num})',
                        'Pila': [s[0] for s in pila],
                        'Entrada': [e.tipo if hasattr(e, 'tipo') else str(e) for e in entrada],
                        'Arbol': pila_nodos[-1].a_dict() if pila_nodos[-1] else None,
                    })
                    break
                
                nt, prod_simbolos = self.productions_list[prod_num - 1]
                
                # Pop len(prod_simbolos) elementos de la pila (cada tupla es (símbolo, estado))
                # La pila tiene el $ inicial en índice 0, luego pares (símbolo, estado)
                símbolos_a_pop = len(prod_simbolos)
                
                # Necesitamos al menos símbolos_a_pop + 1 entradas (incluyendo $ inicial)
                if len(pila) <= símbolos_a_pop:
                    error_msg = f"Paso {paso}: Pila insuficiente para reduce (necesario {símbolos_a_pop + 1}, tiene {len(pila)})"
                    errores.append(error_msg)
                    _registrar({
                        'Paso': paso,
                        'Acción': f'reduce ERROR (pila corta)',
                        'Pila': [s[0] for s in pila],
                        'Entrada': [e.tipo if hasattr(e, 'tipo') else str(e) for e in entrada],
                        'Arbol': pila_nodos[-1].a_dict() if pila_nodos[-1] else None,
                    })
                    break
                
                # Quitar símbolos y estados de la pila, y recopilar nodos AST
                nodos_hijos = []
                for _ in range(símbolos_a_pop):
                    if pila:
                        pila.pop()  # Quitar (simbolo, estado)
                        if pila_nodos:
                            nodos_hijos.append(pila_nodos.pop())
                
                # Los nodos se extrajeron en orden inverso (LIFO), revertir para orden correcto
                nodos_hijos.reverse()
                
                # Obtener el estado actual después de hacer pop
                if pila:
                    estado_actual = pila[-1][1]
                else:
                    error_msg = f"Paso {paso}: Pila vacía después de reduce"
                    errores.append(error_msg)
                    _registrar({
                        'Paso': paso,
                        'Acción': f'reduce {prod_num}: {nt} → {_rhs_legible(prod_simbolos)}',
                        'Pila': [s[0] for s in pila],
                        'Entrada': [e.tipo if hasattr(e, 'tipo') else str(e) for e in entrada],
                        'Arbol': pila_nodos[-1].a_dict() if pila_nodos[-1] else None,
                    })
                    break
                
                # Caso especial: si reducimos el símbolo inicial <programa>, aceptamos directamente
                if nt == '<programa>':
                    # Crear nodo raíz del AST
                    nodo_raiz = NodoAST(tipo=nt)
                    for hijo in nodos_hijos:
                        nodo_raiz.agregar_hijo(hijo)
                    
                    _registrar({
                        'Paso': paso,
                        'Acción': f'reduce {prod_num}: {nt} → {_rhs_legible(prod_simbolos)} (accept)',
                        'Pila': [s[0] for s in pila] + [nt],
                        'Entrada': [e.tipo if hasattr(e, 'tipo') else str(e) for e in entrada],
                        'Arbol': nodo_raiz.a_dict(),
                    })
                    return nodo_raiz, traza, True, []
                
                # Buscar GOTO desde el estado actual con el non-terminal
                if nt in self.goto_table and estado_actual in self.goto_table[nt]:
                    nuevo_estado = self.goto_table[nt][estado_actual]
                else:
                    # No usar fallback incorrecto - reportar error si no se encuentra GOTO
                    error_msg = f"Paso {paso}: No se encontró GOTO para {nt} desde estado {estado_actual}"
                    errores.append(error_msg)
                    _registrar({
                        'Paso': paso,
                        'Acción': f'reduce {prod_num}: {nt} → {_rhs_legible(prod_simbolos)}',
                        'Pila': [s[0] for s in pila],
                        'Entrada': [e.tipo if hasattr(e, 'tipo') else str(e) for e in entrada],
                        'Arbol': pila_nodos[-1].a_dict() if pila_nodos[-1] else None,
                    })
                    break
                
                # Crear nodo padre para el non-terminal
                nodo_padre = NodoAST(tipo=nt)
                for hijo in nodos_hijos:
                    nodo_padre.agregar_hijo(hijo)
                
                # Push el non-terminal y el nuevo estado, junto con el nodo AST
                pila.append((nt, nuevo_estado))
                pila_nodos.append(nodo_padre)
                
                _registrar({
                    'Paso': paso,
                    'Acción': f'reduce {prod_num}: {nt} → {_rhs_legible(prod_simbolos)}',
                    'Pila': [s[0] for s in pila],
                    'Entrada': [e.tipo if hasattr(e, 'tipo') else str(e) for e in entrada],
                    'Arbol': nodo_padre.a_dict(),
                })
                
            elif accion == 'acc':
                # Accept: análisis completado exitosamente
                # Buscar el nodo raíz <programa> en la pila de nodos
                ast = None
                for nodo in reversed(pila_nodos):
                    if nodo and nodo.tipo == '<programa>':
                        ast = nodo
                        break
                if ast is None:
                    # Fallback: buscar cualquier non-terminal que parezca raíz
                    for nodo in reversed(pila_nodos):
                        if nodo and nodo.tipo.startswith('<') and nodo.tipo.endswith('>'):
                            ast = nodo
                            break
                if ast is None and len(pila_nodos) > 1:
                    # Fallback: construir un árbol simple desde la pila
                    # Los nodos en pila_nodos (excluyendo None inicial) son los tokens desplazados
                    # Intentamos agruparlos de forma simple
                    nodos_validos = [n for n in pila_nodos if n is not None]
                    if nodos_validos:
                        ast = NodoAST(tipo='<programa>', hijos=nodos_validos)
                    else:
                        ast = NodoAST(tipo='programa', hijos=[])
                else:
                    ast = NodoAST(tipo='programa', hijos=[])
                
                _registrar({
                    'Paso': paso,
                    'Acción': 'accept',
                    'Pila': [s[0] for s in pila],
                    'Entrada': [],
                    'Arbol': ast.a_dict() if ast else None,
                })
                traza_final = traza
                return ast, traza_final, True, []
                
            else:
                error_msg = f"Paso {paso}: Acción desconocida '{accion}'"
                errores.append(error_msg)
                _registrar({
                    'Paso': paso,
                    'Acción': accion,
                    'Pila': [s[0] for s in pila],
                    'Entrada': [e.tipo if hasattr(e, 'tipo') else str(e) for e in entrada],
                    'Arbol': pila_nodos[-1].a_dict() if pila_nodos[-1] else None,
                })
                break
        
        # Si salimos del bucle sin accept
        traza_final = traza
        return ast, traza_final, False, errores


def generar_parser_lalr1(resultado_lalr1):
    """Factory function para crear un parser LALR(1) desde los resultados del generador.
    
    Args:
        resultado_lalr1: dict resultado de generar_tabla_lalr1_completa()
        
    Returns:
        ParserLALR1: instancia configurada o None si no hay datos
    """
    # Usar la gramática local en lugar de importar de tabla_ll1
    from parser_lalr import GRAMATICA_BNF
    
    # Calcular terminales de la gramática
    non_terminals = set(GRAMATICA_BNF.keys())
    grammar_terminals = set()
    for prods in GRAMATICA_BNF.values():
        for prod in prods:
            for sym in prod:
                if sym not in non_terminals and sym != 'ε' and sym != '':
                    grammar_terminals.add(sym)
    grammar_terminals.add('$')
    grammar_terminals.add('FIN_ARCHIVO')
    
    # Usar el nuevo constructor de tabla ACTION indexada por estado
    action_table, prod_list = _construir_tabla_action_estados(
        resultado_lalr1['lalr_states_items'],
        resultado_lalr1['goto_by_nt'],
        resultado_lalr1['terminal_transitions'],  # Nuevo: transiciones de terminales
        resultado_lalr1['primeros'],
        resultado_lalr1['siguientes'],
        GRAMATICA_BNF,
        terminals=grammar_terminals
    )
    
    # Terminales incluyen '$' y todos los símbolos terminales
    terminals = grammar_terminals
    
    if not action_table or not resultado_lalr1.get('goto_by_nt'):
        return None
    
    parser = ParserLALR1(
        action_table=action_table,
        goto_table=resultado_lalr1['goto_by_nt'],
        non_terminals=non_terminals,
        terminals=terminals,
        grammar=GRAMATICA_BNF,
        lalr_states_items=resultado_lalr1['lalr_states_items']
    )
    return parser


# =============================================================================
#  TABLAS ACTION / GOTO REALES (indexadas por ESTADO)
# =============================================================================

def construir_dataframes_lalr1(resultado_lalr1):
    """Construye las tablas ACTION y GOTO reales de LALR(1), indexadas por ESTADO.

    A diferencia de las matrices LL(1) (que se indexan por no-terminal), las
    tablas de un analizador ascendente LR se indexan por estado:

        ACTION[estado][terminal]  = s{n} (shift) | r{k} (reduce) | acc | vacío
        GOTO[estado][no_terminal] = estado_destino | vacío

    Args:
        resultado_lalr1: dict devuelto por generar_tabla_lalr1_completa()

    Returns:
        dict con:
        - action_df:    DataFrame (filas = estados, columnas = terminales)
        - goto_df:      DataFrame (filas = estados, columnas = no-terminales)
        - producciones: lista [(no_terminal, simbolos_derecha)] donde la
                        posición k-1 es la producción numerada r{k}
        - parser:       instancia ParserLALR1 usada (para inspección por estado)
    """
    import pandas as pd
    # Celda vacía de GOTO: se usa pd.NA (y no "") para que la columna se infiera
    # como entero anulable y Arrow/Streamlit no reciba tipos mezclados.
    VACIO_GOTO = pd.NA

    parser = generar_parser_lalr1(resultado_lalr1)
    if parser is None:
        vacio = pd.DataFrame()
        return {"action_df": vacio, "goto_df": vacio,
                "producciones": [], "parser": None}

    n_estados = len(resultado_lalr1["lalr_states_items"])

    # Alfabeto terminal: todos los terminales de la gramática más cualquier
    # terminal que aparezca realmente en la tabla ACTION.
    terminales = set()
    for prods in GRAMATICA_BNF.values():
        for prod in prods:
            for sym in prod:
                if sym not in GRAMATICA_BNF and sym not in ("ε", ""):
                    terminales.add(sym)
    terminales.add("$")
    for acciones in parser.action_table.values():
        terminales.update(acciones)
    terminales_ordenados = sorted(terminales)

    no_terminales = sorted(GRAMATICA_BNF.keys())

    filas_action, filas_goto = [], []
    for estado in range(n_estados):
        acciones = parser.action_table.get(estado, {})
        filas_action.append(
            {"Estado": estado, **{t: acciones.get(t, "") for t in terminales_ordenados}}
        )
        filas_goto.append(
            {"Estado": estado,
             **{nt: parser.goto_table.get(nt, {}).get(estado, VACIO_GOTO)
                for nt in no_terminales}}
        )

    action_df = pd.DataFrame(filas_action).set_index("Estado")
    goto_df = pd.DataFrame(filas_goto).set_index("Estado")
    # Enteros anulables explícitos (pd.NA) para que las celdas vacías se
    # rendericen en blanco sin arrastrar la columna a tipo object.
    goto_df = goto_df.astype("Int64")

    # Lista de producciones: r{k} corresponde a la posición k-1 de esta lista.
    producciones = [(nt, list(prod)) for nt, prod in parser.productions_list]

    return {
        "action_df": action_df,
        "goto_df": goto_df,
        "producciones": producciones,
        "parser": parser,
    }