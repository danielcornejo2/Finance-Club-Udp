import sys
from pathlib import Path

import pandas as pd

# Los scripts de extraccion/ no son un paquete: se agrega su carpeta a la ruta de Python
RAIZ = Path(__file__).resolve().parent
sys.path.append(str(RAIZ / "extraccion"))

import E_BCCH
import E_FRED

FECHA_CORTE = pd.Timestamp("2026-09-30")   # fecha de corte del proyecto (anotada en el README)


def descargar_fuente(modulo, credenciales: tuple) -> list[str]:
    """
    Descarga todas las series de una fuente (E_BCCH o E_FRED) hasta la fecha de corte
    y guarda un CSV por serie. Devuelve la lista de series que fallaron.
    """
    modulo.CARPETA_SALIDA.mkdir(parents=True, exist_ok=True)
    errores = []

    for nombre, codigo in modulo.SERIES.items():
        try:
            # *credenciales entrega (usuario, clave) al BCCh y (api_key,) a FRED
            df = modulo.descargar_serie(codigo, *credenciales)
            df = modulo.a_mensual(df[df["fecha"] <= FECHA_CORTE])
            if df.empty:
                raise ValueError("no hay datos hasta la fecha de corte")
        except (E_BCCH.SinConexion, E_FRED.SinConexion) as e:
            sys.exit(f"\n[ERROR] {e}. Revisa tu internet (o la VPN) e intenta de nuevo.")
        except (ValueError, KeyError) as e:
            print(f"  [ERROR] {nombre}: {e}")
            errores.append(nombre)
            continue

        df["serie"] = nombre
        df["codigo"] = codigo
        df.to_csv(modulo.CARPETA_SALIDA / f"{nombre}.csv", index=False)
        print(f"  [OK] {nombre}: {len(df)} meses, "
              f"desde {df['fecha'].min():%Y-%m} hasta {df['fecha'].max():%Y-%m}")

    return errores


def main():
    print(f"Fecha de corte: {FECHA_CORTE:%Y-%m-%d}")

    print("\n1) Descargando series del Banco Central de Chile...")
    errores = descargar_fuente(E_BCCH, E_BCCH.cargar_credenciales())

    print("\n2) Descargando series de FRED...")
    errores += descargar_fuente(E_FRED, (E_FRED.cargar_api_key(),))

    # El CSV de una serie fallida no se actualiza: si existía, quedó el de la descarga anterior
    if errores:
        sys.exit(f"\n[ERROR] Fallaron estas series: {', '.join(errores)}. "
                 "Sus CSV no se actualizaron.")

    total = len(E_BCCH.SERIES) + len(E_FRED.SERIES)
    print(f"\n[OK] {total} series guardadas en data/raw/ con fecha de corte {FECHA_CORTE:%Y-%m-%d}")


if __name__ == "__main__":
    main()