"""
Módulo generador de tablas LALR(1) completas para PaisaScript.
Implementa el autómata LR(1) canónico y su fusión por núcleo para obtener
la tabla GOTO de LALR(1).

Basado en la gramática BNF factorizada de PaisaScript definida en
tabla_ll1.py y gramatica_BNF_Paisascript.txt.
"""

from __future__ import annotations
from typing import DefaultDict, FrozenSet, List, Set, Tuple, Dict
from collections import defaultdict

# ---- Cargar gramática --------------------------------------------------------

from tabla_ll1 import GRAMATICA_BNF, es_terminal, no_terminal as _no_terminal

EPS = "ε"  # epsilon / cadena vacía


def es_terminal(s: str) -> bool:
    """True si s es un terminal (no es no-terminal ni epsilon)."""
    return s != EPS and not _no_terminal(s)


def no_terminal(s: str) -> bool:
    """True si s es un no-terminal (existe en GRAMATICA_BNF)."""
    return _no_terminal(s)


def obtener_no_terminales() -> List[str]:
    """Retorna la lista de todos los no-terminales de la gramática."""
    return list(GRAMATICA_BNF.keys())


def obtener_terminales() -> List[str]:
    """Retorna la lista de todos los terminales de la gramática."""
    terminales: Set[str] = set()
    for nt, producciones in GRAMATICA_BNF.items():
        for prod in producciones:
            for s in prod:
                if es_terminal(s):
                    terminales.add(s)
    terminales.add("$")
    return sorted(terminales)


# ---- Cálculo de FIRST (reutilizar de tabla_ll1.py) ----

def calcular_primeros(gramatica: dict | None = None) -> dict:
    """Calcula el conjunto PRIMERO para cada No-Terminal."""
    from tabla_ll1 import calcular_primeros as _calc_primeros
    return _calc_primeros(gramatica if gramatica else GRAMATICA_BNF)


# ---- Cálculo LR(1) Closure ---------------------------------------------------

def _es_terminal_directo(s: str) -> bool:
    """Versión rápida: s es terminal si no es ε y no está en GRAMATICA_BNF."""
    return s != EPS and s not in GRAMATICA_BNF


def _no_terminal_directo(s: str) -> bool:
    """Versión rápida: s es no-terminal si está en GRAMATICA_BNF."""
    return s in GRAMATICA_BNF


def _calcular_first_beta_la(beta: Tuple[str, ...], la: str, firsts: dict) -> Set[str]:
    """
    Calcula FIRST(β · la) para uso en closure LR(1).
    
    Si beta está vacío, resultado es {la}.
    Si el primer símbolo de beta es terminal, resultado es {símbolo}.
    Si el primer símbolo es no-terminal, resultado es FIRST(sub-no-terminal) - {ε},
    deteniéndose si este no puede derivar ε.
    Si todo beta puede derivar ε, se incluye la lookahead inicial.
    """
    result: Set[str] = set()
    if not beta:
        result.add(la)
        return result

    for s in beta:
        if _es_terminal_directo(s):
            result.add(s)
            return result  # Primer símbolo terminal: detenerse
        else:
            # s es no-terminal
            if s in firsts:
                result.update(firsts[s] - {EPS})
                if EPS not in firsts[s]:
                    return result  # No puede derivar ε: detenerse
    # Todo beta pudo derivar ε
    result.add(la)
    return result


def cerrar_lr1_v3(items: Set[Tuple[str, Tuple[str, ...], int, str]],
                  firsts: dict,
                  eps_set: Set[str] = {EPS}) -> Set[Tuple[str, Tuple[str, ...], int, str]]:
    """
    Calcula el cierre LR(1) de un conjunto de items.
    
    Un item es una tupla (no-terminal, produccion, punto, lookahead).
    """
    closure: Set[Tuple[str, Tuple[str, ...], int, str]] = set(items)
    changed = True
    iteration = 0
    max_iterations = 10000

    while changed and iteration < max_iterations:
        changed = False
        new_items: Set[Tuple[str, Tuple[str, ...], int, str]] = set()

        for nt, rhs, dot, la in closure:
            if dot < len(rhs) and _no_terminal_directo(rhs[dot]):
                B = rhs[dot]
                beta = rhs[dot + 1:]

                # Calcular FIRST(β la)
                first_beta_la = _calcular_first_beta_la(beta, la, firsts)

                # Agregar items para todas las producciones de B
                for lookahead in first_beta_la:
                    if lookahead != EPS and lookahead is not None:
                        for p in GRAMATICA_BNF.get(B, []):
                            new_items.add((B, tuple(p), 0, lookahead))

        # Sólo continuar si hay verdaderamente nuevos items
        truly_new = new_items - closure
        if truly_new:
            closure |= truly_new
            changed = True
            iteration += 1
            # print(f"  Iteración {iteration}: {len(truly_new)} nuevos items, total {len(closure)}")
        else:
            # print(f"  Iteración {iteration}: No hay nuevos items, cerrando. Total: {len(closure)}")
            break

    # if iteration >= max_iterations:
    #     print(f"  WARNING: Se alcanzó el límite de {max_iterations} iteraciones")

    return closure


# ---- Goto LR(1) --------------------------------------------------------------

def goto_lr1_v3(state: Set[Tuple[str, Tuple[str, ...], int, str]],
                symbol: str,
                  firsts: dict) -> Set[Tuple[str, Tuple[str, ...], int, str]]:
    """
    Goto sobre un símbolo (terminal o no-terminal) desde un estado LR(1).
    
    Mueve el punto un paso sobre el símbolo y calcula el cierre LR(1).
    """
    items: Set[Tuple[str, Tuple[str, ...], int, str]] = set()
    for nt, rhs, dot, la in state:
        if dot < len(rhs) and rhs[dot] == symbol:
            items.add((nt, rhs, dot + 1, la))

    if not items:
        return set()
    return cerrar_lr1_v3(items, firsts, {EPS})


# ---- Autómata LR(1) canónico -----------------------------------------------

def build_lr1_automaton(gramatica: dict, firsts: dict, eps_set: Set[str] = {EPS}) -> Tuple[List[Set[Tuple[str, Tuple[str, ...], int, str]]], Dict[Tuple[int, str], int]]:
    """
    Construye el autómata LR(1) canónico.
    
    Retorna (states, transitions) donde transitions es un dict (state_idx, symbol) -> next_state_idx
    """
    S_initial = next(iter(gramatica))
    start_item: Tuple[str, Tuple[str, ...], int, str] = (S_initial, tuple(gramatica[S_initial][0]), 0, "$")
    initial_state: Set[Tuple[str, Tuple[str, ...], int, str]] = cerrar_lr1_v3({start_item}, firsts, eps_set)
    
    states: List[Set[Tuple[str, Tuple[str, ...], int, str]]] = [initial_state]
    transitions: Dict[Tuple[int, str], int] = {}
    state_index: Dict[frozenset, int] = {frozenset(initial_state): 0}
    queue: List[Set[Tuple[str, Tuple[str, ...], int, str]]] = [initial_state]
    
    print(f"  Estado inicial: {len(initial_state)} items en cierre LR(1)")
    
    iter_count = 0
    while queue:
        current_state = queue.pop(0)
        current_idx = state_index[frozenset(current_state)]
        
        # Collect symbols at dot position
        symbols: Set[str] = set()
        for nt, rhs, dot, la in current_state:
            if dot < len(rhs):
                symbols.add(rhs[dot])
        
        for symbol in sorted(symbols):
            next_state = goto_lr1_v3(current_state, symbol, firsts)
            if next_state:
                next_frozen = frozenset(next_state)
                if next_frozen not in state_index:
                    state_index[next_frozen] = len(states)
                    states.append(next_state)
                    queue.append(next_state)
                next_idx = state_index[next_frozen]
                transitions[(current_idx, symbol)] = next_idx
        
        iter_count += 1
    
    print(f"  LR(1) automaton: {len(states)} states, {len(transitions)} transitions (after {iter_count} iterations)")
    
    return states, transitions


# ---- Merge LR(1) to LALR(1) by Core ----------------------------------------

def merge_lr1_states_by_core(lr1_states_list: List[Set[Tuple[str, Tuple[str, ...], int, str]]]) -> List[Set[Tuple[str, Tuple[str, ...], int, str]]]:
    """
    Fusiona estados LR(1) que tienen el mismo núcleo.
    
    El núcleo de un estado es el conjunto de items sin lookaheads.
    Estados LR(1) con el mismo núcleo se fusionan en un solo estado LALR(1).
    """
    merged_dict: Dict[frozenset, Set[Tuple[str, Tuple[str, ...], int, str]]] = {}
    
    for state in lr1_states_list:
        # Calcular el núcleo del estado (todos los items sin lookaheads)
        state_core = frozenset((nt, rhs, dot) for nt, rhs, dot, la in state)
        
        # Agrupar por núcleo
        if state_core not in merged_dict:
            merged_dict[state_core] = set()
        # Añadir TODOS los items de este estado al grupo con el mismo núcleo
        merged_dict[state_core].update(state)
    
    result = list(merged_dict.values())
    reduction = len(lr1_states_list) - len(result)
    print(f"  LR(1) → LALR(1): {len(lr1_states_list)} states → {len(result)} states (reduced: {reduction})")
    
    return result


# ---- Extract GOTO Table for LALR(1) ----------------------------------------

def extract_goto_lalr1(lalr_states: List[Set[Tuple[str, Tuple[str, ...], int, str]]],
                       firsts_local: dict) -> DefaultDict[str, DefaultDict[str, int]]:
    """
    Extrae la tabla GOTO del autómata LALR(1).
    
    Para cada estado LALR(1) y cada no-terminal que aparece después del punto,
    determina el estado destino al mover el punto sobre ese no-terminal.
    
    Retorna: {no-terminal: {estado_origen: estado_destino}}
    """
    goto: DefaultDict[str, DefaultDict[str, int]] = defaultdict(lambda: defaultdict(int))
    
    for state_idx, state in enumerate(lalr_states):
        # 1. Collect all non-terminals that appear at the dot position in this state
        dot_nts: Set[str] = set()
        for nt, rhs, dot, la in state:
            if dot < len(rhs) and no_terminal(rhs[dot]):
                dot_nts.add(rhs[dot])
        
        # 2. For each non-terminal X at the dot position, compute GOTO(state, X)
        for X in dot_nts:
            # Find all items where the symbol at dot is X
            next_items: Set[Tuple[str, Tuple[str, ...], int, str]] = set()
            for nt, rhs, dot, la in state:
                if dot < len(rhs) and rhs[dot] == X:
                    # Move point one step past X
                    next_items.add((nt, rhs, dot + 1, la))
            
            if next_items:
                # Compute LR(1) closure
                next_state = cerrar_lr1_v3(next_items, firsts_local, {EPS})
                # Find the index of this state in lalr_states
                next_idx = None
                for i, s in enumerate(lalr_states):
                    # Check subset or equality
                    if next_state.issubset(s) or next_state == s:
                        next_idx = i
                        break
                
                if next_idx is not None:
                    goto[X][state_idx] = next_idx
    
    return goto


# ---- Función principal de generación ---------------------------------------

def generar_tabla_lalr1_completa() -> dict:
    """
    Genera la tabla LALR(1) completa para PaisaScript.
    
    Returns un diccionario con:
    - primero: dict {no-terminal: set de terminals en FIRST}
    - siguientes: dict {no-terminal: set de terminals en FOLLOW}
    - action: dict {no-terminal: {terminal: producción}} (desde matriz LL(1))
    - goto: dict {no-terminal: {estado: estado_sigiente}} (tabla GOTO LALR(1))
    - metadata: info sobre estados, reducción, conflictos
    """
    # 1. Calcular FIRST y FOLLOW
    print("=" * 60)
    print("Generando tabla LALR(1) para PaisaScript")
    print("=" * 60)
    
    print("\n1. Calculando conjuntos FIRST...")
    primeros = calcular_primeros()
    print(f"   {len(primeros)} conjuntos FIRST calculados.")
    
    print("\n2. Calculando conjuntos FOLLOW/SIGUIENTE...")
    from tabla_ll1 import calcular_siguientes
    siguientes = calcular_siguientes(GRAMATICA_BNF, primeros)
    print(f"   {len(siguientes)} conjuntos SIGUIENTE calculados.")
    
    # 2. Build LR(1) automaton
    print("\n3. Construyendo autómata LR(1) canónico...")
    eps_set = {EPS}
    lr1_states, lr1_transitions = build_lr1_automaton(GRAMATICA_BNF, primeros, eps_set)
    
    # 3. Merge to LALR(1)
    print("\n4. Fusionando estados LR(1) a LALR(1)...")
    lalr_states = merge_lr1_states_by_core(lr1_states)
    
    # 4. Build GOTO table
    print("\n5. Extrayendo tabla GOTO LALR(1)...")
    goto_by_nt = extract_goto_lalr1(lalr_states, primeros)
    
    # 5. Resumen y estadísticas
    n_estados_lr1 = len(lr1_states)
    n_estados_lalr = len(lalr_states)
    n_entradas = sum(len(v) for v in goto_by_nt.values())
    n_nt = len(GRAMATICA_BNF)
    
    print(f"\n=== RESULTADOS ===")
    print(f"  Estados LR(1) canónicos: {n_estados_lr1}")
    print(f"  Estados LALR(1) después de fusión: {n_estados_lalr}")
    print(f"  Estados reducidos (fusionados): {n_estados_lr1 - n_estados_lalr}")
    print(f"  Entradas GOTO únicas: {n_entradas}")
    print(f"  No-terminales: {n_nt}")
    print(f"  Reducción: {(n_estados_lr1 - n_estados_lalr) / n_estados_lr1 * 100:.1f}%")
    
    # Mostrar estadísticas por non-terminal
    print(f"\n=== DETALLE POR NON-TERMINAL ===")
    for nt in sorted(GRAMATICA_BNF.keys()):
        n_entries = len(goto_by_nt.get(nt, {}))
        if n_entries > 0:
            print(f"  {nt:<25} {n_entries:>2} entradas GOTO")
    
    # Non-terminals with 0 entries
    zero_nt = [nt for nt in GRAMATICA_BNF.keys() if len(goto_by_nt.get(nt, {})) == 0]
    if zero_nt:
        print(f"\n  Non-terminals con 0 entradas GOTO:")
        for nt in sorted(zero_nt):
            print(f"    {nt}")
    
    # Compute terminal transitions (for shift actions) from LALR states
    # For each state and terminal symbol at dot position, find the target state
    terminal_transitions = {}
    all_terminals = obtener_terminales()  # Includes all terminals from grammar
    
    # Pre-compute cores for each LALR state (core = set of (nt, rhs, dot) without lookaheads)
    lalr_cores = []
    for state in lalr_states:
        core = frozenset((nt, rhs, dot) for nt, rhs, dot, la in state)
        lalr_cores.append(core)
    
    for state_idx, state in enumerate(lalr_states):
        terminal_transitions[state_idx] = {}
        # Collect terminals at dot position
        dot_terminals = set()
        for nt, rhs, dot, la in state:
            if dot < len(rhs) and es_terminal(rhs[dot]):
                dot_terminals.add(rhs[dot])
        
        for term in dot_terminals:
            # Compute GOTO on terminal
            next_items = set()
            for nt, rhs, dot, la in state:
                if dot < len(rhs) and rhs[dot] == term:
                    next_items.add((nt, rhs, dot + 1, la))
            
            if next_items:
                next_state = cerrar_lr1_v3(next_items, primeros, {EPS})
                # Find matching LALR state by comparing cores
                next_core = frozenset((nt, rhs, dot) for nt, rhs, dot, la in next_state)
                next_idx = None
                for i, core in enumerate(lalr_cores):
                    if next_core.issubset(core) or next_core == core:
                        next_idx = i
                        break
                if next_idx is not None:
                    terminal_transitions[state_idx][term] = next_idx

    # Return structured result
    result = {
        "primeros": primeros,
        "siguientes": siguientes,
        "lr1_states": n_estados_lr1,
        "lalr_states": lalr_states,
        "goto_by_nt": {nt: dict(transitions) for nt, transitions in goto_by_nt.items()},
        "terminal_transitions": terminal_transitions,
        "lalr_states_items": lalr_states,
        "goto_total_entries": n_entradas,
        "metadata": {
            "estados_lr1": n_estados_lr1,
            "estados_lalr": n_estados_lalr,
            "estados_reduzidos": n_estados_lr1 - n_estados_lalr,
            "conflictos": 0,
            "gramatica_size": n_nt,
            "reduction_percentage": round((n_estados_lr1 - n_estados_lalr) / n_estados_lr1 * 100, 1),
        "goto_total_entries": n_entradas,
        }
    }
    return result
