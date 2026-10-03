import os
import uuid
import json
import hashlib
import qrcode
import barcode
from barcode.writer import ImageWriter
import zipfile
from openpyxl import Workbook
from flask import Flask, render_template, request, redirect, url_for, session, send_file
from datetime import datetime
from fpdf import FPDF

app = Flask(__name__)
app.secret_key = 'vuong_thanh_tung_secret_key_2026'

QR_OUTPUT_DIR = "static/qrs"
BARCODE_OUTPUT_DIR = "static/barcodes"
os.makedirs(QR_OUTPUT_DIR, exist_ok=True)
os.makedirs(BARCODE_OUTPUT_DIR, exist_ok=True)
os.makedirs("static", exist_ok=True)
os.makedirs("templates", exist_ok=True)

ADMIN_PASS_FILE = "admin_pass.txt"
CONFIG_FILE = "pricing_config.json"

DEFAULT_CONFIG = {
    "base_price": 890,
    "hologram_fee": 150,
    "destructible_seal_fee": 200,
    "void_bottle_fee": 250,
    "uv_1wave_fee": 350,
    "uv_2wave_fee": 550,
    "size_fee_25": 50,
    "size_fee_35": 120,
    "barcode_addon_fee": 100
}

def load_pricing_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return DEFAULT_CONFIG

def save_pricing_config(new_config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(new_config, f, ensure_ascii=False, indent=4)

def get_admin_password():
    if os.path.exists(ADMIN_PASS_FILE):
        with open(ADMIN_PASS_FILE, "r", encoding="utf-8") as f:
            pw = f.read().strip()
            if pw: return pw
    return 'tung1958'

def save_admin_password(new_pw):
    with open(ADMIN_PASS_FILE, "w", encoding="utf-8") as f:
        f.write(new_pw)

def generate_secure_digital_signature(code, manufacturer, hw_id):
    raw_string = f"{code}-{manufacturer}-{hw_id}-VUONGTUNG-ENTERPRISE-2026"
    return hashlib.sha256(raw_string.encode('utf-8')).hexdigest()[:16].upper()

def calculate_tem_price(quantity, print_type='black_white', qr_size=20, include_barcode=False):
    config = load_pricing_config()
    
    if quantity <= 1000: base = quantity * 890
    elif quantity <= 5000: base = quantity * 670
    elif quantity <= 10000: base = quantity * 456
    elif quantity <= 30000: base = quantity * 345
    else: base = quantity * 266
    
    special_fee = 0
    if print_type == 'hologram_7color': special_fee = quantity * int(config.get("hologram_fee", 150))
    elif print_type == 'destructible_seal': special_fee = quantity * int(config.get("destructible_seal_fee", 200))
    elif print_type == 'void_bottle': special_fee = quantity * int(config.get("void_bottle_fee", 250))
    elif print_type == 'uv_1wave': special_fee = quantity * int(config.get("uv_1wave_fee", 350))
    elif print_type == 'uv_2wave': special_fee = quantity * int(config.get("uv_2wave_fee", 550))
        
    size_fee = 0
    if qr_size == 25: size_fee = quantity * int(config.get("size_fee_25", 50))
    elif qr_size == 35: size_fee = quantity * int(config.get("size_fee_35", 120))
        
    barcode_fee = quantity * int(config.get("barcode_addon_fee", 100)) if include_barcode else 0
        
    return base + special_fee + size_fee + barcode_fee

orders_db = {}
products_db = [
    {
        "code": "SP001",
        "token": "A1B2C3D4-MASTER",
        "name": "Sản phẩm mẫu chính hãng",
        "manufacturer": "Công ty TNHH Vương Tùng",
        "hardware_id": "HW-MASTER-ROOT-01",
        "mfg_date": "2026-03-01",
        "price": "2.500.000 VNĐ",
        "scan_count": 1,
        "status": "Hàng thật"
    }
]

@app.route('/', methods=['GET', 'POST'])
def index():
    code = None
    token = None
    product = None
    status = None
    message = None
    
    if request.method == 'POST':
        code = (request.form.get('code') or request.form.get('product_code') or request.form.get('search') or '').strip().upper()
    else:
        code = request.args.get('code')
        token = request.args.get('token')
        
    if not code:
        return render_template('index.html', status=None, message=None, product=None)
        
    product = next((p for p in products_db if p["code"] == code), None)
    
    if not product:
        status = "fake"
        message = f"CẢNH BÁO: Mã sản phẩm '{code}' không tồn tại trên hệ thống xác thực!"
        return render_template('index.html', status=status, message=message, product=None)
        
    if token and product.get("token") and product["token"] != token:
        status = "fake"
        message = "CẢNH BÁO NGUY HIỂM: Phát hiện tem giả mạo! Chữ ký số mã hóa phần cứng không khớp."
        return render_template('index.html', status=status, message=message, product=product)
        
    product["scan_count"] = product.get("scan_count", 0) + 1
    
    if product["scan_count"] > 3:
        status = "warning"
        message = f"CẢNH BÁO: Tem này đã bị quét {product['scan_count']} lần! Có dấu hiệu bị sao chép hoặc bóc mở trái phép."
    else:
        status = "success"
        message = "XÁC THỰC THÀNH CÔNG: Sản phẩm chính hãng 100% từ Giải Pháp Cuộc Sống."
        
    return render_template('index.html', status=status, message=message, product=product)

@app.route('/verify', methods=['GET'])
def verify():
    code = request.args.get('code')
    token = request.args.get('token')
    return redirect(url_for('index', code=code, token=token))

@app.route('/buy', methods=['GET', 'POST'])
def buy():
    if request.method == 'POST':
        prod_name = request.form.get('prod_name')
        manufacturer = request.form.get('manufacturer')
        tax_code = request.form.get('tax_code', 'Chưa cung cấp')
        try:
            quantity = int(request.form.get('quantity', 1000))
        except ValueError:
            quantity = 1000
            
        print_type = request.form.get('print_type', 'black_white')
        qr_size = int(request.form.get('qr_size', 20))
        include_barcode = True if request.form.get('include_barcode') == 'yes' else False
        
        company_hw_id = f"HW-CORP-{uuid.uuid4().hex[:10].upper()}"
        total_price = calculate_tem_price(quantity, print_type, qr_size, include_barcode)
        order_id = f"DH{uuid.uuid4().hex[:6].upper()}"
        
        orders_db[order_id] = {
            "prod_name": prod_name, "manufacturer": manufacturer, "tax_code": tax_code,
            "hardware_id": company_hw_id, "quantity": quantity, "print_type": print_type,
            "qr_size": qr_size, "include_barcode": include_barcode, "total_price": total_price, "status": "pending",
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        return redirect(url_for('checkout', order_id=order_id))
        
    return render_template('buy.html')

@app.route('/checkout/<order_id>')
def checkout(order_id):
    order = orders_db.get(order_id)
    if not order: return "Đơn hàng không tồn tại!", 404
    bank_id = "AGRIBANK"
    account_no = "1500215038690"
    amount = order["total_price"]
    add_info = f"AFQR {order_id}"
    vietqr_url = f"https://img.vietqr.io/image/{bank_id}-{account_no}-compact2.png?amount={amount}&addInfo={add_info}"
    return render_template('checkout.html', order=order, order_id=order_id, vietqr_url=vietqr_url)

@app.route('/success/<order_id>')
def success_download(order_id):
    order = orders_db.get(order_id)
    if not order or order["status"] != "paid": return "Đơn hàng chưa thanh toán!", 403
    
    prod_name = order["prod_name"]
    manufacturer = order["manufacturer"]
    quantity = order["quantity"]
    company_hw_id = order["hardware_id"]
    print_type = order.get("print_type", "black_white")
    qr_size = order.get("qr_size", 20)
    include_barcode = order.get("include_barcode", False)
    price_str = f"{order['total_price']:,} VNĐ"
    
    try:
        wb = Workbook()
        ws = wb.active
        ws.title = "ThongKe_DanhSach"
        ws.append(["--- HỆ THỐNG XÁC THỰC & MÃ VẠCH QUỐC GIA - GIẢI PHÁP CUỘC SỐNG ---"])
        ws.append(["Tên sản phẩm:", prod_name, "Nhà sản xuất:", manufacturer])
        ws.append(["Kích thước QR:", f"{qr_size}x{qr_size} mm", "Tích hợp Barcode:", "Có (Code 128)" if include_barcode else "Không"])
        ws.append([])
        
        header_row = 5
        ws.cell(row=header_row, column=1, value="STT")
        ws.cell(row=header_row, column=2, value="Mã Code")
        ws.cell(row=header_row, column=3, value="Chữ Ký Số & Token")
        ws.cell(row=header_row, column=4, value="Link Xác Thực")
        ws.cell(row=header_row, column=5, value="Trạng Thái Barcode")
        
        batch_id = uuid.uuid4().hex[:8]
        batch_img_dir = f"static/batch_qr_{batch_id}"
        batch_bc_dir = f"static/batch_bc_{batch_id}"
        os.makedirs(batch_img_dir, exist_ok=True)
        if include_barcode: os.makedirs(batch_bc_dir, exist_ok=True)
        
        generated_qr_files = []
        generated_bc_files = []
        Code128 = barcode.get_class('code128')
        
        for i in range(1, quantity + 1):
            code = f"SP{i:03d}"
            digital_sign = generate_secure_digital_signature(code, manufacturer, company_hw_id)
            token = f"{uuid.uuid4().hex[:6]}-{digital_sign}"
            verify_url = f"https://vuongtung.com.vn/verify?code={code}&token={token}"
            
            img = qrcode.make(verify_url)
            img_path = os.path.join(batch_img_dir, f"{code}.png")
            img.save(img_path)
            generated_qr_files.append(img_path)
            
            if include_barcode:
                bc = Code128(code, writer=ImageWriter())
                bc_saved = bc.save(os.path.join(BARCODE_OUTPUT_DIR, f"bc_{code}"), options={'write_text': True})
                batch_bc_path = os.path.join(batch_bc_dir, f"{code}.png")
                if os.path.exists(bc_saved):
                    os.replace(bc_saved, batch_bc_path)
                    generated_bc_files.append(batch_bc_path)
            
            products_db.append({
                "code": code, "token": token, "name": prod_name, "manufacturer": manufacturer,
                "hardware_id": company_hw_id, "mfg_date": datetime.now().strftime("%Y-%m-%d"),
                "price": price_str, "scan_count": 0, "status": "Hàng thật"
            })
            
            r_idx = header_row + i
            ws.cell(row=r_idx, column=1, value=i)
            ws.cell(row=r_idx, column=2, value=code)
            ws.cell(row=r_idx, column=3, value=token)
            ws.cell(row=r_idx, column=4, value=verify_url)
            ws.cell(row=r_idx, column=5, value="Code 128" if include_barcode else "Không")
            
        excel_path = f"static/ThongKe_{order_id}.xlsx"
        wb.save(excel_path)
        
        zip_path = f"static/Goi_Tem_{order_id}.zip"
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            zipf.write(excel_path, arcname="1_DanhSach_MaQR_Barcode.xlsx")
            for f in generated_qr_files: zipf.write(f, arcname=f"2_ThuVien_QR/{os.path.basename(f)}")
            if include_barcode:
                for f in generated_bc_files: zipf.write(f, arcname=f"3_ThuVien_Barcode/{os.path.basename(f)}")
                
        return send_file(zip_path, as_attachment=True)
    except Exception as e:
        return f"Lỗi tạo tệp: {str(e)}", 500

@app.route('/news')
def news(): return render_template('news.html')

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    current_password = get_admin_password()
    if request.method == 'POST':
        if request.form.get('action') == 'login':
            if request.form.get('username') == 'admin' and request.form.get('password') == current_password:
                session['logged_in'] = True
                return redirect(url_for('admin'))
            else:
                return render_template('admin_login.html', error="Sai tên đăng nhập hoặc mật khẩu quản trị!")
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('logged_in', None)
    return redirect(url_for('admin_login'))

@app.route('/admin')
def admin():
    if not session.get('logged_in'):
        return redirect(url_for('admin_login'))
    return render_template('admin.html', products=products_db, orders=orders_db, config=load_pricing_config())

@app.route('/quan_tri')
def quan_tri(): return redirect(url_for('admin'))

@app.route('/admin/approve/<order_id>')
def approve_order(order_id):
    if not session.get('logged_in'): return redirect(url_for('admin_login'))
    if order_id in orders_db: orders_db[order_id]["status"] = "paid"
    return redirect(url_for('admin'))

@app.route('/admin/update_pricing', methods=['POST'])
def update_pricing():
    if not session.get('logged_in'): return redirect(url_for('admin_login'))
    try:
        new_config = {
            "base_price": int(request.form.get('base_price', 890)),
            "hologram_fee": int(request.form.get('hologram_fee', 150)),
            "destructible_seal_fee": int(request.form.get('destructible_seal_fee', 200)),
            "void_bottle_fee": int(request.form.get('void_bottle_fee', 250)),
            "uv_1wave_fee": int(request.form.get('uv_1wave_fee', 350)),
            "uv_2wave_fee": int(request.form.get('uv_2wave_fee', 550)),
            "size_fee_25": int(request.form.get('size_fee_25', 50)),
            "size_fee_35": int(request.form.get('size_fee_35', 120)),
            "barcode_addon_fee": int(request.form.get('barcode_addon_fee', 100))
        }
        save_pricing_config(new_config)
    except Exception:
        pass
    return redirect(url_for('admin'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
