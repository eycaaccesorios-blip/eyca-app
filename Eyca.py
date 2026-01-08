import streamlit as st
import pandas as pd
from supabase import create_client
import cloudinary.uploader
from fpdf import FPDF
from datetime import datetime
from PIL import Image
import io

# 1. CONFIGURACIÓN E INICIALIZACIÓN
st.set_page_config(page_title="Eyca Accesorios - Bodega", layout="wide")

# Conexión a Supabase
supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

# Configuración Cloudinary
cloudinary.config(
    cloud_name = st.secrets["cloud_name"],
    api_key = st.secrets["api_key"],
    api_secret = st.secrets["api_secret"]
)

# 2. SISTEMA DE SEGURIDAD
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

# 3. FUNCIÓN FACTURA PDF
def generar_pdf(cliente, nit, vendedor, carrito, subtotal, desc_porc, total):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, "EYCA ACCESORIOS - FACTURA MAYORISTA", ln=True, align='C')
    pdf.set_font("Arial", size=10)
    pdf.cell(100, 7, f"Cliente: {cliente} | NIT/CC: {nit}", ln=True)
    pdf.cell(100, 7, f"Vendedor: {vendedor} | Fecha: {datetime.now().strftime('%d/%m/%Y')}", ln=True)
    pdf.ln(10)
    
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(90, 8, "Producto", 1, 0, 'C', True)
    pdf.cell(20, 8, "Cant", 1, 0, 'C', True)
    pdf.cell(40, 8, "P. Unit", 1, 0, 'C', True)
    pdf.cell(40, 8, "Subtotal", 1, 1, 'C', True)
    
    for item in carrito:
        pdf.cell(90, 8, item['nombre'][:35], 1)
        pdf.cell(20, 8, str(item['cant']), 1, 0, 'C')
        pdf.cell(40, 8, f"${item['precio']:,.0f}", 1, 0, 'R')
        pdf.cell(40, 8, f"${item['sub']:,.0f}", 1, 1, 'R')
    
    pdf.ln(5)
    pdf.cell(150, 8, "SUBTOTAL:", 0, 0, 'R')
    pdf.cell(40, 8, f"${subtotal:,.0f}", 0, 1, 'R')
    pdf.cell(150, 8, f"DESCUENTO ({desc_porc}%):", 0, 0, 'R')
    pdf.cell(40, 8, f"-${(subtotal * desc_porc / 100):,.0f}", 0, 1, 'R')
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(150, 10, "TOTAL NETO:", 0, 0, 'R')
    pdf.cell(40, 10, f"${total:,.0f}", 0, 1, 'R')
    
    return pdf.output(dest='S').encode('latin-1')

# --- MENÚ DE NAVEGACIÓN ---
menu = st.sidebar.radio("Navegación", ["✨ Catálogo Público", "🔐 Gestión de Bodega"])

if menu == "✨ Catálogo Público":
    st.title("💍 Catálogo Público Eyca Accesorios 2026")
    res = supabase.table("inventario").select("*").execute()
    df = pd.DataFrame(res.data)
    
    if not df.empty:
        cats = ["Todos"] + sorted(df['categoria'].unique().tolist())
        filtro = st.selectbox("Categoría:", cats)
        items = df if filtro == "Todos" else df[df['categoria'] == filtro]
        
        grid = st.columns(3)
        for i, row in items.iterrows():
            with grid[i % 3]:
                st.image(row['foto_url'], use_container_width=True)
                st.write(f"**{row['nombre']}**")
                st.caption(f"Ref: {row['codigo']}")
    else:
        st.info("Catálogo en mantenimiento...")

elif menu == "🔐 Gestión de Bodega":
    if login():
        accion = st.sidebar.selectbox("Tarea", ["Vender / Facturar", "Cargar Inventario", "Ver Stock"])

        if accion == "Cargar Inventario":
            st.header("📦 Nuevo Producto")
            metodo = st.pills("Origen de Imagen", ["Cámara", "Galería"], default="Cámara")
            foto = st.camera_input("Foto") if metodo == "Cámara" else st.file_uploader("Subir", type=['jpg','png','jpeg'])

            with st.form("carga", clear_on_submit=True):
                c1, c2 = st.columns(2)
                with c1:
                    cod = st.text_input("Código Único")
                    nom = st.text_input("Nombre")
                    cat = st.selectbox("Categoría", ["Anillos", "Aretes", "Cadenas", "Relojes", "Otros"])
                with c2:
                    pre = st.number_input("Precio Mayorista", min_value=0)
                    stk = st.number_input("Stock Inicial", min_value=0)
                
                if st.form_submit_button("Guardar Permanentemente"):
                    if foto and cod and nom:
                        with st.spinner("Guardando..."):
                            img_res = cloudinary.uploader.upload(foto)
                            supabase.table("inventario").insert({
                                "codigo": cod, "nombre": nom, "precio": pre, 
                                "stock": stk, "categoria": cat, "foto_url": img_res['secure_url']
                            }).execute()
                            st.success(f"✅ {nom} registrado en base de datos.")
                    else:
                        st.error("Faltan datos o imagen.")

        elif accion == "Vender / Facturar":
            st.header("🛒 Panel de Ventas")
            if 'car' not in st.session_state: st.session_state.car = []
            
            res = supabase.table("inventario").select("*").execute()
            df_inv = pd.DataFrame(res.data)

            for i, row in df_inv.iterrows():
                col1, col2, col3 = st.columns([1,2,1])
                with col1: st.image(row['foto_url'], width=80)
                with col2: st.write(f"**{row['nombre']}** (${row['precio']:,})")
                with col3:
                    cant = st.number_input("Cant", min_value=1, max_value=int(row['stock']), key=f"s_{row['codigo']}")
                    if st.button("Añadir", key=row['codigo']):
                        st.session_state.car.append({'id': row['codigo'], 'nombre': row['nombre'], 'precio': row['precio'], 'cant': int(cant), 'sub': row['precio']*cant})
                        st.toast("Añadido")

            if st.session_state.car:
                st.divider()
                df_car = pd.DataFrame(st.session_state.car)
                subt = df_car['sub'].sum()
                desc = st.slider("Descuento (%)", 0, 50, 0)
                total = subt * (1 - desc/100)
                
                st.table(df_car[['nombre', 'cant', 'sub']])
                st.write(f"### TOTAL: ${total:,.0f}")
                
                nom_c = st.text_input("Cliente")
                nit_c = st.text_input("NIT/Cédula")
                nom_v = st.text_input("Vendedor")
                
                if st.button("Finalizar y Descontar Stock"):
                    for item in st.session_state.car:
                        nuevo_stk = int(df_inv.loc[df_inv['codigo'] == item['id'], 'stock'].values[0] - item['cant'])
                        supabase.table("inventario").update({"stock": nuevo_stk}).eq("codigo", item['id']).execute()
                    
                    pdf = generar_pdf(nom_c, nit_c, nom_v, st.session_state.car, subt, desc, total)
                    st.download_button("📩 Descargar Factura PDF", pdf, f"Factura_{nom_c}.pdf", "application/pdf")
                    st.session_state.car = []
                    st.success("Stock actualizado y factura lista.")

        elif accion == "Ver Stock":
            st.header("📊 Inventario Real")
            res = supabase.table("inventario").select("*").execute()
            st.dataframe(pd.DataFrame(res.data), use_container_width=True)
