import shutil
import subprocess
import sys
import venv
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
CARPETA_VENV = RAIZ / ".venv"
REQUIREMENTS = RAIZ / "requirements.txt"
ENV = RAIZ / ".env"
ENV_EJEMPLO = RAIZ / ".env.example"
ES_WINDOWS = sys.platform.startswith("win")


def python_del_venv():
    """Ruta al ejecutable de Python dentro de .venv (cambia según el sistema operativo)."""
    if ES_WINDOWS:
        return CARPETA_VENV / "Scripts" / "python.exe"
    return CARPETA_VENV / "bin" / "python"


def crear_entorno():
    if python_del_venv().exists():
        print("[1/3] El entorno virtual .venv ya existe, se reutiliza.")
        return
    print("[1/3] Creando entorno virtual .venv ...")
    venv.create(CARPETA_VENV, with_pip=True)


def instalar_dependencias():
    print("[2/3] Instalando dependencias de requirements.txt ...")
    py = str(python_del_venv())
    # Se llama al pip del entorno virtual directamente: no hace falta activarlo.
    subprocess.run([py, "-m", "pip", "install", "--upgrade", "pip", "--quiet"], check=True)
    subprocess.run([py, "-m", "pip", "install", "-r", str(REQUIREMENTS), "--quiet"], check=True)


def leer_variables(ruta):
    """Devuelve {VARIABLE: valor} de un archivo .env, ignorando comentarios y líneas vacías."""
    variables = {}
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if linea and not linea.startswith("#") and "=" in linea:
            nombre, valor = linea.split("=", 1)
            variables[nombre.strip()] = valor.strip().strip('"').strip("'")
    return variables


def preparar_env():
    if not ENV_EJEMPLO.exists():
        print("[3/3] AVISO: no se encontró .env.example en la raíz del proyecto.")
        return
    if not ENV.exists():
        shutil.copy(ENV_EJEMPLO, ENV)
        print("[3/3] Se creó .env a partir de .env.example.")
        return

    # El .env ya existe: solo se agregan al final las variables que le falten
    ejemplo = leer_variables(ENV_EJEMPLO)
    faltantes = [nombre for nombre in ejemplo if nombre not in leer_variables(ENV)]
    if not faltantes:
        print("[3/3] El archivo .env ya existe y está completo, no se modifica.")
        return
    contenido = ENV.read_text(encoding="utf-8")
    separador = "" if contenido.endswith("\n") or not contenido else "\n"
    nuevas = "".join(f"{nombre}={ejemplo[nombre]}\n" for nombre in faltantes)
    ENV.write_text(
        contenido + separador + "\n# Agregado por configurar_entorno.py: completa estos valores\n" + nuevas,
        encoding="utf-8",
    )
    print(f"[3/3] Se agregaron a .env las variables nuevas: {', '.join(faltantes)}")


def credenciales_por_completar():
    """Variables del .env que siguen con el valor de ejemplo (sin mostrar los valores reales)."""
    if not ENV.exists() or not ENV_EJEMPLO.exists():
        return []
    ejemplo = leer_variables(ENV_EJEMPLO)
    actuales = leer_variables(ENV)
    return [nombre for nombre, valor in ejemplo.items() if actuales.get(nombre, valor) in ("", valor)]


def main():
    if sys.version_info < (3, 9):
        sys.exit("Se requiere Python 3.9 o superior.")

    crear_entorno()
    instalar_dependencias()
    preparar_env()

    activar = ".venv\\Scripts\\activate" if ES_WINDOWS else "source .venv/bin/activate"
    print("\nListo. Próximos pasos:")
    pendientes = credenciales_por_completar()
    if pendientes:
        print(f"  - Abre el archivo .env y completa: {', '.join(pendientes)}")
    print("  - En VS Code: Select Interpreter → .venv (la terminal se activará sola)")
    print(f"  - Fuera de VS Code:       {activar}")
    print("  - Descarga los datos:     python extraccion/E_BCCH.py")
    print("                            python extraccion/E_FRED.py")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError:
        sys.exit("\nERROR: falló la instalación de dependencias. Revisa tu conexión a internet "
                 "y que requirements.txt esté en la raíz del proyecto.")