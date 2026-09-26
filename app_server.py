from flask import Flask, jsonify, request
from flask_cors import CORS
import mysql.connector
import uuid

app = Flask(__name__)
CORS(app)

def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="anti_fake_db"
    )

# 1. Giao diện trang chủ tích hợp Camera quét QR thực tế cho Android/iPhone/Web
@app.route('/')
def home():
    return """
    <!DOCTYPE html>
    <html lang="vi">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Quét Mã QR Chống Giả & So Sánh Giá</title>
        <!-- Thư viện quét mã QR qua Camera -->
        <script src="https://unpkg.com/html5-qrcode" type="text/javascript"></script>
        <style>
            body { font-family: Arial, sans-serif; background-color: #f4f6f9; margin: 0; padding: 15px; display: flex; justify-content: center; }
            .container { width: 100%; max-width: 500px; background: white; padding: 20px; border-radius: 12px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }
            h2 { text-align: center; color: #333; font-size: 22px; }
            #reader { width: 100%; border-radius: 8px; overflow: hidden; margin-bottom: 15px; }
            .result-box { margin-top: 15px; padding: 15px; border-radius: 8px; background: #e9ecef; display: none; }
            .success { color: #28a745; font-weight: bold; }
            .danger { color: #dc3545; font-weight: bold; }
            .nav-link { text-align: center; margin-top: 15px; }
            .test-buttons { display: flex; gap: 10px; margin-top: 10px; justify-content: center; }
            .test-buttons button { padding: 8px 12px; font-size: 13px; background: #6c757d; color: white; border: none; border-radius: 5px; cursor: pointer; }
        </style>
    </head>
    <body>
    <div class="container">
        <h2>Quét Mã QR Sản Phẩm</h2>
        <p style="text-align: center; color: #666; font-size: 13px;">Hướng camera vào mã QR trên sản phẩm để kiểm tra chính hãng</p>
        
        <!-- Khung hiển thị Camera quét QR -->
        <div id="reader"></div>

        <!-- Khu vực hiển thị kết quả quét -->
        <div id="resultBox" class="result-box">
            <h3 id="statusTitle" style="margin-top: 0;"></h3>
            <p><b>Tên sản phẩm:</b> <span id="prodName"></span></p>
            <p><b>Hãng sản xuất:</b> <span id="prodMaker"></span></p>
            <p><b>Giá niêm yết chuẩn:</b> <span id="prodPrice" style="color: red; font-weight: bold;"></span> VNĐ</p>
            <hr>
            <p><b>🛒 So sánh giá thị trường:</b></p>
            <ul id="priceList" style="padding-left: 20px; margin-bottom: 0;"></ul>
        </div>

        <!-- Nút test nhanh khi dùng trên máy tính không có camera -->
        <div class="test-buttons">
            <button onclick="scanCode('TOKEN_ABC123XYZ_THAT_01')">Test Mã Thật</button>
            <button onclick="scanCode('TOKEN_MA_GIA_MAO_999')">Test Mã Giả</button>
        </div>

        <div class="nav-link">
            <a href="/admin" target="_blank" style="font-size: 14px;">⚙️ Trang Quản Trị Doanh Nghiệp (B2B Admin)</a>
        </div>
    </div>

    <script>
        // Hàm gọi API kiểm tra mã QR
        async function scanCode(token) {
            try {
                let response = await fetch('/api/scan', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ qr_token: token })
                });
                let data = await response.json();
                let box = document.getElementById('resultBox');
                box.style.display = 'block';
                
                if (response.status === 200) {
                    document.getElementById('statusTitle').innerHTML = `✅ HÀNG CHÍNH HÃNG (Lượt quét: ${data.scan_count})`;
                    document.getElementById('statusTitle').className = "success";
                    document.getElementById('prodName').innerText = data.product.name;
                    document.getElementById('prodMaker').innerText = data.product.manufacturer;
                    document.getElementById('prodPrice').innerText = Number(data.product.listed_price).toLocaleString();
                    
                    let html = '';
                    data.market_prices.forEach(item => {
                        html += `<li><b>${item.platform}:</b> ${Number(item.current_price).toLocaleString()} VNĐ - <a href="${item.shop_link}" target="_blank">Xem</a></li>`;
                    });
                    document.getElementById('priceList').innerHTML = html;
                } else if (response.status === 403) {
                    document.getElementById('statusTitle').innerHTML = `⚠️ CẢNH BÁO: MÃ ĐÃ BỊ QUÉT ${data.scan_count} LẦN!`;
                    document.getElementById('statusTitle').className = "danger";
                    document.getElementById('prodName').innerText = data.product.name + " (Nguy cơ bị sao chép nhãn mác)";
                    document.getElementById('prodMaker').innerText = data.product.manufacturer;
                    document.getElementById('prodPrice').innerText = Number(data.product.listed_price).toLocaleString();
                    document.getElementById('priceList').innerHTML = "<li>Mã này đã kích hoạt trước đó. Cẩn trọng hàng giả!</li>";
                } else {
                    document.getElementById('statusTitle').innerHTML = `❌ CẢNH BÁO HÀNG GIẢ TUYỆT ĐỐI!`;
                    document.getElementById('statusTitle').className = "danger";
                    document.getElementById('prodName').innerText = data.message;
                    document.getElementById('prodMaker').innerText = "Không rõ nguồn gốc";
                    document.getElementById('prodPrice').innerText = "0";
                    document.getElementById('priceList').innerHTML = "";
                }
            } catch (err) {
                console.error(err);
            }
        }

        // Khởi động Camera quét QR qua thư viện html5-qrcode
        function onScanSuccess(decodedText, decodedResult) {
            // Khi camera bắt được mã QR, tự động gửi chuỗi mã đó vào hàm xử lý
            console.log(`Đã quét thấy mã: ${decodedText}`);
            scanCode(decodedText);
        }

        let html5QrCode = new Html5QrcodeScanner(
            "reader", { fps: 10, qrbox: 250 }, false);
        html5QrCode.render(onScanSuccess);
    </script>
    </body>
    </html>
    """

# 2. Giao diện trang Quản trị Doanh nghiệp (B2B Admin)
@app.route('/admin')
def admin_panel():
    return """
    <!DOCTYPE html>
    <html lang="vi">
    <head>
        <meta charset="UTF-8">
        <title>Quản Trị Doanh Nghiệp - Sinh Mã QR</title>
        <style>
            body { font-family: Arial, sans-serif; background-color: #f4f6f9; margin: 0; padding: 20px; display: flex; justify-content: center; }
            .container { width: 100%; max-width: 600px; background: white; padding: 25px; border-radius: 12px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }
            h2 { text-align: center; color: #007bff; }
            .form-group { margin-bottom: 15px; display: flex; flex-direction: column; }
            label { font-weight: bold; margin-bottom: 5px; }
            input { padding: 10px; font-size: 14px; border: 1px solid #ccc; border-radius: 6px; }
            button { padding: 12px; font-size: 16px; background-color: #28a745; color: white; border: none; border-radius: 8px; cursor: pointer; width: 100%; margin-top: 10px; }
            button:hover { background-color: #218838; }
            .log-box { margin-top: 20px; padding: 15px; border-radius: 8px; background: #e9ecef; display: none; word-break: break-all; }
        </style>
    </head>
    <body>
    <div class="container">
        <h2>⚙️ Cổng Quản Trị Doanh Nghiệp</h2>
        <div class="form-group">
            <label>Nhập ID Sản phẩm cần sinh mã QR:</label>
            <input type="number" id="productId" value="1">
        </div>
        <button onclick="generateQR()">Tạo Mã QR Chống Giả Mới</button>
        <div id="logBox" class="log-box">
            <h3>🎉 Sinh Mã Thành Công!</h3>
            <p><b>Mã Token mới:</b> <span id="newToken" style="color: blue; font-family: monospace;"></span></p>
        </div>
        <div style="text-align: center; margin-top: 20px;">
            <a href="/" target="_blank">🔍 Quay lại trang Quét mã QR</a>
        </div>
    </div>
    <script>
        async function generateQR() {
            let prodId = document.getElementById('productId').value;
            let response = await fetch('/api/admin/generate-qr', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ product_id: prodId })
            });
            let data = await response.json();
            let box = document.getElementById('logBox');
            box.style.display = 'block';
            if(response.ok) { document.getElementById('newToken').innerText = data.qr_token; }
        }
    </script>
    </body>
    </html>
    """

# 3. API quét mã QR
@app.route('/api/scan', methods=['POST'])
def scan_qr():
    data = request.json
    scanned_token = data.get('qr_token')
    db_connection = get_db_connection()
    cursor = db_connection.cursor(dictionary=True)
    
    cursor.execute("SELECT * FROM QR_Tokens WHERE qr_token = %s", (scanned_token,))
    token_data = cursor.fetchone()
    
    if not token_data:
        cursor.close()
        db_connection.close()
        return jsonify({"status": "fake", "message": "Mã QR không tồn tại trong hệ thống! Nguy cơ hàng giả cao."}), 404
        
    product_id = token_data['product_id']
    scan_count = token_data['scan_count']
    
    cursor.execute("SELECT * FROM Products WHERE product_id = %s", (product_id,))
    product_data = cursor.fetchone()
    
    cursor.execute("SELECT platform, current_price, shop_link FROM Market_Prices WHERE product_id = %s", (product_id,))
    prices_data = cursor.fetchall()
    
    if scan_count == 0:
        cursor.execute("UPDATE QR_Tokens SET scan_count = 1, is_activated = TRUE, first_scanned_at = NOW() WHERE token_id = %s", (token_data['token_id'],))
        db_connection.commit()
        cursor.close()
        db_connection.close()
        return jsonify({"status": "success", "scan_count": 1, "product": product_data, "market_prices": prices_data}), 200
    else:
        cursor.execute("UPDATE QR_Tokens SET scan_count = scan_count + 1 WHERE token_id = %s", (token_data['token_id'],))
        db_connection.commit()
        cursor.close()
        db_connection.close()
        return jsonify({"status": "warning", "scan_count": scan_count + 1, "product": product_data, "market_prices": prices_data}), 403

# 4. API sinh mã QR tự động
@app.route('/api/admin/generate-qr', methods=['POST'])
def admin_generate_qr():
    data = request.json
    product_id = data.get('product_id')
    new_token = f"TOKEN_{uuid.uuid4().hex.upper()[:16]}"
    
    db_connection = get_db_connection()
    cursor = db_connection.cursor()
    cursor.execute("INSERT INTO QR_Tokens (product_id, qr_token, scan_count, is_activated) VALUES (%s, %s, 0, FALSE)", (product_id, new_token))
    db_connection.commit()
    cursor.close()
    db_connection.close()
    
    return jsonify({"status": "success", "qr_token": new_token})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)