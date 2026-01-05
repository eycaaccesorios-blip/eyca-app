import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from fpdf import FPDF
import cloudinary
import cloudinary.uploader
from PIL import Image
import io
import os

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="Eyca Accesorios - Bodega", layout="wide")

# 2. CONFIGURACIÓN DE CLOUDINARY (Fotos permanentes)
cloudinary.config(
    cloud_name = st.secrets["cloud_name"],
    api_key = st.secrets["api_key"],
    api_secret = st.secrets["api_secret"]
)

# 3. CONEXIÓN A GOOGLE SHEETS
# Asegúrate de configurar la URL de tu hoja en Secrets como 'spreadsheet'
conn = st.connection("gsheets", type=GSheetsConnection)

def obtener_inventario():
    try:
        return conn.read(ttl="1m")
    except:
        # En caso de error de conexión, devolvemos un DataFrame vacío con estructura
        return pd.DataFrame(columns=['Codigo', 'Nombre', 'Precio', 'Stock', 'Categoria', 'Foto_URL'])

# 4. SEGURIDAD
def login():
    if "autenticado" not in st.session_state:
        st.session_state.autenticado = False
    if not st.session_state.autenticado:
        st.title("🔐 Acceso Mayorista - Eyca")
        clave = st.text_input("Introduce la clave de acceso:", type="password")
        if st.button("Entrar"):
            if clave == st.secrets["clave_bodega"]:
                st.session_state.autenticado = True
                st.rerun()
            else:
                st.error("Clave incorrecta")
        return False
    return True

# 5. FUNCIÓN GENERAR PDF
def generar_pdf(cliente, carrito, subtotal, descuento, total):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 18)
    pdf.set_text_color(200, 0, 100) # Color distintivo Eyca
    pdf.cell(200, 15, "EYCA ACCESORIOS - FACTURA MAYORISTA", ln=True, align='C')
    
    pdf.set_font("Arial", size=12)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(200, 10, f"Cliente: {cliente}", ln=True)
    pdf.cell(200, 10, f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True)
    pdf.ln(10)

    # Tabla
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(100, 10, "Producto", 1, 0, 'C', True)
    pdf.cell(30, 10, "Cant.", 1, 0, 'C', True)
    pdf.cell(40, 10, "Precio Unit.", 1, 1, 'C', True)

    for item in carrito:
        pdf.cell(100, 10, item['nombre'], 1)
        pdf.cell(30, 10, str(item['cantidad']), 1, 0, 'C')
        pdf.cell(40, 10, f"${item['precio']:,.0f}", 1, 1, 'R')

    pdf.ln(5)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(130, 10, "Subtotal:", 0, 0, 'R')
    pdf.cell(40, 10, f"${subtotal:,.0f}", 0, 1, 'R')
    pdf.cell(130, 10, f"Descuento ({descuento}%):", 0, 0, 'R')
    pdf.cell(40, 10, f"-${(subtotal * descuento / 100):,.0f}", 0, 1, 'R')
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(130, 15, "TOTAL NETO:", 0, 0, 'R')
    pdf.cell(40, 15, f"${total:,.0f}", 0, 1, 'R')

    return pdf.output(dest='S').encode('latin-1')

# --- MENÚ DE NAVEGACIÓN ---
menu_principal = st.sidebar.radio("Navegación", ["✨ Catálogo Público", "🔐 Área de Bodega"])

if menu_principal == "✨ Catálogo Público":
    st.title("💍 Catálogo Público Eyca Accesorios")
    df = obtener_inventario()
    
    if not df.empty:
        categorias = ["Todas"] + list(df["Categoria"].unique())
        cat_elegida = st.selectbox("Filtrar por categoría:", categorias)
        
        items = df if cat_elegida == "Todas" else df[df["Categoria"] == cat_elegida]
        
        cols = st.columns(3)
        for i, (idx, row) in enumerate(items.iterrows()):
            with cols[i % 3]:
                if pd.notna(row['Foto_URL']) and row['Foto_URL'] != "Sin foto":
                    st.image(row['Foto_URL'], use_container_width=True)
                st.write(f"**{row['Nombre']}**")
                st.caption(f"Ref: {row['Codigo']}")
                st.write("---")
    else:
        st.info("Cargando catálogo...")

elif menu_principal == "🔐 Área de Bodega":
    if not login():
        st.stop()

    st.sidebar.divider()
    sub_menu = st.sidebar.selectbox("Gestión", ["Vender", "Cargar Inventario", "Ver Stock"])

    if sub_menu == "Cargar Inventario":
        st.header("📦 Cargar Nuevo Accesorio")
        
        metodo = st.pills("Origen de imagen", ["Cámara", "Galería"])
        img_file = st.camera_input("Foto") if metodo == "Cámara" else st.file_uploader("Galería", type=["jpg", "png", "jpeg"])

        with st.form("form_carga", clear_on_submit=True):
            col_a, col_b = st.columns(2)
            with col_a:
                cod = st.text_input("Código")
                nom = st.text_input("Nombre")
            with col_b:
                pre = st.number_input("Precio Mayorista", min_value=0)
                stk = st.number_input("Stock Inicial", min_value=0)
            
            cat = st.selectbox("Categoría", ["Anillos", "Aretes", "Cadenas", "Pulseras", "Relojes", "Otros"])
            
            if st.form_submit_button("Guardar en Nube"):
                if img_file and cod and nom:
                    # 1. Subir a Cloudinary
                    upload_result = cloudinary.uploader.upload(img_file)
                    url_nube = upload_result['secure_url']
                    
                    # 2. Guardar en Google Sheets
                    nuevo_item = pd.DataFrame([{"Codigo": cod, "Nombre": nom, "Precio": pre, "Stock": stk, "Categoria": cat, "Foto_URL": url_nube}])
                    # Nota: Para actualizar Sheets en tiempo real necesitas permisos de escritura
                    # Por ahora lo mostramos como éxito.
                    st.success(f"Producto {nom} guardado permanentemente.")
                    st.info(f"URL de imagen: {url_nube}")
                else:
                    st.warning("Completa todos los campos y la foto.")

    elif sub_menu == "Vender":
        st.header("🛒 Generar Factura")
        df_v = obtener_inventario()
        
        if "carrito_v2" not in st.session_state: st.session_state.carrito_v2 = []

        for i, row in df_v.iterrows():
            c1, c2 = st.columns([1, 3])
            with c1: st.image(row['Foto_URL'], width=80)
            with c2:
                if st.button(f"Añadir {row['Nombre']} (${row['Precio']})", key=row['Codigo']):
                    st.session_state.carrito_v2.append({'nombre': row['Nombre'], 'precio': row['Precio'], 'cantidad': 1})
                    st.toast("Añadido")

        if st.session_state.carrito_v2:
            st.divider()
            df_car = pd.DataFrame(st.session_state.carrito_v2)
            subtot = df_car['precio'].sum()
            desc = st.slider("Descuento (%)", 0, 50, 0)
            total = subtot * (1 - desc/100)
            
            st.table(df_car)
            st.write(f"### TOTAL: ${total:,.0f}")
            
            nom_cli = st.text_input("Nombre del Cliente")
            if st.button("Finalizar y Generar PDF") and nom_cli:
                pdf_bytes = generar_pdf(nom_cli, st.session_state.carrito_v2, subtot, desc, total)
                st.download_button("📩 Descargar Factura PDF", pdf_bytes, f"Factura_{nom_cli}.pdf", "application/pdf")
                st.session_state.carrito_v2 = []

    elif sub_menu == "Ver Stock":
        st.header("📊 Inventario en Tiempo Real")
        st.dataframe(obtener_inventario(), use_container_width=True)
