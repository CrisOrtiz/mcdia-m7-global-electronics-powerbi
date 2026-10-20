"""Genera las paginas del informe (PBIR) dentro del .pbix.

Uso: python gen_report.py <pbix_entrada> <pbix_salida>
"""
import json
import sys
import zipfile
import hashlib

SRC, DST = sys.argv[1], sys.argv[2]

VC_SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.0.0/schema.json"
PAGE_SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json"
PAGES_SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.1.0/schema.json"

NAVY = "#0B2545"
RED = "#C8102E"


def uid(*parts):
    return hashlib.md5("|".join(parts).encode()).hexdigest()[:20]


def lit(v):
    return {"expr": {"Literal": {"Value": v}}}


def s(v):
    return lit("'" + v.replace("'", "''") + "'")


def color(hexv):
    return {"solid": {"color": s(hexv)}}


# ---------- campos ----------
def M(name, entity="Fact_Sales"):
    return ("Measure", entity, name)


def C(entity, name):
    return ("Column", entity, name)


def field(f):
    kind, ent, prop = f
    return {kind: {"Expression": {"SourceRef": {"Entity": ent}}, "Property": prop}}


def proj(f):
    _, ent, prop = f
    return {"field": field(f), "queryRef": f"{ent}.{prop}", "nativeQueryRef": prop}


# ---------- visuales ----------
class Page:
    def __init__(self, name, display):
        self.name = name
        self.display = display
        self.visuals = []

    def add(self, vtype, x, y, w, h, roles=None, title=None, sort=None, objects=None, vco=None):
        z = len(self.visuals)
        vname = uid(self.name, str(z), vtype)
        visual = {"visualType": vtype}
        if roles:
            visual["query"] = {
                "queryState": {role: {"projections": [proj(f) for f in fs]} for role, fs in roles.items()}
            }
            if sort:
                f, direction = sort
                visual["query"]["sortDefinition"] = {
                    "sort": [{"field": field(f), "direction": direction}],
                    "isDefaultSort": True,
                }
        if objects:
            visual["objects"] = objects
        container_objs = vco or {}
        if title is not None:
            container_objs.setdefault("title", [{"properties": {
                "show": lit("true"), "text": s(title), "fontColor": color(NAVY), "bold": lit("true"),
            }}])
        container_objs.setdefault("border", [{"properties": {
            "show": lit("true"), "color": color("#D9DEE7"), "radius": lit("8D"),
        }}])
        container_objs.setdefault("subTitle", [{"properties": {"show": lit("false")}}])
        container_objs.setdefault("dropShadow", [{"properties": {"show": lit("false")}}])
        visual["visualContainerObjects"] = container_objs
        visual["drillFilterOtherVisuals"] = True
        self.visuals.append({
            "$schema": VC_SCHEMA,
            "name": vname,
            "position": {"x": x, "y": y, "z": z * 1000, "height": h, "width": w, "tabOrder": z * 1000},
            "visual": visual,
        })

    # --- atajos ---
    def header(self, subtitle):
        self.add("shape", 0, 0, 1920, 90, objects={
            "shape": [{"properties": {"tileShape": s("rectangle")}}],
            "fill": [{"properties": {"fillColor": color(NAVY), "transparency": lit("0D")}, "selector": {"id": "default"}}],
            "outline": [{"properties": {"show": lit("false")}}],
        }, vco={"border": [{"properties": {"show": lit("false")}}]})
        self.add("shape", 0, 90, 1920, 6, objects={
            "shape": [{"properties": {"tileShape": s("rectangle")}}],
            "fill": [{"properties": {"fillColor": color(RED), "transparency": lit("0D")}, "selector": {"id": "default"}}],
            "outline": [{"properties": {"show": lit("false")}}],
        }, vco={"border": [{"properties": {"show": lit("false")}}]})
        self.add("textbox", 24, 8, 1150, 76, objects={"general": [{"properties": {"paragraphs": [
            {"textRuns": [{"value": "GLOBAL ELECTRONICS  |  " + self.display.upper(),
                           "textStyle": {"fontWeight": "bold", "fontSize": "24pt", "color": "#FFFFFF"}}]},
            {"textRuns": [{"value": subtitle, "textStyle": {"fontSize": "12pt", "color": "#DCE3EE"}}]},
        ]}}]}, vco={"background": [{"properties": {"show": lit("false")}}],
                    "border": [{"properties": {"show": lit("false")}}]})

    def slicer(self, x, f, title, y=14, w=230, h=66):
        self.add("slicer", x, y, w, h, roles={"Values": [f]}, objects={
            "data": [{"properties": {"mode": s("Dropdown")}}],
            "header": [{"properties": {"show": lit("true"), "text": s(title), "fontColor": color("#FFFFFF"),
                                       "textSize": lit("11D")}}],
            "items": [{"properties": {"fontColor": color(NAVY), "background": color("#FFFFFF")}}],
        }, vco={"background": [{"properties": {"show": lit("false")}}],
                "border": [{"properties": {"show": lit("false")}}]})
        # ocultar "(En blanco)" en la lista del filtro
        _, ent, prop = f
        self.visuals[-1]["filterConfig"] = {"filters": [{
            "name": uid(self.name, prop, "noblank"),
            "field": field(f),
            "type": "Advanced",
            "filter": {"Version": 2, "From": [{"Name": "d", "Entity": ent, "Type": 0}],
                       "Where": [{"Condition": {"Not": {"Expression": {"Comparison": {
                           "ComparisonKind": 0,
                           "Left": {"Column": {"Expression": {"SourceRef": {"Source": "d"}}, "Property": prop}},
                           "Right": {"Literal": {"Value": "null"}}}}}}}]},
            "howCreated": "User",
        }]}

    def kpis(self, measures, y=116, h=140):
        n = len(measures)
        gap = 20
        w = (1920 - 48 - gap * (n - 1)) // n
        for i, (m, label) in enumerate(measures):
            self.add("card", 24 + i * (w + gap), y, w, h, roles={"Values": [M(m)]}, objects={
                "labels": [{"properties": {"color": color(NAVY), "fontSize": lit("32D")}}],
                "categoryLabels": [{"properties": {"show": lit("false")}}],
            }, title=label, vco={"title": [{"properties": {
                "show": lit("true"), "text": s(label), "fontColor": color("#5A6478"),
                "alignment": s("center"), "fontSize": lit("13D"),
            }}], "border": [{"properties": {"show": lit("true"), "color": color(RED), "radius": lit("8D")}}]})


def data_labels(on=True):
    return {"labels": [{"properties": {"show": lit("true" if on else "false")}}]}


def bar_colors(hexv=NAVY):
    return {"dataPoint": [{"properties": {"fill": color(hexv)}}]}


def merge(*dicts):
    out = {}
    for d in dicts:
        out.update(d)
    return out


def top_n_filter(name, col, measure, n):
    """Filtro Top N de nivel visual: los n valores de col con mayor measure."""
    _, cent, cprop = col
    _, ment, mprop = measure
    colref = lambda src: {"Column": {"Expression": {"SourceRef": {"Source": src}}, "Property": cprop}}
    return {
        "name": name,
        "field": field(col),
        "type": "TopN",
        "filter": {
            "Version": 2,
            "From": [
                {"Name": "subquery", "Expression": {"Subquery": {"Query": {
                    "Version": 2,
                    "From": [{"Name": "d", "Entity": cent, "Type": 0}, {"Name": "f", "Entity": ment, "Type": 0}],
                    "Select": [dict(colref("d"), Name="field")],
                    "OrderBy": [{"Direction": 2, "Expression": {"Measure": {
                        "Expression": {"SourceRef": {"Source": "f"}}, "Property": mprop}}}],
                    "Top": n,
                }}}, "Type": 2},
                {"Name": "d", "Entity": cent, "Type": 0},
            ],
            "Where": [{"Condition": {"In": {
                "Expressions": [colref("d")],
                "Table": {"SourceRef": {"Source": "subquery"}},
            }}}],
        },
    }


ANIO = C("Dim_Date", "Anio")
MESANIO = C("Dim_Date", "MesAnio")
CANAL = C("Fact_Sales", "Canal")
DONUT_LABELS = {"labels": [{"properties": {"show": lit("true"), "labelStyle": s("Category, percent of total")}}]}
pages = []

# ===================== 1. Resumen: ¿Como va el negocio? =====================
p = Page("176cbb42f41c99eb56dc", "Resumen")
p.header("¿Cómo va el negocio?  Visión general de ventas 2016-2021 (USD)")
p.slicer(1420, ANIO, "Año")
p.slicer(1666, CANAL, "Canal")
p.kpis([("Ventas USD", "Ventas"), ("Margen %", "Margen %"), ("Pedidos", "Pedidos"),
        ("Ticket Promedio", "Ticket promedio"), ("Crecimiento % YoY", "Crecimiento % vs año anterior")])
p.add("clusteredColumnChart", 24, 276, 1236, 380, roles={"Category": [ANIO], "Y": [M("Ventas USD")]},
      sort=(ANIO, "Ascending"), objects=merge(data_labels(), bar_colors(NAVY)), title="Ventas por año")
p.add("donutChart", 1280, 276, 616, 380, roles={"Category": [CANAL], "Y": [M("Ventas USD")]},
      objects=DONUT_LABELS, title="Participación por canal")
p.add("clusteredBarChart", 24, 676, 1236, 380,
      roles={"Category": [C("Dim_Products", "Category")], "Y": [M("Ventas USD")]},
      sort=(M("Ventas USD"), "Descending"), objects=merge(data_labels(), bar_colors(NAVY)),
      title="Ventas por categoría")
p.add("clusteredColumnChart", 1280, 676, 616, 380,
      roles={"Category": [C("Dim_Customers", "Country")], "Y": [M("Ventas USD")]},
      sort=(M("Ventas USD"), "Descending"), objects=bar_colors(RED), title="Ventas por país")
pages.append(p)

# ===================== 2. Tiempo: ¿Como evolucionan las ventas? =====================
p = Page("a1b2c3d4e5f600000002", "Tiempo")
p.header("¿Cómo evolucionan las ventas?  Tendencia, comparación interanual y acumulado")
p.slicer(1420, ANIO, "Año")
p.slicer(1666, C("Dim_Products", "Category"), "Categoría")
p.kpis([("Ventas USD", "Ventas"), ("Ventas AA", "Ventas año anterior"),
        ("Crecimiento % YoY", "Crecimiento %"), ("Ventas Acumuladas", "Acumulado del año (YTD)")])
p.add("lineChart", 24, 276, 1236, 380, roles={"Category": [MESANIO], "Y": [M("Ventas USD"), M("Ventas AA")]},
      sort=(MESANIO, "Ascending"), title="Ventas mensuales vs. año anterior")
p.add("lineClusteredColumnComboChart", 1280, 276, 616, 380,
      roles={"Category": [ANIO], "Y": [M("Ventas USD")], "Y2": [M("Crecimiento % YoY")]},
      sort=(ANIO, "Ascending"), objects=bar_colors(NAVY), title="Ventas anuales y crecimiento %")
p.add("pivotTable", 24, 676, 1236, 380,
      roles={"Rows": [ANIO], "Columns": [C("Dim_Date", "MesCorto")], "Values": [M("Ventas USD")]},
      title="Matriz de ventas: año × mes")
p.add("areaChart", 1280, 676, 616, 380, roles={"Category": [MESANIO], "Y": [M("Ventas Acumuladas")]},
      sort=(MESANIO, "Ascending"), title="Ventas acumuladas en el año (YTD)")
pages.append(p)

# ===================== 3. Productos: ¿Que se vende y que deja margen? =====================
p = Page("a1b2c3d4e5f600000003", "Productos")
p.header("¿Qué se vende y qué deja margen?  Rentabilidad por categoría, marca y producto")
p.slicer(1420, ANIO, "Año")
p.slicer(1666, C("Dim_Products", "Category"), "Categoría")
p.kpis([("Ventas USD", "Ventas"), ("Costo USD", "Costo"), ("Margen USD", "Margen USD"),
        ("Margen %", "Margen %"), ("Unidades", "Unidades")])
p.add("clusteredBarChart", 24, 276, 908, 780,
      roles={"Category": [C("Dim_Products", "Product Name")], "Y": [M("Ventas USD")]},
      sort=(M("Ventas USD"), "Descending"), objects=merge(data_labels(), bar_colors(NAVY)),
      title="Top 10 productos por ventas")
p.visuals[-1]["filterConfig"] = {"filters": [top_n_filter(
    "top10productos", C("Dim_Products", "Product Name"), M("Ventas USD"), 10)]}
p.add("clusteredBarChart", 952, 276, 944, 380,
      roles={"Category": [C("Dim_Products", "Category")], "Y": [M("Ventas USD"), M("Margen USD")]},
      sort=(M("Ventas USD"), "Descending"), title="Ventas y margen por categoría")
p.add("clusteredBarChart", 952, 676, 944, 380,
      roles={"Category": [C("Dim_Products", "Brand")], "Y": [M("Ventas USD"), M("Margen USD")]},
      sort=(M("Ventas USD"), "Descending"), title="Ventas y margen por marca")
pages.append(p)

# ===================== 4. Clientes: ¿Quien compra y quien vuelve? =====================
p = Page("a1b2c3d4e5f600000004", "Clientes")
p.header("¿Quién compra y quién vuelve?  Perfil y recurrencia de los clientes")
p.slicer(1420, ANIO, "Año")
p.slicer(1666, C("Dim_Customers", "Continent"), "Continente")
p.kpis([("Clientes", "Clientes activos"), ("% Clientes Recurrentes", "% clientes recurrentes"),
        ("Ticket Promedio", "Ticket promedio")])
p.add("clusteredBarChart", 24, 276, 1236, 780,
      roles={"Category": [C("Dim_Customers", "Country")], "Y": [M("Clientes")]},
      sort=(M("Clientes"), "Descending"), objects=merge(data_labels(), bar_colors(NAVY)),
      title="Clientes activos por país")
p.add("donutChart", 1280, 276, 616, 380, roles={"Category": [C("Dim_Customers", "Gender")], "Y": [M("Clientes")]},
      objects=DONUT_LABELS, title="Clientes por género")
p.add("clusteredColumnChart", 1280, 676, 616, 380,
      roles={"Category": [C("Dim_Customers", "Rango Edad")], "Y": [M("Clientes")]},
      sort=(C("Dim_Customers", "Rango Edad"), "Ascending"), objects=merge(data_labels(), bar_colors(RED)),
      title="Clientes por rango de edad")
pages.append(p)

# ===================== 5. Canal: ¿Donde y como se vende? =====================
p = Page("a1b2c3d4e5f600000005", "Canal")
p.header("¿Dónde y cómo se vende?  Online vs. tienda física, tiendas y entregas")
p.slicer(1420, ANIO, "Año")
p.slicer(1666, C("Dim_Stores", "Country"), "País de la tienda")
p.kpis([("% Ventas Online", "% ventas online"), ("Ventas por m2", "Ventas por m² (tiendas)"),
        ("Días Entrega Prom", "Días promedio de entrega"), ("Unidades", "Unidades")])
p.add("donutChart", 24, 276, 600, 380, roles={"Category": [CANAL], "Y": [M("Ventas USD")]},
      objects=DONUT_LABELS, title="Ventas: online vs. tienda física")
p.add("clusteredColumnChart", 644, 276, 616, 380,
      roles={"Category": [ANIO], "Y": [M("Unidades")], "Series": [CANAL]},
      sort=(ANIO, "Ascending"), title="Unidades por año y canal")
p.add("tableEx", 1280, 276, 616, 780,
      roles={"Values": [C("Dim_Stores", "StoreKey"), C("Dim_Stores", "Country"), C("Dim_Stores", "State"),
                        M("Ventas USD"), M("Ventas por m2")]},
      sort=(M("Ventas USD"), "Descending"), title="Ranking de tiendas")
p.add("lineChart", 24, 676, 1236, 380, roles={"Category": [MESANIO], "Y": [M("Días Entrega Prom")]},
      sort=(MESANIO, "Ascending"), objects=bar_colors(RED),
      title="Días promedio de entrega por mes (ventas online)")
pages.append(p)


# ---------- escribir pbix ----------
files = {}
base = "Report/definition/pages/"
files[base + "pages.json"] = {"$schema": PAGES_SCHEMA, "pageOrder": [pg.name for pg in pages],
                              "activePageName": pages[0].name}
for pg in pages:
    files[f"{base}{pg.name}/page.json"] = {
        "$schema": PAGE_SCHEMA, "name": pg.name, "displayName": pg.display,
        "displayOption": "FitToPage", "height": 1080, "width": 1920,
        "objects": {"background": [{"properties": {"color": color("#F4F6FA"), "transparency": lit("0D")}}]},
    }
    for v in pg.visuals:
        files[f"{base}{pg.name}/visuals/{v['name']}/visual.json"] = v

zin = zipfile.ZipFile(SRC)
with zipfile.ZipFile(DST, "w") as zout:
    for info in zin.infolist():
        if info.filename.startswith(base) or info.filename == "SecurityBindings":
            continue
        data = zin.read(info.filename)
        if info.filename == "[Content_Types].xml":
            data = data.replace(b'<Override PartName="/SecurityBindings" ContentType="" />', b"")
        zout.writestr(info, data, compress_type=info.compress_type)
    for path, obj in files.items():
        zout.writestr(path, json.dumps(obj, ensure_ascii=False, indent=2).encode("utf-8"),
                      compress_type=zipfile.ZIP_DEFLATED)
print(f"{len(pages)} paginas, {sum(len(pg.visuals) for pg in pages)} visuales -> {DST}")
