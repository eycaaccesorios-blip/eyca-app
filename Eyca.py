import streamlit as st
import pandas as pd
from supabase import create_client
import cloudinary.uploader
from fpdf import FPDF
from datetime import datetime
from PIL import Image
import io

# 1. CONFIGURACIÓN INICIAL
st.set_page_config(page_title="Eyca Accesorios - Bodega", layout="wide")

# Conexión a Supabase (Base de Datos)
supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

# Configuración Cloudinary (Fotos)
cloudinary.config(
    cloud_name = st.secrets["cloud_name"],
    api_key = st.secrets["api_key"],
    api_secret = st.secrets["api_secret"]
)

# 2. SISTEMA DE SEGURIDAD
def login():
    if "auth" not in st.session_state: 
        st.session_state.auth = False
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

# 3. FUNCIÓN FACTURA PDF (Optimizada para fpdf2)
def generar_pdf(cliente, nit, vendedor, carrito, subtotal, desc_porc, total):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("helvetica", 'B', 16)
    pdf.cell(200, 10, "EYCA ACCESORIOS ", ln=True, align='C')
    pdf.set_font("helvetica", 'B', 12)
    pdf.cell(200, 10, "Complementa tú estilo", ln=True, align='C')
    
    pdf.set_font("helvetica", size=10)
    pdf.cell(100, 7, f"Cliente: {cliente} | NIT/CC: {nit}", ln=True)
    pdf.cell(100, 7, f"Vendedor: {vendedor} | Fecha: {datetime.now().strftime('%d/%m/%Y')}", ln=True)
    pdf.ln(10)
    
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(90, 8, "Producto", 1, 0, 'C', True)
    pdf.cell(20, 8, "Cant", 1, 0, 'C', True)
    pdf.cell(40, 8, "P. Unit", 1, 0, 'C', True)
    pdf.cell(40, 8, "Subtotal", 1, 1, 'C', True)
    
    pdf.set_font("helvetica", size=10)
    for item in carrito:
        pdf.cell(90, 8, str(item['nombre'])[:35], 1)
        pdf.cell(20, 8, str(item['cant']), 1, 0, 'C')
        pdf.cell(40, 8, f"${item['precio']:,.0f}", 1, 0, 'R')
        pdf.cell(40, 8, f"${item['sub']:,.0f}", 1, 1, 'R')
    
    pdf.ln(5)
    descuento_valor = subtotal * (desc_porc / 100)
    pdf.cell(150, 8, "SUBTOTAL:", 0, 0, 'R')
    pdf.cell(40, 8, f"${subtotal:,.0f}", 0, 1, 'R')
    pdf.cell(150, 8, f"DESCUENTO ({desc_porc}%):", 0, 0, 'R')
    pdf.cell(40, 8, f"-${descuento_valor:,.0f}", 0, 1, 'R')
    pdf.set_font("helvetica", 'B', 12)
    pdf.cell(150, 10, "TOTAL NETO:", 0, 0, 'R')
    pdf.cell(40, 10, f"${total:,.0f}", 0, 1, 'R')
    
    return bytes(pdf.output())

# --- FLUJO DE LA APLICACIÓN ---
menu = st.sidebar.radio("Navegación", ["✨ Catálogo Público", "🔐 Gestión de Bodega"])

if menu == "✨ Catálogo Público":
    st.title("💍 Catálogo Eyca Accesorios")
    try:
        res = supabase.table("inventario").select("*").execute()
        df = pd.DataFrame(res.data)
        if not df.empty:
            cats = ["Todos"] + sorted(df['categoria'].unique().tolist())
            filtro = st.selectbox("Filtrar por Categoría:", cats)
            items = df if filtro == "Todos" else df[df['categoria'] == filtro]
            
            grid = st.columns(3)
            for i, row in items.iterrows():
                with grid[i % 3]:
                    st.image(row['foto_url'], use_container_width=True)
                    st.write(f"**{row['nombre']}**")
                    st.caption(f"Referencia: {row['codigo']}")
        else:
            st.info("No hay productos disponibles actualmente.")
    except Exception as e:
        st.error("Error al conectar con la base de datos.")

elif menu == "🔐 Gestión de Bodega":
    if login():
        accion = st.sidebar.selectbox("Tarea", ["Vender / Facturar", "Cargar Inventario", "Ver Stock"])

        # MÓDULO CARGAR INVENTARIO
        if accion == "Cargar Inventario":
            st.header("📦 Registro de Producto Nuevo")
            metodo = st.radio("Origen de Imagen", ["Cámara", "Galería"])
            foto = st.camera_input("Captura") if metodo == "Cámara" else st.file_uploader("Subir", type=['jpg','png','jpeg'])

            with st.form("form_carga", clear_on_submit=True):
                c1, c2 = st.columns(2)
                with c1:
                    cod = st.text_input("Código de Referencia")
                    nom = st.text_input("Nombre del Accesorio")
                    cat = st.selectbox("Categoría", ["Anillos", "Aretes", "Cadenas", "Pulseras", "Relojes", "Otros"])
                with c2:
                    pre = st.number_input("Precio Mayorista ($)", min_value=0, step=100)
                    stk = st.number_input("Stock Inicial", min_value=0, step=1)
                
                if st.form_submit_button("Guardar en Bodega"):
                    if foto and cod and nom:
                        with st.spinner("Subiendo archivos..."):
                            img_res = cloudinary.uploader.upload(foto)
                            supabase.table("inventario").insert({
                                "codigo": cod, "nombre": nom, "precio": pre, 
                                "stock": stk, "categoria": cat, "foto_url": img_res['secure_url']
                            }).execute()
                            st.success(f"✅ {nom} registrado correctamente.")
                    else:
                        st.error("Faltan datos obligatorios o la imagen.")

        # MÓDULO VENDER / FACTURAR
        elif accion == "Vender / Facturar":
            st.header("🛒 Panel de Ventas")
            if 'car' not in st.session_state: st.session_state.car = []
            
            res_v = supabase.table("inventario").select("*").execute()
            df_inv = pd.DataFrame(res_v.data)

            for i, row in df_inv.iterrows():
                col1, col2, col3 = st.columns([1, 2, 1])
                with col1: st.image(row['foto_url'], width=80)
                with col2: st.write(f"**{row['nombre']}**  \nPrecio: ${row['precio']:,}")
                with col3:
                    cant = st.number_input("Cant", min_value=1, max_value=int(row['stock']) if int(row['stock']) > 0 else 1, key=f"v_{row['codigo']}")
                    if st.button("Añadir", key=row['codigo']):
                        st.session_state.car.append({
                            'id': row['codigo'], 
                            'nombre': row['nombre'], 
                            'precio': row['precio'], 
                            'cant': int(cant), 
                            'sub': row['precio'] * int(cant)
                        })
                        st.toast(f"{row['nombre']} añadido.")

            if st.session_state.car:
                st.divider()
                st.subheader("📝 Resumen de la Factura")
                df_car = pd.DataFrame(st.session_state.car)
                subt = df_car['sub'].sum()
                desc = st.slider("Descuento Mayorista (%)", 0, 50, 0)
                total = subt * (1 - desc/100)
                
                st.table(df_car[['nombre', 'cant', 'sub']])
                st.write(f"### TOTAL A PAGAR: ${total:,.0f}")
                
                nom_c = st.text_input("Nombre del Cliente")
                nit_c = st.text_input("Cédula o NIT")
                nom_v = st.text_input("Nombre del Vendedor")
                
                if st.button("Procesar Venta"):
                    with st.spinner("Actualizando stock..."):
                        try:
                            for item in st.session_state.car:
                                # Obtener stock actual correctamente
                                producto_db = df_inv.loc[df_inv['codigo'] == item['id']]
                                if not producto_db.empty:
                                    stock_actual = int(producto_db['stock'].values[0])
                                    nuevo_stk = stock_actual - item['cant']
                                    supabase.table("inventario").update({"stock": nuevo_stk}).eq("codigo", item['id']).execute()
                            
                            # Generar PDF y convertirlo a BytesIO para Streamlit 2026
                            pdf_output = generar_pdf(nom_c, nit_c, nom_v, st.session_state.car, subt, desc, total)
                            
                            # Convertimos los bytes a un objeto que download_button acepte sin errores
                            st.session_state.pdf_eyca = io.BytesIO(pdf_output)
                            st.session_state.car = [] 
                            st.success("✅ Venta procesada exitosamente")
                        except Exception as e:
                            st.error(f"Error al procesar: {e}")

                # El botón de descarga ahora usa el buffer de memoria
                if "pdf_eyca" in st.session_state and st.session_state.pdf_eyca is not None:
                    st.download_button(
                        label="📩 Descargar Factura PDF",
                        data=st.session_state.pdf_eyca.getvalue(), # Extraemos los bytes limpios
                        file_name=f"Factura_{nom_c}.pdf",
                        mime="application/pdf",
                        key="download_btn_final"
                    )


        # MÓDULO VER STOCK
        elif accion == "Ver Stock":
            st.header("📊 Inventario en Tiempo Real")
            res_s = supabase.table("inventario").select("*").execute()
            st.dataframe(pd.DataFrame(res_s.data), use_container_width=True)
