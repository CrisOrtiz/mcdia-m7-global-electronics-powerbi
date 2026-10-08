"""
Validación de los datos del repositorio Global Electronics (MCDIA M7 - Grupo 2).

Comprueba que los CSV de data/ sigan siendo los originales y que el modelo
de Power BI los pueda leer como está configurado en Power Query:

  - Existen los 6 archivos, con sus columnas y cantidad de filas.
  - Codificación y separador esperados.
  - Fechas en formato M/D/YYYY y precios con formato "$1,234.56".
  - Claves únicas en las dimensiones y sin ventas huérfanas.
  - Delivery Date solo en ventas Online.
  - Totales de control (ventas y costo en USD).
  - Reglas del repo: nada de .xlsx en data/ y el .pbix por debajo del límite de GitHub.

Uso:
    python scripts/validar_datos.py [ruta_del_repo]

Devuelve código 1 si alguna validación falla.
"""

from __future__ import annotations

import os
import re
import sys
from io import StringIO
from pathlib import Path

import pandas as pd

# --------------------------------------------------------------------------
# Valores esperados (calculados sobre los CSV originales)
# --------------------------------------------------------------------------

ARCHIVOS = {
    "Sales.csv": {
        "encoding": "utf-8",
        "sep": ",",
        "filas": 62884,
        "columnas": ["Order Number", "Line Item", "Order Date", "Delivery Date",
                     "CustomerKey", "StoreKey", "ProductKey", "Quantity", "Currency Code"],
    },
    "Customers.csv": {
        "encoding": "cp1252",
        "sep": ",",
        "filas": 15266,
        "columnas": ["CustomerKey", "Gender", "Name", "City", "State Code", "State",
                     "Zip Code", "Country", "Continent", "Birthday"],
    },
    "Products.csv": {
        "encoding": "utf-8",
        "sep": ",",
        "filas": 2517,
        "columnas": ["ProductKey", "Product Name", "Brand", "Color", "Unit Cost USD",
                     "Unit Price USD", "SubcategoryKey", "Subcategory", "CategoryKey", "Category"],
    },
    "Stores.csv": {
        "encoding": "utf-8",
        "sep": ",",
        "filas": 67,
        "columnas": ["StoreKey", "Country", "State", "Square Meters", "Open Date"],
    },
    "Exchange_Rates.csv": {
        "encoding": "utf-8",
        "sep": ",",
        "filas": 11215,
        "columnas": ["Date", "Currency", "Exchange"],
    },
    "Data_Dictionary.csv": {
        "encoding": "utf-8",
        "sep": ";",
        "filas": 37,
        "columnas": ["Table", "Field", "Description"],
    },
}

TOTAL_VENTAS_USD = 55_755_479.59
TOTAL_COSTO_USD = 23_092_791.21
TOLERANCIA = 0.01

LIMITE_GITHUB_MB = 100
AVISO_PBIX_MB = 50

PATRON_FECHA = re.compile(r"^\d{1,2}/\d{1,2}/\d{4}$")
PATRON_PRECIO = re.compile(r"^\$\d{1,3}(,\d{3})*\.\d{2}$")
# Secuencias típicas de un texto UTF-8 leído como Windows-1252 ("FÃ¼rstenberg")
PATRON_MOJIBAKE = re.compile(r"Ã[\x80-\xbf¡-ÿ]")


# --------------------------------------------------------------------------
# Registro de resultados
# --------------------------------------------------------------------------

class Resultado:
    def __init__(self) -> None:
        self.errores: list[str] = []
        self.avisos: list[str] = []
        self.ok: list[str] = []

    def check(self, condicion: bool, mensaje_ok: str, mensaje_error: str) -> bool:
        if condicion:
            self.ok.append(mensaje_ok)
        else:
            self.errores.append(mensaje_error)
        return condicion

    def aviso(self, mensaje: str) -> None:
        self.avisos.append(mensaje)


# --------------------------------------------------------------------------
# Validaciones
# --------------------------------------------------------------------------

def leer_csv(ruta: Path, spec: dict, r: Resultado) -> pd.DataFrame | None:
    nombre = ruta.name
    try:
        texto = ruta.read_bytes().decode(spec["encoding"])
    except UnicodeDecodeError as e:
        pista = "¿Se guardó con otra codificación?"
        if spec["encoding"] == "cp1252":
            try:
                ruta.read_bytes().decode("utf-8")
                pista = ("Parece guardado en UTF-8. Power Query lo lee con Encoding=1252, "
                         "así que los acentos se verían mal. Restaurar el CSV original.")
            except UnicodeDecodeError:
                pass
        r.errores.append(f"{nombre}: no se puede leer como {spec['encoding']} "
                         f"(byte inválido en la posición {e.start}). {pista}")
        return None

    if spec["encoding"] == "cp1252" and PATRON_MOJIBAKE.search(texto):
        r.errores.append(f"{nombre}: parece estar en UTF-8 y no en Windows-1252 "
                         "(aparecen caracteres como 'Ã¼'). Power Query lo lee con Encoding=1252, "
                         "así que los acentos se verían mal. Restaurar el CSV original.")

    df = pd.read_csv(StringIO(texto), sep=spec["sep"], dtype=str, keep_default_na=False)

    r.check(list(df.columns) == spec["columnas"],
            f"{nombre}: columnas correctas",
            f"{nombre}: columnas distintas a las esperadas.\n"
            f"    esperado: {spec['columnas']}\n    encontrado: {list(df.columns)}")
    r.check(len(df) == spec["filas"],
            f"{nombre}: {len(df):,} filas".replace(",", "."),
            f"{nombre}: tiene {len(df)} filas, se esperaban {spec['filas']}")
    return df


def validar_fechas(df: pd.DataFrame, archivo: str, columna: str, r: Resultado,
                   permite_vacio: bool = False) -> None:
    valores = df[columna]
    if permite_vacio:
        valores = valores[valores != ""]
    malos = valores[~valores.str.match(PATRON_FECHA)]
    if not malos.empty:
        r.errores.append(f"{archivo}[{columna}]: {len(malos)} valores no tienen formato M/D/YYYY "
                         f"(ej.: {malos.iloc[0]!r}). Si el CSV se abrió y guardó en Excel, "
                         "restaurar el original.")
        return
    invalidas = pd.to_datetime(valores, format="%m/%d/%Y", errors="coerce").isna().sum()
    r.check(invalidas == 0,
            f"{archivo}[{columna}]: fechas M/D/YYYY válidas",
            f"{archivo}[{columna}]: {invalidas} fechas no válidas como mes/día/año")


def validar_precios(products: pd.DataFrame, r: Resultado) -> None:
    for col in ["Unit Cost USD", "Unit Price USD"]:
        valores = products[col].str.strip()
        malos = valores[~valores.str.match(PATRON_PRECIO)]
        r.check(malos.empty,
                f"Products.csv[{col}]: formato de precio correcto",
                f"Products.csv[{col}]: {len(malos)} valores con formato inesperado "
                f"(ej.: {malos.iloc[0] if not malos.empty else ''!r})")


def a_numero(serie: pd.Series) -> pd.Series:
    return pd.to_numeric(serie.str.replace(r"[$,\s]", "", regex=True))


def validar_claves(sales, customers, products, stores, r: Resultado) -> None:
    for nombre, df, clave in [("Customers.csv", customers, "CustomerKey"),
                              ("Products.csv", products, "ProductKey"),
                              ("Stores.csv", stores, "StoreKey")]:
        dup = df[clave].duplicated().sum()
        r.check(dup == 0,
                f"{nombre}: {clave} sin duplicados",
                f"{nombre}: {dup} valores de {clave} duplicados")

        huerfanas = (~sales[clave].isin(df[clave])).sum()
        r.check(huerfanas == 0,
                f"Sales.csv: todo {clave} existe en {nombre}",
                f"Sales.csv: {huerfanas} ventas con {clave} que no existe en {nombre}")


def validar_entregas(sales: pd.DataFrame, r: Resultado) -> None:
    online = sales["StoreKey"] == "0"
    con_entrega = sales["Delivery Date"] != ""
    r.check(bool((online == con_entrega).all()),
            "Sales.csv: Delivery Date presente solo y siempre en ventas Online",
            "Sales.csv: hay ventas en tienda con Delivery Date o ventas Online sin ella")


def validar_totales(sales, products, r: Resultado) -> None:
    precios = products[["ProductKey"]].assign(
        costo=a_numero(products["Unit Cost USD"]),
        precio=a_numero(products["Unit Price USD"]),
    )
    m = sales[["ProductKey", "Quantity"]].merge(precios, on="ProductKey", how="left")
    cantidad = pd.to_numeric(m["Quantity"])
    ventas = round(float((cantidad * m["precio"]).sum()), 2)
    costo = round(float((cantidad * m["costo"]).sum()), 2)

    fmt = lambda x: f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    r.check(abs(ventas - TOTAL_VENTAS_USD) <= TOLERANCIA,
            f"Ventas USD = {fmt(ventas)}",
            f"Ventas USD = {fmt(ventas)}, se esperaba {fmt(TOTAL_VENTAS_USD)}")
    r.check(abs(costo - TOTAL_COSTO_USD) <= TOLERANCIA,
            f"Costo USD = {fmt(costo)}",
            f"Costo USD = {fmt(costo)}, se esperaba {fmt(TOTAL_COSTO_USD)}")


def validar_repo(raiz: Path, r: Resultado) -> None:
    data = raiz / "data"
    extras = sorted(p.name for p in data.iterdir()
                    if p.is_file() and p.name not in ARCHIVOS)
    excel = [n for n in extras if n.lower().endswith((".xlsx", ".xls"))]
    r.check(not excel,
            "data/: sin archivos de Excel",
            f"data/: contiene archivos de Excel {excel}. El modelo usa solo los CSV; "
            "las copias en Excel tienen fechas invertidas.")
    otros = [n for n in extras if n not in excel]
    if otros:
        r.aviso(f"data/: archivos que no forman parte del modelo: {otros}")

    pbix = sorted((raiz / "powerbi").glob("*.pbix")) if (raiz / "powerbi").is_dir() else []
    if not r.check(bool(pbix), "powerbi/: .pbix encontrado",
                   "powerbi/: no hay ningún archivo .pbix"):
        return
    if len(pbix) > 1:
        r.aviso(f"powerbi/: hay {len(pbix)} archivos .pbix {[p.name for p in pbix]}; "
                "debería haber uno solo")
    for p in pbix:
        mb = p.stat().st_size / 1024 / 1024
        r.check(mb < LIMITE_GITHUB_MB,
                f"powerbi/{p.name}: {mb:.1f} MB",
                f"powerbi/{p.name}: pesa {mb:.1f} MB, GitHub no acepta archivos de más de "
                f"{LIMITE_GITHUB_MB} MB")
        if AVISO_PBIX_MB <= mb < LIMITE_GITHUB_MB:
            r.aviso(f"powerbi/{p.name}: pesa {mb:.1f} MB, se acerca al límite de GitHub")


# --------------------------------------------------------------------------
# Programa principal
# --------------------------------------------------------------------------

def main() -> int:
    raiz = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    data = raiz / "data"
    r = Resultado()

    if not data.is_dir():
        print(f"ERROR: no existe la carpeta {data}")
        return 1

    dfs: dict[str, pd.DataFrame] = {}
    for nombre, spec in ARCHIVOS.items():
        ruta = data / nombre
        if not r.check(ruta.is_file(), f"{nombre}: encontrado", f"{nombre}: no existe en data/"):
            continue
        df = leer_csv(ruta, spec, r)
        if df is not None and list(df.columns) == spec["columnas"]:
            dfs[nombre] = df

    if "Sales.csv" in dfs:
        validar_fechas(dfs["Sales.csv"], "Sales.csv", "Order Date", r)
        validar_fechas(dfs["Sales.csv"], "Sales.csv", "Delivery Date", r, permite_vacio=True)
        validar_entregas(dfs["Sales.csv"], r)
    if "Customers.csv" in dfs:
        validar_fechas(dfs["Customers.csv"], "Customers.csv", "Birthday", r)
    if "Stores.csv" in dfs:
        validar_fechas(dfs["Stores.csv"], "Stores.csv", "Open Date", r)
    if "Exchange_Rates.csv" in dfs:
        validar_fechas(dfs["Exchange_Rates.csv"], "Exchange_Rates.csv", "Date", r)
    if "Products.csv" in dfs:
        validar_precios(dfs["Products.csv"], r)

    if all(n in dfs for n in ["Sales.csv", "Customers.csv", "Products.csv", "Stores.csv"]):
        validar_claves(dfs["Sales.csv"], dfs["Customers.csv"],
                       dfs["Products.csv"], dfs["Stores.csv"], r)
        if not any("Products.csv[Unit" in e for e in r.errores):
            validar_totales(dfs["Sales.csv"], dfs["Products.csv"], r)

    validar_repo(raiz, r)

    # Salida en consola
    for m in r.ok:
        print(f"  OK     {m}")
    for m in r.avisos:
        print(f"  AVISO  {m}")
    for m in r.errores:
        print(f"  ERROR  {m}")
    print()
    estado = "FALLÓ" if r.errores else "PASÓ"
    print(f"Validación {estado}: {len(r.ok)} OK, {len(r.avisos)} avisos, {len(r.errores)} errores")

    # Resumen en la página del workflow de GitHub Actions
    resumen = os.environ.get("GITHUB_STEP_SUMMARY")
    if resumen:
        with open(resumen, "a", encoding="utf-8") as f:
            f.write(f"## Validación de datos: {'❌' if r.errores else '✅'} {estado}\n\n")
            f.write(f"{len(r.ok)} OK · {len(r.avisos)} avisos · {len(r.errores)} errores\n\n")
            if r.errores:
                f.write("### Errores\n\n" + "".join(f"- {e}\n" for e in r.errores) + "\n")
            if r.avisos:
                f.write("### Avisos\n\n" + "".join(f"- {a}\n" for a in r.avisos) + "\n")
            f.write("<details><summary>Validaciones correctas</summary>\n\n")
            f.write("".join(f"- {m}\n" for m in r.ok))
            f.write("\n</details>\n")

    return 1 if r.errores else 0


if __name__ == "__main__":
    sys.exit(main())
