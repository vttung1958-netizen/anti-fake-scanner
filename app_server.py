import os
import uuid
import qrcode
import pandas as pd
from flask import render_template, request, redirect, url_for, session, send_file

# Đảm bảo thư mục lưu ảnh QR tồn tại để tránh lỗi Internal Server Error
QR_OUTPUT_DIR = "static/qrs"
os.makedirs(QR_OUTPUT_DIR, exist_ok=True)

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
            
            # Tạo ảnh QR Code lưu trữ an toàn
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
        return f"Lỗi xử lý hệ thống: {str(e)}", 500
