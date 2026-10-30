# Tarea 3.2 — Visualizaciones empresariales · Global Electronics

**Objetivo del informe:** ver en un solo lugar cuánto, qué, dónde y a quién se vende, y cómo evoluciona.

El informe `powerbi/MCDIA_M7_GRUPO2.pbix` tiene 5 páginas. Todas usan el mismo diseño: encabezado azul con la pregunta de negocio, filtros de **Año** y una segunda dimensión arriba a la derecha, una fila de tarjetas KPI y debajo los gráficos. Todos los montos están en USD (`Cantidad × Precio unitario USD`).

Las medidas y columnas calculadas están en [`powerbi/medidas_visualizaciones.tmdl`](../powerbi/medidas_visualizaciones.tmdl).

---

## 1. Resumen — ¿Cómo va el negocio?

| Elemento | Visual | Requerimiento de información que satisface |
|---|---|---|
| Ventas, Margen %, Pedidos, Ticket promedio, Crecimiento % | Tarjetas KPI | Conocer de un vistazo el tamaño del negocio, su rentabilidad y si crece o cae frente al año anterior |
| Ventas por año | Columnas | Comparar el volumen de ventas entre años |
| Participación por canal | Anillo | Saber qué parte de las ventas viene de la tienda online y qué parte de las tiendas físicas |
| Ventas por categoría | Barras horizontales ordenadas | Identificar qué líneas de producto aportan más ingresos |
| Ventas por país | Columnas | Identificar los mercados más importantes |

**Filtros:** Año, Canal.

## 2. Tiempo — ¿Cómo evolucionan las ventas?

| Elemento | Visual | Requerimiento de información que satisface |
|---|---|---|
| Ventas, Ventas año anterior, Crecimiento %, Acumulado (YTD) | Tarjetas KPI | Medir el avance del año contra el año anterior |
| Ventas mensuales vs. año anterior | Líneas (2 series) | Detectar tendencia, estacionalidad y meses atípicos comparando cada mes con el mismo mes del año previo |
| Ventas anuales y crecimiento % | Combinado columnas + línea | Ver en un solo gráfico el volumen anual y su tasa de crecimiento |
| Matriz año × mes | Matriz | Consultar el valor exacto de cada mes y comparar los mismos meses entre años |
| Ventas acumuladas en el año | Área | Ver cómo se acumulan las ventas dentro de cada año |

**Filtros:** Año, Categoría.

## 3. Productos — ¿Qué se vende y qué deja margen?

| Elemento | Visual | Requerimiento de información que satisface |
|---|---|---|
| Ventas, Costo, Margen USD, Margen %, Unidades | Tarjetas KPI | Conocer ingresos, costos y rentabilidad del portafolio |
| Top 10 productos por ventas | Barras con filtro Top N | Identificar los productos estrella |
| Ventas y margen por categoría | Barras agrupadas | Comparar ingreso y margen de cada categoría: qué vende mucho y qué deja más ganancia |
| Ventas y margen por marca | Barras agrupadas | Evaluar el desempeño de cada marca |

**Filtros:** Año, Categoría.

## 4. Clientes — ¿Quién compra y quién vuelve?

| Elemento | Visual | Requerimiento de información que satisface |
|---|---|---|
| Clientes activos, % clientes recurrentes, Ticket promedio | Tarjetas KPI | Medir la base de clientes, su fidelidad (clientes con más de un pedido) y su gasto por pedido |
| Clientes activos por país | Barras horizontales ordenadas | Ubicar en qué países están los clientes y cuáles son los mercados con más clientes |
| Clientes por género | Anillo | Conocer la composición de la base por género |
| Clientes por rango de edad | Columnas | Identificar qué grupos de edad compran más |

**Filtros:** Año, Continente.

## 5. Canal — ¿Dónde y cómo se vende?

| Elemento | Visual | Requerimiento de información que satisface |
|---|---|---|
| % ventas online, Ventas por m², Días de entrega, Unidades | Tarjetas KPI | Medir el peso del canal online, la productividad del espacio de las tiendas y el servicio de entrega |
| Online vs. tienda física | Anillo | Comparar la participación de cada canal |
| Unidades por año y canal | Columnas agrupadas | Ver si el canal online gana o pierde terreno con los años |
| Ranking de tiendas | Tabla ordenada por ventas | Identificar las tiendas con mejor y peor desempeño, absoluto y por m² |
| Días promedio de entrega por mes | Líneas | Seguir la evolución del tiempo de entrega de los pedidos online |

**Filtros:** Año, País de la tienda.

---

## Medidas DAX

| Medida | Definición |
|---|---|
| Ventas USD | `SUMX(Fact_Sales, Quantity × RELATED(Unit Price USD))` |
| Costo USD | `SUMX(Fact_Sales, Quantity × RELATED(Unit Cost USD))` |
| Margen USD | Ventas − Costo |
| Margen % | Margen USD ÷ Ventas |
| Pedidos | Conteo distinto de `Order Number` |
| Ticket Promedio | Ventas ÷ Pedidos |
| Ventas AA | Ventas con `SAMEPERIODLASTYEAR` |
| Crecimiento % YoY | (Ventas − Ventas AA) ÷ Ventas AA |
| Ventas Acumuladas | `TOTALYTD` de Ventas |
| Clientes | Conteo distinto de `CustomerKey` en ventas |
| % Clientes Recurrentes | Clientes con más de un pedido ÷ Clientes |
| % Ventas Online | Ventas con `StoreKey = 0` ÷ Ventas |
| Ventas por m2 | Ventas de tiendas físicas ÷ m² de las tiendas |
| Días Entrega Prom | Promedio de días entre pedido y entrega (solo ventas con entrega real, excluye la fecha centinela 31/12/3000) |

**Columnas calculadas:** `Fact_Sales[Canal]` (Online / Tienda física), `Dim_Customers[Edad]` y `Dim_Customers[Rango Edad]` (edad al 20/02/2021, último día con datos).
