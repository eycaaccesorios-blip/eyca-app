import streamlit as st
import pandas as pd
from datetime import datetime
from PIL import Image
import os
from streamlit_gsheets import GSheetsConnection

# 1. CONFIGURACIÓN ÚNICA DE PÁGINA
st.set_page_config(page_title="Eyca Accesorios", layout="wide")

# 2. SEGURIDAD (Se define aquí, se usa abajo)
def login():
    if "autenticado" not in st.session_state:
        st.session_state.autenticado = False

    if not st.session_state.autenticado:
        st.title("🔐 Acceso Mayorista - Eyca")
        clave_ingresada = st.text_input("Introduce la clave:", type="password")
        if st.button("Entrar"):
            if clave_ingresada == st.secrets["clave_bodega"]:
                st.session_state.autenticado = True
                st.rerun()
            else:
                st.error("❌ Clave incorrecta")
        return False
    return True

# 3. PERSISTENCIA DE DATOS LOCALES (Hasta que termines la conexión a Sheets)
if 'inventario' not in st.session_state:
    if os.path.exists('inventario.csv'):
        st.session_state.inventario = pd.read_csv('inventario.csv', index_col='Codigo')
    else:
        st.session_state.inventario = pd.DataFrame(columns=['Nombre', 'Precio', 'Stock', 'Categoria', 'Foto'])
        st.session_state.inventario.index.name = 'Codigo'

if 'carrito' not in st.session_state:
    st.session_state.carrito = []

def guardar_datos():
    st.session_state.inventario.to_csv('inventario.csv')

# --- MENÚ PRINCIPAL ---
menu_principal = st.sidebar.radio("Navegación", ["✨ Catálogo Público", "🔐 Área de Bodega (Privado)"])

# --- SECCIÓN 1: CATÁLOGO PÚBLICO ---
if menu_principal == "✨ Catálogo Público":
    st.title("💍 Catálogo Eyca Accesorios")
    st.markdown("### Tendencias 2026")
    
    items = st.session_state.inventario
    if not items.empty:
        cat_filtro = st.multiselect("Filtrar por categoría", items["Categoria"].unique())
        if cat_filtro:
            items = items[items["Categoria"].isin(cat_filtro)]

        cols = st.columns(3)
        for i, (idx, row) in enumerate(items.iterrows()):
            with cols[i % 3]:
                if os.path.exists(str(row['Foto'])):
                    st.image(row['Foto'], use_container_width=True)
                else:
                    st.write("📸 Foto próximamente")
                st.write(f"**{row['Nombre']}**")
                st.write(f"Ref: {idx}")
                st.write("---")
    else:
        st.info("El catálogo está siendo actualizado. ¡Vuelve pronto!")

# --- SECCIÓN 2: ÁREA DE BODEGA (Privado) ---
elif menu_principal == "🔐 Área de Bodega (Privado)":
    if not login():
        st.stop()
    
    st.sidebar.divider()
    menu_bodega = st.sidebar.selectbox("Menú de Gestión", ["Vender / Facturar", "Cargar Inventario", "Gestionar Stock"])

    if menu_bodega == "Cargar Inventario":
        st.header("📦 Registro de Nuevo Producto")
        opcion_foto = st.pills("Método de imagen", ["Cámara", "Galería"], default="Cámara")
        
        foto_archivo = None
        if opcion_foto == "Cámara":
            foto_archivo = st.camera_input("Capturar Foto")
        else:
            foto_archivo = st.file_uploader("Acceder a galería", type=["jpg", "png", "jpeg"])

        with st.form("datos_producto", clear_on_submit=True):
            codigo = st.text_input("Código Único")
            nombre = st.text_input("Nombre")
            precio = st.number_input("Precio Mayorista", min_value=0, step=100)
            stock = st.number_input("Stock", min_value=0, step=1)
            categoria = st.selectbox("Categoría", ["Anillos", "Aretes", "Cadenas", "Pulseras", "Candongas", "Topitos", "Tobilleras", "Relojes", "Otros"])
            
            if st.form_submit_button("Registrar"):
                if codigo and nombre:
                    if not os.path.exists('fotos'): os.makedirs('fotos')
                    foto_path = f"fotos/{codigo}.jpg"
                    if foto_archivo:
                        img = Image.open(foto_archivo).convert('RGB')
                        img.save(foto_path)
                    else:
                        foto_path = "Sin foto"
                    
                    st.session_state.inventario.loc[codigo] = [nombre, precio, stock, categoria, foto_path]
                    guardar_datos()
                    st.success("✅ Registrado")
                    st.rerun()

    elif menu_bodega == "Vender / Facturar":
        st.header("🛒 Ventas Mayoristas")
        busqueda = st.text_input("🔍 Buscar...")
        items_v = st.session_state.inventario
        if busqueda:
            items_v = items_v[items_v['Nombre'].str.contains(busqueda, case=False) | items_v.index.str.contains(busqueda, case=False)]

        for codigo_id, row in items_v.iterrows():
            with st.container():
                c1, c2 = st.columns([1, 2])
                with c1:
                    if os.path.exists(str(row['Foto'])): st.image(row['Foto'], width=120)
                with c2:
                    st.write(f"**{row['Nombre']}** (Ref: {codigo_id})")
                    st.write(f"Stock: {row['Stock']} | **${row['Precio']:,}**")
                    
                    col_q, col_b = st.columns([1, 1])
                    with col_q:
                        cant = st.number_input("Cant.", min_value=1, max_value=int(row['Stock']) if row['Stock'] > 0 else 1, key=f"q_{codigo_id}")
                    with col_b:
                        if st.button("Añadir", key=f"btn_{codigo_id}"):
                            for _ in range(int(cant)):
                                st.session_state.carrito.append({'id': codigo_id, 'nombre': row['Nombre'], 'precio': row['Precio']})
                            st.toast("Añadido")

        if st.session_state.carrito:
            st.divider()
            df_p = pd.DataFrame(st.session_state.carrito)
            desc = st.slider("Descuento (%)", 0, 50, 0)
            total = df_p['precio'].sum() * (1 - desc/100)
            st.dataframe(df_p)
            st.write(f"### TOTAL: ${total:,.0f}")
            if st.button("Confirmar Venta"):
                for item in st.session_state.carrito:
                    st.session_state.inventario.at[item['id'], 'Stock'] -= 1
                guardar_datos()
                st.session_state.carrito = []
                st.success("Venta Guardada")
                st.balloons()

    elif menu_bodega == "Gestionar Stock":
        st.header("📊 Inventario Actual")
        st.dataframe(st.session_state.inventario, use_container_width=True)
        st.download_button("Descargar Excel", st.session_state.inventario.to_csv().encode('utf-8'), "inventario.csv", "text/csv")
        if st.button("Actualizar Stock desde CSV"):
            archivo_csv = st.file_uploader("Subir archivo CSV", type=["csv"])
            if archivo_csv:
                nuevo_stock = pd.read_csv(archivo_csv, index_col='Codigo')
                for codigo_id, row in nuevo_stock.iterrows():
                    if codigo_id in st.session_state.inventario.index:
                        st.session_state.inventario.at[codigo_id, 'Stock'] = row['Stock']
                guardar_datos()
                st.success("Stock actualizado")
                st.rerun()