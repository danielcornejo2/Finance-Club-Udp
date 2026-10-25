import os
import sys
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

URL_API = "https://api.stlouisfed.org/fred/series/observations"
FECHA_INICIO = "2010-01-01"                       # mismo inicio que las series del Banco Central
TIEMPO_ESPERA = 60                                # segundos máximos por consulta
RAIZ = Path(__file__).resolve().parent.parent     # carpeta raíz del proyecto
CARPETA_SALIDA = RAIZ / "data" / "raw" / "fred"

# Series a descargar: {nombre_corto: código FRED}. Signo = efecto esperado sobre la TPM.
# Los nombres deben ser distintos a los de E_BCCH.py, porque la base junta ambas fuentes.
SERIES = {
    "precio_cobre": "PCOPPUSDM",                  # términos de intercambio 
    "fed_funds": "FEDFUNDS",                      # diferencial de tasas con EE.UU. 
    "ipc_eeuu": "CPIAUCSL",                       # inflación externa
    "produccion_industrial_eeuu": "INDPRO",       # ciclo de la demanda externa 
    "petroleo_wti": "DCOILWTICO",                 # Precio diario spot del crudo WTI (Europeo)
    "petroleo_brent_mensual": "POILBREUSDM",      # Precio global del Brent (Mensual)

}


class SinConexion(Exception):
    """No se pudo llegar al servidor de FRED (internet, VPN o red bloqueada)."""


def cargar_api_key() -> str:
    """Lee la API key de FRED desde .env y detiene el programa si falta."""
    load_dotenv(RAIZ / ".env")
    api_key = (os.getenv("FRED_API_KEY") or "").strip()
    if not api_key:
        sys.exit("ERROR: falta FRED_API_KEY en el archivo .env (ver .env.example). "
                 "Se obtiene gratis en https://fred.stlouisfed.org/docs/api/api_key.html")
    return api_key


def mensaje_de_error(respuesta: requests.Response) -> str:
    """Arma el mensaje de error usando la explicación que entrega FRED en "error_message"."""
    try:
        detalle = respuesta.json().get("error_message", "")
    except ValueError:  # la respuesta no venía en JSON
        detalle = ""
    return f"FRED respondió con error HTTP {respuesta.status_code}: {detalle or respuesta.reason}"


def llamar_api(params: dict) -> dict:
    """Consulta la API y devuelve la respuesta, o lanza un error con un mensaje claro."""
    # Los mensajes de error de requests incluyen la URL con la API key,
    # por eso nunca se muestran: se reemplazan por mensajes propios.
    try:
        respuesta = requests.get(URL_API, params=params, timeout=TIEMPO_ESPERA)
    except requests.ConnectionError:
        raise SinConexion("no hay conexión con api.stlouisfed.org") from None
    except requests.RequestException:
        raise ValueError("la API no respondió a tiempo") from None

    if respuesta.status_code != 200:
        raise ValueError(mensaje_de_error(respuesta))
    return respuesta.json()


def descargar_serie(codigo: str, api_key: str, desde: str = FECHA_INICIO) -> pd.DataFrame:
    """Descarga una serie y la devuelve como DataFrame con columnas fecha y valor."""
    params = {
        "api_key": api_key,
        "series_id": codigo,
        "observation_start": desde,
        "file_type": "json",
    }
    df = pd.DataFrame(llamar_api(params).get("observations", []))
    if df.empty:
        raise ValueError("la API no devolvió observaciones")

    df["fecha"] = pd.to_datetime(df["date"], format="%Y-%m-%d")
    df["valor"] = pd.to_numeric(df["value"], errors="coerce")  # FRED marca los faltantes con "."
    return df[["fecha", "valor"]]


def a_mensual(df: pd.DataFrame) -> pd.DataFrame:
    """Promedia cada mes (fecha = día 1). Las series mensuales quedan iguales."""
    if df.empty:
        return df
    mensual = df.set_index("fecha")["valor"].astype(float).resample("MS").mean()
    return mensual.reset_index()


def main():
    api_key = cargar_api_key()
    CARPETA_SALIDA.mkdir(parents=True, exist_ok=True)
    errores = []

    for nombre, codigo in SERIES.items():
        print(f"Descargando {nombre}...")
        try:
            df = a_mensual(descargar_serie(codigo, api_key))
        except SinConexion as e:
            sys.exit(f"\nERROR: {e}. Revisa tu internet (o la VPN) e intenta de nuevo.")
        except ValueError as e:
            # Si FRED rechaza la API key, fallarán todas las series: no tiene sentido seguir
            if "api_key" in str(e):
                sys.exit(f"\nERROR: {e}\nRevisa FRED_API_KEY en tu archivo .env.")
            print(f"  ERROR en {nombre}: {e}")
            errores.append(nombre)
            continue

        df["serie"] = nombre
        df["codigo"] = codigo
        df.to_csv(CARPETA_SALIDA / f"{nombre}.csv", index=False)
        print(f"  OK: {len(df)} meses, desde {df['fecha'].min():%Y-%m} hasta {df['fecha'].max():%Y-%m}")

    if errores:
        sys.exit(f"\nTerminado con errores en: {', '.join(errores)}")
    print("\nTodas las series se descargaron correctamente.")


if __name__ == "__main__":
    main()