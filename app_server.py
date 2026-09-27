from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import sqlite3
import pandas as pd
import os

app = Flask(__name__)
app.secret_key = 'vuongtungaotosecretkey'  # Khóa phiên đăng nhập admin

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Hàm kết nối cơ sở dữ liệu SQLite
def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

# Khởi tạo bảng dữ liệu sản phẩm mẫu nếu chưa có
def init_db():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            manufacturer TEXT NOT NULL,
            mfg_date TEXT NOT NULL,
            price TEXT NOT NULL,
            status TEXT NOT NULL
        )
    ''')
    # Thêm sẵn dữ liệu mẫu chuẩn
    conn.execute('''
        INSERT OR IGNORE INTO products (code, name, manufacturer, mfg_date, price, status)
        VALUES 
        ('SP001', 'Sâm ngọc linh nguyên chất', 'Tập đoàn dược phẩm VN', '2026-02-10', '2.500.000 VNĐ', 'Hàng thật'),
        ('SP002', 'Đông trùng hạ thảo chính hãng', 'Công ty cổ phần dược liệu', '2026-01-15', '1.800.000 VNĐ', 'Hàng thật')
    ''')
    conn.commit()
    conn.close()

init_db()

# Trang chủ cho khách hàng quét mã
@app.route('/')
def index():
    return render_template('index.html')

# API kiểm tra sản phẩm
@app.route('/check', methods=['POST'])
def check_product():
    data = request.get_json()
    code = data.get('code', '').strip().upper()
    
    conn = get_db_connection()
    product = conn.execute('SELECT * FROM products WHERE code = ?', (code,)).fetchone()
    conn.close()
    
    if product:
        return jsonify({
            'success': True,
            'name': product['name'],
            'manufacturer': product['manufacturer'],
            'mfg_date': product['mfg_date'],
            'price': product['price'],
            'status': product['status']
        })
    else:
        return jsonify({
            'success': False,
            'message': 'Mã sản phẩm không tồn tại hoặc sản phẩm không rõ nguồn gốc (Cảnh báo hàng giả!).'
        })

# --- TRANG QUẢN TRỊ ADMIN (TỰ ĐỘNG QUẢN LÝ SẢN PHẨM) ---

# Đăng nhập Admin đơn giản
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == 'admin' and password == 'vuongtung2026':
            session['logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            error = 'Sai tên đăng nhập hoặc mật khẩu!'
    return render_template('admin_login.html', error=error)

# Trang quản lý danh sách và thêm sản phẩm tự động
@app.route('/admin')
def admin_dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('admin_login'))
    
    conn = get_db_connection()
    products = conn.execute('SELECT * FROM products ORDER BY id DESC').fetchall()
    conn.close()
    return render_template('admin.html', products=products)

# Thêm sản phẩm mới thủ công vào Database
@app.route('/admin/add', methods=['POST'])
def admin_add_product():
    if not session.get('logged_in'):
        return redirect(url_for('admin_login'))
    
    code = request.form['code'].strip().upper()
    name = request.form['name'].strip()
    manufacturer = request.form['manufacturer'].strip()
    mfg_date = request.form['mfg_date'].strip()
    price = request.form['price'].strip()
    status = request.form['status'].strip()
    
    try:
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO products (code, name, manufacturer, mfg_date, price, status)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (code, name, manufacturer, mfg_date, price, status))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Lỗi thêm sản phẩm: {e}")
        
    return redirect(url_for('admin_dashboard'))

# TÍNH NĂNG MỚI: Nhập danh sách tự động hàng loạt từ File Excel
@app.route('/admin/import_excel', methods=['POST'])
def admin_import_excel():
    if not session.get('logged_in'):
        return redirect(url_for('admin_login'))
    
    if 'excel_file' not in request.files:
        return redirect(url_for('admin_dashboard'))
    
    file = request.files['excel_file']
    if file.filename == '':
        return redirect(url_for('admin_dashboard'))
        
    if file:
        file_path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(file_path)
        
        try:
            df = pd.read_excel(file_path)
            conn = get_db_connection()
            for _, row in df.iterrows():
                code_val = str(row['code']).strip().upper()
                name_val = str(row['name']).strip()
                manufacturer_val = str(row.get('manufacturer', '')).strip()
                mfg_date_val = str(row.get('mfg_date', '')).strip()
                price_val = str(row.get('price', '')).strip()
                status_val = str(row.get('status', 'Hàng thật')).strip()
                
                # Kiểm tra tránh trùng lặp mã sản phẩm
                existing = conn.execute('SELECT * FROM products WHERE code = ?', (code_val,)).fetchone()
                if not existing:
                    conn.execute('''
                        INSERT INTO products (code, name, manufacturer, mfg_date, price, status)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (code_val, name_val, manufacturer_val, mfg_date_val, price_val, status_val))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Lỗi import Excel: {e}")
            
        return redirect(url_for('admin_dashboard'))

# Xóa sản phẩm tự động
@app.route('/admin/delete/<string:code>')
def admin_delete_product(code):
    if not session.get('logged_in'):
        return redirect(url_for('admin_login'))
    
    conn = get_db_connection()
    conn.execute('DELETE FROM products WHERE code = ?', (code,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin_dashboard'))

# Đăng xuất Admin
@app.route('/admin/logout')
def admin_logout():
    session.pop('logged_in', None)
    return redirect(url_for('admin_login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)