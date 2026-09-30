import os
import uuid
import qrcode
import zipfile
import openpyxl
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter
from openpyxl.drawing.image import Image as XLImage
from flask import Flask, render_template, request, redirect, url_for, session, send_file

# Thư viện tạo PDF cho trang in thử mẫu
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    PDF_READY = True
except ImportError:
    PDF_READY = False

app = Flask(__name__)
app.secret_key = 'vuong_thanh_tung_secret_key_2026'

QR_OUTPUT_DIR = "static/qrs"
os.makedirs(QR_OUTPUT_DIR, exist_ok=True)
os.makedirs("static", exist_ok=True)

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
        
        wb = Workbook()
        ws = wb.active
        ws.title = "ThongKe_Va_TemQR"
        
        ws.append(["--- THÔNG TIN LÔ HÀNG & DANH SÁCH MÃ QR ĐẶC QUYỀN ---"])
        ws.append(["Tên sản phẩm:", prod_name, "Nhà sản xuất:", manufacturer])
        ws.append(["Số lượng mã:", quantity, "Đơn giá niêm yết:", price])
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
        sample_qr_data_for_pdf = [] # Lưu tối đa 12 mã để in trang mẫu thử nghiệm
        
        for i in range(1, quantity + 1):
            code = f"SP{len(products_db) + i:03d}"
            token = uuid.uuid4().hex[:12]
            verify_url = f"https://anti-fake-scanner-2026.onrender.com/verify?code={code}&token={token}"
            
            img = qrcode.make(verify_url)
            img_filename = f"{code}.png"
            img_path = os.path.join(QR_OUTPUT_DIR, img_filename)
            img.save(img_path)
            
            batch_img_path = os.path.join(batch_img_dir, img_filename)
            img.save(batch_img_path)
            generated_qr_files.append(batch_img_path)
            
            if len(sample_qr_data_for_pdf) < 12: # Lấy 12 mã đầu tiên làm trang in thử
                sample_qr_data_for_pdf.append((code, batch_img_path))
            
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
            
            row_idx = header_row + i
            ws.cell(row=row_idx, column=1, value=i)
            ws.cell(row=row_idx, column=2, value=code)
            ws.cell(row=row_idx, column=3, value=token)
            ws.cell(row=row_idx, column=4, value=prod_name)
            ws.cell(row=row_idx, column=5, value=manufacturer)
            ws.cell(row=row_idx, column=6, value=verify_url)
            
        excel_path = "static/ThongKe_DanhSach_MaQR.xlsx"
        wb.save(excel_path)
        
        # Tự động tạo tệp PDF trang in thử mẫu (Label Sheet A4) để doanh nghiệp test trước khi in bao bì
        sample_pdf_path = "static/TrangInThu_MauA4.pdf"
        if PDF_READY and sample_qr_data_for_pdf:
            doc = SimpleDocTemplate(sample_pdf_path, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
            elements = []
            styles = getSampleStyleSheet()
            
            title_style = ParagraphStyle(
                'TitleStyle',
                parent=styles['Heading1'],
                fontName='Helvetica-Bold',
                fontSize=14,
                textColor=colors.HexColor('#1A365D'),
                spaceAfter=15,
                alignment=1
            )
            elements.append(Paragraph(f"<b>TRANG IN THỬ MẪU (TEST TEM QR) - LÔ: {prod_name}</b>", title_style))
            elements.append(Paragraph("<i>(Doanh nghiệp in trang này ra giấy A4 thường để kiểm tra kích thước và quét thử mã QR trước khi gửi đi in hàng loạt lên bao bì)</i>", ParagraphStyle('Sub', parent=styles['Normal'], fontSize=9, textColor=colors.HexColor('#718096'), spaceAfter=20, alignment=1)))
            
            # Sắp xếp 12 mã QR thành lưới 3 cột x 4 hàng
            table_data = []
            row_cells = []
            for idx, (code_val, img_p) in enumerate(sample_qr_data_for_pdf):
                # Mỗi ô gồm mã code và hình ảnh QR
                cell_content = [
                    Paragraph(f"<b>{code_val}</b>", ParagraphStyle('CodeSt', parent=styles['Normal'], fontSize=10, alignment=1)),
                    Spacer(1, 4),
                    RLImage(img_p, width=80, height=80)
                ]
                row_cells.append(cell_content)
                if len(row_cells) == 3:
                    table_data.append(row_cells)
                    row_cells = []
            if row_cells: # Thêm phần dư nếu chưa đủ hàng
                while len(row_cells) < 3:
                    row_cells.append("")
                table_data.append(row_cells)
                
            t = Table(table_data, colWidths=[170, 170, 170])
            t.setStyle(TableStyle([
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E0')),
                ('TOPPADDING', (0,0), (-1,-1), 10),
                ('BOTTOMPADDING', (0,0), (-1,-1), 10),
            ]))
            elements.append(t)
            doc.build(elements)

        # Đóng gói toàn bộ vào file ZIP giao cho doanh nghiệp
        zip_path = "static/Goi_Tem_QR_DoanhNghiep.zip"
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            zipf.write(excel_path, arcname="1_ThongKe_DanhSach_MaQR.xlsx")
            if os.path.exists(sample_pdf_path):
                zipf.write(sample_pdf_path, arcname="2_TrangInThu_MauA4.pdf")
            for qr_file in generated_qr_files:
                zipf.write(qr_file, arcname=f"3_ThuVien_Anh_QR_Goc/{os.path.basename(qr_file)}")
                
        return send_file(zip_path, as_attachment=True)
    except Exception as e:
        return f"<h3>Lỗi hệ thống khi tạo gói dữ liệu doanh nghiệp:</h3><p>{str(e)}</p><a href='/admin'>Quay lại</a>", 500

@app.super_admin_route if hasattr(app, 'super_admin_route') else app.route('/super_admin')
def super_admin():
    return render_template('super_admin.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
