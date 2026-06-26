import streamlit as st
import ezdxf
import pyproj
import simplekml
import os
import re
import aspose.cad as cad  # Thư viện giải mã file .DWG ngầm

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
st.caption("Hệ thống hỗ trợ đọc trực tiếp file .DWG/.DXF dung lượng lớn lên đến 30MB và trích xuất Layer thông minh")
st.markdown("---")

# Khu vực cho người dùng kéo thả hoặc tải file bản vẽ lên
uploaded_file = st.file_uploader("Tải lên bản vẽ quy hoạch của bạn (Chấp nhận .dwg hoặc .dxf)", type=['dxf', 'dwg'])

if uploaded_file:
    # Bước 1: Tạo tên file tạm thời trên máy chủ để xử lý cấu trúc dữ liệu
    temp_filename = f"temp_{uploaded_file.name}"
    with open(temp_filename, "wb") as f:
        f.write(uploaded_file.getbuffer())
        
    try:
        # Bước 2: Tự động nhận diện và xử lý ngầm nếu người dùng nạp file .DWG
        if uploaded_file.name.lower().endswith('.dwg'):
            st.info("🔄 Hệ thống đang tự động giải mã cấu trúc dữ liệu file .DWG 2018...")
            
            # Nạp dữ liệu nhị phân của file DWG
            image = cad.Image.load(temp_filename)
            
            # Thiết lập tên file DXF trung gian
            temp_dxf = temp_filename.replace('.dwg', '.dxf')
            
            # Xuất ngầm sang định dạng DXF để thư viện hình học có thể bóc tách
            image.save(temp_dxf)
            
            # Đọc cấu trúc bản vẽ sau khi đã chuyển đổi thành công
            doc = ezdxf.readfile(temp_dxf)
            
            # Dọn dẹp file DXF trung gian để tránh nặng máy chủ
            if os.path.exists(temp_dxf):
                os.remove(temp_dxf)
        else:
            # Nếu người dùng tải lên trực tiếp file .DXF thì hệ thống đọc luôn
            doc = ezdxf.readfile(temp_filename)
            
        # Truy cập vào không gian mô hình (Model Space) của bản vẽ
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
                                    
                                    # Chuyển đổi ma trận đỉnh: Cố định lỗi lệch vị trí bằng cách truyền Y trước, X sau
                                    for x, y in vn2000_coords:
                                        lon, lat = transformer.transform(y, x)
                                        wgs84_coords.append((lon, lat))
                                        
                                    if len(wgs84_coords) >= 2:
                                        # Nếu đường khép kín trong CAD -> Tạo thành Polygon (Vùng đất khép kín) mờ trên Google Earth
                                        if hasattr(entity, 'closed') and entity.closed:
                                            if wgs84_coords[0] != wgs84_coords[-1]:
                                                wgs84_coords.append(wgs84_coords[0])
                                            poly = kml_folder.newpolygon(name=f"Vùng_{layer_name}")
                                            poly.outerboundaryis = wgs84_coords
                                            poly.style.linestyle.color = simplekml.Color.red
                                            poly.style.linestyle.width = 2
                                            poly.style.polystyle.color = simplekml.Color.changealphaint(30, simplekml.Color.red)
                                        # Nếu là đường hở (Tim đường, ranh giới mở
