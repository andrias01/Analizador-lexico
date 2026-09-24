"""
Módulo: ai_assistant.py
Descripción: Integración con OpenAI para detección de errores sintácticos
y sugerencias inteligentes adaptadas al contexto del compilador Paisascript.
"""
import os
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

# Carga las variables definidas en el archivo .env al entorno de Python
load_dotenv(override=True)

# Streamlit es opcional: este modulo debe poder importarse desde un script
# suelto o desde una prueba sin que exista una sesion de Streamlit.
try:
    import streamlit as st
except ImportError:
    st = None

# Directorio raíz del proyecto para ubicar la gramática
RAIZ = Path(__file__).parent


def leer_secreto(nombre, defecto=None):
    """Lee una variable de configuracion, en este orden de prioridad:

    1. st.secrets  -> lo que se escribe en "Secrets" de Streamlit Cloud
                      (y, en local, en .streamlit/secrets.toml)
    2. os.environ  -> variables de entorno del sistema o del archivo .env

    Asi el mismo codigo funciona desplegado y en la maquina local sin
    cambiar una linea: basta con definir el nombre en el sitio que
    corresponda. Devuelve `defecto` si no aparece en ninguno de los dos.
    """
    # 1. Secrets de Streamlit. El acceso se envuelve porque, si no hay
    # archivo de secretos, Streamlit lanza una excepcion en vez de devolver
    # vacio; ese caso no es un error, solo significa "seguir buscando".
    if st is not None:
        try:
            if nombre in st.secrets:
                return str(st.secrets[nombre])
        except Exception:
            pass

    # 2. Entorno del proceso, que ya incluye lo cargado desde .env
    return os.getenv(nombre, defecto)


def limpiar_api_key(key):
    """Limpia la clave de posibles prefijos o caracteres accidentales."""
    if not key:
        return None
    key = key.replace("OPENAI_API_KEY=", "")
    key = key.replace("'", "").replace('"', '').strip()
    return key


def hay_api_key_configurada():
    """Indica si existe una clave utilizable sin que el usuario escriba nada.

    La usa la interfaz para mostrar el estado de la conexion en la barra
    lateral sin tener que instanciar el cliente.
    """
    return limpiar_api_key(leer_secreto("OPENAI_API_KEY")) is not None


def origen_api_key():
    """Devuelve de donde sale la clave: 'secrets', 'entorno' o None.

    Sirve unicamente para informar al usuario en la interfaz.
    """
    if st is not None:
        try:
            if "OPENAI_API_KEY" in st.secrets and limpiar_api_key(str(st.secrets["OPENAI_API_KEY"])):
                return "secrets"
        except Exception:
            pass
    if limpiar_api_key(os.getenv("OPENAI_API_KEY")):
        return "entorno"
    return None


def obtener_cliente_openai(api_key=None):
    """
    Inicializa el cliente de OpenAI.
    Si no se pasa una clave explícita, la busca en los Secrets de Streamlit
    y, en su defecto, en las variables de entorno.
    """
    if not api_key:
        api_key = leer_secreto("OPENAI_API_KEY")

    api_key_limpia = limpiar_api_key(api_key)

    if not api_key_limpia:
        return None

    return OpenAI(api_key=api_key_limpia)

def cargar_gramatica():
    """Lee el archivo de la gramática BNF para dárselo como contexto a la IA."""
    ruta_gramatica = RAIZ / "gramatica_BNF_Paisascript.txt"
    if ruta_gramatica.exists():
        return ruta_gramatica.read_text(encoding="utf-8")
    return "Gramática BNF no disponible localmente."

def analizar_error_con_ia(codigo_fuente, error_detectado, api_key=None):
    """
    Envía el fragmento de código, el error y la gramática BNF de Paisascript 
    a OpenAI para obtener una explicación y sugerencias de corrección precisas.
    """
    cliente = obtener_cliente_openai(api_key)
    
    if not cliente:
        return "⚠️ No se ha configurado una API Key de OpenAI válida o la variable de entorno está vacía."

    # Cargamos la gramática para que la IA conozca las reglas exactas del lenguaje
    gramatica_bn = cargar_gramatica()

    prompt_sistema = (
        "Eres un asistente experto en compiladores, análisis sintáctico y en el lenguaje de programación 'Paisascript'. "
        "Tu objetivo es ayudar a estudiantes a corregir errores de sintaxis en su código fuente de forma clara, amigable y dando una sugerencia concreta.\n\n"
        "A continuación se presenta la gramática oficial en formato BNF de Paisascript que debes utilizar estrictamente como referencia para evaluar el código:\n"
        f"```\n{gramatica_bn}\n```"
    )

    prompt_usuario = f"""
    Analiza el siguiente código fuente en Paisascript que presentó un fallo en el compilador:
    
    CÓDIGO FUENTE:
    {codigo_fuente}
    
    ERROR DETECTADO / ESTADO DEL PARSER:
    {error_detectado}
    
    Por favor, responde estructuradamente con:
    1. 🔍 **¿Qué falló?** (Explicación breve del error sintáctico o léxico basándote en la gramática BNF).
    2. 💡 **Sugerencia de corrección** (Cómo debe ajustarse el código para que cumpla con la gramática de Paisascript).
    """

    try:
        # El modelo tambien es configurable por Secrets / entorno; si no se
        # define en ninguno de los dos se usa el valor por defecto.
        response = cliente.chat.completions.create(
            model=leer_secreto("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": prompt_sistema},
                {"role": "user", "content": prompt_usuario}
            ],
            temperature=0.3,
            max_tokens=400
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"❌ Ocurrió un error al comunicarse con la API de OpenAI: {str(e)}"
