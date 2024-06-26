import streamlit as st
import pandas as pd

# Título de la aplicación
st.markdown("<h1 style='text-align: center; color: black; font-size: 24px;'>MONITOR GESTIÓN PRESUPUESTARIA</h1>", unsafe_allow_html=True)

# Definimos la URL del archivo de referencia
DATA0_URL = 'https://streamlitmaps.s3.amazonaws.com/Data_0524.csv'

# Función para cargar el archivo de referencia
@st.cache_data
def load_data0():
    data0 = pd.read_csv(DATA0_URL, encoding='ISO-8859-1', sep=';')
    data0['Valor/mon.inf.'] = pd.to_numeric(data0['Valor/mon.inf.'].str.replace(',', ''), errors='coerce').fillna(0)
    return data0

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

# Cargamos el archivo de referencia
data0 = load_data0()

# Eliminamos filas con valores específicos en "Grupo_Ceco"
data0 = eliminar_filas_grupo_ceco(data0)

# Identificamos y eliminamos pares de valores opuestos
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

# Aplicar los filtros seleccionados
if opcion_año != 'Todos':
    data0 = data0[data0['Ejercicio'] == opcion_año]
if opcion_area != 'Todos':
    data0 = data0[data0['Area'] == opcion_area]
if opcion_fam_cuenta != 'Todos':
    data0 = data0[data0['Familia_Cuenta'] == opcion_fam_cuenta]
if opcion_clase_coste != 'Todos':
    data0 = data0[data0['Clase de coste'] == opcion_clase_coste]
if opcion_grupo_ceco != 'Todos':
    data0 = data0[data0['Grupo_Ceco'] == opcion_grupo_ceco]

# Visualización de los datos filtrados
st.write(data0)
