import os
import requests
from flask import Flask, render_template, request, redirect, url_for, session, flash
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)
app.secret_key = 'alpha_super_secret_key'

# --- CONFIGURACIÓN ---
DB_URL = os.environ.get("DATABASE_URL", "postgresql://usuario:password@host:port/defaultdb")
IMGBB_API_KEY = "df01bb05ce03159d54c33e1e22eba2cf"

# --- DICCIONARIO DE TRADUCCIÓN ---
TRANSLATIONS = {
    'es': {
        'shippy': 'Envíos Certificados',
        'cart': 'Carrito',
        'catalog': 'Catálogo',
        'offers': 'Ofertas',
        'scenarios': 'Escenarios',
        'weapons': 'Armas',
        'kits': 'Kit de Tiro',
        'sims': 'Simuladores',
        'admin': 'Admin',
        'contact': 'Contacto',
        'tech_support': 'Servicio Técnico',
        'warranty': 'Garantía ALPHA',
        'shipping_info': 'Envíos de Armas',
        'login_title': 'Acceso Administrativo',
        'pass_label': 'Contraseña de Seguridad',
        'enter_btn': 'Ingresar',
        'panel_title': 'Panel de Administración',
        'logout': 'Cerrar Sesión',
        'prod_name': 'Nombre del Producto',
        'category': 'Categoría',
        'specs': 'Especificaciones',
        'images_label': 'Imágenes del Producto (Seleccionar varias)',
        'price_usd': 'Precio en USD',
        'price_cop': 'Precio COP (Automático)',
        'save_btn': 'Guardar Producto',
        'add_cart': 'AÑADIR AL CARRITO',
        'no_products': 'No hay productos cargados.',
        'footer_slogan': 'Líderes en tecnología de simulación de tiro.',
        'rights': 'Todos los derechos reservados.'
    },
    'en': {
        'shippy': 'Certified Shipping',
        'cart': 'Cart',
        'catalog': 'Catalog',
        'offers': 'Offers',
        'scenarios': 'Scenarios',
        'weapons': 'Weapons',
        'kits': 'Shooting Kits',
        'sims': 'Simulators',
        'admin': 'Admin',
        'contact': 'Contact',
        'tech_support': 'Tech Support',
        'warranty': 'ALPHA Warranty',
        'shipping_info': 'Weapon Shipping',
        'login_title': 'Admin Access',
        'pass_label': 'Security Password',
        'enter_btn': 'Enter',
        'panel_title': 'Admin Panel',
        'logout': 'Logout',
        'prod_name': 'Product Name',
        'category': 'Category',
        'specs': 'Specs',
        'images_label': 'Product Images (Select multiple)',
        'price_usd': 'Price USD',
        'price_cop': 'Price COP (Auto)',
        'save_btn': 'Save Product',
        'add_cart': 'ADD TO CART',
        'no_products': 'No products loaded.',
        'footer_slogan': 'Leaders in shooting simulation technology.',
        'rights': 'All rights reserved.'
    },
    'pt': {
        'shippy': 'Envios Certificados',
        'cart': 'Carrinho',
        'catalog': 'Catálogo',
        'offers': 'Ofertas',
        'scenarios': 'Cenários',
        'weapons': 'Armas',
        'kits': 'Kits de Tiro',
        'sims': 'Simuladores',
        'admin': 'Admin',
        'contact': 'Contato',
        'tech_support': 'Suporte Técnico',
        'warranty': 'Garantia ALPHA',
        'shipping_info': 'Envio de Armas',
        'login_title': 'Acesso Administrativo',
        'pass_label': 'Senha de Segurança',
        'enter_btn': 'Entrar',
        'panel_title': 'Painel de Administração',
        'logout': 'Sair',
        'prod_name': 'Nome do Produto',
        'category': 'Categoria',
        'specs': 'Especificações',
        'images_label': 'Imagens do Produto (Selecione várias)',
        'price_usd': 'Preço em USD',
        'price_cop': 'Preço COP (Auto)',
        'save_btn': 'Salvar Produto',
        'add_cart': 'ADICIONAR AO CARRINHO',
        'no_products': 'Não há produtos carregados.',
        'footer_slogan': 'Líderes em tecnologia de simulação de tiro.',
        'rights': 'Todos os direitos reservados.'
    }
}

def get_db_connection():
    conn = psycopg2.connect(DB_URL, cursor_factory=RealDictCursor)
    return conn

# --- HELPERS ---
def upload_image_to_imgbb(file):
    """Sube un archivo a ImgBB y retorna la URL"""
    url = "https://api.imgbb.com/1/upload"
    payload = {'key': IMGBB_API_KEY}
    files = {'image': file}
    try:
        response = requests.post(url, data=payload, files=files)
        data = response.json()
        if data['success']:
            return data['data']['url']
    except Exception as e:
        print(f"Error subiendo imagen: {e}")
    return None

@app.context_processor
def inject_lang():
    """Inyecta el diccionario de traducción al HTML"""
    lang = session.get('lang', 'es')
    return dict(t=TRANSLATIONS[lang], current_lang=lang)

# --- RUTAS ---

@app.route('/set_language/<lang>')
def set_language(lang):
    if lang in TRANSLATIONS:
        session['lang'] = lang
    return redirect(request.referrer or url_for('index'))

@app.route('/')
def index():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM products ORDER BY id DESC")
    products = cur.fetchall()
    
    # Procesar imágenes (convertir string CSV a lista)
    for p in products:
        if p['image_urls']:
            p['images'] = p['image_urls'].split(',')
        else:
            p['images'] = []
            
    cur.close()
    conn.close()
    return render_template('index.html', products=products)

@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        password = request.form['password']
        if password == "1032491753Outlook*":
            session['logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Contraseña incorrecta', 'error')
    return render_template('login.html')

@app.route('/admin', methods=['GET', 'POST'])
def admin_dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('admin_login'))
    
    if request.method == 'POST':
        name = request.form['name']
        category = request.form['category']
        specs = request.form['specs']
        price_usd = float(request.form['price_usd'])
        tasa_cambio = 4150 
        price_cop = price_usd * tasa_cambio
        
        # Manejo de múltiples imágenes
        uploaded_files = request.files.getlist('images')
        image_urls_list = []
        
        for file in uploaded_files:
            if file.filename != '':
                img_url = upload_image_to_imgbb(file)
                if img_url:
                    image_urls_list.append(img_url)
        
        # Unir URLs por comas para guardar en TEXT
        final_images_str = ",".join(image_urls_list)

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO products (name, category, specs, price_usd, price_cop, image_urls)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (name, category, specs, price_usd, price_cop, final_images_str))
        conn.commit()
        cur.close()
        conn.close()
        flash('Producto agregado correctamente', 'success')
        
    return render_template('admin.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)