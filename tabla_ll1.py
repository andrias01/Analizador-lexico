"""
Módulo: tabla_ll1.py
Descripción: Generador dinámico de Conjuntos PRIMERO, SIGUIENTE y 
Tabla de Análisis Sintáctico LL(1) M[A, a] según la gramática BNF.
"""
import pandas as pd

# ==========================================
# 1. GRAMÁTICA BNF (FACTORIZADA PARA LL1)
# ==========================================
# Las claves son los No-Terminales. 
# Los valores son listas de producciones (cada producción es una lista de símbolos).
GRAMATICA_BNF = {
    "<programa>": [["<lista_declaraciones>"]],
    "<lista_declaraciones>": [["<declaracion>", "<lista_declaraciones>"], ["ε"]],
    "<declaracion>": [["<def_funcion>"], ["<sentencia>"]],
    
    "<def_funcion>": [["KW_FUNCION", "IDENTIFICADOR", "PAR_ABRE", "<parametros>", "PAR_CIERRA", "<tipo_retorno>", "KW_HACER", "<bloque>", "KW_FIN_FUNCION"]],
    "<tipo_retorno>": [["KW_FLECHA", "<tipo>"], ["ε"]],
    "<parametros>": [["<param_lista>"], ["ε"]],
    "<param_lista>": [["<tipo>", "IDENTIFICADOR", "<param_resto>"]],
    "<param_resto>": [["COMA", "<tipo>", "IDENTIFICADOR", "<param_resto>"], ["ε"]],
    "<tipo>": [["KW_TIPO_ENTERO"], ["KW_TIPO_REAL"], ["KW_TIPO_CADENA"], ["KW_TIPO_BOOLEANO"]],
    
    "<bloque>": [["<sentencia>", "<lista_sentencias>"]],
    "<lista_sentencias>": [["<sentencia>", "<lista_sentencias>"], ["ε"]],
    
    "<sentencia>": [
        ["<sent_declaracion>"], ["<sent_lectura>"], ["<sent_impresion>"],
        ["<sent_si>"], ["<sent_mientras>"], ["<sent_para>"],
        ["<sent_pillemos>"], ["<sent_retornar>"], ["<sent_asignacion_o_llamada>"]
    ],
    
    "<sent_declaracion>": [["KW_DECLARACION", "<tipo_opcional>", "IDENTIFICADOR", "OP_ASIGNACION", "<expresion>"]],
    "<tipo_opcional>": [["<tipo>"], ["ε"]],
    "<sent_lectura>": [["KW_LECTURA", "PAR_ABRE", "IDENTIFICADOR", "PAR_CIERRA"]],
    "<sent_impresion>": [["KW_IMPRESION", "PAR_ABRE", "<expresion>", "PAR_CIERRA"]],
    "<sent_retornar>": [["KW_RETORNAR", "<expresion>"]],
    
    # Factorización izquierda para asignación vs llamada
    "<sent_asignacion_o_llamada>": [["IDENTIFICADOR", "<resto_asignacion_llamada>"]],
    "<resto_asignacion_llamada>": [["PAR_ABRE", "<argumentos>", "PAR_CIERRA"], ["OP_ASIGNACION", "<expresion>"]],
    
    "<sent_si>": [["KW_SI", "<expresion>", "KW_ENTONCES", "<bloque>", "<rama_sino>", "KW_FIN_SI"]],
    "<rama_sino>": [["KW_SINO", "<bloque>"], ["ε"]],
    "<sent_mientras>": [["KW_MIENTRAS", "<expresion>", "KW_HACER", "<bloque>", "KW_FIN_MIENTRAS"]],
    "<sent_para>": [["KW_PARA", "IDENTIFICADOR", "KW_DESDE", "<expresion>", "KW_HASTA", "<expresion>", "<paso_opcional>", "KW_HACER", "<bloque>", "KW_FIN_PARA"]],
    "<paso_opcional>": [["KW_PASO", "<expresion>"], ["ε"]],
    
    "<sent_pillemos>": [["KW_PILLEMOS", "<expresion>", "LLAVE_ABRE", "<lista_casos>", "LLAVE_CIERRA"]],
    "<lista_casos>": [["<caso>", "<lista_casos_resto>"]],
    "<lista_casos_resto>": [["<caso>", "<lista_casos_resto>"], ["ε"]],
    "<caso>": [["<patron>", "KW_FLECHA", "<cuerpo_caso>"]],
    "<cuerpo_caso>": [["LLAVE_ABRE", "<bloque>", "LLAVE_CIERRA"], ["<sentencia>"]],
    "<patron>": [["NUM_ENTERO"], ["NUM_REAL"], ["CADENA_LITERAL"], ["LIT_VERDADERO"], ["LIT_FALSO"], ["IDENTIFICADOR"], ["COMODIN"]],
    
    # Expresiones LL1 (Niveles de precedencia)
    "<expresion>": [["<expr_o>"]],
    "<expr_o>": [["<expr_y>", "<expr_o_p>"]],
    "<expr_o_p>": [["OP_O", "<expr_y>", "<expr_o_p>"], ["ε"]],
    "<expr_y>": [["<expr_igualdad>", "<expr_y_p>"]],
    "<expr_y_p>": [["OP_Y", "<expr_igualdad>", "<expr_y_p>"], ["ε"]],
    "<expr_igualdad>": [["<expr_relacional>", "<expr_igualdad_p>"]],
    "<expr_igualdad_p>": [["OP_IGUAL", "<expr_relacional>", "<expr_igualdad_p>"], ["OP_DISTINTO", "<expr_relacional>", "<expr_igualdad_p>"], ["ε"]],
    "<expr_relacional>": [["<expr_concat>", "<expr_relacional_p>"]],
    "<expr_relacional_p>": [["OP_MAYOR", "<expr_concat>", "<expr_relacional_p>"], ["OP_MENOR", "<expr_concat>", "<expr_relacional_p>"], ["OP_MAYOR_IGUAL", "<expr_concat>", "<expr_relacional_p>"], ["OP_MENOR_IGUAL", "<expr_concat>", "<expr_relacional_p>"], ["ε"]],
    "<expr_concat>": [["<expr_aditiva>", "<expr_concat_p>"]],
    "<expr_concat_p>": [["OP_CONCAT", "<expr_aditiva>", "<expr_concat_p>"], ["ε"]],
    "<expr_aditiva>": [["<expr_multiplicativa>", "<expr_aditiva_p>"]],
    "<expr_aditiva_p>": [["OP_SUMA", "<expr_multiplicativa>", "<expr_aditiva_p>"], ["OP_RESTA", "<expr_multiplicativa>", "<expr_aditiva_p>"], ["ε"]],
    "<expr_multiplicativa>": [["<expr_potencia>", "<expr_multiplicativa_p>"]],
    "<expr_multiplicativa_p>": [["OP_MULT", "<expr_potencia>", "<expr_multiplicativa_p>"], ["OP_DIV", "<expr_potencia>", "<expr_multiplicativa_p>"], ["OP_MODULO", "<expr_potencia>", "<expr_multiplicativa_p>"], ["ε"]],
    "<expr_potencia>": [["<expr_unaria>", "<expr_potencia_p>"]],
    "<expr_potencia_p>": [["OP_POTENCIA", "<expr_potencia>"], ["ε"]],
    "<expr_unaria>": [["OP_NO", "<expr_unaria>"], ["OP_RESTA", "<expr_unaria>"], ["<expr_primaria>"]],
    
    "<expr_primaria>": [["PAR_ABRE", "<expresion>", "PAR_CIERRA"], ["NUM_ENTERO"], ["NUM_REAL"], ["CADENA_LITERAL"], ["LIT_VERDADERO"], ["LIT_FALSO"], ["IDENTIFICADOR", "<sufijo_id>"]],
    "<sufijo_id>": [["PAR_ABRE", "<argumentos>", "PAR_CIERRA"], ["ε"]],
    
    "<argumentos>": [["<arg_lista>"], ["ε"]],
    "<arg_lista>": [["<expresion>", "<arg_resto>"]],
    "<arg_resto>": [["COMA", "<expresion>", "<arg_resto>"], ["ε"]]
}

# ==========================================
# 2. MOTOR DE CÁLCULO DE CONJUNTOS
# ==========================================

def es_terminal(simbolo):
    return simbolo not in GRAMATICA_BNF and simbolo != "ε"

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
            if prod[0] == "ε":
                primeros[nt].add("ε")

    cambio = True
    while cambio:
        cambio = False
        for nt, producciones in gramatica.items():
            for prod in producciones:
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
    return simbolo in GRAMATICA_BNF

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
# 3. CONSTRUCCIÓN MATRIZ M[A, a]
# ==========================================

def construir_matriz_ll1(gramatica, primeros, siguientes):
    """Construye la matriz de análisis predictivo M[A, a]."""
    terminales = obtener_terminales(gramatica)
    tabla = {nt: {t: None for t in terminales} for nt in gramatica}

    for nt, producciones in gramatica.items():
        for prod in producciones:
            primeros_prod = set()
            todas_epsilon = True
            
            # Calcular PRIMERO de la producción específica
            for s in prod:
                if s == "ε":
                    primeros_prod.add("ε")
                    continue
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

            # Mapear a la matriz
            for term in primeros_prod - {"ε"}:
                # En caso de conflicto LL(1), la tabla guardaría el último encontrado
                # pero con esta gramática factorizada no debería haber.
                tabla[nt][term] = prod

            # Si la producción puede derivar en ε, usamos los SIGUIENTES
            if "ε" in primeros_prod:
                for term in siguientes[nt]:
                    tabla[nt][term] = prod
                    
    return tabla

# ==========================================
# 4. EXPORTACIÓN PARA INTERFAZ Y CONSOLA
# ==========================================

def generar_datos_completos_ll1():
    """Genera todo el motor empaquetado para el parser_ll1 y Streamlit."""
    primeros = calcular_primeros(GRAMATICA_BNF)
    siguientes = calcular_siguientes(GRAMATICA_BNF, primeros)
    tabla = construir_matriz_ll1(GRAMATICA_BNF, primeros, siguientes)
    terminales = obtener_terminales(GRAMATICA_BNF)
    return primeros, siguientes, tabla, terminales

def obtener_dataframe_tabla():
    """Exporta la tabla LL(1) como DataFrame para mostrarla en app.py."""
    _, _, tabla, terminales = generar_datos_completos_ll1()
    
    # Filtrar terminales que no tienen ninguna celda asignada para limpiar la vista
    columnas_utiles = []
    for t in terminales:
        en_uso = any(tabla[nt][t] is not None for nt in tabla)
        if en_uso:
            columnas_utiles.append(t)
            
    df_data = []
    for nt in GRAMATICA_BNF.keys():
        fila = {"No Terminal": nt}
        for t in columnas_utiles:
            prod = tabla[nt][t]
            fila[t] = " ".join(prod) if prod else ""
        df_data.append(fila)
        
    return pd.DataFrame(df_data).set_index("No Terminal")

def obtener_dataframes_conjuntos():
    """Exporta Primeros y Siguientes como DataFrames."""
    primeros, siguientes, _, _ = generar_datos_completos_ll1()
    
    df_data = []
    for nt in GRAMATICA_BNF.keys():
        df_data.append({
            "No Terminal": nt,
            "PRIMERO": "{ " + ", ".join(primeros[nt]) + " }",
            "SIGUIENTE": "{ " + ", ".join(siguientes[nt]) + " }"
        })
    return pd.DataFrame(df_data).set_index("No Terminal")

if __name__ == "__main__":
    df_tabla = obtener_dataframe_tabla()
    df_conjuntos = obtener_dataframes_conjuntos()
    
    print("\n\033[1;36m=== CONJUNTOS PRIMERO Y SIGUIENTE ===\033[0m")
    print(df_conjuntos.to_string())
    
    print("\n\033[1;33m=== TABLA DE ANÁLISIS LL(1) M[A, a] (Muestra) ===\033[0m")
    print(df_tabla.iloc[:, :5].to_string()) # Muestra parcial para no desbordar consola
