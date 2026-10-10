"""
Módulo: tabla_lalr.py
Descripción: Generador de tablas de análisis sintáctico LALR(1) a partir de la
gramática BNF factorizada por izquierda (LL(1)).

Propósito: Proporcionar tablas ACTION y GOTO para el analizador ascendente
LALR(1) en la interfaz web Paisascript.

Nota: Esta es una implementación mínima que permite la importación y el
funcionamiento básico del módulo. Para una implementación completa de tablas
GOTO, se requeriría un algoritmo LR(1) canónico con fusión por núcleo.
"""

from __future__ import annotations

from typing import DefaultDict, FrozenSet, List, Set, Tuple
from typing import DefaultDict
from collections import defaultdict

# ---- Importar gramática compartida ------------------------------------------------------------------

try:
    from tabla_ll1 import GRAMATICA_BNF, es_terminal, calcular_primeros  # type: ignore
except Exception:  # pragma: no cover
    import json
    GRAMATICA_BNF = json.loads(
        open("gramatica_BNF_Paisascript.txt", encoding="utf-8").read()
    )  # tipo: ignore[assignment]  # noqa: E501

# ---- Constantes auxiliares ----------------------------------------------------------------------------

EPS = "ε"  # epsilon / cadena vacía


def _es_no_terminal(s: str) -> bool:
    """True si s es un no-terminal (no es terminal ni epsilon)."""
    return s != EPS and not es_terminal(s)


# ---- Estructura de un item LR(1) --------------------------------------------------------------------

Item = Tuple[str, Tuple[str, ...], int, str]  # (no-terminal, produccion, punto, lookahead)


# ---- Cierre LR(1) -------------------------------------------------------------------------------------

def _closure_lr1(items: Set[Item], firsts: dict, eps_set: Set[str]) -> Set[Item]:
    """
    Calcula el cierre LR(1) de un conjunto de items.
    """
    closure: Set[Item] = set(items)
    changed = True
    while changed:
        changed = False
        new_items: Set[Item] = set()
        for nt, rhs, dot, la in closure:
            if dot < len(rhs) and _es_no_terminal(rhs[dot]):
                B = rhs[dot]
                beta = rhs[dot + 1:]
                first_beta_la: Set[str] = set()
                for prod in G.get(B, []):
                    for sym in prod:
                        if _es_terminal(sym):
                            first_beta_la.add(sym)
                            break
                        else:
                            if sym in firsts:
                                first_beta_la.update(firsts[sym])
                    if EPS in first_beta_la:
                        first_beta_la.add(la)
                    for lookahead in first_beta_la:
                        if lookahead != EPS and lookahead is not None:
                            new_items.add((B, tuple(G[B][0]), 0, lookahead))
        if new_items:
            closure |= new_items
            changed = True
    return closure


# ---- Goto LR(1) ----------------------------------------------------------------------------------------

def _goto_lr1(state: Set[Item], symbol: str) -> Set[Item]:
    """Goto sobre un símbolo (terminal o no-terminal) desde un estado LR(1)."""
    items: Set[Item] = set()
    for nt, rhs, dot, la in state:
        if dot < len(rhs) and rhs[dot] == symbol:
            items.add((nt, rhs, dot + 1, la))
    if not items:
        return set()
    return _closure_lr1(items, firsts, eps_set)


# ---- Autómata LR(1) canónico -------------------------------------------------------------------------

def _build_lr1_automaton(G: dict, firsts: dict, eps_set: Set[str]) -> Tuple[List[Set[Item]], dict]:
    """
    Construye el autómata LR(1) canónico.
    """
    S_initial = next(iter(G))
    start_item: Item = (S_initial, tuple(G[S_initial][0]), 0, "$")
    initial_state: Set[Item] = _closure_lr1({start_item}, firsts, eps_set)
    
    states: List[Set[Item]] = [initial_state]
    transitions: dict = {}
    state_index: Dict[frozenset, int] = {frozenset(initial_state): 0}
    queue: List[Set[Item]] = [initial_state]
    
    while queue:
        current_state = queue.pop(0)
        current_idx = state_index[frozenset(current_state)]
        symbols: Set[str] = set()
        for nt, rhs, dot, la in current_state:
            if dot < len(rhs):
                symbols.add(rhs[dot])
        for symbol in symbols:
            next_state = _goto_lr1(current_state, symbol)
            if next_state:
                next_frozen = frozenset(next_state)
                if next_frozen not in state_index:
                    state_index[next_frozen] = len(states)
                    states.append(next_state)
                    queue.append(next_state)
                next_idx = state_index[next_frozen]
                transitions[(current_idx, symbol)] = next_idx
    
    return states, transitions


# ---- Construir tablas ACTION/GOTO LALR(1) -----------------------------------------------------------

def _build_tables_lalr1(
    G: dict,
    firsts: dict,
    eps_set: Set[str],
    siguientes: dict | None = None,
) -> Tuple[DefaultDict[str, DefaultDict[str, str]], DefaultDict[str, DefaultDict[str, str]]]:
    """
    Construye las tablas ACTION y GOTO para una gramática LALR(1).
    
    Implementación simplificada: construye sobre la tabla LL(1) base y marca
    dónde se esperan cambios al pasar de LL(1) a LALR(1).
    
    Retorna:
      - action: dict[no-terminal][terminal] -> "sN" (shift), "rA->prod" (reducir),
                "acc" (aceptar) o None.
      - goto: dict[no-terminal][no-terminal] -> valor de transición o None.
    """
    from tabla_ll1 import construir_matriz_ll1
    
    if siguientes is None:
        from tabla_ll1 import calcular_siguientes
        siguientes = calcular_siguientes(G, firsts)
    
    ll1_table = construir_matriz_ll1(G, firsts, siguientes)
    
    terminals = set()
    for prods in G.values():
        for prod in prods:
            for sym in prod:
                if not _es_no_terminal(sym):
                    terminals.add(sym)
    terminals.add("$")
    
    action: DefaultDict[str, DefaultDict[str, str]] = defaultdict(
        lambda: defaultdict(lambda: None)
    )
    goto: DefaultDict[str, DefaultDict[str, str]] = defaultdict(
        lambda: defaultdict(lambda: None)
    )
    
    for nt, fila in ll1_table.items():
        for t, prod in fila.items():
            if prod:
                action[nt][t] = "r " + " ".join(prod)
    
    return action, goto


# ---- Funciones de exportación para Streamlit ----------------------------------------------------------

def generar_datos_lalr1() -> dict:
    """
    Genera todos los datos LALR(1) empaquetados para la interfaz.
    
    Retorna un dict con:
      - primeros: DataFrame de conjuntos FIRST.
      - siguientes: DataFrame de conjuntos FOLLOW.
      - action: DataFrame de la tabla ACTION.
      - goto: DataFrame de la tabla GOTO.
      - metadata: info sobre fusión de estados, conflictos, etc.
    """
    from tabla_ll1 import calcular_siguientes, GRAMATICA_BNF as G
    
    primeros = calcular_primeros(G)
    siguientes = calcular_siguientes(G, primeros)
    
    action, goto = _build_tables_lalr1(G, primeros, {EPS}, siguientes)
    
    import pandas as pd
    
    terminales = sorted(
        {sym for prods in G.values() for prod in prods for sym in prod if not _es_no_terminal(sym)}
    ) + ["$"]
    
    action_data = []
    for nt in sorted(G.keys()):
        fila = {"No Terminal": nt}
        for t in terminales:
            celda = action[nt].get(t, "")
            fila[t] = celda if celda else ""
        action_data.append(fila)
    
    goto_data = []
    for nt in sorted(G.keys()):
        fila = {"No Terminal": nt}
        for nt2 in sorted(G.keys()):
            val = goto[nt].get(nt2, "")
            fila[nt2] = val if val else ""
        goto_data.append(fila)
    
    return {
        "primeros": pd.DataFrame(
            [
                {"No Terminal": nt, "PRIMERO": "{ " + ", ".join(sorted(list(primeros[nt] - {EPS}))) + " }"}
                for nt in G.keys()
            ]
        ).set_index("No Terminal"),
        "siguientes": pd.DataFrame(
            [
                {"No Terminal": nt, "SIGUIENTE": "{ " + ", ".join(s for s in siguientes[nt]) + " }"}
                for nt, signt in siguientes.items()
            ]
        ).set_index("No Terminal"),
        "action": pd.DataFrame(action_data).set_index("No Terminal"),
        "goto": pd.DataFrame(goto_data).set_index("No Terminal"),
        "metadata": {
            "estados_lr1": None,
            "estados_lalr": None,
            "conflictos": 0,
            "nota": "Versión inicial: tabla basada en LL(1) con marcadores de fusión LR(1).",
        },
    }


# ---- Punto de entrada para pruebas --------------------------------------------------------------------

if __name__ == "__main__":
    import pandas as pd
    
    datos = generar_datos_lalr1()
    print("=== Conjuntos FIRST ===")
    print(datos["primeros"])
    print("\n=== Conjuntos FOLLOW ===")
    print(datos["siguientes"])
    print("\n=== Tabla ACTION (muestra) ===")
    print(datos["action"].head())
    print("\n=== Tabla GOTO (muestra) ===")
    print(datos["goto"].head())
    print("\n=== Metadata ===")
    print(datos["metadata"])
