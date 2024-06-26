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

# Filtro lateral para seleccionar Sociedad
with st.sidebar:
    st.header("Parámetros")
    opciones_año = ['Todos'] + list(data0['Ejercicio'].unique())
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
def aplicar_filtros(data, opcion_año, opcion_area, opcion_fam_cuenta, opcion_clase_coste, opcion_grupo_ceco):
    if opcion_año != 'Todos':
        data = data[data['Ejercicio'] == opcion_año]
    if opcion_area != 'Todos':
        data = data[data['Area'] == opcion_area]
    if opcion_fam_cuenta != 'Todos':
        data = data[data['Familia_Cuenta'] == opcion_fam_cuenta]
    if opcion_clase_coste != 'Todos':
        data = data[data['Clase de coste'] == opcion_clase_coste]
    if opcion_grupo_ceco != 'Todos':
        data = data[data['Grupo_Ceco'] == opcion_grupo_ceco]
    return data

data0 = aplicar_filtros(data0, opcion_año, opcion_area, opcion_fam_cuenta, opcion_clase_coste, opcion_grupo_ceco)
budget_data = aplicar_filtros(budget_data, opcion_año, opcion_area, opcion_fam_cuenta, opcion_clase_coste, opcion_grupo_ceco)

# Calcular las sumas por mes para Gasto Real y Gasto Presupuestado
gasto_real = data0.groupby('Período')['Valor/mon.inf.'].sum().reset_index()
gasto_real['Valor/mon.inf.'] = (gasto_real['Valor/mon.inf.'] / 1000000).round(1)

gasto_presupuestado = budget_data.groupby('Mes')['Presupuesto'].sum().reset_index()
gasto_presupuestado['Presupuesto'] = gasto_presupuestado['Presupuesto'].round(1)

# Mostrar las tablas en la aplicación Streamlit
st.markdown("### ANÁLISIS DE GASTO Y PRESUPUESTO")

# Tabla de Gasto Real
st.markdown("#### Tabla de Gasto Real")
st.dataframe(gasto_real.set_index('Mes').T)

# Tabla de Gasto Presupuestado
st.markdown("#### Tabla de Gasto Presupuestado")
st.dataframe(gasto_presupuestado.set_index('Mes').T)
