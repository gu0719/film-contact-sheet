from PIL import Image, ImageDraw

# Repeats sideways. Holes only on the top and bottom edges.
TILE_SIZE = (120, 200)


def default_sprocket() -> Image.Image:
    width, height = TILE_SIZE
    tile = Image.new("RGB", TILE_SIZE, "black")
    draw = ImageDraw.Draw(tile)
    draw.rounded_rectangle((36, 10, 84, 28), radius=4, fill="white")
    draw.rounded_rectangle((36, height - 28, 84, height - 10), radius=4, fill="white")
    return tile
