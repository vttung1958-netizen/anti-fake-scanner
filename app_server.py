import os
import uuid
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, session, send_file
import qrcode

app = Flask(__name__)
app.secret_key = 'vuongtung_secret_key_2026'

# Cơ sở dữ liệu lưu sản phẩm và trạng thái quét chống hàng giả
products_db = [
    {
        "code": "SP001",
        "token": "tok_alpha_123",
        "name": "Sâm ngọc linh nguyên chất",
        "manufacturer": "Tập đoàn dược phẩm VN",
        "mfg_date": "2026-02-10",
        "price": "2.500.000 VNĐ",
        "scan_count": 0,
        "status": "Hàng thật"
    }
]

QR_OUTPUT_DIR = "static/generated_qrs"
os.makedirs(QR_OUTPUT_DIR, exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

# Trang xác thực thông minh (Chống sao chép tem, phát hiện hàng giả qua số lần quét)
@app.route('/verify', methods=['GET'])
def verify_product():
    code = request.args.get('code', '')
    token = request.args.get('token', '')
    
    product = next((p for p in products_db if p['code'] == code and p['token'] == token), None)
    
    if not product:
        return "<h2 style='color:red; text-align:center; font-family:Arial; margin-top:50px;'>🚨 CẢNH BÁO: Mã sản phẩm không tồn tại hoặc tem giả mạo!</h2>", 404
    
    product['scan_count'] += 1
    
    if product['scan_count'] > 3:
        return f"""
        <div style='text-align:center; font-family:Arial; max-width:600px; margin:50px auto; padding:30px; border:2px solid red; border-radius:10px; background:#fff5f5;'>
            <h1 style='color:red;'>🚨 CẢNH BÁO NGUY HIỂM: NGHI VẤN HÀNG GIẢ!</h1>
            <p>Mã sản phẩm <b>{product['name']}</b> đã bị quét quá nhiều lần ({product['scan_count']} lần).</p>
            <p>Tem chống giả có dấu hiệu bị sao chép. Vui lòng liên hệ chủ sở hữu thương hiệu: <b>{product['manufacturer']}</b></p>
        </div>
        """
    
    return f"""
    <div style='font-family:Arial; max-width:600px; margin:50px auto; padding:30px; border:2px solid #27ae60; border-radius:10px; background:#f9fff9;'>
        <h2 style='color:#27ae60;'>✅ XÁC THỰC THÀNH CÔNG: HÀNG CHÍNH HÃNG</h2>
        <hr style='border:0; border-top:1px solid #ddd; margin:15px 0;'>
        <p><b>Tên sản phẩm:</b> {product['name']}</p>
        <p><b>Nhà sản xuất:</b> {product['manufacturer']}</p>
        <p><b>Ngày sản xuất:</b> {product['mfg_date']}</p>
        <p><b>Giá thị trường / Niêm yết:</b> <span style='color:blue; font-size:18px;'>{product['price']}</span></p>
        <p style='color:gray; font-size:12px; margin-top:20px;'>Lượt quét kiểm tra lần thứ: {product['scan_count']}</p>
    </div>
    """

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    error = None
    if request.method == 'POST':
        if request.form.get('username') == 'admin' and request.form.get('password') == 'vuongtung2026':
            session['logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        error = 'Tên đăng nhập hoặc mật khẩu không chính xác!'
    return render_template('admin_login.html', error=error)

@app.route('/admin')
def admin_dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('admin_login'))
    return render_template('admin.html', products=products_db)

# Tính năng tự động sinh lô mã QR định danh cho nhà sản xuất
@app.route('/admin/generate_batch', methods=['POST'])
def generate_batch():
    if not session.get('logged_in'):
        return redirect(url_for('admin_login'))
    
    qty = int(request.form.get('quantity', 10))
    prod_name = request.form.get('prod_name', 'Sản phẩm mới')
    manufacturer = request.form.get('manufacturer', 'Công ty đối tác')
    price = request.form.get('price', '1.000.000 VNĐ')
    
    batch_data = []
    for i in range(qty):
        code = f"SP-{uuid.uuid4().hex[:6].upper()}"
        token = uuid.uuid4().hex[:12]
        
        verify_url = f"https://anti-fake-scanner-2026.onrender.com/verify?code={code}&token={token}"
        img = qrcode.make(verify_url)
        img_path = os.path.join(QR_OUTPUT_DIR, f"{code}.png")
        img.save(img_path)
        
        new_prod = {
            "code": code,
            "token": token,
            "name": prod_name,
            "manufacturer": manufacturer,
            "mfg_date": "2026-03-01",
            "price": price,
            "scan_count": 0,
            "status": "Hàng thật"
        }
        products_db.append(new_prod)
        batch_data.append({"Mã Code": code, "Token": token, "Link Xác Thực": verify_url})
    
    df = pd.DataFrame(batch_data)
    export_file = "static/Danh_Sach_Tem_QR.xlsx"
    df.to_excel(export_file, index=False)
    
    return send_file(export_file, as_attachment=True)

@app.route('/admin/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('admin_login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
