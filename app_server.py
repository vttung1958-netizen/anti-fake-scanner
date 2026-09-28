import os
import uuid
import qrcode
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, session, send_file

app = Flask(__name__)
app.secret_key = 'vuong_thanh_tung_secret_key_2026'

# Đảm bảo thư mục lưu trữ ảnh QR và file tồn tại
QR_OUTPUT_DIR = "static/qrs"
os.makedirs(QR_OUTPUT_DIR, exist_ok=True)
os.makedirs("static", exist_ok=True)

# Cơ sở dữ liệu mẫu lưu trên bộ nhớ tạm của server
products_db = [
    {
        "code": "SP001",
        "token": "a1b2c3d4e5f6",
        "name": "Sâm ngọc linh nguyên chất",
        "manufacturer": "Tập đoàn dược phẩm VN",
        "mfg_date": "2026-03-01",
        "price": "2.500.000 VNĐ",
        "scan_count": 0,
        "status": "Hàng thật"
    }
]

@app.route('/')
def index():
    code = request.args.get('code')
    token = request.args.get('token')
    
    if not code:
        return render_template('index.html', status="error", message="Vui lòng quét mã QR hợp lệ trên sản phẩm.")
    
    product = next((p for p in products_db if p["code"] == code), None)
    
    if not product:
        return render_template('index.html', status="fake", message="CẢNH BÁO: Mã sản phẩm không tồn tại trên hệ thống!")
    
    if product["token"] != token:
        return render_template('index.html', status="fake", message="CẢNH BÁO NGUY HIỂM: Phát hiện tem giả mạo (Sai mã Token bảo mật)!", product=product)
    
    product["scan_count"] += 1
    
    if product["scan_count"] > 3:
        product["status"] = "Hàng giả / Bị nghi ngờ"
        return render_template('index.html', status="warning", message=f"CẢNH BÁO: Tem này đã bị quét {product['scan_count']} lần! Có dấu hiệu bị sao chép hàng loạt.", product=product)
    
    return render_template('index.html', status="success", message="XÁC THỰC THÀNH CÔNG: Sản phẩm chính hãng 100%.", product=product)

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if not session.get('logged_in'):
        return redirect(url_for('admin_login'))
    return render_template('admin.html', products=products_db)

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == 'admin' and password == 'tung1958':
            session['logged_in'] = True
            return redirect(url_for('admin'))
        else:
            return render_template('admin_login.html', error="Sai tên đăng nhập hoặc mật khẩu!")
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('logged_in', None)
    return redirect(url_for('admin_login'))

@app.route('/admin/generate_batch', methods=['POST'])
def generate_batch():
    if not session.get('logged_in'):
        return redirect(url_for('admin_login'))
    
    try:
        prod_name = request.form.get('prod_name')
        manufacturer = request.form.get('manufacturer')
        price = request.form.get('price')
        quantity = int(request.form.get('quantity', 100))
        
        batch_data = []
        
        for i in range(1, quantity + 1):
            code = f"SP{len(products_db) + i:03d}"
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
    except Exception as e:
        return f"<h3>Lỗi hệ thống:</h3><p>{str(e)}</p><a href='/admin'>Quay lại</a>", 500

@app.route('/super_admin')
def super_admin():
    return render_template('super_admin.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
