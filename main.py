import asyncio
import random
from datetime import datetime, date, time as dtime
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps
from moon.dialamoon import Moon
import ephem
import python_weather
import json

CACHE_PATH = Path(__file__).resolve().parent / "weather_cache.json"


BASE_DIR = Path(__file__).resolve().parent

# Nook-ish starter size (tune later to exact screen)
WIDTH = 800
HEIGHT = 600

TODAYS_MOON_PATH = BASE_DIR / "todays_moon.png"
SIGIL_IMAGE = BASE_DIR / "sigil.png"

def get_quote():
    with open("quotes.txt", "r") as f:
        return random.choice(f.readlines()).strip().capitalize()

# ---- Moon helpers ----
def phase_name_from_fraction(frac: float) -> str:
    # frac in [0,1], 0=new, 0.5=full
    # Use ranges (don't compare floats with ==)
    if frac < 0.05 or frac > 0.95:
        return "New Moon"
    elif frac < 0.25:
        return "Waxing Crescent"
    elif frac < 0.45:
        return "Waxing Gibbous"
    elif frac < 0.55:
        return "Full Moon"
    elif frac < 0.75:
        return "Waning Gibbous"
    elif frac < 0.95:
        return "Waning Crescent"
    return "New Moon"

def compute_moon_phase_name_for_seattle() -> str:
    observer = ephem.Observer()
    observer.lat = "47.6062"
    observer.lon = "-122.3321"
    observer.date = datetime.now()

    m = ephem.Moon(observer)
    frac = float(m.moon_phase)  # 0..1
    print(f"Phase of the Moon: {frac:.3f}")
    name = phase_name_from_fraction(frac)
    print(f"Phase Name: {name}")
    return name

def generate_todays_moon_image():
    # Your library is already making the 730x730 moon image.
    moon = Moon()
    moon.set_moon_phase()
    moon.save_to_disk("todays_moon")  # library may append extension itself

    # If it saves without .png, standardize it:
    # Many libs write "todays_moon.png" already; this handles both.
    import os
    if os.path.exists("todays_moon") and not os.path.exists(TODAYS_MOON_PATH):
        os.rename("todays_moon", TODAYS_MOON_PATH)
    elif os.path.exists("todays_moon.jpg") and not os.path.exists(TODAYS_MOON_PATH):
        # if it writes jpg, keep your loader consistent:
        os.rename("todays_moon.jpg", TODAYS_MOON_PATH)

def prep_moon(path: str, size: int) -> Image.Image:
    moon_img = Image.open(path).convert("L")
    # Your moon has black bg, invert so it's white bg (e-ink friendly)
    moon_img = ImageOps.invert(moon_img)
    moon_img = ImageOps.autocontrast(moon_img, cutoff=1)
    moon_img = moon_img.resize((size, size), Image.Resampling.LANCZOS)
    return moon_img


# ---- Weather helpers ----

def format_hourly_table(hourly_weather: list[tuple[str, str, str]], rows: int = 10) -> list[str]:
    """
    Returns a list of strings, each one a table row, aligned for monospace fonts.
    hourly_weather items: (time_str, temp_str, cond_str)
    """
    # Normalize and cap
    data = [(t, temp, cond) for (t, temp, cond) in hourly_weather[:rows]]

    # Column widths (dynamic, but bounded so it stays tidy)
    t_w = max(4, min(6, max((len(t) for t,_,_ in data), default=4)))
    temp_w = max(3, min(4, max((len(temp) for _,temp,_ in data), default=3)))
    cond_w = max(5, min(12, max((len(cond) for *_,cond in data), default=5)))

    header = f"{'Time':<{t_w}}  {'Temp':>{temp_w}}  {'Cond':<{cond_w}}"
    sep    = f"{'-'*t_w}  {'-'*temp_w}  {'-'*cond_w}"

    lines = [header, sep]
    for t, temp, cond in data:
        cond = cond[:cond_w]
        lines.append(f"{t:<{t_w}}  {temp:>{temp_w}}  {cond:<{cond_w}}")
    return lines

def kind_to_short(kind) -> str:
    # python_weather Kind enum -> short label
    s = str(kind).split(".")[-1].replace("_", " ").title()
    # shorten a couple common ones
    return {
        "Very Cloudy": "Cloudy",
        "Partly Cloudy": "Partly",
        "Light Rain": "Rain",
    }.get(s, s)

async def get_hourly_weather(city: str = "Seattle") -> list[tuple[str, str, str]]:
    async with python_weather.Client(unit=python_weather.IMPERIAL) as client:
        weather = await client.get(city)

        # Grab first day's hourlies (today)
        today = next(iter(weather))
        hourlies = []
        for hourly in today:
            # hourly.time is a datetime.time
            t = hourly.time.strftime("%-I%p").lower() if hasattr(hourly.time, "strftime") else str(hourly.time)
            temp = f"{hourly.temperature}°"
            cond = str(hourly.kind).split(".")[-1].replace("_", " ").title()
            hourlies.append((t, temp, cond))

        return hourlies

# ---- Sigil helpers ----
def prep_bw_asset(path: str, target_size: tuple[int, int], invert_if_needed: bool = False) -> Image.Image:
    """
    Loads an image as grayscale (L), boosts contrast, resizes.
    If your source is black on white and you want white on black (or vice versa), use invert_if_needed.
    """
    img = Image.open(path).convert("L")
    img = ImageOps.autocontrast(img, cutoff=1)
    if invert_if_needed:
        img = ImageOps.invert(img)
    img = img.resize(target_size, Image.Resampling.LANCZOS)
    return img

def paste_with_mask(dst: Image.Image, src: Image.Image, xy: tuple[int, int]):
    """
    Pastes grayscale src onto dst using src as its own mask so white stays transparent-ish.
    Works best when src is black on white.
    """
    # Turn white -> transparent mask (white = 0 mask)
    mask = ImageOps.invert(src)  # black becomes white mask, white becomes black mask
    dst.paste(src, xy, mask)

# ---- Dashboard renderer ----
def generate_image(moon_phase: str, quote: str, hourly_weather: list[tuple[str, str, str]], sigil_img_path) -> Image.Image:
    img = Image.new("L", (WIDTH, HEIGHT), 255)
    draw = ImageDraw.Draw(img)

    # Fonts (note the leading /)
    title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 48)
    body_font  = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf", 32)
    small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf", 20)
    mono_font  = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 18)

    # Layout constants
    right_bar_x = WIDTH - 70
    sidebar_left = WIDTH - 370
    sidebar_right = WIDTH - 90
    top_pad = 30

    # Date
    date_str = datetime.now().strftime("%A, %B %d")
    draw.text((WIDTH/2, top_pad + 10), date_str, font=body_font, fill=0, anchor="mm")

    # Right bar + label
    draw.line([(right_bar_x, top_pad + 10), (right_bar_x, HEIGHT - top_pad - 10)], fill=0, width=3)
    label = "ORACLE OF DEL-PI"
    label_img = Image.new("L", (220, 60), 255)
    ld = ImageDraw.Draw(label_img)
    ld.text((110, 30), label, font=small_font, fill=0, anchor="mm")
    label_img = label_img.rotate(90, expand=True)
    img.paste(label_img, (right_bar_x + 10, HEIGHT//2 - label_img.size[1]//2))

    # Moon circle + moon image
    circle_center = (WIDTH//2 - 80, HEIGHT//2 - 40)
    radius = 120
    circle_bbox = (
        circle_center[0] - radius, circle_center[1] - radius,
        circle_center[0] + radius, circle_center[1] + radius
    )


    moon_size = int(radius * 2.5)
    try:
        moon_img = prep_moon(TODAYS_MOON_PATH, moon_size)
        x = circle_center[0] - moon_size // 2 - 100
        y = circle_center[1] - moon_size // 2
        img.paste(moon_img, (x, y))
    except FileNotFoundError:
        draw.text(circle_center, "moon\nmissing", font=small_font, fill=0, anchor="mm")

    draw.text((circle_center[0] - 100, circle_center[1] + radius + 50),
              moon_phase, font=small_font, fill=0, anchor="mm")

    # Weather sidebar title
    draw.text(((sidebar_left + sidebar_right) // 2, 120), "Hourly", font=small_font, fill=0, anchor="mm")

    table_lines = format_hourly_table(hourly_weather, rows=10)

    y = 150
    line_h = 22  # tune for your font size
    for line in table_lines:
        draw.text((sidebar_left, y), line, font=mono_font, fill=0, anchor="la")
        y += line_h

    # Quote area
    draw.line([(100, HEIGHT - 100), (right_bar_x, HEIGHT - 100)], fill=0, width=2)
    quote_box_top = HEIGHT - 120
    max_width_px = (right_bar_x - 120)
    words = quote.split()
    lines, current = [], ""
    for w in words:
        test = (current + " " + w).strip().capitalize()
        if draw.textlength(test, font=small_font) <= max_width_px:
            current = test
        else:
            lines.append(current)
            current = w
    if current:
        lines.append(current)

    quote_text = "\n".join(lines[:4])
    draw.multiline_text((WIDTH/2 - 10, quote_box_top + 70), quote_text, font=small_font, fill=0, spacing=6, anchor="mm", align="center")


    # sigil placed at the corner where the two lines meet (bottom line + right bar)
    if sigil_img_path:
        try:
            sigil_size = 250  # adjust to taste
            sigil = prep_bw_asset(sigil_img_path, (sigil_size, sigil_size), invert_if_needed=False)
            # Place it slightly inset so it looks intentional
            sx = right_bar_x - 60 - sigil_size // 2
            sy = HEIGHT - 170 - sigil_size // 2
            paste_with_mask(img, sigil, (sx, sy))
        except FileNotFoundError:
            pass

    return img


# ---- Weather fetch ----


async def main():
    # 1) weather
    hourly = []
    try:
        hourly = await get_hourly_weather("Seattle")
        print("Hourly weather gathered.")
        CACHE_PATH.write_text(json.dumps(hourly, default=str), encoding="utf-8")
    except Exception as e:
        print(f"Weather fetch failed: {e}")
        if CACHE_PATH.exists():
            try:
                hourly = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
                print("Loaded weather from cache.")
            except Exception as e2:
                print(f"Failed to load cache: {e2}")
                hourly = []

    # 2) moon phase + moon image
    phase_name = compute_moon_phase_name_for_seattle()
    generate_todays_moon_image()
    print("Moon phase and image generated.")

    # 3) quote
    quote = get_quote()
    print("Quote chosen.")

    # 4) render dashboard
    img = generate_image(phase_name, quote, hourly, sigil_img_path=SIGIL_IMAGE)
    img.save(Path("/var/www/html/daily.png"), "PNG")
    print("Saved dashboard.png")


if __name__ == "__main__":
    asyncio.run(main())
