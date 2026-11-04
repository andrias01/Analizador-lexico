# -*- coding: utf-8 -*-
"""
ejemplos.py — Cadenas predefinidas para el analizador lexico de Paisascript.

Cubren distintos programas del lenguaje (requisito 11 del enunciado): E/S,
funciones, condicionales, los TRES tipos de bucle (mientras_que, pa_cada y
repita_pues), calce de patrones, y casos dedicados a los errores lexicos y
semanticos.

Cada entrada es (titulo, descripcion, codigo).
"""

EJEMPLOS = [
    (
        "Entrada, aritmetica y salida",
        "Lectura de consola, precedencia de operadores y concatenacion.",
        '''// Le sube un par de anios a la edad que digite el usuario
escuche_pues(edad)
pille_pues numerito calculo = (edad * 2) + 5
pille_pues cuento mensaje = "El resultado es: " <> calculo
hable_pues(mensaje)''',
    ),
    (
        "Funcion, condicional anidado y retorno",
        "hagale_pues / si_acaso / sino_pues / entregue_pues con anotaciones de tipo.",
        '''hagale_pues clasificar(numerito nota) pa_que_lleve cuento dele_pues
    si_acaso nota >= 45 y_tambien nota <= 50 entonces_pues
        entregue_pues "Sobresaliente, mijo"
    sino_pues
        si_acaso nota >= 30 entonces_pues
            entregue_pues "Pasaste raspando"
        sino_pues
            entregue_pues "Se quemo, parcero"
        asi_quedo
    asi_quedo
ya_quedo

hable_pues(clasificar(47))''',
    ),
    (
        "Bucle mientras_que con acumulador",
        "Se traduce a una funcion recursiva de cola en Gleam.",
        '''// Suma de los primeros n numeros naturales
hagale_pues sumatoria(numerito n) pa_que_lleve numerito dele_pues
    pille_pues numerito acumulado = 0
    pille_pues numerito i = 1
    mientras_que i <= n dele_pues
        pille_pues acumulado = acumulado + i
        pille_pues i = i + 1
    hasta_ahi
    entregue_pues acumulado
ya_quedo

hable_pues(sumatoria(100))''',
    ),
    (
        "Bucle pa_cada con paso, modulo y potencia",
        "Los seis operadores aritmeticos exigidos, incluidos % y **.",
        '''pa_cada k desde 0 hasta 20 de_a 2 dele_pues
    si_acaso k % 3 igualito 0 entonces_pues
        hable_pues("Multiplo de tres: " <> k)
    asi_quedo
listo_pues

pille_pues quebradito radio = 2.5
pille_pues quebradito area = 3.1416 * radio ** 2.0
pille_pues quebradito sobrante = 17.0 - 4.0 / 2.0
hable_pues(area)''',
    ),
    (
        "Bucle repita_pues con condicion al final",
        "El tercer bucle: post-test. El cuerpo corre al menos una vez y hasta_que es la condicion de SALIDA.",
        '''// Pide la clave hasta que acierte o se agoten los tres intentos.
// El cuerpo corre primero y SOLO despues se comprueba la condicion, asi
// que siempre se pide la clave por lo menos una vez.
pille_pues numerito intentos = 0
pille_pues cuento clave = ""
repita_pues
    escuche_pues(clave)
    pille_pues intentos = intentos + 1
    hable_pues("Intento numero " <> intentos)
hasta_que clave igualito "abreme" o_que intentos >= 3

si_acaso clave igualito "abreme" entonces_pues
    hable_pues("Entre pues, mijo")
sino_pues
    hable_pues("Se le acabaron los intentos")
asi_quedo''',
    ),
    (
        "Los tres bucles en un solo programa",
        "mientras_que (pre-test), pa_cada (contador) y repita_pues (post-test). Los tres se traducen a recursion de cola en Gleam.",
        '''hagale_pues demostracion(numerito n) pa_que_lleve numerito dele_pues
    // 1) mientras_que: condicion al principio, puede no entrar nunca
    pille_pues numerito suma = 0
    pille_pues numerito i = 1
    mientras_que i <= n dele_pues
        pille_pues suma = suma + i
        pille_pues i = i + 1
    hasta_ahi

    // 2) pa_cada: contador con limites y paso explicito
    pa_cada k desde 0 hasta 10 de_a 2 dele_pues
        hable_pues("k vale: " <> k)
    listo_pues

    // 3) repita_pues: condicion al final, entra al menos una vez
    pille_pues numerito intentos = 0
    repita_pues
        pille_pues intentos = intentos + 1
        hable_pues("vuelta " <> intentos)
    hasta_que intentos >= 3

    entregue_pues suma
ya_quedo

hable_pues(demostracion(5))''',
    ),
    (
        "Calce de patrones y operadores logicos",
        "pillemos con literales, comodin y bloque; y_tambien / o_que / nanai.",
        '''escuche_pues(resultado)
escuche_pues(edad)
escuche_pues(tiene_permiso)

pillemos resultado {
    10       pa_que_lleve hable_pues("Sacaste diez, que elegancia")
    "error"  pa_que_lleve hable_pues("Algo salio mal, mijo")
    sizas    pa_que_lleve {
                 hable_pues("Todo bien")
                 hable_pues("Todo correcto")
             }
    _        pa_que_lleve hable_pues("No se que paso ahi")
}

pille_pues siono valido = nanai (edad < 18) o_que tiene_permiso
pille_pues siono raro = valido distinto naranjas''',
    ),
    (
        "Programa completo: numeros primos",
        "Todo junto: dos funciones, ambos bucles, condicional y llamadas.",
        '''// Determina si un numero es primo y lista los primos hasta un limite
hagale_pues es_primo(numerito n) pa_que_lleve siono dele_pues
    si_acaso n < 2 entonces_pues
        entregue_pues naranjas
    asi_quedo
    pille_pues numerito d = 2
    mientras_que d * d <= n dele_pues
        si_acaso n % d igualito 0 entonces_pues
            entregue_pues naranjas
        asi_quedo
        pille_pues d = d + 1
    hasta_ahi
    entregue_pues sizas
ya_quedo

hagale_pues listar_primos(numerito limite) dele_pues
    pa_cada n desde 2 hasta limite dele_pues
        si_acaso es_primo(n) entonces_pues
            hable_pues("Primo encontrado: " <> n)
        asi_quedo
    listo_pues
ya_quedo

escuche_pues(tope)
listar_primos(tope)''',
    ),
    (
        "Identificadores con tildes y letra enie",
        "El enunciado (2.1) los exige; Gleam solo acepta ASCII y se transliteran.",
        '''pille_pues numerito años = 30
pille_pues cuento nombre_niño = "Andrés"
pille_pues quebradito camión_peso = 12.75
hable_pues(nombre_niño <> " tiene " <> años)''',
    ),
    (
        "ERRORES LEXICOS deliberados",
        "Cinco errores distintos; el analisis continua y los reporta todos.",
        '''pille_pues x = 5 @ 3
pille_pues Total = 10
pille_pues y = "sin cerrar
pille_pues z = 3.
hable_pues(a $ b)
pille_pues bien = 42''',
    ),
    (
        "ANALISIS SEMANTICO — programa correcto",
        "Tipos coherentes, funciones, llamadas y ámbitos: SEM-1 a SEM-5 sin errores.",
        '''hagale_pues promediar(numerito a, numerito b) pa_que_lleve numerito dele_pues
    pille_pues numerito suma = a + b
    entregue_pues suma
ya_quedo

pille_pues numerito cantidad = 3
pille_pues quebradito precio = 19.99
pille_pues quebradito total = precio * 2.0
si_acaso cantidad > 0 entonces_pues
    hable_pues("Total: " <> total)
asi_quedo
hable_pues(promediar(4, 6))''',
    ),
    (
        "ERRORES SEMANTICOS deliberados",
        "Acumula violaciones de SEM-1..SEM-5; el analisis semantico sigue y las reporta todas.",
        '''hagale_pues promediar(numerito a, numerito b) pa_que_lleve quebradito dele_pues
    entregue_pues a + b
ya_quedo

pille_pues numerito edad = "veinte"
pille_pues quebradito precio = 19.99
pille_pues numerito cantidad = 3
pille_pues total = precio + cantidad
hable_pues(saldo_disponible)
si_acaso cantidad entonces_pues
    hable_pues("hay unidades")
asi_quedo
pille_pues quebradito promedio = promediar(5)
hable_pues(promedio)''',
    ),
    (
        "ERRORES DE BUCLE deliberados (SEM-6, SEM-7, SEM-8)",
        "Bucles que no pueden terminar, escritura sobre la variable de control y pasos imposibles.",
        '''// SEM-6: el cuerpo no redefine 'tope', la condicion nunca cambia
pille_pues numerito tope = 10
mientras_que tope > 0 dele_pues
    hable_pues("doy vueltas sin avanzar")
hasta_ahi

// SEM-6: condicion constante
mientras_que sizas dele_pues
    hable_pues("esto no para")
hasta_ahi

// SEM-6: en repita_pues, hasta_que es la condicion de SALIDA
pille_pues numerito veces = 0
repita_pues
    hable_pues("tampoco avanzo")
hasta_que veces > 5

// SEM-7: 'm' es la variable de control, es de solo lectura
pa_cada m desde 1 hasta 3 dele_pues
    pille_pues m = 99
listo_pues

// SEM-8: paso 0, la variable de control nunca avanza
pa_cada i desde 1 hasta 10 de_a 0 dele_pues
    hable_pues(i)
listo_pues

// SEM-8: paso positivo pero desde > hasta, el cuerpo nunca se ejecuta
pa_cada j desde 10 hasta 1 dele_pues
    hable_pues(j)
listo_pues''',
    ),
]
