import streamlit as st
import pandas as pd
import io
import plotly.express as px
import plotly.graph_objects as go

# Título de la aplicación
st.markdown("<h1 style='text-align: center; color: black; font-size: 24px;'>MONITOR GESTIÓN PRESUPUESTARIA</h1>", unsafe_allow_html=True)

# Definimos las URLs de los archivos de referencia
DATA0_URL = 'https://streamlitmaps.s3.amazonaws.com/Data_0524.csv'
BUDGET_URL = 'https://streamlitmaps.s3.amazonaws.com/Base_Presupuesto_2.csv'
ORDERS_URL = 'https://streamlitmaps.s3.amazonaws.com/Base_Ordenes_3.csv'
BASE_UTEC_URL = 'https://streamlitmaps.s3.amazonaws.com/Base_UTEC_BudgetVersion.csv'
BASE_CECO_URL = 'https://streamlitmaps.s3.amazonaws.com/Base_Ceco_3.csv'

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

# Función para convertir DataFrame a CSV
def convertir_a_csv(df):
    buffer = io.StringIO()
    df.to_csv(buffer, index=False, sep=';')
    buffer.seek(0)
    return buffer.getvalue()

# Cargar los datos
data0 = load_data(DATA0_URL)
data0['id'] = range(1, len(data0) + 1)
budget_data = load_data(BUDGET_URL)
orders_data = load_data(ORDERS_URL)
base_utec_data = load_data(BASE_UTEC_URL)
base_ceco_data = load_data(BASE_CECO_URL)

# Verificar que las columnas necesarias están presentes en los DataFrames cargados
assert 'Orden' in orders_data.columns, "La columna 'Orden' no está presente en orders_data"
assert 'Utec' in orders_data.columns, "La columna 'Utec' no está presente en orders_data"
assert 'Utec' in base_utec_data.columns, "La columna 'Utec' no está presente en base_utec_data"
assert 'Proceso' in base_utec_data.columns, "La columna 'Proceso' no está presente en base_utec_data"
assert 'Recinto' in base_utec_data.columns, "La columna 'Recinto' no está presente en base_utec_data"
assert 'Ceco' in base_ceco_data.columns, "La columna 'Ceco' no está presente en base_ceco_data"
assert 'Proceso' in base_ceco_data.columns, "La columna 'Proceso' no está presente en base_ceco_data"
assert 'Recinto' in base_ceco_data.columns, "La columna 'Recinto' no está presente en base_ceco_data"

# Asegurarse de que 'Ejercicio' y 'Período' son de tipo string
data0['Ejercicio'] = data0['Ejercicio'].astype(str)
data0['Período'] = data0['Período'].astype(str)
budget_data['Año'] = budget_data['Año'].astype(str)
budget_data['Mes'] = budget_data['Mes'].astype(str)

# Agregar nuevas columnas a data0
data0['Utec'] = None
data0['Proceso'] = None
data0['Recinto'] = None

# Convertir la columna 'Período' y 'Valor/mon.inf.' a tipo numérico
data0['Período'] = pd.to_numeric(data0['Período'], errors='coerce')
data0['Valor/mon.inf.'] = pd.to_numeric(data0['Valor/mon.inf.'], errors='coerce')

# Primer mapeo: Asignar Utec utilizando ORDERS_URL
if 'Orden partner' in data0.columns and 'Orden' in orders_data.columns:
    data0 = data0.merge(orders_data[['Orden', 'Utec']], how='left', left_on='Orden partner', right_on='Orden', suffixes=('_original', '_merged'))
    if 'Utec_merged' in data0.columns:
        data0['Utec'] = data0['Utec_merged']
        data0.drop(columns=['Utec_original', 'Utec_merged'], inplace=True)
    else:
        st.error("No se encontraron las columnas necesarias para el primer mapeo ('Utec')")
else:
    st.error("No se encontraron las columnas necesarias para el primer mapeo")

# Verificar si data0 es un DataFrame
if not isinstance(data0, pd.DataFrame):
    st.error("data0 no es un DataFrame después del primer mapeo")

# Segundo mapeo: Asignar Proceso utilizando Base_UTEC_BudgetVersion.csv
if 'Utec' in data0.columns:
    data0 = data0.merge(base_utec_data[['Utec', 'Proceso']], how='left', on='Utec', suffixes=('_original', '_merged'))
    if 'Proceso_merged' in data0.columns:
        data0['Proceso'] = data0['Proceso_merged']
        data0.drop(columns=['Proceso_original', 'Proceso_merged'], inplace=True)
    else:
        st.error("No se encontraron las columnas necesarias para el segundo mapeo")
else:
    st.error("No se encontraron las columnas necesarias para el segundo mapeo")

# Verificar si data0 es un DataFrame
if not isinstance(data0, pd.DataFrame):
    st.error("data0 no es un DataFrame después del primer mapeo")

# Asignar Recinto utilizando Base_UTEC_BudgetVersion.csv
if 'Utec' in data0.columns:
    data0 = data0.merge(base_utec_data[['Utec', 'Recinto']], how='left', on='Utec', suffixes=('_original', '_merged'))
    if 'Recinto_merged' in data0.columns:
        data0['Recinto'] = data0['Recinto_merged']
        data0.drop(columns=['Recinto_original', 'Recinto_merged'], inplace=True)
    else:
        st.error("No se encontraron las columnas necesarias para el tercer mapeo")
else:
    st.error("No se encontraron las columnas necesarias para el tercer mapeo")

# Asegurarse de que data0 es un DataFrame
if isinstance(data0, pd.DataFrame):
    # Convertir temporalmente 'Período' a tipo numérico para eliminar pares opuestos
    data0['Período'] = pd.to_numeric(data0['Período'], errors='coerce')
    
    # Ejecutar `eliminar_pares_opuestos`
    data0, removed_data = eliminar_pares_opuestos(data0)  # Capturar ambos DataFrames
    
    # Convertir 'Período' de vuelta a cadena si es necesario
    # data0['Período'] = data0['Período'].astype(str)
else:
    st.error("data0 no es un DataFrame")

# Procesamiento de data0
if isinstance(data0, pd.DataFrame):
    data0 = eliminar_filas_grupo_ceco(data0)
else:
    st.error("data0 no es un DataFrame antes de eliminar filas con valores específicos en 'Grupo_Ceco'")

# Filtrar filas sin Proceso y Recinto completos
data0_incomplete = data0[(data0['Proceso'].isna()) & (data0['Recinto'].isna())].copy()

# Convertir columnas a string
data0_incomplete['Centro de coste'] = data0_incomplete['Centro de coste'].astype(str)
base_ceco_data['Ceco'] = base_ceco_data['Ceco'].astype(str)
base_ceco_data['Recinto'] = base_ceco_data['Recinto'].astype(str)
base_ceco_data['Proceso'] = base_ceco_data['Proceso'].astype(str)

# Verificar si data0 es un DataFrame
if not isinstance(data0_incomplete, pd.DataFrame):
    st.error("data0_incomplete no es un DataFrame después del mapeo ceco")

# Mapeo de Proceso utilizando Base_Ceco_2.csv
if 'Centro de coste' in data0_incomplete.columns:
    data0_incomplete = data0_incomplete.merge(base_ceco_data[['Ceco', 'Proceso']], how='left', left_on='Centro de coste', right_on='Ceco')
    if 'Proceso_y' in data0_incomplete.columns:
        data0_incomplete['Proceso'] = data0_incomplete['Proceso_y']
        data0_incomplete.drop(columns=['Proceso_y', 'Proceso_x', 'Ceco'], inplace=True)
else:
    st.error("No se encontraron las columnas necesarias para el mapeo de Proceso")

# Mapeo de Recinto utilizando Base_Ceco_2.csv
if 'Centro de coste' in data0_incomplete.columns:
    data0_incomplete = data0_incomplete.merge(base_ceco_data[['Ceco', 'Recinto']], how='left', left_on='Centro de coste', right_on='Ceco')
    if 'Recinto_y' in data0_incomplete.columns:
        data0_incomplete['Recinto'] = data0_incomplete['Recinto_y']
        data0_incomplete.drop(columns=['Recinto_y', 'Recinto_x', 'Ceco'], inplace=True)
else:
    st.error("No se encontraron las columnas necesarias para el mapeo de Recinto")

# Limpieza y normalización de los valores antes del merge
data0['Centro de coste'] = data0['Centro de coste'].str.strip().str.upper()
data0_incomplete['Centro de coste'] = data0_incomplete['Centro de coste'].str.strip().str.upper()

combined_data = data0.merge(
    data0_incomplete[['Centro de coste', 'Proceso', 'Recinto', 'id']],
    on=['Centro de coste', 'id'],
    how='left',
    suffixes=('', '_incomplete')
)

# Actualizar los valores de 'Proceso' y 'Recinto' en data0
combined_data['Proceso'] = combined_data['Proceso'].combine_first(combined_data['Proceso_incomplete'])
combined_data['Recinto'] = combined_data['Recinto'].combine_first(combined_data['Recinto_incomplete'])

combined_data.drop(columns=['Proceso_incomplete', 'Recinto_incomplete'], inplace=True)

# Asignar el DataFrame resultante a data0
data0 = combined_data

# Convertir todos los valores en la columna 'Proceso' a cadenas para evitar el error de ordenación
data0['Proceso'] = data0['Proceso'].astype(str)
data0['Recinto'] = data0['Recinto'].astype(str)

# Generar el enlace de descarga para las filas procesadas
#csv_procesed_data = convertir_a_csv(combined_data)

# Agregar un botón de descarga en la aplicación
#st.download_button(
    #label="Descargar_procesed_data",
    #data=csv_procesed_data,
    #file_name='filas_procesed_data.csv',
    #mime='text/csv',
#)

# Filtros Laterales
with st.sidebar:
    st.header("Parámetros")
    opcion_año = st.selectbox('Año', ['2024'] + sorted(data0['Ejercicio'].unique()))
    
    opciones_proceso = ['Todos'] + [proceso for proceso in sorted(data0['Proceso'].unique()) if proceso != 'Overhead']
    opcion_proceso = st.selectbox('Proceso', opciones_proceso)
    
    opciones_fam_cuenta = ['Todos'] + sorted(data0['Familia_Cuenta'].unique())
    opcion_fam_cuenta = st.selectbox('Familia_Cuenta', opciones_fam_cuenta)
    
    opciones_clase_coste = ['Todos'] + sorted(data0['Clase de coste'].unique())
    opcion_clase_coste = st.selectbox('Clase de coste', opciones_clase_coste)
    
    opciones_recinto = ['Todos'] + [recinto for recinto in sorted(data0['Recinto'].unique()) if recinto != 'Overhead']
    opcion_recinto = st.selectbox('Recinto', opciones_recinto)

# Aplicar filtros seleccionados a los DataFrames
def aplicar_filtros(data, opcion_año, opcion_proceso, opcion_fam_cuenta, opcion_clase_coste, opcion_recinto, col_año):
    if opcion_año != 'Todos':
        data = data[data[col_año] == opcion_año]
    if opcion_proceso != 'Todos':
        data = data[data['Proceso'] == opcion_proceso]
    if opcion_fam_cuenta != 'Todos':
        data = data[data['Familia_Cuenta'] == opcion_fam_cuenta]
    if opcion_clase_coste != 'Todos':
        data = data[data['Clase de coste'] == opcion_clase_coste]
    if opcion_recinto != 'Todos':
        data = data[data['Recinto'] == opcion_recinto]
    return data

data0 = aplicar_filtros(data0, opcion_año, opcion_proceso, opcion_fam_cuenta, opcion_clase_coste, opcion_recinto, 'Ejercicio')
budget_data = aplicar_filtros(budget_data, opcion_año, opcion_proceso, opcion_fam_cuenta, opcion_clase_coste, opcion_recinto, 'Año')

# Paso 1: Calcular el gasto real de "Overhead" por año y período
gasto_real_overhead = data0[data0['Proceso'] == 'Overhead'].groupby(['Ejercicio', 'Período'])['Valor/mon.inf.'].sum().reset_index()
gasto_real_overhead = gasto_real_overhead.rename(columns={'Valor/mon.inf.': 'Overhead'})

# Paso 2: Calcular el gasto real sin "Overhead" por año y período
gasto_real_sin_overhead = data0[data0['Proceso'] != 'Overhead'].groupby(['Ejercicio', 'Período'])['Valor/mon.inf.'].sum().reset_index()

# Paso 3: Calcular las proporciones del gasto sin "Overhead" por año y período
proporciones = data0[data0['Proceso'] != 'Overhead'].groupby(['Ejercicio', 'Período', 'Proceso'])['Valor/mon.inf.'].sum() / data0[data0['Proceso'] != 'Overhead'].groupby(['Ejercicio', 'Período'])['Valor/mon.inf.'].sum().reset_index(drop=True)

# Paso 4: Distribuir el gasto "Overhead" proporcionalmente por año y período
gasto_real_overhead = gasto_real_overhead.merge(proporciones.reset_index(), on=['Ejercicio', 'Período'], how='left')
gasto_real_overhead['Distribuido'] = gasto_real_overhead['Overhead'] * gasto_real_overhead['Valor/mon.inf.']

# Paso 5: Sumar la distribución proporcional del gasto "Overhead" al gasto real sin "Overhead"
gasto_real_ajustado = gasto_real_sin_overhead.merge(gasto_real_overhead[['Ejercicio', 'Período', 'Distribuido']], on=['Ejercicio', 'Período'], how='left')
gasto_real_ajustado['Valor/mon.inf.'] += gasto_real_ajustado['Distribuido']

# Convertir a millones y renombrar columnas
gasto_real_ajustado['Valor/mon.inf.'] = (gasto_real_ajustado['Valor/mon.inf.'] / 1000000).round(1)
gasto_real = gasto_real_ajustado.rename(columns={'Ejercicio': 'Año', 'Período': 'Mes'})

# Eliminar filas correspondientes a "Overhead"
data0 = data0[data0['Proceso'] != 'Overhead']

# Verificación final: imprimir el gasto real ajustado con "Overhead" distribuido
st.write("Gasto Real Ajustado con Overhead por Año y Período:")
st.write(gasto_real)

gasto_presupuestado = budget_data.groupby(['Año', 'Mes'])['Presupuesto'].sum().reset_index()
gasto_presupuestado['Presupuesto'] = gasto_presupuestado['Presupuesto'].round(1)

# Asegurarse de que las columnas son del mismo tipo
gasto_real['Año'] = gasto_real['Año'].astype(str)
gasto_real['Mes'] = gasto_real['Mes'].astype(int)  # Convertir a entero para orden correcto
gasto_presupuestado['Año'] = gasto_presupuestado['Año'].astype(str)
gasto_presupuestado['Mes'] = gasto_presupuestado['Mes'].astype(int)  # Convertir a entero para orden correcto

# Crear la tabla combinada
combined_data = pd.merge(gasto_real, gasto_presupuestado, on=['Año', 'Mes'], how='outer').fillna(0)

combined_data['Diferencia'] = combined_data['Valor/mon.inf.'] - combined_data['Presupuesto']

# Ordenar las columnas de manera ascendente
combined_data = combined_data.sort_values(by=['Año', 'Mes'])

# Tabla combinada
st.markdown("#### Tabla de Gasto Real vs Presupuestado")

# Ocultar la primera fila de año y ordenar las columnas
combined_data_display = combined_data.drop(columns=['Año']).set_index(['Mes'])
combined_data_display.columns.name = None  # Eliminar el nombre de las columnas
combined_data_display.index = combined_data_display.index.map(str)  # Convertir índice a string para visualización
st.dataframe(combined_data_display.T)

# Nueva sección: Widgets de Gasto Acumulado
st.markdown("#### Gasto Acumulado")

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

# Nueva sección: Tabla de los 5 mayores gastos
st.markdown("#### Top 5 Mayores Gastos")

# Filtrar y ordenar data0 para obtener los 5 mayores gastos
data0_sorted = data0.sort_values(by='Valor/mon.inf.', ascending=False)
top_5_gastos = data0_sorted.head(5)

# Seleccionar columnas específicas para mostrar
top_5_gastos_display = top_5_gastos[['Centro de coste', 'Denominación del objeto', 'Grupo_Ceco', 'Fe.contabilización', 'Valor/mon.inf.']]

# Mostrar la tabla en la aplicación Streamlit
st.dataframe(top_5_gastos_display)

# Nueva sección: Widgets de Gasto con y sin OT
st.markdown("#### Gasto con y sin OT")

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
