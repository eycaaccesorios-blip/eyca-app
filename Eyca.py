import streamlit as st
import pandas as pd
from datetime import datetime
from PIL import Image
import os

# --- NUEVO: SISTEMA DE SEGURIDAD CON SECRETS ---
def login():
    if "autenticado" not in st.session_state:
        st.session_state.autenticado = False

    if not st.session_state.autenticado:
        st.title("🔐 Acceso Mayorista - Eyca")
        clave_ingresada = st.text_input("clave_bodega", type="password")
        
        if st.button("Entrar"):
            # Aquí comparamos con la clave guardada en 'Secrets'
            if clave_ingresada == st.secrets["clave_bodega"]:
                st.session_state.autenticado = True
                st.rerun()
            else:
                st.error("❌ Clave incorrecta. Contacta a la administración de Eyca.")
        return False
    return True

# Si el login falla, detiene el resto del código
if not login():
    st.stop()
# --- FIN SEGURIDAD ---

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="Eyca Accesorios - Bodega", layout="centered")

# 2. PERSISTENCIA DE DATOS (INVENTARIO)
if 'inventario' not in st.session_state:
    if os.path.exists('inventario.csv'):
        # Cargamos el archivo y nos aseguramos de que el código sea el índice
        st.session_state.inventario = pd.read_csv('inventario.csv', index_col='Codigo')
    else:
        # Si no existe, creamos la estructura base
        columnas = ['Nombre', 'Precio', 'Stock', 'Categoria', 'Foto']
        st.session_state.inventario = pd.DataFrame(columns=columnas)
        st.session_state.inventario.index.name = 'Codigo'

if 'carrito' not in st.session_state:
    st.session_state.carrito = []

# --- FUNCIONES ---
def guardar_datos():
    st.session_state.inventario.to_csv('inventario.csv')

# --- INTERFAZ PRINCIPAL ---
st.title("💍 Bodega Eyca Accesorios")
st.markdown("### Gestión Mayorista 2026")

menu = st.sidebar.selectbox("Menú de Gestión", ["Vender / Facturar", "Cargar Inventario", "Gestionar Stock"])

# --- MÓDULO 1: CARGAR INVENTARIO (CON FOTO) ---
if menu == "Cargar Inventario":
    st.header("📦 Registro de Nuevo Producto")
    with st.form("nuevo_producto", clear_on_submit=True):
        codigo = st.text_input("Código Único (ej: AN-001)")
        nombre = st.text_input("Nombre del Accesorio")
        precio = st.number_input("Precio Mayorista ($)", min_value=0, step=100)
        stock = st.number_input("Cantidad en Bodega", min_value=0, step=1)
        categoria = st.selectbox("Categoría", ["Anillos", "Aretes", "Cadenas", "Pulseras", "Otros"])
        foto = st.camera_input("Capturar Foto del Accesorio") # Activa cámara en móvil
        
        enviado = st.form_submit_button("Registrar en Inventario")
        
        if enviado:
            if codigo and nombre:
                # Guardar la imagen físicamente
                foto_path = f"fotos/{codigo}.jpg"
                if not os.path.exists('fotos'): 
                    os.makedirs('fotos')
                
                if foto:
                    img = Image.open(foto)
                    img.save(foto_path)
                else:
                    foto_path = "Sin foto"

                # Agregar al DataFrame
                st.session_state.inventario.loc[codigo] = [nombre, precio, stock, categoria, foto_path]
                guardar_datos()
                st.success(f"✅ {nombre} registrado correctamente.")
            else:
                st.error("⚠️ El Código y el Nombre son obligatorios.")

# --- MÓDULO 2: VENDER Y FACTURAR ---
elif menu == "Vender / Facturar":
    st.header("🛒 Panel de Ventas Mayoristas")
    
    busqueda = st.text_input("🔍 Buscar por nombre o código...")
    items = st.session_state.inventario
    
    if busqueda:
        items = items[items['Nombre'].str.contains(busqueda, case=False) | items.index.str.contains(busqueda, case=False)]

    # Mostrar Galería
    for codigo_id, row in items.iterrows():
        with st.container():
            col1, col2 = st.columns([1, 2])
            with col1:
                if os.path.exists(str(row['Foto'])):
                    st.image(row['Foto'], width=120)
                else:
                    st.info("Sin foto")
            with col2:
                st.write(f"**{row['Nombre']}**")
                st.write(f"Ref: {codigo_id} | Stock: {row['Stock']}")
                st.write(f"Precio: **${row['Precio']:,}**")
                if st.button(f"Añadir al pedido", key=codigo_id):
                    if row['Stock'] > 0:
                        st.session_state.carrito.append({'id': codigo_id, 'nombre': row['Nombre'], 'precio': row['Precio']})
                        st.toast(f"Añadido: {row['Nombre']}")
                    else:
                        st.error("Producto sin stock")

    # Resumen de Factura
    if st.session_state.carrito:
        st.divider()
        st.subheader("📄 Detalle de Factura")
        df_pedido = pd.DataFrame(st.session_state.carrito)
        
        # Gestión de Descuentos
        desc = st.slider("Aplica un descuento (%)", 0, 50, 0)
        
        total_bruto = df_pedido['precio'].sum()
        ahorro = total_bruto * (desc / 100)
        total_neto = total_bruto - ahorro
        
        st.dataframe(df_pedido[['nombre', 'precio']], use_container_width=True)
        
        st.write(f"**Subtotal:** ${total_bruto:,.0f}")
        st.write(f"**Descuento ({desc}%):** -${ahorro:,.0f}")
        st.write(f"### TOTAL A PAGAR: ${total_neto:,.0f}")
        
        cliente = st.text_input("Nombre del Comprador / Vendedor Externo")
        
        if st.button("Confirmar Venta y Descargar Stock"):
            for item in st.session_state.carrito:
                st.session_state.inventario.at[item['id'], 'Stock'] -= 1
            
            guardar_datos()
            st.success(f"📝 Factura generada para {cliente}")
            st.session_state.carrito = [] # Vaciar carrito
            st.balloons()

# --- MÓDULO 3: GESTIONAR STOCK ---
elif menu == "Gestionar Stock":
    st.header("📊 Inventario de Bodega")
    st.dataframe(st.session_state.inventario, use_container_width=True)
    
    if st.button("Exportar a Excel/CSV"):
        st.session_state.inventario.to_csv("reporte_eyca_2026.csv")
        st.download_button(
            label="Descargar Archivo",
            data=st.session_state.inventario.to_csv().encode('utf-8'),
            file_name='inventario_eyca.csv',
            mime='text/csv'
        )
