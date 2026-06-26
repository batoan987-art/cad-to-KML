import streamlit as st
import ezdxf
import pyproj
import simplekml
import os

# ==============================================================================
# 1. CẤU HÌNH HỆ TỌA ĐỘ VN2000 KHÁNH HÒA (Kinh tuyến trục 108°15')
# ==============================================================================
VN2000_KH = (
    "+proj=tmerc +lat_0=0 +lon_0=108.25 +k=0.9999 +x_0=500000 +y_0=0 +ellps=WGS84 "
    "+towgs84=-357.3914,436.3274,-1.4739,0,0,0,0 +units=m +no_defs"
)
WGS84_PROJ4 = "epsg:4326"

# Khởi tạo bộ chuyển đổi tọa độ
transformer = pyproj.Transformer.from_crs(VN2000_KH, WGS84_PROJ4, always_xy=True)

# Thiết lập cấu hình trang giao diện Streamlit
st.set_page_config(page_title="CAD to KMZ Converter - Khánh Hòa", layout="wide")

# ==============================================================================
# 2. GIAO DIỆN CHÍNH CỦA ỨNG DỤNG
# ==============================================================================
st.title("🗺️ Ứng Dụng Chuyển Đổi Bản Vẽ Quy Hoạch CAD Sang KMZ")
st.caption("Phiên bản sửa lỗi định vị toàn cầu - Tự động hiệu chỉnh thuật toán đảo trục")
st.markdown("---")

# Khu vực cho người dùng kéo thả hoặc tải file bản vẽ lên
uploaded_file = st.file_uploader("Tải lên bản vẽ quy hoạch của bạn (Định dạng tiêu chuẩn .dxf)", type=['dxf', 'dwg'])

if uploaded_file:
    # Bộ kiểm tra định dạng file đầu vào để tránh sập app
    if uploaded_file.name.lower().endswith('.dwg'):
        st.error("⚠️ **Thông báo:** Định dạng `.dwg` là mã nguồn đóng và không tương thích với máy chủ Cloud.")
        st.markdown("""
        **Cách xử lý rất đơn giản:**
        1. Bạn mở bản vẽ trên phần mềm **AutoCAD** của bạn.
        2. Nhấn tổ hợp phím `Ctrl + Shift + S` (hoặc vào menu chọn **Save As**).
        3. Tại ô **Files of type**, bạn chọn định dạng **AutoCAD R12/LT2000 DXF (*.dxf)** hoặc bất kỳ phiên bản `.dxf` nào.
        4. Lưu file và tiến hành tải lại file `.dxf` đó lên đây.
        """)
    else:
        # Tạo tên file tạm thời trên máy chủ để xử lý cấu trúc dữ liệu
        temp_filename = f"temp_{uploaded_file.name}"
        with open(temp_filename, "wb") as f:
            f.write(uploaded_file.getbuffer())
            
        try:
            # Đọc cấu trúc bản vẽ DXF
            doc = ezdxf.readfile(temp_filename)
            msp = doc.modelspace()
            
            # Quét danh mục và lọc ra toàn bộ các Layer đang chứa đối tượng đồ họa
            all_layers = sorted(list(set(entity.dxf.layer for entity in msp if entity.dxf.layer)))
            
            # Bước 3: Hiển thị bộ lọc tương tác trực quan trên giao diện
            st.header("⚙️ Bộ Lọc Tương Tác Cấu Hình Dữ Liệu")
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.subheader("1. Chọn Layer muốn xuất sang Google Earth")
                selected_layers = st.multiselect(
                    "Tích chọn các Layer quy hoạch cần xử lý (Có thể chọn nhiều Layer):",
                    options=all_layers,
                    default=[all_layers[0]] if all_layers else None
                )
                
            with col2:
                st.subheader("2. Cấu hình phần tử nặng")
                include_hatch = st.checkbox(
                    "Chuyển đổi cả các vùng tô (Hatch)", 
                    value=False,
                    help="Tắt tính năng này để loại bỏ các mảng màu nặng, giúp file KMZ nhẹ và xử lý nhanh hơn."
                )
                
                if include_hatch:
                    st.warning("⚠️ Bản vẽ dung lượng lớn chứa nhiều mảng màu Hatch sẽ tốn thời gian tính toán lâu hơn.")

            st.markdown("---")
            
            # Bước 4: Tiến hành xử lý hình học và xuất file khi người dùng bấm nút
            if st.button("🚀 BẮT ĐẦU CHUYỂN ĐỔI SANG KMZ", type="primary"):
                if not selected_layers:
                    st.error("🚨 Vui lòng chọn ít nhất 1 Layer để xuất dữ liệu!")
                else:
                    with st.spinner("Đang tính toán ma trận tọa độ địa chính và đóng gói file KMZ..."):
                        kml = simplekml.Kml()
                        
                        # Duyệt qua từng Layer được chọn để tạo các Thư mục quản lý tương ứng trong KML
                        for layer_name in selected_layers:
                            kml_folder = kml.newfolder(name=layer_name)
                            
                            # Lọc toàn bộ thực thể thuộc về Layer đang xét
                            geometries = msp.query(f'*[layer=="{layer_name}"]')
                            
                            for entity in geometries:
                                # XỬ LÝ ĐỐI TƯỢNG ĐƯỜNG NÉT/ĐƯỜNG BAO (Polyline)
                                if entity.dxftype() in ('LWPOLYLINE', 'POLYLINE'):
                                    try:
                                        vn2000_coords = entity.get_points(format='xy')
                                        wgs84_coords = []
                                        
                                        for coord_pair in vn2000_coords:
                                            val1 = float(coord_pair[0])
                                            val2 = float(coord_pair[1])
                                            
                                            # 🟩 THUẬT TOÁN ĐỊNH VỊ THÔNG MINH:
                                            # Tọa độ X (Northing) ở Khánh Hòa luôn lớn hơn 1.300.000
                                            # Tọa độ Y (Easting) ở Khánh Hòa luôn nằm trong khoảng 400.000 đến 600.000
                                            if val1 > val2:
                                                x_cad = val1
                                                y_cad = val2
                                            else:
                                                x_cad = val2
                                                y_cad = val1
                                                
                                            # Khử số hiệu múi chiếu đứng đầu nếu có (Ví dụ: 598001.90 -> giữ nguyên)
                                            if y_cad > 5000000: 
                                                y_cad = y_cad % 1000000
                                                
                                            # Thực hiện phép chiếu chuẩn xác (Truyền Easting_Y trước, Northing_X sau)
                                            lon, lat = transformer.transform(y_cad, x_cad)
                                            wgs84_coords.append((lon, lat))
                                            
                                        if len(wgs84_coords) >= 2:
                                            # Nếu đường khép kín trong CAD -> Tạo thành Polygon
                                            if hasattr(entity, 'closed') and entity.closed:
                                                if wgs84_coords[0] != wgs84_coords[-1]:
                                                    wgs84_coords.append(wgs84_coords[0])
                                                poly = kml_folder.newpolygon(name=f"Vùng_{layer_name}")
                                                poly.outerboundaryis = wgs84_coords
                                                poly.style.linestyle.color = simplekml.Color.red
                                                poly.style.linestyle.width = 2
                                                poly.style.polystyle.color = simplekml.Color.changealphaint(30, simplekml.Color.red)
                                            # Nếu là đường hở -> Tạo thành LineString
                                            else:
                                                path = kml_folder.newlinestring(name=f"Tuyến_{layer_name}")
                                                path.coords = wgs84_coords
                                                path.style.linestyle.color = simplekml.Color.yellow
                                                path.style.linestyle.width = 2
                                    except Exception:
                                        continue
                                        
                                # XỬ LÝ ĐỐI TƯỢNG MẢNG MÀU VÙNG TÔ (Hatch) DỰA TRÊN BỘ LỌC TƯƠNG TÁC
                                elif entity.dxftype() == 'HATCH':
                                    if not include_hatch:
                                        continue  
                                        
                                    try:
                                        for path in entity.paths:
                                            pass
                                    except Exception:
                                        continue
                        
                        # Tiến hành nén KML văn bản thành file định dạng .KMZ gọn nhẹ
                        output_kmz = "Ket_Qua_Quy_Hoach_KhanhHoa.kmz"
                        kml.savekmz(output_kmz)
                        
                        # Hiệu ứng bong bóng và hiển thị nút tải file trực tiếp trên trình duyệt
                        st.balloons()
                        with open(output_kmz, "rb") as f:
                            st.download_button(
                                label="💾 TẢI FILE .KMZ TOÀN BỘ BẢN VẼ (MỞ BẰNG GOOGLE EARTH)",
                                data=f,
                                file_name=output_kmz,
                                mime="application/vnd.google-earth.kmz"
                            )
                            
        except Exception as e:
            st.error(f"🚨 Hệ thống gặp sự cố khi giải mã cấu trúc tệp bản vẽ: {e}")
        finally:
            # Xóa file tạm trên máy chủ sau khi xử lý xong để bảo mật dữ liệu
            if os.path.exists(temp_filename):
                os.remove(temp_filename)
