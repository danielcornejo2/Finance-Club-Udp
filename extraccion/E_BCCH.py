import os
import sys
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

URL_API = "https://si3.bcentral.cl/SieteRestWS/SieteRestWS.ashx"
FECHA_INICIO = "2010-01-01"                       # al menos 10 años de historia, según la pauta
TIEMPO_ESPERA = 60                                # segundos máximos por consulta
RAIZ = Path(__file__).resolve().parent.parent     # carpeta raíz del proyecto
CARPETA_SALIDA = RAIZ / "data" / "raw" / "bcch"

# Series a descargar: {nombre_corto: código BDE}. Signo = efecto esperado sobre la TPM.
SERIES = {
    "tpm": "F022.TPM.TIN.D001.NO.Z.M",                # Tasa de Política Monetaria 
    "ipc": "F074.IPC.VAR.Z.Z.C.M",                    # inflación total, var. mensual 
    "ipc_sae": "F074.IPCSAE.VAR.Z.EP23.Z.M",          # inflación subyacente, desde 2010 
    "imacec": "F032.IMC.IND.Z.Z.EP18.Z.Z.0.M",        # actividad -> brecha del producto 
    "dolar_observado": "F073.TCO.PRE.HIST.M",         # canal cambiario 
    "expectativa_ipc_eee": "F089.IPC.V12.14.M",       # inflación esperada a 12 meses 
    "tasa_bcp_10": "F022.BCLP.TIS.AN10.NO.Z.D",       # bono en pesos 10 años, diaria 
    "tasa_bcu_10": "F022.BUF.TIS.AN10.UF.Z.D",        # bono en UF 10 años, diaria 
    "desempleo": "F049.DES.TAS.INE9.10.M",            # holgura laboral 
    "tpm_11m": "F089.TPM.TAS.11.M",                   # expectativa TPM a 11 meses
    "tpm_23m": "F089.TPM.TAS.23.M",                   # expectativa TPM a 23 meses
    "tpm_35m": "F089.TPM.TAS.35.M",                   # expectativa TPM a 35 meses
    "inflacion_11m": "F089.IPC.V12.14.M",             # expectativa inflación a 11 meses
    "inflacion_23m": "F089.IPC.V12.15.M",             # expectativa inflación a 23 meses
}


class SinConexion(Exception):
    """No se pudo llegar al servidor del Banco Central (internet, VPN o red bloqueada)."""


def cargar_credenciales() -> tuple[str, str]:
    """Lee usuario y clave desde .env y detiene el programa si faltan."""
    load_dotenv(RAIZ / ".env")
    usuario = os.getenv("BCCH_USER")
    clave = os.getenv("BCCH_PASS")
    if not usuario or not clave:
        sys.exit("ERROR: faltan BCCH_USER o BCCH_PASS en el archivo .env (ver .env.example).")
    return usuario, clave


def llamar_api(params: dict) -> dict:
    """Consulta la API y devuelve la respuesta, o lanza un error con un mensaje claro."""
    # Los mensajes de error de requests incluyen la URL con usuario y clave,
    # por eso nunca se muestran: se reemplazan por mensajes propios.
    try:
        respuesta = requests.get(URL_API, params=params, timeout=TIEMPO_ESPERA)
    except requests.ConnectionError:
        raise SinConexion("no hay conexión con si3.bcentral.cl") from None
    except requests.RequestException:
        raise ValueError("la API no respondió a tiempo") from None

    if respuesta.status_code != 200:
        raise ValueError(f"la API respondió con error HTTP {respuesta.status_code}")

    datos = respuesta.json()
    if datos.get("Codigo") != 0:  # la API usa Codigo = 0 para indicar éxito
        raise ValueError(f"la API respondió: {datos.get('Descripcion')}")
    return datos


def descargar_serie(codigo: str, usuario: str, clave: str, desde: str = FECHA_INICIO) -> pd.DataFrame:
    """Descarga una serie y la devuelve como DataFrame con columnas fecha y valor."""
    params = {
        "user": usuario,
        "pass": clave,
        "function": "GetSeries",
        "timeseries": codigo,
        "firstdate": desde,
    }
    df = pd.DataFrame(llamar_api(params)["Series"]["Obs"])
    if df.empty:
        raise ValueError("la API no devolvió observaciones")

    df["fecha"] = pd.to_datetime(df["indexDateString"], format="%d-%m-%Y")
    df["valor"] = pd.to_numeric(df["value"], errors="coerce")
    df.loc[df["statusCode"] != "OK", "valor"] = pd.NA  # meses sin dato quedan como faltantes
    return df[["fecha", "valor"]]


def a_mensual(df: pd.DataFrame) -> pd.DataFrame:
    """Promedia cada mes (fecha = día 1). Las series mensuales quedan iguales."""
    if df.empty:
        return df
    mensual = df.set_index("fecha")["valor"].astype(float).resample("MS").mean()
    return mensual.reset_index()


def main():
    usuario, clave = cargar_credenciales()
    CARPETA_SALIDA.mkdir(parents=True, exist_ok=True)
    errores = []

    for nombre, codigo in SERIES.items():
        print(f"Descargando {nombre}...")
        try:
            df = a_mensual(descargar_serie(codigo, usuario, clave))
        except SinConexion as e:
            sys.exit(f"\nERROR: {e}. Revisa tu internet (o la VPN) e intenta de nuevo.")
        except (ValueError, KeyError) as e:
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