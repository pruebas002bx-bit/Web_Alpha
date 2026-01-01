import os
import io
import time
import requests
from PIL import Image
from flask import Flask, render_template, request, redirect, url_for, session, flash
import psycopg2
from psycopg2.extras import RealDictCursor
from deep_translator import GoogleTranslator

app = Flask(__name__)
app.secret_key = 'alpha_super_secret_key'

# --- CONFIGURACIÓN ---
DB_URL = os.environ.get("DATABASE_URL", "postgresql://usuario:password@host:port/defaultdb")
IMGBB_API_KEY = "df01bb05ce03159d54c33e1e22eba2cf"
CURRENCY_API_KEY = "1a9b899a5a19988a73d68cde"

# --- CACHÉ SIMPLE PARA MONEDA ---
currency_cache = {
    "rate": 4150,  # Valor por defecto si falla la API
    "last_updated": 0
}

def get_usd_to_cop_rate():
    """Obtiene la tasa de cambio con caché de 1 hora"""
    now = time.time()
    # Si pasó menos de 1 hora (3600 seg), usar caché
    if now - currency_cache["last_updated"] < 3600:
        return currency_cache["rate"]

    try:
        url = f"https://v6.exchangerate-api.com/v6/{CURRENCY_API_KEY}/latest/USD"
        response = requests.get(url)
        data = response.json()
        if data['result'] == 'success':
            rate = data['conversion_rates']['COP']
            currency_cache["rate"] = rate
            currency_cache["last_updated"] = now
            return rate
    except Exception as e:
        print(f"Error API Moneda: {e}")
    
    return currency_cache["rate"]

# --- DICCIONARIO DE TRADUCCIÓN INTERFAZ ---
UI_TRANSLATIONS = {
    'es': {
        'shippy': 'Envíos Certificados', 'cart': 'Carrito', 'offers': 'Ofertas',
        'scenarios': 'Escenarios', 'weapons': 'Armas', 'kits': 'Kit de Tiro',
        'sims': 'Simuladores', 'admin': 'Admin', 'contact': 'Contacto',
        'tech_support': 'Servicio Técnico', 'warranty': 'Garantía ALPHA',
        'shipping_info': 'Envíos de Armas', 'add_cart': 'AÑADIR AL CARRITO',
        'footer_slogan': 'Líderes en tecnología de simulación de tiro.',
        'rights': 'Todos los derechos reservados.', 'view_details': 'VER DETALLES',
        'close': 'Cerrar', 'description': 'Descripción', 'price': 'Precio'
    },
    'en': {
        'shippy': 'Certified Shipping', 'cart': 'Cart', 'offers': 'Offers',
        'scenarios': 'Scenarios', 'weapons': 'Weapons', 'kits': 'Shooting Kits',
        'sims': 'Simulators', 'admin': 'Admin', 'contact': 'Contact',
        'tech_support': 'Tech Support', 'warranty': 'ALPHA Warranty',
        'shipping_info': 'Weapon Shipping', 'add_cart': 'ADD TO CART',
        'footer_slogan': 'Leaders in shooting simulation technology.',
        'rights': 'All rights reserved.', 'view_details': 'VIEW DETAILS',
        'close': 'Close', 'description': 'Description', 'price': 'Price'
    },
    'pt': {
        'shippy': 'Envios Certificados', 'cart': 'Carrinho', 'offers': 'Ofertas',
        'scenarios': 'Cenários', 'weapons': 'Armas', 'kits': 'Kits de Tiro',
        'sims': 'Simuladores', 'admin': 'Admin', 'contact': 'Contato',
        'tech_support': 'Suporte Técnico', 'warranty': 'Garantia ALPHA',
        'shipping_info': 'Envio de Armas', 'add_cart': 'ADICIONAR AO CARRINHO',
        'footer_slogan': 'Líderes em tecnologia de simulação de tiro.',
        'rights': 'Todos os direitos reservados.', 'view_details': 'VER DETALHES',
        'close': 'Fechar', 'description': 'Descrição', 'price': 'Preço'
    }
}

def get_db_connection():
    conn = psycopg2.connect(DB_URL, cursor_factory=RealDictCursor)
    return conn

# --- FUNCIÓN DE COMPRESIÓN Y SUBIDA ---
def compress_and_upload(file):
    """Comprime imagen al 50% y la sube a ImgBB"""
    try:
        # 1. Abrir imagen con Pillow
        image = Image.open(file)
        
        # 2. Convertir a RGB (por si es PNG con transparencia)
        if image.mode in ("RGBA", "P"):
            image = image.convert("RGB")
            
        # 3. Guardar en memoria (Buffer) con calidad 50
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='JPEG', quality=50, optimize=True)
        img_byte_arr.seek(0) # Volver al inicio del archivo en memoria

        # 4. Subir a ImgBB
        url = "https://api.imgbb.com/1/upload"
        payload = {'key': IMGBB_API_KEY}
        files = {'image': img_byte_arr}
        
        response = requests.post(url, data=payload, files=files)
        data = response.json()
        
        if data['success']:
            return data['data']['url']
            
    except Exception as e:
        print(f"Error procesando imagen: {e}")
    return None

def translate_text(text, target_lang):
    """Traduce texto de DB usando Google Translate (Deep Translator)"""
    if target_lang == 'es' or not text:
        return text
    try:
        # Mapeo de códigos de idioma para la librería
        lang_map = {'en': 'en', 'pt': 'pt'}
        translator = GoogleTranslator(source='auto', target=lang_map.get(target_lang, 'en'))
        return translator.translate(text)
    except:
        return text

# --- CONTEXTO GLOBAL ---
@app.context_processor
def inject_globals():
    lang = session.get('lang', 'es')
    return dict(t=UI_TRANSLATIONS.get(lang, UI_TRANSLATIONS['es']), current_lang=lang)

# --- RUTAS ---
@app.route('/set_language/<lang>')
def set_language(lang):
    if lang in UI_TRANSLATIONS:
        session['lang'] = lang
    return redirect(request.referrer or url_for('index'))

@app.route('/')
def index():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM products ORDER BY id DESC")
    products = cur.fetchall()
    cur.close()
    conn.close()

    # Obtener tasa actual
    cop_rate = get_usd_to_cop_rate()
    target_lang = session.get('lang', 'es')

    # Procesar productos (Imágenes y Traducción dinámica)
    for p in products:
        # Calcular precio COP actualizado
        if p['price_usd']:
            p['price_cop'] = float(p['price_usd']) * cop_rate
        else:
            p['price_cop'] = 0

        # Separar imágenes
        p['images'] = p['image_urls'].split(',') if p['image_urls'] else []

        # Traducir contenido DB si no es español (Puede hacer la carga un poco lenta)
        if target_lang != 'es':
            p['name'] = translate_text(p['name'], target_lang)
            p['category'] = translate_text(p['category'], target_lang)
            p['specs'] = translate_text(p['specs'], target_lang)

    return render_template('index.html', products=products)

@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form['password'] == "1032491753Outlook*":
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
        
        # Procesar imágenes (Compresión y Subida Múltiple)
        uploaded_files = request.files.getlist('images')
        image_urls_list = []
        
        for file in uploaded_files:
            if file.filename != '':
                img_url = compress_and_upload(file)
                if img_url:
                    image_urls_list.append(img_url)
        
        final_images_str = ",".join(image_urls_list)

        conn = get_db_connection()
        cur = conn.cursor()
        # Nota: Guardamos solo USD, el COP se calcula al vuelo en el index
        cur.execute("""
            INSERT INTO products (name, category, specs, price_usd, price_cop, image_urls)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (name, category, specs, price_usd, 0, final_images_str))
        conn.commit()
        cur.close()
        conn.close()
        flash('Producto guardado (Imágenes optimizadas)', 'success')
        
    return render_template('admin.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)