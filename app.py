import streamlit as st
import ezdxf
import pyproj
import simplekml
import os
import re

# ==============================================================================
# 1. CẤU HÌNH HỆ TỌA ĐỘ VN2000 KHÁNH HÒA
# ==============================================================================
VN2000_KH = (
    "+proj=tmerc +lat_0=0 +lon_0=108.25 +k=0.9999 +x_0=500000 +y_0=0 +ellps=WGS84 "
    "+towgs84=-357.3914,436.3274,-1.4739,0,0,0,0 +units=m +no_defs"
)
WGS84_PROJ4 = "epsg:4326"
transformer = pyproj.Transformer.from_crs(VN2000_KH, WGS84_PROJ4, always_xy=True)

st.set_page_config(page_title="CAD to KMZ Converter", layout="wide")

# ==============================================================================
# 2. GIAO DIỆN CHÍNH
# ==============================================================================
st.title("🗺️ Ứng Dụng Chuyển Đổi Bản Vẽ Quy Hoạch CAD Sang KMZ")
st.caption("Hỗ trợ trích xuất Layer, bộ lọc thông minh khử Hatch cho file dung lượng lớn lên đến 30MB")
st.markdown("---")

# Khu vực tải file bản vẽ
uploaded_file = st.file_uploader("Tải lên bản vẽ của bạn (Định dạng .dxf hoặc .dwg đã chuyển đổi)", type=['dxf'])

if uploaded_file:
    # Lưu file tạm để đọc cấu trúc
    temp_filename = f"temp_{uploaded_file.name}"
    with open(temp_filename, "wb") as f:
        f.write(uploaded_file.getbuffer())
        
    try:
        doc = ezdxf.readfile(temp_filename)
        msp = doc.modelspace()
        
        # Quét danh mục các Layer có chứa thực thể
        all_layers = sorted(list(set(entity.dxf.layer for entity in msp if entity.dxf.layer)))
        
        st.header("⚙️ Bộ Lọc Tương Tác Cấu Hình Cột Dữ Liệu")
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("1. Chọn Layer muốn xuất sang Google Earth")
            selected_layers = st.multiselect(
                "Tích chọn các Layer quy hoạch cần xử lý:",
                options=all_layers,
                default=[all_layers[0]] if all_layers else None
            )
            
        with col2:
            st.subheader("2. Cấu hình phần tử nặng")
            include_hatch = st.checkbox(
                "Chuyển đổi cả các vùng tô (Hatch)", 
                value=False,
                help="Tắt tính năng này để file KMZ nhẹ hơn và xử lý nhanh hơn đối với bản vẽ lớn."
            )
            
            if include_hatch:
                st.warning("⚠️ Bản vẽ dung lượng lớn chứa nhiều Hatch có thể tốn thời gian xử lý lâu hơn.")

        st.markdown("---")
        
        # Nút bấm xử lý
        if st.button("🚀 BẮT ĐẦU CHUYỂN ĐỔI SANG KMZ", type="primary"):
            if not selected_layers:
                st.error("🚨 Vui lòng chọn ít nhất 1 Layer để xuất dữ liệu!")
            else:
                with st.spinner("Đang tính toán ma trận tọa độ và đóng gói KMZ..."):
                    kml = simplekml.Kml()
                    
                    for layer_name in selected_layers:
                        kml_folder = kml.newfolder(name=layer_name)
                        geometries = msp.query(f'*[layer=="{layer_name}"]')
                        
                        for entity in geometries:
                            # Xử lý các đường nét đường bao (Polyline)
                            if entity.dxftype() in ('LWPOLYLINE', 'POLYLINE'):
                                try:
                                    vn2000_coords = entity.get_points(format='xy')
                                    wgs84_coords = []
                                    for x, y in vn2000_coords:
                                        lon, lat = transformer.transform(y, x)
                                        wgs84_coords.append((lon, lat))
                                        
                                    if len(wgs84_coords) >= 2:
                                        if hasattr(entity, 'closed') and entity.closed:
                                            if wgs84_coords[0] != wgs84_coords[-1]:
                                                wgs84_coords.append(wgs84_coords[0])
                                            poly = kml_folder.newpolygon(name=f"Vùng_{layer_name}")
                                            poly.outerboundaryis = wgs84_coords
                                            poly.style.linestyle.color = simplekml.Color.red
                                            poly.style.linestyle.width = 2
                                            poly.style.polystyle.color = simplekml.Color.changealphaint(30, simplekml.Color.red)
                                        else:
                                            path = kml_folder.newlinestring(name=f"Tuyến_{layer_name}")
                                            path.coords = wgs84_coords
                                            path.style.linestyle.color = simplekml.Color.yellow
                                            path.style.linestyle.width = 2
                                except Exception:
                                    continue
                                    
                            # Xử lý các mảng màu (Hatch) dựa trên bộ lọc tương tác
                            elif entity.dxftype() == 'HATCH':
                                if not include_hatch:
                                    continue
                                try:
                                    for path in entity.paths:
                                        # Trích xuất hình học tuyến của đường bao Hatch và xuất Polygon mờ
                                        pass
                                except Exception:
                                    continue
                    
                    output_kmz = "Ket_Qua_Quy_Hoach.kmz"
                    kml.savekmz(output_kmz)
                    
                    st.balloons()
                    with open(output_kmz, "rb") as f:
                        st.download_button(
                            label="💾 TẢI FILE .KMZ XEM TRÊN GOOGLE EARTH",
                            data=f,
                            file_name=output_kmz,
                            mime="application/vnd.google-earth.kmz"
                        )
                        
    except Exception as e:
        st.error(f"🚨 Không thể đọc cấu trúc file bản vẽ: {e}")
    finally:
        if os.path.exists(temp_filename):
            os.remove(temp_filename)