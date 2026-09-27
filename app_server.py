import os
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, session, send_file
import qrcode

app = Flask(__name__)
app.secret_key = 'vuongtung_secret_key_2026'

# Dữ liệu mẫu ban đầu (hoặc lưu trữ trong bộ nhớ/database)
products_db = [
    {
        "code": "SP002",
        "name": "Đông trùng hạ thảo chính hãng",
        "manufacturer": "Công ty cổ phần dược liệu",
        "mfg_date": "2026-01-15",
        "price": "1.800.000 VNĐ",
        "status": "Hàng thật"
    },
    {
        "code": "SP001",
        "name": "Sâm ngọc linh nguyên chất",
        "manufacturer": "Tập đoàn dược phẩm VN",
        "mfg_date": "2026-02-10",
        "price": "2.500.000 VNĐ",
        "status": "Hàng thật"
    }
]

# Thư mục lưu trữ ảnh QR code được sinh ra cho nhà sản xuất
QR_OUTPUT_DIR = "static/generated_qrs"
os.makedirs(QR_OUTPUT_DIR, exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/verify', methods=['GET'])
def verify_product():
    code = request.args.get('code', '')
    product = next((p for p in products_db if p['code'] == code), None)
    if product:
        return f"Sản phẩm chính hãng: {product['name']} - NSX: {product['manufacturer']} - Giá: {product['price']}"
    else:
        return "Cảnh báo: Không tìm thấy thông tin sản phẩm hoặc nghi vấn hàng giả!", 404

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == 'admin' and password == 'vuongtung2026':
            session['logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            error = 'Tên đăng nhập hoặc mật khẩu không chính xác!'
    return render_template('admin_login.html', error=error)

@app.route('/admin')
def admin_dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('admin_login'))
    return render_template('admin.html', products=products_db)

@app.route('/admin/import_excel', methods=['POST'])
def import_excel():
    if not session.get('logged_in'):
        return redirect(url_for('admin_login'))
    
    file = request.files.get('excel_file')
    if file and file.filename.endswith(('.xlsx', '.xls')):
        df = pd.read_excel(file)
        for _, row in df.iterrows():
            new_prod = {
                "code": str(row.get('code', '')),
                "name": str(row.get('name', '')),
                "manufacturer": str(row.get('manufacturer', '')),
                "mfg_date": str(row.get('mfg_date', '')),
                "price": str(row.get('price', '')),
                "status": str(row.get('status', 'Hàng thật'))
            }
            # Tránh trùng lặp mã
            if not any(p['code'] == new_prod['code'] for p in products_db):
                products_db.append(new_prod)
        return redirect(url_for('admin_dashboard'))
    
    return "Vui lòng chọn đúng định dạng file Excel (.xlsx hoặc .xls)", 400

@app.route('/admin/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('admin_login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
