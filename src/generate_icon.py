"""
Utility per la generazione dinamica dell'icona dell'applicazione.
"""

from PIL import Image, ImageDraw


def create_modern_icon():
    """Generates a modern, elegant icon for Intelleo PDF Splitter."""

    # Sizes for the ICO file
    sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    images = []

    # Modern Blue Palette
    primary_blue = "#0D6EFD"  # Bootstrap Primary
    darker_blue = "#0a58ca"
    white = "#FFFFFF"

    for size in sizes:
        w, h = size
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # 1. Document Shape (Rounded Rectangle)
        # Padding
        p = w * 0.1
        rect_coords = [p, p, w - p, h - p]
        radius = w * 0.15

        draw.rounded_rectangle(rect_coords, radius=radius, fill=white, outline=None)

        # 2. Header / Top Bar (Blue)
        # Create a mask for the top part to keep rounded corners
        h * 0.35

        # We can draw a full blue rectangle and mask it, or just draw the top rounded rect
        # Simpler approach: Draw rounded rect in blue, then draw bottom part in white over it?
        # No, better to just draw the document in white, then a blue accent at the top or a symbol.

        # Let's do a "Split" concept. A document being cut or divided.

        # Draw the document outline/shadow for depth
        shadow_offset = w * 0.02
        draw.rounded_rectangle(
            [p + shadow_offset, p + shadow_offset, w - p + shadow_offset, h - p + shadow_offset],
            radius=radius,
            fill=(0, 0, 0, 40),
        )
        draw.rounded_rectangle(rect_coords, radius=radius, fill=white)

        # 3. The "Split" Visual
        # A diagonal or horizontal cut visual using the primary blue color.
        # Let's draw a stylized "S" or a cut line.

        # Draw a thick blue band in the middle, slightly rotated?
        # Or two blue pages overlapping?

        # Let's go with a clean "Page" symbol with a blue cut line.

        # Blue cut line (dashed effect or solid)
        cut_y = h * 0.5
        draw.line([w * 0.2, cut_y, w * 0.8, cut_y], fill=primary_blue, width=int(w * 0.1))

        # Top half subtle shading to imply separation
        # draw.rectangle([w*0.2, w*0.2, w*0.8, cut_y - w*0.05], fill="#F0F0F0")

        # Add a "corner fold" effect on top right?
        w * 0.25
        # draw.polygon([
        #     (w - p - fold_size, p),
        #     (w - p, p + fold_size),
        #     (w - p - fold_size, p + fold_size)
        # ], fill="#E0E0E0")

        # Add "Intelleo" Initial "I" or "PDF" text?
        # At small sizes text is bad. Shapes are better.

        # Let's try a "Stack" of papers effect.
        # Back page (offset top-left)
        back_offset = w * 0.08
        draw.rounded_rectangle(
            [p + back_offset, p - back_offset, w - p + back_offset, h - p - back_offset],
            radius=radius,
            fill=darker_blue,
        )

        # Front page (white)
        draw.rounded_rectangle(rect_coords, radius=radius, fill=white)

        # The Split Line on the front page
        # A nice swoosh or straight cut
        int(w * 0.12)
        w / 2
        h / 2

        # Draw a "cut" symbol (scissors-like or just a dashed line)
        # Let's stick to a solid blue dividing line with a gap

        # Upper block
        # draw.rectangle([w*0.3, h*0.3, w*0.7, h*0.45], fill=primary_blue)
        # Lower block
        # draw.rectangle([w*0.3, h*0.55, w*0.7, h*0.7], fill=primary_blue)

        # Modern Abstract Logo: Two blue shapes separating
        # Top shape
        poly_top = [(w * 0.25, h * 0.25), (w * 0.75, h * 0.25), (w * 0.75, h * 0.45), (w * 0.25, h * 0.45)]
        draw.polygon(poly_top, fill=primary_blue)

        # Bottom shape (shifted slightly right/down to imply movement/split)
        poly_bot = [(w * 0.25, h * 0.55), (w * 0.75, h * 0.55), (w * 0.75, h * 0.75), (w * 0.25, h * 0.75)]
        draw.polygon(poly_bot, fill=darker_blue)

        images.append(img)

    # Save as ICO
    output_path = "resources/icon.ico"
    images[0].save(output_path, format="ICO", sizes=[(i.width, i.height) for i in images])


if __name__ == "__main__":
    create_modern_icon()
