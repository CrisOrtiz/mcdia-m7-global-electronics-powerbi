# Consultas de Power Query que leen los CSV de `data/`

Código M de cada consulta del modelo. Todas leen los CSV del repositorio usando el parámetro `RutaCarpeta` y convierten los tipos con configuración regional **`en-US`**. Así las fechas `M/D/YYYY` y los precios `$1,234.56` se interpretan bien en cualquier computadora, aunque Windows esté en español.

**Cómo reemplazar una consulta:** en Power Query, clic derecho sobre la consulta → **Editor avanzado** → borrar todo → pegar el código → **Listo**.

---

## 1. Parámetro `RutaCarpeta`

Si no existe: **Inicio → Nuevo origen → Consulta en blanco**, ábrela en el **Editor avanzado**, pega esto y renombra la consulta como `RutaCarpeta`. Cambia la ruta por la de tu carpeta `data\` y **termínala con `\`**.

```m
"C:\Users\tu_usuario\repos\mcdia-m7-global-electronics-powerbi\data\" meta [IsParameterQuery = true, Type = "Text", IsParameterQueryRequired = true]
```

Cada integrante solo cambia esta ruta (**Inicio → Editar parámetros**). No se editan las rutas dentro de las consultas.

## 2. `Fact_Sales`

```m
let
    Origen = Csv.Document(File.Contents(RutaCarpeta & "Sales.csv"), [Delimiter = ",", Columns = 9, Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Encabezados = Table.PromoteHeaders(Origen, [PromoteAllScalars = true]),
    Tipos = Table.TransformColumnTypes(Encabezados, {
        {"Order Number", Int64.Type}, {"Line Item", Int64.Type},
        {"Order Date", type date}, {"Delivery Date", type date},
        {"CustomerKey", Int64.Type}, {"StoreKey", Int64.Type}, {"ProductKey", Int64.Type},
        {"Quantity", Int64.Type}, {"Currency Code", type text}
    }, "en-US"),
    // Ventas en tienda fisica: sin fecha de entrega -> fecha centinela 31/12/3000
    EntregaCentinela = Table.ReplaceValue(Tipos, null, #date(3000, 12, 31), Replacer.ReplaceValue, {"Delivery Date"})
in
    EntregaCentinela
```

## 3. `Dim_Customers`

```m
let
    Origen = Csv.Document(File.Contents(RutaCarpeta & "Customers.csv"), [Delimiter = ",", Columns = 10, Encoding = 1252, QuoteStyle = QuoteStyle.Csv]),
    Encabezados = Table.PromoteHeaders(Origen, [PromoteAllScalars = true]),
    Tipos = Table.TransformColumnTypes(Encabezados, {
        {"CustomerKey", Int64.Type}, {"Gender", type text}, {"Name", type text},
        {"City", type text}, {"State Code", type text}, {"State", type text},
        {"Zip Code", type text}, {"Country", type text}, {"Continent", type text},
        {"Birthday", type date}
    }, "en-US")
in
    Tipos
```

## 4. `Dim_Products`

```m
let
    Origen = Csv.Document(File.Contents(RutaCarpeta & "Products.csv"), [Delimiter = ",", Columns = 10, Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Encabezados = Table.PromoteHeaders(Origen, [PromoteAllScalars = true]),
    // "$2,899.99 " -> "2899.99"
    LimpiarPrecios = Table.TransformColumns(Encabezados, {
        {"Unit Cost USD", each Text.Trim(Text.Remove(_, {"$", ","})), type text},
        {"Unit Price USD", each Text.Trim(Text.Remove(_, {"$", ","})), type text}
    }),
    Tipos = Table.TransformColumnTypes(LimpiarPrecios, {
        {"ProductKey", Int64.Type}, {"Product Name", type text}, {"Brand", type text},
        {"Color", type text}, {"Unit Cost USD", type number}, {"Unit Price USD", type number},
        {"SubcategoryKey", type text}, {"Subcategory", type text},
        {"CategoryKey", type text}, {"Category", type text}
    }, "en-US")
in
    Tipos
```

## 5. `Dim_Stores`

```m
let
    Origen = Csv.Document(File.Contents(RutaCarpeta & "Stores.csv"), [Delimiter = ",", Columns = 5, Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Encabezados = Table.PromoteHeaders(Origen, [PromoteAllScalars = true]),
    Tipos = Table.TransformColumnTypes(Encabezados, {
        {"StoreKey", Int64.Type}, {"Country", type text}, {"State", type text},
        {"Square Meters", Int64.Type}, {"Open Date", type date}
    }, "en-US")
in
    Tipos
```

## 6. `Aux_Exchange_Rates`

```m
let
    Origen = Csv.Document(File.Contents(RutaCarpeta & "Exchange_Rates.csv"), [Delimiter = ",", Columns = 3, Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Encabezados = Table.PromoteHeaders(Origen, [PromoteAllScalars = true]),
    Tipos = Table.TransformColumnTypes(Encabezados, {
        {"Date", type date}, {"Currency", type text}, {"Exchange", type number}
    }, "en-US")
in
    Tipos
```

## 7. `_Data_Dictionary`

```m
let
    Origen = Csv.Document(File.Contents(RutaCarpeta & "Data_Dictionary.csv"), [Delimiter = ";", Columns = 3, Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Encabezados = Table.PromoteHeaders(Origen, [PromoteAllScalars = true]),
    Tipos = Table.TransformColumnTypes(Encabezados, {
        {"Table", type text}, {"Field", type text}, {"Description", type text}
    })
in
    Tipos
```
