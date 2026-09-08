import os
import io
import base64
from typing import Dict, Any, List
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

# Catálogo oficial de ítems según FSSA 106 Rev. 06
SECTIONS_STRUCTURE = {
    "LEFT": [
        {
            "title": "SISTEMA ELÉCTRICO",
            "items": [
                "Luces altas",
                "Luces bajas",
                "Luces de posición delanteras / traseras",
                "Luces de giro delanteras / traseras",
                "Luces de freno",
                "Luces de indicación marcha atrás",
                "Balizas intermitentes",
                "Alarma acústica de retroceso (de corresponder)",
                "Luces de tablero instrumentos",
                "Luz de interior*",
                "Bocina",
                "Otros: (Ej: Reflector/es)"
            ]
        },
        {
            "title": "CARROCERÍA Y CHASIS",
            "items": [
                "Chapa",
                "Pintura",
                "Parabrisas",
                "Limpiaparabrisas",
                "Lavaparabrisas",
                "Luneta trasera",
                "Traba de seguridad de las puertas*",
                "Espejos retrovisores",
                "Caño de escape",
                "Arrestallamas (de corresponder)",
                "Silenciador",
                "Frenos",
                "Freno de mano",
                "Barra antivuelco",
                "Otros"
            ]
        }
    ],
    "RIGHT": [
        {
            "title": "INTERIOR",
            "items": [
                "Instrumental (func. de velocimetro, cuenta km, niveles de fluidos)",
                "Levantavidrios",
                "Cerraduras",
                "Parasoles*",
                "Calefaccion / Desempañador",
                "Aire acondicionado",
                "Asientos",
                "Apoyacabezas",
                "Cinturones de seguridad",
                "Espejo retrovisor interior",
                "Otros: (Ej:Limpieza General)"
            ]
        },
        {
            "title": "ELEMENTOS / ACCESORIOS",
            "items": [
                "Extintores",
                "Soporte para extintor",
                "Eslinga / redes para sujecion",
                "Botiquín",
                "Linterna",
                "Balizas triángulo",
                "Llave de ruedas",
                "Gato Hidráulico/Mecánico (Crique)",
                "Kit para control de derrames (bolsas apropiadas)",
                "Kit de herramientas",
                "Equipo de Radio",
                "Tacografo",
                "Otros:"
            ]
        },
        {
            "title": "TREN RODANTE",
            "items": [
                "Desgaste de Cubiertas",
                "Llantas",
                "Alineación / Balanceo",
                "Presión de los neumáticos (según manual o terreno a transitar)",
                "Rueda/s de auxilio",
                "Bulones e indicadores de torque"
            ]
        }
    ]
}


def _get_image_from_base64(b64_str: str, max_w: float = 45 * mm, max_h: float = 18 * mm):
    """Convierte un string base64 o ruta a un objeto Image de ReportLab ajustado en tamaño."""
    if not b64_str:
        return ""
    try:
        if b64_str.startswith("data:image"):
            b64_str = b64_str.split(",", 1)[1]
        img_data = base64.b64decode(b64_str)
        img_buffer = io.BytesIO(img_data)
        return RLImage(img_buffer, width=max_w, height=max_h)
    except Exception as e:
        print(f"Error cargando imagen base64: {e}")
        return ""


def generate_sullair_pdf(
    inspection_data: Dict[str, Any],
    items_data: List[Dict[str, Any]],
    output_path_or_buffer: Any,
    logo_path: str = None
) -> bytes:
    """
    Genera el PDF oficial FSSA 106 Rev. 06 réplica exacta del formato de Sullair Argentina.
    """
    is_buffer = isinstance(output_path_or_buffer, io.BytesIO)
    target = output_path_or_buffer if is_buffer else str(output_path_or_buffer)

    # Configuración de página A4 con márgenes ajustados (10 mm)
    doc = SimpleDocTemplate(
        target,
        pagesize=A4,
        leftMargin=10 * mm,
        rightMargin=10 * mm,
        topMargin=8 * mm,
        bottomMargin=8 * mm
    )

    styles = getSampleStyleSheet()
    
    # Estilos de texto
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=15,
        alignment=TA_CENTER
    )
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=10,
        alignment=TA_CENTER
    )
    meta_code_style = ParagraphStyle(
        'MetaCode',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7,
        leading=8.5,
        alignment=TA_LEFT
    )
    meta_bold_style = ParagraphStyle(
        'MetaBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7.5,
        leading=9,
        alignment=TA_LEFT
    )
    meta_val_style = ParagraphStyle(
        'MetaVal',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.5,
        leading=9,
        alignment=TA_LEFT
    )
    table_hdr_style = ParagraphStyle(
        'TableHdr',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7,
        leading=8,
        alignment=TA_CENTER
    )
    item_lbl_style = ParagraphStyle(
        'ItemLbl',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=6.5,
        leading=7.5,
        alignment=TA_LEFT
    )
    item_val_style = ParagraphStyle(
        'ItemVal',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7,
        leading=8,
        alignment=TA_CENTER
    )
    ref_banner_style = ParagraphStyle(
        'RefBanner',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7,
        leading=8,
        alignment=TA_CENTER
    )
    obs_style = ParagraphStyle(
        'ObsStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=6.5,
        leading=8,
        alignment=TA_LEFT
    )
    sig_label_style = ParagraphStyle(
        'SigLabel',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=9.5,
        alignment=TA_LEFT
    )

    story = []
    page_w = 190 * mm # Ancho útil

    # 1. ENCABEZADO SUPERIOR
    # Col 1: Logo (62mm) | Col 2: Título (83mm) | Col 3: Código de formulario (45mm)
    logo_elem = ""
    if logo_path and os.path.exists(logo_path):
        try:
            # Proporción exacta 550x130 (4.23:1) con márgenes limpios y sin recortes
            logo_elem = RLImage(logo_path, width=48 * mm, height=11.3 * mm)
        except Exception:
            logo_elem = Paragraph("<b>SULLAIR ARGENTINA</b>", title_style)
    else:
        logo_elem = Paragraph("<b>SULLAIR ARGENTINA</b>", title_style)

    center_hdr = [
        Paragraph("<b>Control de Vehículos</b>", title_style),
        Paragraph("(Mensual)", subtitle_style)
    ]

    right_hdr = [
        Paragraph("<b>FSSA 106</b>", meta_code_style),
        Paragraph("Rev. 06", meta_code_style),
        Paragraph("Fecha: 07/02/2023", meta_code_style),
        Paragraph("Página: 1/1", meta_code_style)
    ]

    header_table_data = [[logo_elem, center_hdr, right_hdr]]
    header_table = Table(header_table_data, colWidths=[60 * mm, 85 * mm, 45 * mm], rowHeights=[16 * mm])
    header_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 1.0, colors.black),
        ('INNERGRID', (0, 0), (-1, -1), 0.8, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (0, 0), 'CENTER'),
        ('ALIGN', (1, 0), (1, 0), 'CENTER'),
        ('LEFTPADDING', (0, 0), (-1, -1), 2),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2),
        ('TOPPADDING', (0, 0), (-1, -1), 1),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 1 * mm))

    # 2. METADATOS DEL VEHÍCULO Y FECHA
    # Fila 1: Fecha / Interno / Patente
    # Fila 2: Marca / Modelo / Km
    fecha_str = inspection_data.get("fecha", datetime.now().strftime("%d/%m/%Y"))
    interno_str = str(inspection_data.get("interno", ""))
    patente_str = str(inspection_data.get("patente", ""))
    marca_str = str(inspection_data.get("marca", ""))
    modelo_str = str(inspection_data.get("modelo", ""))
    km_str = str(inspection_data.get("km", ""))

    meta_table_data = [
        [
            Paragraph(f"<b>Fecha:</b> {fecha_str}", meta_val_style),
            Paragraph(f"<b>Interno:</b> {interno_str}", meta_val_style),
            Paragraph(f"<b>Patente:</b> {patente_str}", meta_val_style)
        ],
        [
            Paragraph(f"<b>Marca:</b> {marca_str}", meta_val_style),
            Paragraph(f"<b>Modelo:</b> {modelo_str}", meta_val_style),
            Paragraph(f"<b>Km:</b> {km_str}", meta_val_style)
        ]
    ]
    meta_table = Table(meta_table_data, colWidths=[65 * mm, 70 * mm, 55 * mm], rowHeights=[4.5 * mm, 4.5 * mm])
    meta_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.8, colors.black),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 1 * mm))

    # 3. TABLA DE DOCUMENTACIÓN
    # Col 1: DOCUMENTACION | SI | NO || Col 2: DOCUMENTACION | SI | NO | VENCIMIENTO
    tv_si = "X" if inspection_data.get("tarjeta_verde_si_no") == "SI" else ""
    tv_no = "X" if inspection_data.get("tarjeta_verde_si_no") == "NO" else ""
    man_si = "X" if inspection_data.get("manual_si_no") == "SI" else ""
    man_no = "X" if inspection_data.get("manual_si_no") == "NO" else ""
    vtv_si = "X" if inspection_data.get("vtv_si_no") == "SI" else ""
    vtv_no = "X" if inspection_data.get("vtv_si_no") == "NO" else ""
    vtv_venc = inspection_data.get("vtv_vencimiento", "") or ""
    seg_si = "X" if inspection_data.get("seguro_si_no") == "SI" else ""
    seg_no = "X" if inspection_data.get("seguro_si_no") == "NO" else ""
    seg_venc = inspection_data.get("seguro_vencimiento", "") or ""

    doc_table_data = [
        [
            Paragraph("<b>DOCUMENTACION</b>", table_hdr_style),
            Paragraph("<b>SI</b>", table_hdr_style),
            Paragraph("<b>NO</b>", table_hdr_style),
            Paragraph("<b>DOCUMENTACION</b>", table_hdr_style),
            Paragraph("<b>SI</b>", table_hdr_style),
            Paragraph("<b>NO</b>", table_hdr_style),
            Paragraph("<b>VENCIMIENTO</b>", table_hdr_style)
        ],
        [
            Paragraph("Tarjeta verde", item_lbl_style),
            Paragraph(tv_si, item_val_style),
            Paragraph(tv_no, item_val_style),
            Paragraph("VTV / RTO", item_lbl_style),
            Paragraph(vtv_si, item_val_style),
            Paragraph(vtv_no, item_val_style),
            Paragraph(vtv_venc, item_val_style)
        ],
        [
            Paragraph("Manual", item_lbl_style),
            Paragraph(man_si, item_val_style),
            Paragraph(man_no, item_val_style),
            Paragraph("Seguro vehicular", item_lbl_style),
            Paragraph(seg_si, item_val_style),
            Paragraph(seg_no, item_val_style),
            Paragraph(seg_venc, item_val_style)
        ]
    ]

    doc_widths = [45 * mm, 12 * mm, 12 * mm, 45 * mm, 12 * mm, 12 * mm, 52 * mm]
    doc_table = Table(doc_table_data, colWidths=doc_widths, rowHeights=[4 * mm, 4 * mm, 4 * mm])
    doc_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.8, colors.black),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('BACKGROUND', (0, 0), (2, 0), colors.HexColor("#E0E0E0")),
        ('BACKGROUND', (3, 0), (6, 0), colors.HexColor("#E0E0E0")),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (1, 0), (2, -1), 'CENTER'),
        ('ALIGN', (4, 0), (6, -1), 'CENTER'),
        ('LEFTPADDING', (0, 0), (-1, -1), 2),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(doc_table)
    story.append(Spacer(1, 0.8 * mm))

    # 4. BANNER DE REFERENCIAS
    ref_table_data = [[Paragraph("<b>Referencias de estado: C (Cumple) / NC (No cumple) / NA (No Aplica)</b>", ref_banner_style)]]
    ref_table = Table(ref_table_data, colWidths=[page_w], rowHeights=[3.8 * mm])
    ref_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.8, colors.black),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F2F2F2")),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(ref_table)
    story.append(Spacer(1, 0.8 * mm))

    # 5. GRILLA DE 2 COLUMNAS (LEFT Y RIGHT)
    # Mapear estado de ítems
    items_map = {}
    for it in items_data:
        items_map[it.get("item_name", "").strip().lower()] = it.get("status", "")

    def get_status_val(name: str) -> str:
        s = items_map.get(name.strip().lower(), "")
        return s if s in ["C", "NC", "NA"] else ""

    # Armar lista izquierda
    left_rows = []
    left_styles = []
    current_row = 0

    for section in SECTIONS_STRUCTURE["LEFT"]:
        # Header de sección
        left_rows.append([
            Paragraph(f"<b>{section['title']}</b>", table_hdr_style),
            Paragraph("<b>Estado</b>", table_hdr_style)
        ])
        left_styles.append(('BACKGROUND', (0, current_row), (1, current_row), colors.HexColor("#E5E5E5")))
        current_row += 1

        for item in section["items"]:
            val = get_status_val(item)
            val_cell = Paragraph(f"<b>{val}</b>", item_val_style)
            # Resaltar si es NC
            if val == "NC":
                left_styles.append(('BACKGROUND', (1, current_row), (1, current_row), colors.HexColor("#FFCCCC")))
            left_rows.append([
                Paragraph(item, item_lbl_style),
                val_cell
            ])
            current_row += 1

    # Armar lista derecha
    right_rows = []
    right_styles = []
    current_r_row = 0

    for section in SECTIONS_STRUCTURE["RIGHT"]:
        right_rows.append([
            Paragraph(f"<b>{section['title']}</b>", table_hdr_style),
            Paragraph("<b>Estado</b>", table_hdr_style)
        ])
        right_styles.append(('BACKGROUND', (0, current_r_row), (1, current_r_row), colors.HexColor("#E5E5E5")))
        current_r_row += 1

        for item in section["items"]:
            val = get_status_val(item)
            val_cell = Paragraph(f"<b>{val}</b>", item_val_style)
            if val == "NC":
                right_styles.append(('BACKGROUND', (1, current_r_row), (1, current_r_row), colors.HexColor("#FFCCCC")))
            right_rows.append([
                Paragraph(item, item_lbl_style),
                val_cell
            ])
            current_r_row += 1

    # Igualar cantidad de filas si difieren
    max_rows = max(len(left_rows), len(right_rows))
    while len(left_rows) < max_rows:
        left_rows.append([Paragraph("", item_lbl_style), Paragraph("", item_val_style)])
    while len(right_rows) < max_rows:
        right_rows.append([Paragraph("", item_lbl_style), Paragraph("", item_val_style)])

    # Construir tabla combinada a 4 columnas: [LeftItem, LeftEstado, RightItem, RightEstado]
    combined_rows = []
    combined_styles = [
        ('BOX', (0, 0), (-1, -1), 0.8, colors.black),
        ('INNERGRID', (0, 0), (-1, -1), 0.4, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 2),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]

    for idx in range(max_rows):
        l_item, l_val = left_rows[idx]
        r_item, r_val = right_rows[idx]
        combined_rows.append([l_item, l_val, r_item, r_val])

    for st in left_styles:
        # st es ('BACKGROUND', (0, r), (1, r), color)
        combined_styles.append((st[0], (st[1][0], st[1][1]), (st[2][0], st[2][1]), st[3]))
    for st in right_styles:
        # mapear a cols 2 y 3
        combined_styles.append((st[0], (st[1][0] + 2, st[1][1]), (st[2][0] + 2, st[2][1]), st[3]))

    col_widths_main = [80 * mm, 15 * mm, 80 * mm, 15 * mm] # Total = 190mm
    row_h = 3.65 * mm
    main_table = Table(combined_rows, colWidths=col_widths_main, rowHeights=[row_h] * max_rows)
    main_table.setStyle(TableStyle(combined_styles))
    story.append(main_table)
    story.append(Spacer(1, 0.8 * mm))

    # 6. OBSERVACIONES
    obs_text = inspection_data.get("observaciones", "") or ""
    # Si hay fotos adjuntas, agregar la referencia solicitada por el usuario
    photo_items = [it.get("item_name") for it in items_data if it.get("has_photo")]
    if photo_items:
        ref_photos = f" [Fotos adjuntas disponibles para: {', '.join(photo_items)}]"
        if ref_photos not in obs_text:
            obs_text = (obs_text + "\n" + ref_photos).strip()

    obs_content = Paragraph(obs_text.replace("\n", "<br/>") if obs_text else "", obs_style)
    obs_table_data = [
        [Paragraph("<b>OBSERVACIONES</b>", table_hdr_style)],
        [obs_content]
    ]
    obs_table = Table(obs_table_data, colWidths=[page_w], rowHeights=[3.8 * mm, 14 * mm])
    obs_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.8, colors.black),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('BACKGROUND', (0, 0), (0, 0), colors.HexColor("#E5E5E5")),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 1),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
    ]))
    story.append(obs_table)
    story.append(Spacer(1, 0.8 * mm))

    # 7. FIRMAS (Realizo / Firma / Firma del responsable del sitio)
    realizo_name = inspection_data.get("realizo_nombre", "") or inspection_data.get("user_name", "")
    realizo_sig_img = _get_image_from_base64(inspection_data.get("realizo_firma_png", ""), max_w=50 * mm, max_h=12 * mm)
    resp_sig_img = _get_image_from_base64(inspection_data.get("responsable_sitio_firma_png", ""), max_w=50 * mm, max_h=12 * mm)

    cell_realizo = [
        Paragraph("<b>Realizo:</b>", sig_label_style),
        Spacer(1, 1 * mm),
        Paragraph(f"{realizo_name}", meta_bold_style)
    ]
    cell_firma = [
        Paragraph("<b>Firma:</b>", sig_label_style),
        Spacer(1, 0.5 * mm),
        realizo_sig_img if realizo_sig_img else Paragraph("", meta_code_style)
    ]
    cell_resp = [
        Paragraph("<b>Firma del responsable del sitio:</b>", sig_label_style),
        Spacer(1, 0.5 * mm),
        resp_sig_img if resp_sig_img else Paragraph("", meta_code_style)
    ]

    sig_table_data = [[cell_realizo, cell_firma, cell_resp]]
    sig_widths = [60 * mm, 60 * mm, 70 * mm]
    sig_table = Table(sig_table_data, colWidths=sig_widths, rowHeights=[17 * mm])
    sig_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.8, colors.black),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
    ]))
    story.append(sig_table)

    # Compilar documento
    doc.build(story)

    if is_buffer:
        output_path_or_buffer.seek(0)
        return output_path_or_buffer.getvalue()
    return b""
