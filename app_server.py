import os
import uuid
import platform
import subprocess
import hashlib
import qrcode
import zipfile
import openpyxl
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter
from flask import Flask, render_template, request, redirect, url_for, session, send_file, jsonify
from datetime import datetime
from fpdf import FPDF

app = Flask(__name__)
app.secret_key = 'vuong_thanh_tung_secret_key_2026'

QR_OUTPUT_DIR = "static/qrs"
os.makedirs(QR_OUTPUT_DIR, exist_ok=True)
os.makedirs("static", exist_ok=True)
os.makedirs("templates", exist_ok=True)

ADMIN_PASS_FILE = "admin_pass.txt"

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

def calculate_tem_price(quantity):
    if quantity <= 1000: return quantity * 890
    elif quantity <= 2000: return quantity * 810
    elif quantity <= 3000: return quantity * 750
    elif quantity <= 4000: return quantity * 710
    elif quantity <= 5000: return quantity * 670
    elif quantity <= 6000: return quantity * 630
    elif quantity <= 7000: return quantity * 590
    elif quantity <= 8000: return quantity * 545
    elif quantity <= 9000: return quantity * 500
    elif quantity <= 10000: return quantity * 456
    elif quantity <= 15000: return quantity * 413
    elif quantity <= 20000: return quantity * 383
    elif quantity <= 25000: return quantity * 363
    elif quantity <= 30000: return quantity * 345
    elif quantity <= 35000: return quantity * 328
    elif quantity <= 40000: return quantity * 312
    elif quantity <= 45000: return quantity * 297
    elif quantity <= 50000: return quantity * 283
    elif quantity <= 60000: return quantity * 270
    else: return quantity * 266

orders_db = {}
users_db = {}

products_db = [
    {
        "code": "SP001",
        "token": "A1B2C3D4-MASTER",
        "name": "Sâm ngọc linh nguyên chất",
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
        message = f"CẢNH BÁO: Tem này đã bị quét {product['scan_count']} lần! Có dấu hiệu bị sao chép hoặc in lậu."
    else:
        status = "success"
        message = "XÁC THỰC THÀNH CÔNG: Sản phẩm chính hãng 100% từ Giải Pháp Cuộc Sống."
        
    return render_template('index.html', status=status, message=message, product=product)

@app.route('/verify', methods=['GET'])
def verify():
    code = request.args.get('code')
    token = request.args.get('token')
    return redirect(url_for('index', code=code, token=token))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        fullname = request.form.get('fullname')
        username = request.form.get('username')
        password = request.form.get('password')
        users_db[username] = {
            "fullname": fullname,
            "password": password,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        return redirect(url_for('buy'))
    return render_template('register.html')

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
        company_hw_id = f"HW-CORP-{uuid.uuid4().hex[:10].upper()}"
        total_price = calculate_tem_price(quantity)
        order_id = f"DH{uuid.uuid4().hex[:6].upper()}"
        
        orders_db[order_id] = {
            "prod_name": prod_name,
            "manufacturer": manufacturer,
            "tax_code": tax_code,
            "hardware_id": company_hw_id,
            "quantity": quantity,
            "print_type": print_type,
            "total_price": total_price,
            "status": "pending",
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

@app.route('/api/payment_webhook', methods=['POST'])
def payment_webhook():
    data = request.json or {}
    content = str(data.get('content', '')).upper()
    amount = float(data.get('amount', 0))
    for order_id, order in orders_db.items():
        if order_id in content and amount >= order["total_price"]:
            order["status"] = "paid"
            return jsonify({"success": True, "message": f"Đơn hàng {order_id} đã thanh toán tự động thành công!"})
    return jsonify({"success": False, "message": "Không tìm thấy mã đơn hàng phù hợp."}), 400

@app.route('/api/check_status/<order_id>')
def check_status(order_id):
    order = orders_db.get(order_id)
    if not order: return jsonify({"status": "not_found"})
    return jsonify({"status": order["status"]})

@app.route('/invoice/<order_id>')
def invoice(order_id):
    order = orders_db.get(order_id)
    if not order or order["status"] != "paid": return "Đơn hàng chưa thanh toán!", 403
    return render_template('invoice.html', order=order, order_id=order_id)

@app.route('/admin/approve/<order_id>')
def approve_order(order_id):
    if not session.get('logged_in'): return redirect(url_for('admin_login'))
    if order_id in orders_db: orders_db[order_id]["status"] = "paid"
    return redirect(url_for('admin'))

@app.route('/success/<order_id>')
def success_download(order_id):
    order = orders_db.get(order_id)
    if not order or order["status"] != "paid": return "Đơn hàng chưa thanh toán!", 403
    prod_name = order["prod_name"]
    manufacturer = order["manufacturer"]
    quantity = order["quantity"]
    company_hw_id = order["hardware_id"]
    print_type = order.get("print_type", "black_white")
    price_str = f"{order['total_price']:,} VNĐ"
    print_name_desc = "Tem Trang Den Tieu Chuan" if print_type == "black_white" else "Tem QR 7 Mau / Hologram Cao Cap"
    
    try:
        wb = Workbook()
        ws = wb.active
        ws.title = "ThongKe_DanhSach"
        ws.append(["--- HỆ THỐNG XÁC THỰC CHỐNG HÀNG GIẢ - GIẢI PHÁP CUỘC SỐNG ---"])
        ws.append(["Tên sản phẩm:", prod_name, "Nhà sản xuất:", manufacturer])
        ws.append(["Công nghệ in ấn:", print_name_desc, "Mã định danh HW-ID:", company_hw_id])
        ws.append(["Số lượng tem:", quantity, "Tổng chi phí:", price_str])
        ws.append([])
        
        header_row = 6
        ws.cell(row=header_row, column=1, value="STT")
        ws.cell(row=header_row, column=2, value="Mã Code")
        ws.cell(row=header_row, column=3, value="Chữ Ký Số & Token Bảo Mật")
        ws.cell(row=header_row, column=4, value="Công Nghệ In Ấn")
        ws.cell(row=header_row, column=5, value="Link Xác Thực Ngầm")
        
        batch_img_dir = f"static/batch_{uuid.uuid4().hex[:8]}"
        os.makedirs(batch_img_dir, exist_ok=True)
        generated_qr_files = []
        sample_qr_data = []
        
        for i in range(1, quantity + 1):
            code = f"SP{i:03d}"
            digital_sign = generate_secure_digital_signature(code, manufacturer, company_hw_id)
            token = f"{uuid.uuid4().hex[:6]}-{digital_sign}"
            verify_url = f"https://vuongtung.com.vn/verify?code={code}&token={token}"
            
            img = qrcode.make(verify_url)
            img_filename = f"{code}.png"
            img_path = os.path.join(QR_OUTPUT_DIR, img_filename)
            img.save(img_path)
            
            batch_img_path = os.path.join(batch_img_dir, img_filename)
            img.save(batch_img_path)
            generated_qr_files.append(batch_img_path)
            
            if len(sample_qr_data) < 12: sample_qr_data.append((code, batch_img_path))
                
            new_prod = {
                "code": code, "token": token, "name": prod_name, "manufacturer": manufacturer,
                "hardware_id": company_hw_id, "mfg_date": datetime.now().strftime("%Y-%m-%d"),
                "price": price_str, "scan_count": 0, "status": "Hàng thật"
            }
            products_db.append(new_prod)
            
            row_idx = header_row + i
            ws.cell(row=row_idx, column=1, value=i)
            ws.cell(row=row_idx, column=2, value=code)
            ws.cell(row=row_idx, column=3, value=token)
            ws.cell(row=row_idx, column=4, value=print_name_desc)
            ws.cell(row=row_idx, column=5, value=verify_url)
            
        excel_path = f"static/ThongKe_{order_id}.xlsx"
        wb.save(excel_path)
        
        pdf_path = f"static/InThu_{order_id}.pdf"
        pdf = FPDF(orientation='L', unit='mm', format='A4')
        pdf.add_page()
        pdf.set_font("helvetica", "B", 12)
        pdf.cell(0, 8, f"TRANG IN THU MAU - {print_name_desc.upper()}", align="C", new_x="LMARGIN", new_y="NEXT")
        pdf.output(pdf_path)
        
        zip_path = f"static/Goi_Tem_{order_id}.zip"
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            zipf.write(excel_path, arcname="1_DanhSach_MaQR_DoanhNghiep.xlsx")
            zipf.write(pdf_path, arcname="2_TrangInThu_A4.pdf")
            for qr_file in generated_qr_files:
                folder_name = "3_ThuVien_Anh_QR_Tem_7Mau_Hologram" if print_type == "hologram_7color" else "3_ThuVien_Anh_QR_Tem_TrangDen"
                zipf.write(qr_file, arcname=f"{folder_name}/{os.path.basename(qr_file)}")
                
        return send_file(zip_path, as_attachment=True)
    except Exception as e:
        return f"Lỗi tạo tệp: {str(e)}", 500

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    current_password = get_admin_password()
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'login':
            if request.form.get('username') == 'admin' and request.form.get('password') == current_password:
                session['logged_in'] = True
                return redirect(url_for('admin'))
            else:
                return render_template('admin_login.html', error="Sai tên đăng nhập hoặc mật khẩu!")
        elif action == 'change_password':
            if request.form.get('old_password') == current_password:
                save_admin_password(request.form.get('new_password'))
                return render_template('admin_login.html', success="Đổi mật khẩu thành công!")
            else:
                return render_template('admin_login.html', error="Mật khẩu cũ không chính xác!")
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('logged_in', None)
    return redirect(url_for('admin_login'))

@app.route('/admin')
def admin():
    if not session.get('logged_in'): return redirect(url_for('admin_login'))
    return render_template('admin.html', products=products_db, orders=orders_db)

@app.route('/super_admin')
def super_admin():
    if not session.get('logged_in'): return redirect(url_for('admin_login'))
    return render_template('super_admin.html', total_products=len(products_db), total_scans=sum(p.get("scan_count", 0) for p in products_db), products=products_db)

@app.route('/terms')
def terms(): return render_template('terms.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
