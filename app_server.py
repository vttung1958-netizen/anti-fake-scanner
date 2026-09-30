import os
import uuid
import qrcode
import zipfile
import openpyxl
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font
from openpyxl.drawing.image import Image as XLImage
from flask import Flask, render_template, request, redirect, url_for, session, send_file

# Import thư viện tạo PDF chuyên nghiệp
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

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
        
        # 1. Tạo file Excel thống kê chi tiết lô hàng
        wb = Workbook()
        ws = wb.active
        ws.title = "ThongKe_DanhSach"
        
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
        sample_qr_data = [] # Lưu 12 mã đầu tiên để làm trang PDF in thử
        
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
            
            if len(sample_qr_data) < 12:
                sample_qr_data.append((code, batch_img_path))
            
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
        
        # 2. Tạo tệp PDF "2_TrangInThu_MauA4.pdf" chuẩn chỉnh để in thử
        pdf_path = "static/TrangInThu_MauA4.pdf"
        doc = SimpleDocTemplate(pdf_path, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
        elements = []
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle(
            'TitleStyle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=13,
            textColor=colors.HexColor('#1A365D'),
            spaceAfter=8,
            alignment=1
        )
        sub_style = ParagraphStyle(
            'SubStyle',
            parent=styles['Normal'],
            fontName='Helvetica-Oblique',
            fontSize=9,
            textColor=colors.HexColor('#718096'),
            spaceAfter=15,
            alignment=1
        )
        
        elements.append(Paragraph(f"<b>TRANG IN THỬ MẪU (TEST TEM QR) - LÔ: {prod_name}</b>", title_style))
        elements.append(Paragraph("<i>(Doanh nghiệp in file PDF này ra A4 thường để kiểm tra kích thước và quét thử mã QR trước khi in hàng loạt)</i>", sub_style))
        
        # Sắp xếp 12 mã QR thành lưới 3 cột x 4 hàng trong bảng PDF
        table_data = []
        row_cells = []
        for idx, (c_val, img_p) in enumerate(sample_qr_data):
            cell_content = [
                Paragraph(f"<b>{c_val}</b>", ParagraphStyle('CodeSt', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=10, alignment=1)),
                Spacer(1, 3),
                RLImage(img_p, width=75, height=75)
            ]
            row_cells.append(cell_content)
            if len(row_cells) == 3:
                table_data.append(row_cells)
                row_cells = []
        if row_cells:
            while len(row_cells) < 3:
                row_cells.append("")
            table_data.append(row_cells)
            
        t = Table(table_data, colWidths=[175, 175, 175])
        t.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E0')),
            ('TOPPADDING', (0,0), (-1,-1), 8),
            ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ]))
        elements.append(t)
        doc.build(elements)
        
        # 3. Đóng gói tất cả vào file ZIP
        zip_path = "static/Goi_Tem_QR_DoanhNghiep.zip"
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            zipf.write(excel_path, arcname="1_ThongKe_DanhSach_MaQR.xlsx")
            zipf.write(pdf_path, arcname="2_TrangInThu_MauA4.pdf")
            for qr_file in generated_qr_files:
                zipf.write(qr_file, arcname=f"3_ThuVien_Anh_QR_Goc/{os.path.basename(qr_file)}")
                
        return send_file(zip_path, as_attachment=True)
    except Exception as e:
        return f"<h3>Lỗi hệ thống khi tạo gói dữ liệu doanh nghiệp:</h3><p>{str(e)}</p><a href='/admin'>Quay lại</a>", 500

@app.route('/super_admin')
def super_admin():
    return render_template('super_admin.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
