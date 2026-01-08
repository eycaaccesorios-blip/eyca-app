import streamlit as st
import pandas as pd
import cloudinary
import cloudinary.uploader
from PIL import Image
from datetime import datetime
from fpdf import FPDF
import io
import os

# 1. CONFIGURACIÓN INICIAL
st.set_page_config(page_title="Eyca Accesorios - Bodega", layout="wide")

# Configuración de Cloudinary (Fotos)
cloudinary.config(
    cloud_name = st.secrets["cloud_name"],
    api_key = st.secrets["api_key"],
    api_secret = st.secrets["api_secret"]
)

# 2. CARGA DE DATOS DESDE TU LINK PÚBLICO
def obtener_datos():
    try:
        # Tu enlace específico de Google Sheets
        url_original = "https://docs.google.com/spreadsheets/d/198a2c0RjSbCE8VezyhfjP-W1feYtNeufTmBEyV7I9w4/edit?usp=sharing"
        
        # Transformación para lectura directa en 2026
        url_csv = url_original.replace("/edit?usp=sharing", "/export?format=csv")
        
        # Leemos los datos (cache_drops asegura datos frescos)
        df = pd.read_csv(url_csv)
        return df
    except Exception as e:
        st.error(f"Error de conexión con el inventario: {e}")
        return pd.DataFrame(columns=['Codigo', 'Nombre', 'Precio', 'Stock', 'Categoria', 'Foto_URL'])

# 3. SEGURIDAD
def login():
    if "auth" not in st.session_state: st.session_state.auth = False
    if not st.session_state.auth:
        st.title("🔐 Acceso Administrativo - Eyca")
        clave = st.text_input("Clave de Bodega:", type="password")
        if st.button("Ingresar"):
            if clave == st.secrets["clave_bodega"]:
                st.session_state.auth = True
                st.rerun()
            else:
                st.error("Clave incorrecta")
        return False
    return True

# 4. FUNCIÓN PARA GENERAR FACTURA PDF
def generar_pdf(cliente, carrito, subtotal, desc, total):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, "EYCA ACCESORIOS - FACTURA MAYORISTA", ln=True, align='C')
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, f"Cliente: {cliente}", ln=True)
    pdf.cell(200, 10, f"Fecha: {datetime.now().strftime('%d/%m/%Y')}", ln=True)
    pdf.ln(10)
    
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(100, 10, "Producto", 1, 0, 'C', True)
    pdf.cell(40, 10, "Cant", 1, 0, 'C', True)
    pdf.cell(40, 10, "Subtotal", 1, 1, 'C', True)
    
    for item in carrito:
        pdf.cell(100, 10, item['nombre'], 1)
        pdf.cell(40, 10, str(item['cant']), 1, 0, 'C')
        pdf.cell(40, 10, f"${item['sub']:,}", 1, 1, 'R')
    
    pdf.ln(5)
    pdf.cell(140, 10, "Subtotal:", 0, 0, 'R')
    pdf.cell(40, 10, f"${subtotal:,}", 0, 1, 'R')
    pdf.cell(140, 10, f"Descuento ({desc}%):", 0, 0, 'R')
    pdf.cell(40, 10, f"-${int(subtotal*desc/100):,}", 0, 1, 'R')
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(140, 10, "TOTAL:", 0, 0, 'R')
    pdf.cell(40, 10, f"${total:,}", 0, 1, 'R')
    
    return pdf.output(dest='S').encode('latin-1')

# --- MENÚ DE NAVEGACIÓN ---
menu = st.sidebar.radio("Navegación", ["✨ Catálogo Público", "🔐 Área de Bodega"])

if menu == "✨ Catálogo Público":
    st.title("💍 Catálogo Eyca Accesorios 2026")
    df = obtener_datos()
    
    if not df.empty:
        # Filtro por categoría
        categorias_disponibles = ["Todos"] + sorted(df['Categoria'].dropna().unique().tolist())
        filtro = st.selectbox("Filtrar por tipo de joya:", categorias_disponibles)
        
        items = df if filtro == "Todos" else df[df['Categoria'] == filtro]
        
        # Grid de productos
        grid = st.columns(3)
        for i, (idx, row) in enumerate(items.iterrows()):
            with grid[i % 3]:
                if pd.notna(row['Foto_URL']):
                    st.image(row['Foto_URL'], use_container_width=True)
                st.subheader(row['Nombre'])
                st.caption(f"Referencia: {row['Codigo']}")
                st.write("---")
    else:
        st.warning("El catálogo está vacío. Agrega productos al Google Sheet para verlos aquí.")

elif menu == "🔐 Área de Bodega":
    if login():
        st.sidebar.divider()
        opcion = st.sidebar.selectbox("Gestión", ["Vender / Facturar", "Cargar Fotos a Nube", "Ver Inventario"])
        
        inventario_actual = obtener_datos()

        if opcion == "Cargar Fotos a Nube":
            st.header("📸 Subir Imágenes a Cloudinary")
            st.info("Sube la foto aquí y luego copia el link resultante a tu Google Sheet.")
            
            archivo = st.file_uploader("Selecciona la imagen", type=['jpg', 'png', 'jpeg'])
            if archivo:
                if st.button("Subir ahora"):
                    with st.spinner("Subiendo..."):
                        res = cloudinary.uploader.upload(archivo)
                        st.success("✅ Imagen lista en la nube")
                        st.write("**URL para tu Excel:**")
                        st.code(res['secure_url'])
                        st.image(res['secure_url'], width=200)

        elif opcion == "Vender / Facturar":
            st.header("🛒 Sistema de Ventas")
            if 'carrito_eyca' not in st.session_state: st.session_state.carrito_eyca = []
            
            for i, row in inventario_actual.iterrows():
                col1, col2 = st.columns([1,3])
                with col1: 
                    if pd.notna(row['Foto_URL']): st.image(row['Foto_URL'], width=80)
                with col2:
                    st.write(f"**{row['Nombre']}** | Stock: {row['Stock']}")
                    if st.button(f"Añadir ${row['Precio']:,}", key=f"btn_{row['Codigo']}"):
                        st.session_state.carrito_eyca.append({'nombre': row['Nombre'], 'precio': row['Precio'], 'cant': 1, 'sub': row['Precio']})
                        st.toast(f"Añadido: {row['Nombre']}")

            if st.session_state.carrito_eyca:
                st.divider()
                st.subheader("📝 Resumen del Pedido")
                df_c = pd.DataFrame(st.session_state.carrito_eyca)
                desc = st.slider("Aplicar Descuento (%)", 0, 50, 0)
                subt = df_c['sub'].sum()
                total = subt * (1 - desc/100)
                
                st.table(df_c[['nombre', 'precio']])
                st.write(f"### Total: ${total:,.0f}")
                
                cliente = st.text_input("Nombre del Cliente/Vendedor")
                if st.button("Finalizar Venta (Generar PDF)") and cliente:
                    pdf_bytes = generar_pdf(cliente, st.session_state.carrito_eyca, subt, desc, total)
                    st.download_button("📩 Descargar Factura PDF", pdf_bytes, f"Factura_{cliente}.pdf", "application/pdf")
                    st.session_state.carrito_eyca = []
                    st.balloons()

        elif opcion == "Ver Inventario":
            st.header("📊 Inventario Actual (Google Sheets)")
            st.dataframe(inventario_actual, use_container_width=True)
            st.download_button("Descargar Respaldo CSV", inventario_actual.to_csv(index=False).encode('utf-8'), "inventario_eyca.csv")
