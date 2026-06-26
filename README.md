# cad-to-KML
cadtoKML
# 🗺️ Ứng Dụng Chuyển Đổi Bản Vẽ Quy Hoạch CAD Sang KMZ (Khánh Hòa)

Dự án này được xây dựng trên nền tảng **Streamlit (Python)** cho phép chuyển đổi tự động các lớp bản vẽ kỹ thuật từ hệ tọa độ phẳng **VN-2000** sang hệ tọa độ không gian toàn cầu **WGS-84** nhằm hiển thị trực quan cấu trúc quy hoạch trực tiếp trên phần mềm **Google Earth / Google Maps**.

## 🚀 Tính năng nổi bật
- **Đọc trực tiếp file trích xuất cấu trúc hình học:** Phân tách và nhận diện toàn bộ danh mục Layer có trong bản vẽ.
- **Bộ lọc tương tác nâng cao (Interactive Filter):** Cho phép tùy chọn bật hoặc tắt xuất các lớp vùng tô nặng (`HATCH`) giúp tăng tốc độ xử lý đối với các bản vẽ dung lượng lớn (lên tới 30MB).
- **Phân tách thư mục con:** Tái cấu trúc phân cấp Layer kỹ thuật thành các Folder tương ứng dễ quản lý trên Google Earth.

## 🛠️ Hướng dẫn cài đặt cục bộ (Local)
Nếu bạn muốn chạy ứng dụng này dưới máy tính cá nhân, thực hiện các dòng lệnh sau trong CMD/Terminal:

```bash
# 1. Tải kho lưu trữ về máy
git clone <đường-dẫn-thư-mục-github-của-bạn>
cd <tên-thư-mục>

# 2. Cài đặt các gói thư viện phụ thuộc
pip install -r requirements.txt

# 3. Khởi chạy ứng dụng Web
streamlit run app.py
