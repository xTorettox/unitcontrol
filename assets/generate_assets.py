import os
from PIL import Image, ImageDraw, ImageFont

def create_sullair_logo(output_path: str):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    # Dimensiones para alta resolución
    width = 800
    height = 180
    img = Image.new("RGBA", (width, height), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)

    # Color verde Sullair corporativo (#00853E / #0A8754)
    green_color = (0, 133, 62, 255)
    gray_color = (110, 120, 130, 255)

    # Dibujar isotipo (Engranaje / Turbina Sullair)
    center_x = 90
    center_y = 90
    radius = 65

    # Círculo exterior verde
    draw.ellipse(
        [center_x - radius, center_y - radius, center_x + radius, center_y + radius],
        fill=green_color
    )

    # Aspas blancas del rotor Sullair
    # Dibujamos pétalos/aspas estilizadas
    for i in range(4):
        angle_deg = i * 90
        # Dibujar aspas estilizadas en blanco
        # Cuadrantes interiores
        pass

    # Círculo blanco intermedio
    draw.ellipse(
        [center_x - 45, center_y - 45, center_x + 45, center_y + 45],
        fill=(255, 255, 255, 255)
    )
    # Núcleo verde central
    draw.ellipse(
        [center_x - 22, center_y - 22, center_x + 22, center_y + 22],
        fill=green_color
    )
    # Punto blanco central
    draw.ellipse(
        [center_x - 8, center_y - 8, center_x + 8, center_y + 8],
        fill=(255, 255, 255, 255)
    )

    # Líneas de engranaje / aspas
    for angle in [0, 45, 90, 135, 180, 225, 270, 315]:
        import math
        rad = math.radians(angle)
        x1 = center_x + int(22 * math.cos(rad))
        y1 = center_y + int(22 * math.sin(rad))
        x2 = center_x + int(45 * math.cos(rad))
        y2 = center_y + int(45 * math.sin(rad))
        draw.line([x1, y1, x2, y2], fill=green_color, width=6)

    # Cargar fuentes del sistema
    font_bold = None
    font_light = None
    
    font_paths = [
        "C:\\Windows\\Fonts\\arialbd.ttf",
        "C:\\Windows\\Fonts\\segoeuib.ttf",
        "C:\\Windows\\Fonts\\calibrib.ttf"
    ]
    font_light_paths = [
        "C:\\Windows\\Fonts\\arial.ttf",
        "C:\\Windows\\Fonts\\segoeui.ttf",
        "C:\\Windows\\Fonts\\calibri.ttf"
    ]
    
    for p in font_paths:
        if os.path.exists(p):
            font_bold = ImageFont.truetype(p, 64)
            break
    if not font_bold:
        font_bold = ImageFont.load_default()

    for p in font_light_paths:
        if os.path.exists(p):
            font_light = ImageFont.truetype(p, 54)
            break
    if not font_light:
        font_light = ImageFont.load_default()

    # Texto: SULLAIR (Verde Negrita)
    draw.text((180, 52), "SULLAIR", fill=green_color, font=font_bold)
    
    # Texto: ARGENTINA (Gris Claro Mayúsculas)
    # Calcular ancho de SULLAIR
    bbox = draw.textbbox((180, 52), "SULLAIR", font=font_bold)
    sullair_width = bbox[2] - bbox[0]
    draw.text((180 + sullair_width + 15, 60), "ARGENTINA", fill=gray_color, font=font_light)

    img.save(output_path, "PNG")
    print(f"Logo generado en: {output_path}")

if __name__ == "__main__":
    out = os.path.join(os.path.dirname(__file__), "logo_sullair.png")
    create_sullair_logo(out)
