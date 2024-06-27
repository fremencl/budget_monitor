import streamlit as st
import pandas as pd

# Título de la aplicación
st.markdown("<h1 style='text-align: center; color: black; font-size: 24px;'>MONITOR GESTIÓN PRESUPUESTARIA</h1>", unsafe_allow_html=True)

# Definimos las URLs de los archivos de referencia
DATA0_URL = 'https://streamlitmaps.s3.amazonaws.com/Data_0524.csv'
BUDGET_URL = 'https://streamlitmaps.s3.amazonaws.com/Base_Presupuesto.csv'

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
    groups = data.groupby(['Clase de coste', 'Centro de coste'])
    
    for name, group in groups:
        seen_values = {}
        rows_to_remove = set()
        
        for index, row in group.iterrows():
            value = row['Valor/mon.inf.']
            if -value in seen_values:
                opposite_index = seen_values[-value]
                rows_to_remove.add(index)
                rows_to_remove.add(opposite_index)
                del seen_values[-value]
            else:
                if index not in rows_to_remove:
                    seen_values[value] = index
            
        group_filtered = group.drop(rows_to_remove)
        filtered_df = pd.concat([filtered_df, group_filtered])
    
    return filtered_df

# Cargar los datos
data0 = load_data(DATA0_URL)
budget_data = load_data(BUDGET_URL)

# Procesamiento de data0
data0 = eliminar_filas_grupo_ceco(data0)
data0 = eliminar_pares_opuestos(data0)

# Asegurarse de que 'Ejercicio' y 'Período' son de tipo string
data0['Ejercicio'] = data0['Ejercicio'].astype(str)
data0['Período'] = data0['Período'].astype(str)
budget_data['Año'] = budget_data['Año'].astype(str)
budget_data['Mes'] = budget_data['Mes'].astype(str)

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
st.markdown("### ANÁLISIS DE GASTO Y PRESUPUESTO")

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

# Calcular el gasto acumulado presupuestado
gasto_acumulado_presupuestado = gasto_presupuestado[gasto_presupuestado['Mes'] <= ultimo_mes_real]['Presupuesto'].sum()

# Aplicar lógica de colores
diferencia_porcentaje = (gasto_acumulado_real / gasto_acumulado_presupuestado) * 100

if diferencia_porcentaje <= 100:
    color_real = 'green'
    color_presupuesto = 'green'
elif 100 < diferencia_porcentaje <= 110:
    color_real = 'yellow'
    color_presupuesto = 'yellow'
else:
    color_real = 'red'
    color_presupuesto = 'red'

# Mostrar los widgets alineados horizontalmente
col1, col2 = st.columns(2)

col1.metric(label="Gasto acumulado real", value=f"${gasto_acumulado_real:.1f}M", delta=None, delta_color=color_real)
col2.metric(label="Gasto acumulado presupuestado", value=f"${gasto_acumulado_presupuestado:.1f}M", delta=None, delta_color=color_presupuesto)
