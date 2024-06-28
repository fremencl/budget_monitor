import streamlit as st
import pandas as pd
import io
import plotly.express as px
import plotly.graph_objects as go

# Título de la aplicación
st.markdown("<h1 style='text-align: center; color: black; font-size: 24px;'>MONITOR GESTIÓN PRESUPUESTARIA</h1>", unsafe_allow_html=True)

# Definimos las URLs de los archivos de referencia
DATA0_URL = 'https://streamlitmaps.s3.amazonaws.com/Data_0524.csv'
BUDGET_URL = 'https://streamlitmaps.s3.amazonaws.com/Base_Presupuesto.csv'
ORDERS_URL = 'https://streamlitmaps.s3.amazonaws.com/Base_Ordenes.csv'

# Función para cargar el archivo de referencia
@st.cache_data
def load_data(url):
    data = pd.read_csv(url, encoding='ISO-8859-1', sep=';')
    if 'Valor/mon.inf.' in data.columns:
        data['Valor/mon.inf.'] = pd.to_numeric(data['Valor/mon.inf.'].str.replace(',', ''), errors='coerce').fillna(0)
    return data

# Función para eliminar filas con valores específicos en "Grupo_Ceco"
def eliminar_filas_grupo_ceco(data):
    valores_excluir = ["Abastecimiento y contratos", "Finanzas", "Servicios generales"]
    return data[~data['Grupo_Ceco'].isin(valores_excluir)]

# Función para identificar y eliminar pares de valores opuestos
def eliminar_pares_opuestos(data):
    filtered_df = pd.DataFrame()
    removed_df = pd.DataFrame()
    groups = data.groupby(['Clase de coste', 'Centro de coste'])
    
    for name, group in groups:
        seen_values = {}
        rows_to_remove = set()
        
        # Ordenar el grupo por 'Período' de forma ascendente para procesar en orden temporal
        group = group.sort_values(by='Período')
        
        for index, row in group.iterrows():
            value = row['Valor/mon.inf.']
            period = row['Período']
            
            if value < 0:
                # Buscar coincidencia en el mismo período
                if (period, -value) in seen_values:
                    opposite_index = seen_values[(period, -value)]
                    rows_to_remove.add(index)
                    rows_to_remove.add(opposite_index)
                    del seen_values[(period, -value)]
                else:
                    # Buscar coincidencia en períodos anteriores
                    for past_period in range(period - 1, 0, -1):
                        if (past_period, -value) in seen_values:
                            opposite_index = seen_values[(past_period, -value)]
                            rows_to_remove.add(index)
                            rows_to_remove.add(opposite_index)
                            del seen_values[(past_period, -value)]
                            break
                    else:
                        # No se encontró coincidencia, mantener el valor negativo
                        seen_values[(period, value)] = index
            else:
                seen_values[(period, value)] = index
        
        # Convertir el set a una lista para indexar
        rows_to_remove_list = list(rows_to_remove)
        
        # Eliminar las filas identificadas y almacenar en removed_df
        group_filtered = group.drop(rows_to_remove_list)
        removed_rows = group.loc[rows_to_remove_list]
        removed_df = pd.concat([removed_df, removed_rows])
        filtered_df = pd.concat([filtered_df, group_filtered])
    
    return filtered_df, removed_df

# Cargar los datos
data0 = load_data(DATA0_URL)
budget_data = load_data(BUDGET_URL)
orders_data = load_data(ORDERS_URL)

# Procesamiento de data0
data0 = eliminar_filas_grupo_ceco(data0)
data0, removed_data = eliminar_pares_opuestos(data0)

# Asegurarse de que 'Ejercicio' y 'Período' son de tipo string
data0['Ejercicio'] = data0['Ejercicio'].astype(str)
data0['Período'] = data0['Período'].astype(str)
budget_data['Año'] = budget_data['Año'].astype(str)
budget_data['Mes'] = budget_data['Mes'].astype(str)

# Función para convertir DataFrame a CSV
def convertir_a_csv(df):
    buffer = io.StringIO()
    df.to_csv(buffer, index=False, sep=';')
    buffer.seek(0)
    return buffer.getvalue()

# Generar el enlace de descarga para las filas eliminadas
# csv_removed_data = convertir_a_csv(removed_data)

# Agregar un botón de descarga en la aplicación
#st.download_button(
#    label="Descargar Filas Eliminadas",
#    data=csv_removed_data,
#    file_name='filas_eliminadas.csv',
#    mime='text/csv',
#)

# Filtro lateral para seleccionar Sociedad
with st.sidebar:
    st.header("Parámetros")
    opciones_año = ['2024'] + sorted(data0['Ejercicio'].unique())
    opcion_año = st.selectbox('Año', opciones_año)

    opciones_area = ['Todos'] + sorted(data0['Area'].unique())
    opcion_area = st.selectbox('Area', opciones_area)

    opciones_fam_cuenta = ['Todos'] + sorted(data0['Familia_Cuenta'].unique())
    opcion_fam_cuenta = st.selectbox('Familia_Cuenta', opciones_fam_cuenta)

    opciones_clase_coste = ['Todos'] + sorted(data0['Clase de coste'].unique())
    opcion_clase_coste = st.selectbox('Clase de coste', opciones_clase_coste)

    opciones_grupo_ceco = ['Todos'] + sorted(data0['Grupo_Ceco'].unique())
    opcion_grupo_ceco = st.selectbox('Grupo_Ceco', opciones_grupo_ceco)

# Aplicar los filtros seleccionados a ambos DataFrames
def aplicar_filtros(data, opcion_año, opcion_area, opcion_fam_cuenta, opcion_clase_coste, opcion_grupo_ceco, col_año):
    if opcion_año != 'Todos':
        data = data[data[col_año] == opcion_año]
    if opcion_area != 'Todos':
        data = data[data['Area'] == opcion_area]
    if opcion_fam_cuenta != 'Todos':
        data = data[data['Familia_Cuenta'] == opcion_fam_cuenta]
    if opcion_clase_coste != 'Todos':
        data = data[data['Clase de coste'] == opcion_clase_coste]
    if opcion_grupo_ceco != 'Todos':
        data = data[data['Grupo_Ceco'] == opcion_grupo_ceco]
    return data

# Filtrar los datos
data0 = aplicar_filtros(data0, opcion_año, opcion_area, opcion_fam_cuenta, opcion_clase_coste, opcion_grupo_ceco, 'Ejercicio')
budget_data = aplicar_filtros(budget_data, opcion_año, opcion_area, opcion_fam_cuenta, opcion_clase_coste, opcion_grupo_ceco, 'Año')

# Comentar las tablas de datos filtrados
# st.write("Datos filtrados de gasto real:", data0.head())
# st.write("Datos filtrados de presupuesto:", budget_data.head())

# Calcular las sumas por año y mes para Gasto Real y Gasto Presupuestado
gasto_real = data0.groupby(['Ejercicio', 'Período'])['Valor/mon.inf.'].sum().reset_index()
gasto_real['Valor/mon.inf.'] = (gasto_real['Valor/mon.inf.'] / 1000000).round(1)  # Convertir a millones con un decimal
gasto_real = gasto_real.rename(columns={'Ejercicio': 'Año', 'Período': 'Mes'})

# Comentar tabla de gastos agrupados
# st.write("Gasto real agrupado y convertido:", gasto_real.head())

gasto_presupuestado = budget_data.groupby(['Año', 'Mes'])['Presupuesto'].sum().reset_index()
gasto_presupuestado['Presupuesto'] = gasto_presupuestado['Presupuesto'].round(1)

# Comentar tabla de gastos presupuestados agrupados
# st.write("Gasto presupuestado agrupado:", gasto_presupuestado.head())

# Asegurarse de que las columnas son del mismo tipo
gasto_real['Año'] = gasto_real['Año'].astype(str)
gasto_real['Mes'] = gasto_real['Mes'].astype(int)  # Convertir a entero para orden correcto
gasto_presupuestado['Año'] = gasto_presupuestado['Año'].astype(str)
gasto_presupuestado['Mes'] = gasto_presupuestado['Mes'].astype(int)  # Convertir a entero para orden correcto

# Crear la tabla combinada
combined_data = pd.merge(gasto_real, gasto_presupuestado, on=['Año', 'Mes'], how='outer').fillna(0)

# Comentar la tabla de datos combinados
# st.write("Datos combinados:", combined_data.head())

combined_data['Diferencia'] = combined_data['Valor/mon.inf.'] - combined_data['Presupuesto']

# Ordenar las columnas de manera ascendente
combined_data = combined_data.sort_values(by=['Año', 'Mes'])

# Mostrar las tablas en la aplicación Streamlit
#st.markdown("#### ANÁLISIS DE GASTO Y PRESUPUESTO")

# Tabla combinada
st.markdown("#### Tabla de Gasto Real vs Presupuestado")

# Ocultar la primera fila de año y ordenar las columnas
combined_data_display = combined_data.drop(columns=['Año']).set_index(['Mes'])
combined_data_display.columns.name = None  # Eliminar el nombre de las columnas
combined_data_display.index = combined_data_display.index.map(str)  # Convertir índice a string para visualización
st.dataframe(combined_data_display.T)

# Nueva sección: Widgets de Gasto Acumulado
st.markdown("### Gasto Acumulado")

# Calcular el gasto acumulado real
ultimo_mes_real = gasto_real['Mes'].max()
gasto_acumulado_real = gasto_real[gasto_real['Mes'] <= ultimo_mes_real]['Valor/mon.inf.'].sum()

# Verificar si hay datos presupuestados antes de calcular el gasto acumulado presupuestado
if not gasto_presupuestado[gasto_presupuestado['Mes'] <= ultimo_mes_real].empty:
    gasto_acumulado_presupuestado = gasto_presupuestado[gasto_presupuestado['Mes'] <= ultimo_mes_real]['Presupuesto'].sum()
else:
    gasto_acumulado_presupuestado = None

# Aplicar lógica de colores
if gasto_acumulado_presupuestado is not None and gasto_acumulado_presupuestado != 0:
    diferencia_porcentaje = (gasto_acumulado_real / gasto_acumulado_presupuestado) * 100

    if diferencia_porcentaje <= 100:
        color_real = 'background-color: green;'
        color_presupuesto = 'background-color: green;'
    elif 100 < diferencia_porcentaje <= 110:
        color_real = 'background-color: yellow;'
        color_presupuesto = 'background-color: yellow;'
    else:
        color_real = 'background-color: red;'
        color_presupuesto = 'background-color: red;'
else:
    color_real = 'background-color: grey;'
    color_presupuesto = 'background-color: grey;'

# Mostrar los widgets alineados horizontalmente
col1, col2 = st.columns(2)

col1.markdown(f"<div style='{color_real} padding: 10px; border-radius: 5px; text-align: center;'>Gasto acumulado real<br><strong>${gasto_acumulado_real:.1f}M</strong></div>", unsafe_allow_html=True)
if gasto_acumulado_presupuestado is not None:
    col2.markdown(f"<div style='{color_presupuesto} padding: 10px; border-radius: 5px; text-align: center;'>Gasto acumulado presupuestado<br><strong>${gasto_acumulado_presupuestado:.1f}M</strong></div>", unsafe_allow_html=True)
else:
    col2.markdown(f"<div style='{color_presupuesto} padding: 10px; border-radius: 5px; text-align: center;'>Gasto acumulado presupuestado<br><strong>No disponible</strong></div>", unsafe_allow_html=True)

# Nueva sección: Tabla de los 10 mayores gastos
st.markdown("### Mayores Gastos")

# Filtrar y ordenar data0 para obtener los 10 mayores gastos
data0_sorted = data0.sort_values(by='Valor/mon.inf.', ascending=False)
top_10_gastos = data0_sorted.head(10)

# Seleccionar columnas específicas para mostrar
top_10_gastos_display = top_10_gastos[['Centro de coste', 'Denominación del objeto', 'Grupo_Ceco', 'Fe.contabilización', 'Valor/mon.inf.']]

# Mostrar la tabla en la aplicación Streamlit
st.dataframe(top_10_gastos_display)

# Nueva sección: Widgets de Gasto con y sin OT
st.markdown("### Gasto con y sin OT")

# Calcular gasto con OT
gasto_con_ot = data0[data0['Orden partner'].notna()]['Valor/mon.inf.'].sum()

# Calcular gasto sin OT
gasto_sin_ot = data0[data0['Orden partner'].isna()]['Valor/mon.inf.'].sum()

# Mostrar los widgets alineados horizontalmente
col1, col2 = st.columns(2)

col1.markdown(f"<div style='border: 2px solid black; padding: 10px; border-radius: 5px; text-align: center;'>Gasto con OT<br><strong>${gasto_con_ot:,.0f}M</strong></div>", unsafe_allow_html=True)
col2.markdown(f"<div style='border: 2px solid black; padding: 10px; border-radius: 5px; text-align: center;'>Gasto sin OT<br><strong>${gasto_sin_ot:,.0f}M</strong></div>", unsafe_allow_html=True)

# Nueva sección: Tabla de Tipos de Orden
st.markdown("### Tipos de Orden")

# Unir data0 con orders_data para obtener el tipo de orden
data0 = data0.merge(orders_data, how='left', left_on='Orden partner', right_on='Orden')

# Calcular las métricas para cada tipo de orden
tipo_orden_metrics = data0.groupby('Clase de orden').agg(
    cantidad_ordenes=pd.NamedAgg(column='Orden partner', aggfunc='count'),
    gasto=pd.NamedAgg(column='Valor/mon.inf.', aggfunc='sum')
).reset_index()

# Calcular el valor OT medio
tipo_orden_metrics['valor_ot_media'] = tipo_orden_metrics['gasto'] / tipo_orden_metrics['cantidad_ordenes']

# Seleccionar columnas específicas para mostrar
tipo_orden_metrics_display = tipo_orden_metrics[['Clase de orden', 'cantidad_ordenes', 'gasto', 'valor_ot_media']]

# Renombrar las columnas para la visualización
tipo_orden_metrics_display.columns = ['Tipo de orden', 'Cantidad de ordenes', 'Gasto', 'Valor OT media']

# Redondear valor_ot_media a 0 decimales
tipo_orden_metrics_display['Valor OT media'] = tipo_orden_metrics_display['Valor OT media'].round(0).astype(int)

# Mostrar la tabla en la aplicación Streamlit
st.dataframe(tipo_orden_metrics_display)

# Gráfico de Líneas para Gasto Acumulado
st.markdown("### Gráfico de Gasto Acumulado")

fig_acumulado = go.Figure()
fig_acumulado.add_trace(go.Scatter(x=combined_data['Mes'], y=combined_data['Valor/mon.inf.'].cumsum(), mode='lines+markers', name='Gasto Acumulado Real'))
fig_acumulado.add_trace(go.Scatter(x=combined_data['Mes'], y=combined_data['Presupuesto'].cumsum(), mode='lines+markers', name='Gasto Acumulado Presupuestado'))
fig_acumulado.update_layout(title='Evolución del Gasto Acumulado Real vs Presupuestado', xaxis_title='Mes', yaxis_title='Gasto Acumulado (Millones)')
st.plotly_chart(fig_acumulado)

# Gráfico de Columnas Apiladas con Presupuesto
st.markdown("### Gráfico de Gasto Real por Tipo de Orden y Presupuesto")

# Preparar los datos para el gráfico de columnas apiladas
data0['Mes'] = data0['Período'].astype(int)
data0_grouped = data0.groupby(['Mes', 'Clase de orden'])['Valor/mon.inf.'].sum().reset_index()
data0_pivot = data0_grouped.pivot(index='Mes', columns='Clase de orden', values='Valor/mon.inf.').fillna(0)

# Agregar la columna de presupuesto y multiplicar por 1,000,000
data0_pivot['Presupuesto'] = combined_data.set_index('Mes')['Presupuesto'] * 1000000

fig_columnas = go.Figure()

# Añadir las columnas apiladas por tipo de orden
for column in data0_pivot.columns:
    if column != 'Presupuesto':
        fig_columnas.add_trace(go.Bar(x=data0_pivot.index, y=data0_pivot[column], name=column))

# Añadir la línea de presupuesto
fig_columnas.add_trace(go.Scatter(x=data0_pivot.index, y=data0_pivot['Presupuesto'], mode='lines+markers', name='Presupuesto', line=dict(color='grey', width=2, dash='dash')))

fig_columnas.update_layout(barmode='stack', title='Gasto Real por Tipo de Orden vs Presupuesto', xaxis_title='Mes', yaxis_title='Gasto', legend_title='Tipo de Orden')
st.plotly_chart(fig_columnas)
