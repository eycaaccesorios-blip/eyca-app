import streamlit as st
import pandas as pd
import cloudinary
import cloudinary.uploader
from PIL import Image
from datetime import datetime
from fpdf import FPDF
import io

# 1. CONFIGURACIÓN INICIAL
st.set_page_config(page_title="Eyca Accesorios - Bodega", layout="wide")

# Configuración de Cloudinary (Fotos)
cloudinary.config(
    cloud_name = st.secrets["cloud_name"],
    api_key = st.secrets["api_key"],
    api_secret = st.secrets["api_secret"]
)

# 2. CARGA DE DATOS DESDE LINK PÚBLICO (Google Sheets)
def obtener_datos():
    try:
        # El link de secrets debe terminar en /edit... lo convertimos a exportación CSV
        url_original = st.secrets["connections"]["gsheets"]["spreadsheet"]
        url_csv = url_original.replace("/edit?usp=sharing", "/export?format=csv")
        url_csv = url_csv.replace("/edit#gid=", "/export?format=csv&gid=")
        return pd.read_csv(url_csv)
    except Exception as e:
        # Si falla, creamos uno vacío para no romper la app
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
    pdf.cell(40, 10, f"-${(subtotal*desc/100):,}", 0, 1, 'R')
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
        cat = ["Todos"] + list(df['Categoria'].unique())
        filtro = st.selectbox("Filtrar por tipo:", cat)
        items = df if filtro == "Todos" else df[df['Categoria'] == filtro]
        
        grid = st.columns(3)
        for i, (idx, row) in enumerate(items.iterrows()):
            with grid[i % 3]:
                st.image(row['Foto_URL'], use_container_width=True)
                st.subheader(row['Nombre'])
                st.caption(f"Ref: {row['Codigo']}")
                st.write("---")
    else:
        st.warning("Aún no hay productos en el catálogo de Google Sheets.")

elif menu == "🔐 Área de Bodega":
    if login():
        st.sidebar.divider()
        opcion = st.sidebar.selectbox("Gestión", ["Vender", "Cargar Inventario", "Respaldo"])
        
        inventario_actual = obtener_datos()

        if opcion == "Cargar Inventario":
            st.header("📦 Cargar Nuevo Producto")
            st.info("Nota: Las fotos se guardan en la nube. Los datos de texto debes copiarlos a tu Google Sheet.")
            
            with st.form("carga_form", clear_on_submit=True):
                c1, c2 = st.columns(2)
                with c1:
                    cod = st.text_input("Código")
                    nom = st.text_input("Nombre del Accesorio")
                    cat = st.selectbox("Categoría", ["Anillos", "Aretes", "Cadenas", "Relojes", "Otros"])
                with c2:
                    pre = st.number_input("Precio Mayorista", min_value=0)
                    stk = st.number_input("Stock Inicial", min_value=0)
                
                foto_input = st.file_uploader("Subir imagen (Cámara o Galería)", type=['jpg','png','jpeg'])
                
                if st.form_submit_button("Subir a la Nube"):
                    if foto_input and cod:
                        # Subir a Cloudinary
                        res = cloudinary.uploader.upload(foto_input)
                        st.success(f"✅ Foto cargada. Copia este link a tu Google Sheet en la columna Foto_URL: {res['secure_url']}")
                        st.code(f"{cod}, {nom}, {pre}, {stk}, {cat}, {res['secure_url']}")
                    else:
                        st.error("Faltan datos o foto.")

        elif opcion == "Vender":
            st.header("🛒 Facturación Mayorista")
            if 'carrito_eyca' not in st.session_state: st.session_state.carrito_eyca = []
            
            for i, row in inventario_actual.iterrows():
                col1, col2 = st.columns([1,3])
                with col1: st.image(row['Foto_URL'], width=80)
                with col2:
                    if st.button(f"Añadir {row['Nombre']} (${row['Precio']:,})", key=row['Codigo']):
                        st.session_state.carrito_eyca.append({'nombre': row['Nombre'], 'precio': row['Precio'], 'cant': 1, 'sub': row['Precio']})
                        st.toast("Añadido")

            if st.session_state.carrito_eyca:
                st.divider()
                df_c = pd.DataFrame(st.session_state.carrito_eyca)
                desc = st.slider("Descuento (%)", 0, 50, 0)
                subt = df_car = df_c['sub'].sum()
                total = subt * (1 - desc/100)
                
                st.table(df_c[['nombre', 'precio', 'cant']])
                st.write(f"### Total: ${total:,.0f}")
                
                cliente = st.text_input("Nombre del Cliente")
                if st.button("Finalizar y Descargar PDF") and cliente:
                    pdf = generar_pdf(cliente, st.session_state.carrito_eyca, subt, desc, total)
                    st.download_button("📩 Descargar Factura", pdf, f"Factura_{cliente}.pdf", "application/pdf")
                    st.session_state.carrito_eyca = []

        elif opcion == "Respaldo":
            st.header("📊 Ver Inventario Completo")
            st.dataframe(inventario_actual)
            st.download_button("Descargar CSV para Respaldo", inventario_actual.to_csv(index=False).encode('utf-8'), "inventario.csv")
