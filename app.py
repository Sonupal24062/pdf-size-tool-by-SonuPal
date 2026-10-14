
import io
import streamlit as st
import fitz
from PIL import Image

st.set_page_config(page_title="PDF Size Tool", page_icon="📄")

st.title("📄 Resize PDF to Desired File Size")
st.write("Enter your required PDF file size, upload a PDF, and compress it.")

uploaded_pdf = st.file_uploader(
    "Upload your PDF",
    type=["pdf"]
)

target_kb = st.number_input(
    "Required output size (KB)",
    min_value=50,
    max_value=100000,
    value=500,
    step=50
)

st.caption("Example: 500 KB = about 0.5 MB; 1024 KB = 1 MB.")

if st.button("Compress PDF"):
    if uploaded_pdf is None:
        st.error("Please upload a PDF first.")
    else:
        source_data = uploaded_pdf.getvalue()
        target_bytes = int(target_kb * 1024)

        if len(source_data) <= target_bytes:
            st.success("Your PDF is already within the target size.")
            st.download_button(
                "Download PDF",
                data=source_data,
                file_name="resized.pdf",
                mime="application/pdf"
            )
        else:
            source = None
            best_data = None
            best_dpi = None
            best_quality = None

            try:
                source = fitz.open(
                    stream=source_data,
                    filetype="pdf"
                )

                # Try high-quality settings before lower-quality ones.
                settings = [
                    (dpi, quality)
                    for dpi in [150, 130, 110, 96, 85, 72, 60]
                    for quality in [85, 80, 75, 70, 65, 60, 50, 40, 30]
                ]

                settings.sort(
                    key=lambda item: (
                        item[0] * item[1],
                        item[0],
                        item[1]
                    ),
                    reverse=True
                )

                progress = st.progress(0)
                status = st.empty()
                target_reached = False

                for index, (dpi, quality) in enumerate(settings):
                    status.write(
                        f"Trying {dpi} DPI and quality {quality}/100..."
                    )

                    output = fitz.open()

                    try:
                        for page in source:
                            pix = page.get_pixmap(
                                matrix=fitz.Matrix(dpi / 72, dpi / 72),
                                colorspace=fitz.csRGB,
                                alpha=False
                            )

                            image = Image.frombytes(
                                "RGB",
                                (pix.width, pix.height),
                                pix.samples
                            )

                            buffer = io.BytesIO()
                            image.save(
                                buffer,
                                format="JPEG",
                                quality=quality,
                                optimize=True
                            )

                            new_page = output.new_page(
                                width=page.rect.width,
                                height=page.rect.height
                            )

                            new_page.insert_image(
                                new_page.rect,
                                stream=buffer.getvalue()
                            )

                        candidate = output.tobytes(
                            garbage=4,
                            deflate=True
                        )
                    finally:
                        output.close()

                    if best_data is None or len(candidate) < len(best_data):
                        best_data = candidate
                        best_dpi = dpi
                        best_quality = quality

                    if len(candidate) <= target_bytes:
                        best_data = candidate
                        best_dpi = dpi
                        best_quality = quality
                        target_reached = True
                        progress.progress(1.0)
                        break

                    progress.progress((index + 1) / len(settings))

                progress.empty()
                status.empty()

                if best_data is not None:
                    original_kb = len(source_data) / 1024
                    output_kb = len(best_data) / 1024

                    st.write(f"Original size: **{original_kb:.1f} KB**")
                    st.write(f"Target size: **{target_kb:.1f} KB**")
                    st.write(f"Output size: **{output_kb:.1f} KB**")
                    st.write(f"Resolution: **{best_dpi} DPI**")
                    st.write(f"Image quality: **{best_quality}/100**")

                    if target_reached:
                        st.success("Target file size achieved!")
                    else:
                        st.warning(
                            "Target not reached. The smallest result "
                            "found is available to download."
                        )

                    st.warning(
                        "This method converts pages into images. "
                        "Selectable text, links, forms, and some PDF "
                        "features may be lost. Keep your original."
                    )

                    st.download_button(
                        "Download compressed PDF",
                        data=best_data,
                        file_name="resized.pdf",
                        mime="application/pdf"
                    )

            except Exception as error:
                st.error(f"Could not process PDF: {error}")

            finally:
                if source is not None:
                    source.close()
