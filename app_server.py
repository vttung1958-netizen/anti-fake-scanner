import os
import uuid
import qrcode
import zipfile
import openpyxl
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter
from openpyxl.drawing.image import Image as XLImage
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

orders_db = {}
products_db = [
    {
        "code": "SP001",
        "token": "a1b2c3d4e5f6",
        "name": "Sâm ngọc linh nguyên chất",
        "manufacturer": "Công ty TNHH Vương Tùng",
        "mfg_date": "2026-03-01",
        "price": "2.500.000 VNĐ",
        "scan_count": 1,
        "status": "Hàng thật"
    },
    {
        "code": "SP002",
        "token": "b2c3d4e5f6a1",
        "name": "Thiết bị điện tử điều khiển ESP32",
        "manufacturer": "Công ty TNHH Vương Tùng",
        "mfg_date": "2026-04-01",
        "price": "450.000 VNĐ",
        "scan_count": 0,
        "status": "Hàng thật"
    }
]

# Trang chủ xử lý tra cứu mã (Hỗ trợ GET quét QR và POST nhập ô tìm kiếm)
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
        message = f"CẢNH BÁO: Mã sản phẩm '{code}' không tồn tại trên hệ thống!"
        return render_template('index.html', status=status, message=message, product=None)
        
    if token and product.get("token") and product["token"] != token:
        status = "fake"
        message = "CẢNH BÁO NGUY HIỂM: Phát hiện tem giả mạo (Sai mã Token bảo mật)!"
        return render_template('index.html', status=status, message=message, product=product)
        
    product["scan_count"] = product.get("scan_count", 0) + 1
    
    if product["scan_count"] > 3:
        status = "warning"
        message = f"CẢNH BÁO: Tem này đã bị quét {product['scan_count']} lần! Có dấu hiệu bị sao chép hàng loạt."
    else:
        status = "success"
        message = "XÁC THỰC THÀNH CÔNG: Sản phẩm chính hãng 100% từ Auto Vương Tùng."
        
    return render_template('index.html', status=status, message=message, product=product)

@app.route('/verify', methods=['GET'])
def verify():
    code = request.args.get('code')
    token = request.args.get('token')
    return redirect(url_for('index', code=code, token=token))

# 1. Cổng đăng ký mua tem cho khách hàng
@app.route('/buy', methods=['GET', 'POST'])
def buy():
    if request.method == 'POST':
        prod_name = request.form.get('prod_name')
        manufacturer = request.form.get('manufacturer')
        tax_code = request.form.get('tax_code', 'Chưa cung cấp')
        quantity = int(request.form.get('quantity', 1000))
        
        if quantity <= 1000:
            total_price = quantity * 500
        elif quantity <= 5000:
            total_price = quantity * 450
        else:
            total_price = quantity * 350
            
        order_id = f"DH{uuid.uuid4().hex[:6].upper()}"
        
        orders_db[order_id] = {
            "prod_name": prod_name,
            "manufacturer": manufacturer,
            "tax_code": tax_code,
            "quantity": quantity,
            "total_price": total_price,
            "status": "pending",
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        return redirect(url_for('checkout', order_id=order_id))
        
    return render_template('buy.html')

# 2. Trang quét VietQR chờ thanh toán thực tế
@app.route('/checkout/<order_id>')
def checkout(order_id):
    order = orders_db.get(order_id)
    if not order:
        return "Đơn hàng không tồn tại!", 404
        
    bank_id = "AGRIBANK"
    account_no = "1500215038690" # Chủ tài khoản: VƯƠNG THANH TÙNG
    amount = order["total_price"]
    add_info = f"AFQR {order_id}"
    
    vietqr_url = f"https://img.vietqr.io/image/{bank_id}-{account_no}-compact2.png?amount={amount}&addInfo={add_info}"
    return render_template('checkout.html', order=order, order_id=order_id, vietqr_url=vietqr_url)

# 3. API Webhook tự động nhận diện dòng tiền từ Ngân hàng
@app.route('/api/payment_webhook', methods=['POST'])
def payment_webhook():
    data = request.json or {}
    content = str(data.get('content', '')).upper()
    amount = float(data.get('amount', 0))
    
    for order_id, order in orders_db.items():
        if order_id in content and amount >= order["total_price"]:
            order["status"] = "paid"
            return jsonify({"success": True, "message": f"Đơn hàng {order_id} đã khớp lệnh thanh toán tự động!"})
            
    return jsonify({"success": False, "message": "Không tìm thấy mã đơn hàng phù hợp."}), 400

@app.route('/api/check_status/<order_id>')
def check_status(order_id):
    order = orders_db.get(order_id)
    if not order:
        return jsonify({"status": "not_found"})
    return jsonify({"status": order["status"]})

@app.route('/invoice/<order_id>')
def invoice(order_id):
    order = orders_db.get(order_id)
    if not order or order["status"] != "paid":
        return "Đơn hàng chưa được thanh toán hoặc không tồn tại!", 403
    return render_template('invoice.html', order=order, order_id=order_id)

@app.route('/admin/approve/<order_id>')
def approve_order(order_id):
    if not session.get('logged_in'):
        return redirect(url_for('admin_login'))
    if order_id in orders_db:
        orders_db[order_id]["status"] = "paid"
    return redirect(url_for('admin'))

# 4. Tự động sinh tệp .ZIP từ đơn hàng đã thanh toán
@app.route('/success/<order_id>')
def success_download(order_id):
    order = orders_db.get(order_id)
    if not order or order["status"] != "paid":
        return "Đơn hàng chưa thanh toán!", 403
        
    prod_name = order["prod_name"]
    manufacturer = order["manufacturer"]
    quantity = order["quantity"]
    price_str = f"{order['total_price']:,} VNĐ"
    
    try:
        wb = Workbook()
        ws = wb.active
        ws.title = "ThongKe_DanhSach"
        
        ws.append(["--- THÔNG TIN LÔ HÀNG & DANH SÁCH MÃ QR ĐẶC QUYỀN ---"])
        ws.append(["Tên sản phẩm:", prod_name, "Nhà sản xuất:", manufacturer])
        ws.append(["Số lượng mã:", quantity, "Đơn giá:", price_str])
        ws.append([])
        
        header_row = 5
        ws.cell(row=header_row, column=1, value="STT")
        ws.cell(row=header_row, column=2, value="Mã Code")
        ws.cell(row=header_row, column=3, value="Token Bảo Mật")
        ws.cell(row=header_row, column=4, value="Tên Sản Phẩm")
        ws.cell(row=header_row, column=5, value="Nhà Sản Xuất")
        ws.cell(row=header_row, column=6, value="Link Xác Thực Ngầm")
        
        batch_img_dir = f"static/batch_{uuid.uuid4().hex[:8]}"
        os.makedirs(batch_img_dir, exist_ok=True)
        
        generated_qr_files = []
        sample_qr_data = []
        
        for i in range(1, quantity + 1):
            code = f"SP{len(products_db) + i:03d}"
            token = uuid.uuid4().hex[:12]
            verify_url = f"https://vuongtung.com.vn/verify?code={code}&token={token}"
            
            img = qrcode.make(verify_url)
            img_filename = f"{code}.png"
            img_path = os.path.join(QR_OUTPUT_DIR, img_filename)
            img.save(img_path)
            
            batch_img_path = os.path.join(batch_img_dir, img_filename)
            img.save(batch_img_path)
            generated_qr_files.append(batch_img_path)
            
            if len(sample_qr_data) < 12:
                sample_qr_data.append((code, batch_img_path))
                
            new_prod = {
                "code": code,
                "token": token,
                "name": prod_name,
                "manufacturer": manufacturer,
                "mfg_date": datetime.now().strftime("%Y-%m-%d"),
                "price": price_str,
                "scan_count": 0,
                "status": "Hàng thật"
            }
            products_db.append(new_prod)
            
            row_idx = header_row + i
            ws.cell(row=row_idx, column=1, value=i)
            ws.cell(row=row_idx, column=2, value=code)
            ws.cell(row=row_idx, column=3, value=token)
            ws.cell(row=row_idx, column=4, value=prod_name)
            ws.cell(row=row_idx, column=5, value=manufacturer)
            ws.cell(row=row_idx, column=6, value=verify_url)
            
        excel_path = f"static/ThongKe_{order_id}.xlsx"
        wb.save(excel_path)
        
        pdf_path = f"static/InThu_{order_id}.pdf"
        pdf = FPDF(orientation='L', unit='mm', format='A4')
        pdf.add_page()
        pdf.set_font("helvetica", "B", 13)
        pdf.cell(0, 8, f"TRANG IN THU MAU - LO: {order_id}", align="C", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("helvetica", "I", 9)
        pdf.cell(0, 6, "In file nay ra giay A4 de kiem tra kich thuoc ma QR.", align="C", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(5)
        
        col_width = 65
        row_height = 45
        start_x = 18
        start_y = pdf.get_y()
        
        for idx, (s_code, s_path) in enumerate(sample_qr_data):
            c = idx % 4
            r = idx // 4
            x = start_x + c * col_width
            y = start_y + r * row_height
            
            pdf.rect(x, y, col_width - 6, row_height - 4)
            pdf.set_xy(x, y + 3)
            pdf.set_font("helvetica", "B", 10)
            pdf.cell(col_width - 6, 6, s_code, align="C", new_x="LMARGIN", new_y="NEXT")
            
            try:
                pdf.image(s_path, x=x + 17, y=y + 10, w=30, h=30)
            except Exception:
                pass
                
        pdf.output(pdf_path)
        
        zip_path = f"static/Goi_Tem_{order_id}.zip"
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            zipf.write(excel_path, arcname="1_DanhSach_MaQR.xlsx")
            zipf.write(pdf_path, arcname="2_TrangInThu_A4.pdf")
            for qr_file in generated_qr_files:
                zipf.write(qr_file, arcname=f"3_ThuVien_Anh_QR/{os.path.basename(qr_file)}")
                
        return send_file(zip_path, as_attachment=True)
    except Exception as e:
        return f"Lỗi tạo tệp: {str(e)}", 500

# 5. Xử lý tạo lô tem trực tiếp từ trang Quản trị Admin (/admin/generate_batch)
@app.route('/admin/generate_batch', methods=['POST'])
def admin_generate_batch():
    if not session.get('logged_in'):
        return redirect(url_for('admin_login'))
        
    prod_name = request.form.get('prod_name')
    manufacturer = request.form.get('manufacturer')
    price_str = request.form.get('price', '2.000.000 VNĐ')
    
    try:
        quantity = int(request.form.get('quantity', 100))
    except ValueError:
        quantity = 100
        
    order_id = f"AD{uuid.uuid4().hex[:6].upper()}"
    
    try:
        wb = Workbook()
        ws = wb.active
        ws.title = "ThongKe_DanhSach"
        
        ws.append(["--- THÔNG TIN LÔ HÀNG & DANH SÁCH MÃ QR ĐẶC QUYỀN ---"])
        ws.append(["Tên sản phẩm:", prod_name, "Nhà sản xuất:", manufacturer])
        ws.append(["Số lượng mã:", quantity, "Đơn giá:", price_str])
        ws.append([])
        
        header_row = 5
        ws.cell(row=header_row, column=1, value="STT")
        ws.cell(row=header_row, column=2, value="Mã Code")
        ws.cell(row=header_row, column=3, value="Token Bảo Mật")
        ws.cell(row=header_row, column=4, value="Tên Sản Phẩm")
        ws.cell(row=header_row, column=5, value="Nhà Sản Xuất")
        ws.cell(row=header_row, column=6, value="Link Xác Thực Ngầm")
        
        batch_img_dir = f"static/batch_{uuid.uuid4().hex[:8]}"
        os.makedirs(batch_img_dir, exist_ok=True)
        
        generated_qr_files = []
        sample_qr_data = []
        
        for i in range(1, quantity + 1):
            code = f"SP{len(products_db) + i:03d}"
            token = uuid.uuid4().hex[:12]
            verify_url = f"https://vuongtung.com.vn/verify?code={code}&token={token}"
            
            img = qrcode.make(verify_url)
            img_filename = f"{code}.png"
            img_path = os.path.join(QR_OUTPUT_DIR, img_filename)
            img.save(img_path)
            
            batch_img_path = os.path.join(batch_img_dir, img_filename)
            img.save(batch_img_path)
            generated_qr_files.append(batch_img_path)
            
            if len(sample_qr_data) < 12:
                sample_qr_data.append((code, batch_img_path))
                
            new_prod = {
                "code": code,
                "token": token,
                "name": prod_name,
                "manufacturer": manufacturer,
                "mfg_date": datetime.now().strftime("%Y-%m-%d"),
                "price": price_str,
                "scan_count": 0,
                "status": "Hàng thật"
            }
            products_db.append(new_prod)
            
            row_idx = header_row + i
            ws.cell(row=row_idx, column=1, value=i)
            ws.cell(row=row_idx, column=2, value=code)
            ws.cell(row=row_idx, column=3, value=token)
            ws.cell(row=row_idx, column=4, value=prod_name)
            ws.cell(row=row_idx, column=5, value=manufacturer)
            ws.cell(row=row_idx, column=6, value=verify_url)
            
        excel_path = f"static/ThongKe_{order_id}.xlsx"
        wb.save(excel_path)
        
        pdf_path = f"static/InThu_{order_id}.pdf"
        pdf = FPDF(orientation='L', unit='mm', format='A4')
        pdf.add_page()
        pdf.set_font("helvetica", "B", 13)
        pdf.cell(0, 8, f"TRANG IN THU MAU - LO: {order_id}", align="C", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("helvetica", "I", 9)
        pdf.cell(0, 6, "In file nay ra giay A4 de kiem tra kich thuoc ma QR.", align="C", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(5)
        
        col_width = 65
        row_height = 45
        start_x = 18
        start_y = pdf.get_y()
        
        for idx, (s_code, s_path) in enumerate(sample_qr_data):
            c = idx % 4
            r = idx // 4
            x = start_x + c * col_width
            y = start_y + r * row_height
            
            pdf.rect(x, y, col_width - 6, row_height - 4)
            pdf.set_xy(x, y + 3)
            pdf.set_font("helvetica", "B", 10)
            pdf.cell(col_width - 6, 6, s_code, align="C", new_x="LMARGIN", new_y="NEXT")
            
            try:
                pdf.image(s_path, x=x + 17, y=y + 10, w=30, h=30)
            except Exception:
                pass
                
        pdf.output(pdf_path)
        
        zip_path = f"static/Goi_Tem_{order_id}.zip"
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            zipf.write(excel_path, arcname="1_DanhSach_MaQR.xlsx")
            zipf.write(pdf_path, arcname="2_TrangInThu_A4.pdf")
            for qr_file in generated_qr_files:
                zipf.write(qr_file, arcname=f"3_ThuVien_Anh_QR/{os.path.basename(qr_file)}")
                
        return send_file(zip_path, as_attachment=True)
    except Exception as e:
        return f"Lỗi tạo tệp: {str(e)}", 500

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    current_password = get_admin_password()
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'login':
            username = request.form.get('username')
            password = request.form.get('password')
            if username == 'admin' and password == current_password:
                session['logged_in'] = True
                return redirect(url_for('admin'))
            else:
                return render_template('admin_login.html', error="Sai tên đăng nhập hoặc mật khẩu!")
        elif action == 'change_password':
            old_pass = request.form.get('old_password')
            new_pass = request.form.get('new_password')
            if old_pass == current_password:
                save_admin_password(new_pass)
                return render_template('admin_login.html', success="Đổi mật khẩu thành công! Vui lòng đăng nhập lại.")
            else:
                return render_template('admin_login.html', error="Mật khẩu cũ không chính xác!")
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('logged_in', None)
    return redirect(url_for('admin_login'))

@app.route('/admin')
def admin():
    if not session.get('logged_in'):
        return redirect(url_for('admin_login'))
    return render_template('admin.html', products=products_db, orders=orders_db)

@app.route('/super_admin')
def super_admin():
    if not session.get('logged_in'):
        return redirect(url_for('admin_login'))
    total_products = len(products_db)
    total_scans = sum(p.get("scan_count", 0) for p in products_db)
    return render_template('super_admin.html', total_products=total_products, total_scans=total_scans, products=products_db)

@app.route('/terms')
def terms():
    return render_template('terms.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
