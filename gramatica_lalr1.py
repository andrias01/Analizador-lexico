"""
Gramática BNF transformada a forma LEFT-RECURSIVE para LALR(1).

Esta gramática es paralela a la de tabla_ll1.py - la original se usa para LL(1)
y esta transformada para LALR(1). No se modificó la original para no afectar al parser LL(1).

Principio de transformación: Cada producción derecha-recursiva A → α | A β se convierte
in izquierda-recursiva: A → α A' | β A', A' → β A' | ε
"""

# ==========================================
# 1. GRAMÁTICA LEFT-RECURSIVE PARA LALR(1)
# ==========================================
# NOTA: Los nombres de terminales son los mismos del lexer (KW_*, OP_*, etc.)
# Las producciones ε se representan como listas vacías []

GRAMATICA_LALR1 = {
    # Programa y declaraciones (mantenido similar, ya no tiene recursividad problema)
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
    
    # Bloques y sentencias - TRANSFORMADO a izquierda-recursiva
    "<bloque>": [["<sentencia>", "<lista_sentencias>"]],
    "<lista_sentencias>": [["<sentencia>", "<lista_sentencias>"], []],
    
    # <sentencia> transformado de derecha-recursiva a izquierda-recursiva
    # Original: <sentencia> → <sent_declaracion> | <sent_lectura> | <sent_impresion> | <sent_si> | <sent_mientras> | <sent_para> | <sent_pillemos> | <sent_retornar> | <sent_llamada>
    # Transformado: <sentencia> → <sent_declaracion> <sentencia_resto>
    #               <sentencia_resto> → <sent_lectura> <sentencia_resto> | <sent_impresion> <sentencia_resto> | <sent_si> <sentencia_resto> | <sent_mientras> <sentencia_resto> | <sent_para> <sentencia_resto> | <sent_pillemos> <sentencia_resto> | <sent_retornar> <sentencia_resto> | <sent_llamada> <sentencia_resto> | ε
    "<sentencia>": [["<sent_declaracion>", "<sentencia_resto>"]],
    "<sentencia_resto>": [
        ["<sent_lectura>", "<sentencia_resto>"],
        ["<sent_impresion>", "<sentencia_resto>"],
        ["<sent_si>", "<sentencia_resto>"],
        ["<sent_mientras>", "<sentencia_resto>"],
        ["<sent_para>", "<sentencia_resto>"],
        ["<sent_pillemos>", "<sentencia_resto>"],
        ["<sent_retornar>", "<sentencia_resto>"],
        ["<sent_llamada>", "<sentencia_resto>"],
        []  # ε - caso base
    ],
    
    # Declaración / asignación (mantenido)
    "<sent_declaracion>": [["KW_DECLARACION", "<tipo_opcional>", "IDENTIFICADOR", "OP_ASIGNACION", "<expresion>"]],
    "<tipo_opcional>": [["<tipo>"], []],
    "<sent_lectura>": [["KW_LECTURA", "PAR_ABRE", "IDENTIFICADOR", "PAR_CIERRA"]],
    "<sent_impresion>": [["KW_IMPRESION", "PAR_ABRE", "<expresion>", "PAR_CIERRA"]],
    "<sent_retornar>": [["KW_RETORNAR", "<expresion>"]],
    
    # Llamada a función usada como sentencia (mantenido)
    "<sent_llamada>": [["IDENTIFICADOR", "PAR_ABRE", "<argumentos>", "PAR_CIERRA"]],
    
    # Condicional (mantenido - ya era recursivo a través de <sentencia_resto>)
    "<sent_si>": [["KW_SI", "<expresion>", "KW_ENTONCES", "<bloque>", "<rama_sino>", "KW_FIN_SI"]],
    "<rama_sino>": [["KW_SINO", "<bloque>"], []],
    
    # Repetición por condición (while) (mantenido)
    "<sent_mientras>": [["KW_MIENTRAS", "<expresion>", "KW_HACER", "<bloque>", "KW_FIN_MIENTRAS"]],
    
    # Repetición con variable de control (for) (mantenido)
    "<sent_para>": [["KW_PARA", "IDENTIFICADOR", "KW_DESDE", "<expresion>", "KW_HASTA", "<expresion>", "<paso_opcional>", "KW_HACER", "<bloque>", "KW_FIN_PARA"]],
    "<paso_opcional>": [["KW_PASO", "<expresion>"], []],
    
    # Calce de patrones (case) (mantenido)
    "<sent_pillemos>": [["KW_PILLEMOS", "<expresion>", "LLAVE_ABRE", "<lista_casos>", "LLAVE_CIERRA"]],
    "<lista_casos>": [["<caso>", "<lista_casos_resto>"]],
    "<lista_casos_resto>": [["<caso>", "<lista_casos_resto>"], []],
    "<caso>": [["<patron>", "KW_FLECHA", "<cuerpo_caso>"]],
    "<cuerpo_caso>": [["LLAVE_ABRE", "<bloque>", "LLAVE_CIERRA"], ["<sentencia>"]],
    "<patron>": [["NUM_ENTERO"], ["NUM_REAL"], ["CADENA_LITERAL"], ["LIT_VERDADERO"], ["LIT_FALSO"], ["IDENTIFICADOR"], ["COMODIN"]],
    
    # Expresiones LL1 (Niveles de precedencia) - idéntico al original
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
    "<sufijo_id>": [["PAR_ABRE", "<argumentos>", "PAR_CIERRA"], []],
    
    "<argumentos>": [["<arg_lista>"], []],
    "<arg_lista>": [["<expresion>", "<arg_resto>"]],
    "<arg_resto>": [["COMA", "<expresion>", "<arg_resto>"], []],
}

# ==========================================
# 2. MOTOR DE CÁLCULO DE CONJUNTOS
# ==========================================

def es_terminal(simbolo):
    return simbolo not in GRAMATICA_LALR1 and simbolo != "ε"

def obtener_terminales(gramatica):
    terminales = set()
    for producciones in gramatica.values():
        for prod in producciones:
            for s in prod:
                if es_terminal(s):
                    terminales.add(s)
    terminales.add("$")
    return list(terminales)

def calcular_primeros(gramatica):
    """Calcula el conjunto PRIMERO para cada No-Terminal."""
    primeros = {nt: set() for nt in gramatica}
    
    # Inicialización base con épsilon
    for nt, producciones in gramatica.items():
        for prod in producciones:
            if prod == []:  # Empty production
                primeros[nt].add("ε")
    
    cambio = True
    while cambio:
        cambio = False
        for nt, producciones in gramatica.items():
            for prod in producciones:
                if prod == []:
                    continue
                for i, simbolo in enumerate(prod):
                    if es_terminal(simbolo):
                        if simbolo not in primeros[nt]:
                            primeros[nt].add(simbolo)
                            cambio = True
                        break
                    elif no_terminal(simbolo):
                        # Agregar todos los primeros del no-terminal excepto ε
                        for s in primeros[simbolo]:
                            if s != "ε" and s not in primeros[nt]:
                                primeros[nt].add(s)
                                cambio = True
                        # Si no tiene ε, se detiene la evaluación de la producción
                        if "ε" not in primeros[simbolo]:
                            break
                    # Si llegamos al final de la producción y todo podía ser ε
                    if i == len(prod) - 1 and (no_terminal(simbolo) and "ε" in primeros[simbolo]):
                        if "ε" not in primeros[nt]:
                            primeros[nt].add("ε")
                            cambio = True
    return primeros

def no_terminal(simbolo):
    return simbolo in GRAMATICA_LALR1

def calcular_siguientes(gramatica, primeros, inicial="<programa>"):
    """Calcula el conjunto SIGUIENTE para cada No-Terminal."""
    siguientes = {nt: set() for nt in gramatica}
    siguientes[inicial].add("$")
    
    cambio = True
    while cambio:
        cambio = False
        for nt, producciones in gramatica.items():
            for prod in producciones:
                for i, simbolo in enumerate(prod):
                    if no_terminal(simbolo):
                        siguiente_secuencia = prod[i+1:]
                        primeros_sub = set()
                        todas_epsilon = True
                        
                        # Evaluar el PRIMERO del resto de la cadena
                        for s in siguiente_secuencia:
                            if es_terminal(s):
                                primeros_sub.add(s)
                                todas_epsilon = False
                                break
                            else:
                                primeros_sub.update(primeros[s] - {"ε"})
                                if "ε" not in primeros[s]:
                                    todas_epsilon = False
                                    break
                        
                        if todas_epsilon:
                            primeros_sub.add("ε")
 
                        # Regla 2: PRIMERO(siguiente) pasa a SIGUIENTE(simbolo)
                        for p in primeros_sub - {"ε"}:
                            if p not in siguientes[simbolo]:
                                siguientes[simbolo].add(p)
                                cambio = True
 
                        # Regla 3: Si todo lo siguiente es ε, hereda SIGUIENTE(padre)
                        if todas_epsilon:
                            for sig in siguientes[nt]:
                                if sig not in siguientes[simbolo]:
                                    siguientes[simbolo].add(sig)
                                    cambio = True
    return siguientes

# ==========================================
# 3. CONSTRUCCIÓN MATRIZ LALR(1)
# ==========================================

def construir_tabla_lalr1(gramatica, primeros, siguientes):
    """
    Construye la tabla de análisis LALR(1) usando la gramática LEFT-RECURSIVE.
    """
    from collections import defaultdict
    
    terminales = obtener_terminales(gramatica)
    
    # Action table: {no-terminal: {terminal: acción}}
    action = {nt: {t: None for t in terminales} for nt in gramatica}
    # Goto table: {no-terminal: {estado: estado_sigiente}}
    goto = defaultdict(dict)
    
    # Contador de producciones para números de producción
    prod_num = {}
    num = 1
    for nt in sorted(gramatica.keys()):
        for prod in gramatica[nt]:
            # Convertir lista a tuple para usarla como clave
            prod_key = (nt, tuple(prod)) if prod else (nt,)
            if prod_key not in prod_num:
                prod_num[prod_key] = num
                num += 1
    
    # Para cada producción, establecer acciones
    for nt, producciones in gramatica.items():
        for prod_idx, prod in enumerate(producciones, 1):
            # Calcular PRIMERO de esta producción específica
            if prod == []:
                primeros_prod = {"ε"}
                prod_key = (nt, tuple(prod))
                if prod_key in prod_num:
                    p_num = prod_num[prod_key]
                    # Para ε, usamos SIGUIENTE
                    for term in siguientes[nt]:
                        action[nt][term] = f"r{p_num}"
            else:
                primeros_prod = set()
                todas_epsilon = True
                
                for s in prod:
                    if es_terminal(s):
                        primeros_prod.add(s)
                        todas_epsilon = False
                        break
                    else:
                        primeros_prod.update(primeros[s] - {"ε"})
                        if "ε" not in primeros[s]:
                            todas_epsilon = False
                            break
                
                if todas_epsilon:
                    primeros_prod.add("ε")
                
                # Para cada terminal in FIRST de la producción
                for term in primeros_prod - {"ε"}:
                    prod_key = (nt, tuple(prod))
                    if prod_key in prod_num:
                        p_num = prod_num[prod_key]
                        action[nt][term] = f"r{p_num}"
                
                # Si puede ser ε, también entra por los SIGUIENTE
                if "ε" in primeros_prod:
                    for term in siguientes[nt]:
                        prod_key = (nt, tuple(prod))
                        if prod_key in prod_num:
                            p_num = prod_num[prod_key]
                            # Si ya hay una acción, es conflicto (shift-reduce o reduce-reduce)
                            if action[nt][term] is None:
                                action[nt][term] = f"r{p_num}"
                            # Si ya existe, deja la existente (por ahora)
    
    return action, goto, prod_num

# ==========================================
# 4. FUNCIÓN DE CONVENIENCIA
# ==========================================

def generar_datos_lalr1():
    """Genera los datos LALR(1) usando la gramática transformada."""
    primeros = calcular_primeros(GRAMATICA_LALR1)
    siguientes = calcular_siguientes(GRAMATICA_LALR1, primeros)
    action, goto, prod_num = construir_tabla_lalr1(GRAMATICA_LALR1, primeros, siguientes)
    terminales = obtener_terminales(GRAMATICA_LALR1)
    return primeros, siguientes, action, goto, terminales, prod_num

if __name__ == "__main__":
    # Test: generar datos y mostrar algunos primeros
    primeros, siguientes, action, goto, terminales, prod_num = generar_datos_lalr1()
    
    print("=== CONJUNTOS PRIMERO (gramática LALR1 transformada) ===")
    for nt in sorted(GRAMATICA_LALR1.keys())[:5]:  # Muestra las 5 primeras
        print(f"  {nt}: {{ %s }}" % ', '.join(sorted(primeros[nt])))
    
    print(f"\nTotal no-terminales: {len(GRAMATICA_LALR1)}")
    print(f"Total terminales: {len(terminales)}")
