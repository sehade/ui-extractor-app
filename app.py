import streamlit as st
import cv2
import os
import numpy as np
import tempfile
import shutil
import zipfile
from io import BytesIO

# --- KONFIGURASI HALAMAN ---
st.set_page_config(
    page_title="UI Design Extractor",
    page_icon="🎨",
    layout="wide"
)

# --- BACKEND LOGIC ---
class SmartUIExtractor:
    def __init__(self, threshold=0.015, min_time_gap=0.5):
        self.threshold = threshold
        self.min_time_gap = min_time_gap

    def calculate_difference(self, img1, img2):
        gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
        diff = cv2.absdiff(gray1, gray2)
        _, thresh = cv2.threshold(diff, 30, 255, cv2.THRESH_BINARY)
        non_zero_count = np.count_nonzero(thresh)
        total_pixels = thresh.shape[0] * thresh.shape[1]
        return non_zero_count / total_pixels

    def process_video(self, video_path, output_folder, progress_bar, status_text):
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return []

        extracted_data = [] 
        last_saved_frame = None
        last_saved_time = -1
        
        # Bersihkan folder lama
        if os.path.exists(output_folder):
            shutil.rmtree(output_folder)
        os.makedirs(output_folder)

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        frame_count = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            frame_count += 1
            if frame_count % 10 == 0 and total_frames > 0:
                progress_bar.progress(min(frame_count / total_frames, 1.0))
                status_text.text(f"Menganalisis frame {frame_count}...")

            current_timestamp = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0
            
            should_save = False
            if last_saved_frame is None:
                should_save = True
            elif (current_timestamp - last_saved_time) >= self.min_time_gap:
                diff = self.calculate_difference(last_saved_frame, frame)
                if diff > self.threshold:
                    should_save = True
            
            if should_save:
                filename = f"ui_{current_timestamp:.2f}s.png"
                save_path = os.path.join(output_folder, filename)
                cv2.imwrite(save_path, frame)
                extracted_data.append({
                    "path": save_path, 
                    "timestamp": current_timestamp,
                    "filename": filename
                })
                last_saved_frame = frame
                last_saved_time = current_timestamp

        cap.release()
        return extracted_data

# --- FRONTEND UI ---

st.title("🎨 Smart UI Extractor")
st.markdown("Upload video UI Anda, ekstrak desainnya, lalu **pilih** mana yang ingin disimpan.")

# Sidebar Config
st.sidebar.header("⚙️ Konfigurasi")
threshold_val = st.sidebar.slider("Sensitivitas (Threshold)", 0.001, 0.1, 0.015, 0.001, format="%.3f")
time_gap_val = st.sidebar.slider("Jeda Waktu Min (Detik)", 0.1, 2.0, 0.5, 0.1)

# Session State Initialization
if 'extracted_images' not in st.session_state:
    st.session_state.extracted_images = []
if 'processing_done' not in st.session_state:
    st.session_state.processing_done = False

# 1. UPLOAD SECTION
uploaded_file = st.file_uploader("Upload Video (MP4, MOV)", type=["mp4", "mov", "avi"])

if uploaded_file:
    # Simpan file sementara
    tfile = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
    tfile.write(uploaded_file.read())
    
    st.video(tfile.name)
    
    # Tombol Proses
    if st.button("🚀 Mulai Ekstraksi UI", type="primary"):
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        extractor = SmartUIExtractor(threshold=threshold_val, min_time_gap=time_gap_val)
        results = extractor.process_video(tfile.name, "temp_frames", progress_bar, status_text)
        
        # Simpan hasil ke session state
        st.session_state.extracted_images = results
        st.session_state.processing_done = True
        
        progress_bar.progress(100)
        status_text.success(f"Selesai! Ditemukan {len(results)} desain unik. Silakan pilih di bawah.")

# 2. SELECTION & DOWNLOAD SECTION
if st.session_state.processing_done and st.session_state.extracted_images:
    st.divider()
    st.subheader(f"✅ Pilih Gambar untuk Di-download ({len(st.session_state.extracted_images)} item)")
    
    # Container Form untuk Seleksi
    selected_files = []
    
    # Grid Layout
    cols = st.columns(4) 
    
    for idx, item in enumerate(st.session_state.extracted_images):
        col = cols[idx % 4]
        with col:
            st.image(item['path'], use_container_width=True)
            # Checkbox unik
            is_selected = st.checkbox(
                f"{item['timestamp']:.2f}s", 
                value=True, 
                key=f"chk_{idx}"
            )
            if is_selected:
                selected_files.append(item)

    st.divider()
    
    if len(selected_files) > 0:
        st.write(f"**{len(selected_files)} gambar terpilih.**")
        
        # Buat ZIP
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zf:
            for item in selected_files:
                zf.write(item['path'], item['filename'])
        
        zip_buffer.seek(0)
        
        st.download_button(
            label=f"📦 Download ZIP ({len(selected_files)} File)",
            data=zip_buffer,
            file_name="selected_ui_designs.zip",
            mime="application/zip",
            type="primary"
        )
    else:
        st.warning("⚠️ Silakan centang minimal satu gambar.")

elif st.session_state.processing_done and not st.session_state.extracted_images:
    st.warning("Tidak ada perubahan UI yang terdeteksi. Coba turunkan nilai Threshold.")
