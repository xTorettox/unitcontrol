import os
from database.connection import get_db
from modules.pdf_generator import generate_sullair_pdf, SECTIONS_STRUCTURE

def test_pdf():
    db = get_db()
    
    # Mock data
    inspection_data = {
        "fecha": "07/09/2026",
        "interno": "INT-104",
        "patente": "AE 452 CD",
        "marca": "Toyota",
        "modelo": "Hilux 4x4 D/C",
        "km": 48250,
        "tarjeta_verde_si_no": "SI",
        "manual_si_no": "SI",
        "vtv_si_no": "SI",
        "vtv_vencimiento": "15/11/2026",
        "seguro_si_no": "SI",
        "seguro_vencimiento": "30/10/2026",
        "observaciones": "Unidad en excelente estado general. Se realizó cambio de lámpara de posición trasera derecha.",
        "realizo_nombre": "Martín Rodríguez",
        "realizo_firma_png": "",
        "responsable_sitio_nombre": "Carlos Fernández (CASS)",
        "responsable_sitio_firma_png": ""
    }

    # Populate items with all 'C' except one 'NC' and one 'NA'
    items_data = []
    for side in ["LEFT", "RIGHT"]:
        for sec in SECTIONS_STRUCTURE[side]:
            for it in sec["items"]:
                status = "C"
                has_photo = False
                if "Silenciador" in it:
                    status = "NC"
                    has_photo = True
                elif "Arrestallamas" in it:
                    status = "NA"
                items_data.append({
                    "section": sec["title"],
                    "item_name": it,
                    "status": status,
                    "has_photo": has_photo
                })

    logo_path = os.path.join(os.path.dirname(__file__), "assets", "logo_sullair.png")
    out_pdf = os.path.join(os.path.dirname(__file__), "test_output_fssa106.pdf")
    
    generate_sullair_pdf(inspection_data, items_data, out_pdf, logo_path)
    print(f"PDF generado con éxito en: {out_pdf}")
    
    # Check page count with PyMuPDF
    import fitz
    doc = fitz.open(out_pdf)
    print(f"Cantidad de páginas del PDF: {len(doc)}")
    
    # Render preview image
    page = doc[0]
    pix = page.get_pixmap(dpi=150)
    preview_img = os.path.join(os.path.dirname(__file__), "test_preview_page1.png")
    pix.save(preview_img)
    print(f"Vista previa guardada en: {preview_img}")

if __name__ == "__main__":
    test_pdf()
