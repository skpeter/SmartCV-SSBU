import configparser
import time
import numpy as np
from PIL import Image
import ssbu
import core.core as core
from core.matching import findBestMatch
client_name = "smartcv-ssbu"
config = configparser.ConfigParser()
config.read('config.ini')
# Get the feed path from the config file
base_width = 1920
base_height = 1080
previous_states = [None]
resultDetectRetries = 0
game_end_latched = False
pending_stock_ocr = None
stock_event_armed = True
versus_ocr_attempts = 0
VERSUS_OCR_MAX_TRIES = 5
# GAME!/TIME! share a thick white bottom outline with a black band above it.
_END_OUTLINE_X = (360, 1560)
_END_OUTLINE_Y = (510, 590)
_END_WHITE_MIN = 240
_END_BLACK_MAX = 40
_END_MIN_RUN = 400
_END_BLACK_ABOVE = (15, 25)

payload = {
    "state": None,
    "stage": None,
    "players": [
        {
            "name": None,
            "character": None,
            "stocks": None,
            "damage": None
        },
        {
            "name": None,
            "character": None,
            "stocks": None,
            "damage": None
        }
    ]
}


def detect_stage_select_screen(payload: dict, img, scale_x: float, scale_y: float):
    pixel1 = img.getpixel((int(596 * scale_x), int(698 * scale_y)))
    pixel2 = img.getpixel((int(1842 * scale_x), int(54 * scale_y)))

    # Define the target colors and deviation
    target_color1 = (85, 98, 107)  # #55626b in RGB
    target_color2 = (180, 5, 5)   # # a50215 in RGB
    deviation = 0.125
    core.print_with_time("Got 1st color code ", pixel1,
                         " at function detect_stage_select_screen", debug_only=True)
    core.print_with_time("Got 2nd color code ", pixel2,
                         " at function detect_stage_select_screen -", end=' ', debug_only=True)
    if core.is_within_deviation(pixel1, target_color1, deviation) and core.is_within_deviation(pixel2, target_color2, deviation):
        print("Stage select screen detected")
        payload['state'] = "stage_select"
        payload['stage'] = None
        _reset_in_game_detection_state()
        if payload['state'] != previous_states[-1]:
            previous_states.append(payload['state'])
    else:
        if config.getboolean('settings', 'debug_mode', fallback=False):
            print("No match")


def detect_selected_stage(payload: dict, img, scale_x: float, scale_y: float):
    if payload['stage']:
        return
    pixel = img.getpixel((int(1842 * scale_x), int(54 * scale_y)))

    # Define the target color and deviation
    target_color = (75, 5, 7)  # #4b0507 in RGB
    deviation = 0.125

    core.print_with_time("Got color code ", pixel,
                         " at function detect_selected_stage -", end=' ', debug_only=True)
    if core.is_within_deviation(pixel, target_color, deviation):
        stage = core.read_text(img, (int(
            110 * scale_x), int(700 * scale_y), int(500 * scale_x), int(100 * scale_y)))
        if stage:
            payload['stage'], _ = findBestMatch(' '.join(stage), ssbu.stages)
        print("Selected stage:", payload['stage'])
        time.sleep(1)
    else:
        if config.getboolean('settings', 'debug_mode', fallback=False):
            print("No match")


def detect_character_select_screen(payload: dict, img, scale_x: float, scale_y: float):
    global versus_ocr_attempts
    pixel = img.getpixel((int(433 * scale_x), int(36 * scale_y)))

    # Define the target color and deviation
    target_color = (230, 208, 24)  # # e6d018 in RGB
    deviation = 0.125
    core.print_with_time("Got color code ", pixel,
                         " at function detect_character_select_screen -", end=' ', debug_only=True)
    if core.is_within_deviation(pixel, target_color, deviation):
        payload['state'] = "character_select"
        print("Character select screen detected")
        if payload['state'] != previous_states[-1]:
            previous_states.append(payload['state'])
            _reset_in_game_detection_state()
            # clean up some more player information
            for player in payload['players']:
                player['stocks'] = None
                player['damage'] = None
                player['character'] = None
                player['name'] = None
            versus_ocr_attempts = 0
    else:
        if config.getboolean('settings', 'debug_mode', fallback=False):
            print("No match")
    return


def _enter_in_game(payload: dict):
    if payload['state'] == "in_game":
        return
    payload['state'] = "in_game"
    for player in payload['players']:
        if player['stocks'] is None:
            player['stocks'] = 3
    if previous_states[-1] != "in_game":
        previous_states.append(payload['state'])
        _reset_in_game_detection_state()


def read_characters_and_names(payload: dict, img, scale_x: float, scale_y: float):
    c1 = core.read_text(img, (int(
        110 * scale_x), int(10 * scale_y), int(870 * scale_x), int(120 * scale_y)))
    if c1:
        c1, score = findBestMatch(' '.join(c1), ssbu.characters)
        if score and score < 0.75:
            c1 = do_mii_recognition(img, 1, scale_x, scale_y)
    c2 = core.read_text(img, (int(
        1070 * scale_x), int(10 * scale_y), int(870 * scale_x), int(120 * scale_y)))
    if c2:
        c2, score = findBestMatch(' '.join(c2), ssbu.characters)
        if score and score < 0.75:
            c2 = do_mii_recognition(img, 2, scale_x, scale_y)
    if not c1 or not c2:
        return False
    core.print_with_time("Player 1 character:", c1)
    core.print_with_time("Player 2 character:", c2)
    t1 = ' '.join(core.read_text(
        img, (int(5 * scale_x), int(155 * scale_y), int(240 * scale_x), int(50 * scale_y))) or [])
    core.print_with_time("Player 1 tag:", t1)
    t2 = ' '.join(core.read_text(img, (int(
        965 * scale_x), int(155 * scale_y), int(240 * scale_x), int(50 * scale_y))) or [])
    core.print_with_time("Player 2 tag:", t2)
    payload['players'][0]['character'], payload['players'][1]['character'], payload[
        'players'][0]['name'], payload['players'][1]['name'] = c1, c2, t1, t2
    return True


def detect_versus_screen(payload: dict, img, scale_x: float, scale_y: float):
    global versus_ocr_attempts
    if payload['players'][0]['character'] and payload['players'][1]['character']:
        return
    if versus_ocr_attempts >= VERSUS_OCR_MAX_TRIES:
        _enter_in_game(payload)
        return

    pixel = img.getpixel((int(30 * scale_x), int(69 * scale_y)))
    pixel2 = img.getpixel((int(1040 * scale_x), int(55 * scale_y)))

    target_color = (251, 53, 51)  # # FB3533 in RGB
    target_color2 = (33, 140, 254)  # #218CFE in RGB
    target_color3 = (255, 194, 33)  # # FFC221 in RGB
    target_color4 = (41, 176, 80)  # #29B050 in RGB

    deviation = 0.2

    core.print_with_time("Got color code ", pixel,
                         " at function detect_versus_screen -", end=' ', debug_only=True)
    versus_visible = (
        core.is_within_deviation(pixel, target_color, deviation)
        or core.is_within_deviation(pixel, target_color2, deviation)
        or core.is_within_deviation(pixel, target_color3, deviation)
    ) and (
        core.is_within_deviation(pixel2, target_color2, deviation)
        or core.is_within_deviation(pixel2, target_color3, deviation)
        or core.is_within_deviation(pixel2, target_color4, deviation)
    )
    if versus_visible:
        versus_ocr_attempts += 1
        if versus_ocr_attempts == 1:
            print("Versus screen detected")
        else:
            core.print_with_time(
                f"Versus OCR retry {versus_ocr_attempts}/{VERSUS_OCR_MAX_TRIES}")
        if read_characters_and_names(payload, img, scale_x, scale_y):
            versus_ocr_attempts = VERSUS_OCR_MAX_TRIES
            _enter_in_game(payload)
            return
        if versus_ocr_attempts >= VERSUS_OCR_MAX_TRIES:
            core.print_with_time(
                f"Versus OCR failed after {VERSUS_OCR_MAX_TRIES} tries, continuing in_game")
            _enter_in_game(payload)
        return

    # Splash gone. Already tried OCR → do not sit on character_select.
    if versus_ocr_attempts > 0:
        _enter_in_game(payload)
    elif config.getboolean('settings', 'debug_mode', fallback=False):
        print("No match")
    return img


def do_mii_recognition(img, player: int, scale_x, scale_y):
    result = None
    offset_x = 0 if player == 1 else int(960 * scale_x)
    brawler_pixel = img.getpixel(
        (int(190 * scale_x + offset_x), int(550 * scale_y)))  # his left gauntlet
    gunner_pixel = img.getpixel(
        # the corner of her vest
        (int(840 * scale_x + offset_x), int(770 * scale_y)))
    swordfighter_pixel = img.getpixel(
        (int(334 * scale_x + offset_x), int(789 * scale_y)))  # above his belt

    # Define the target colors and deviation
    brawler_color = (253, 46, 45)  # #55626b in RGB
    gunner_color = (240, 175, 58)  # # f0af3a in RGB
    swordfighter_color = (22, 63, 148)  # #163f94 in RGB
    deviation = 0.125
    core.print_with_time("Got color code ", brawler_color,
                         " at function do_mii_recognition", debug_only=True)
    core.print_with_time("Got color code ", gunner_color,
                         " at function do_mii_recognition", debug_only=True)
    core.print_with_time(
        "Got color code ", swordfighter_color, " at function do_mii_recognition", debug_only=True)
    if core.is_within_deviation(brawler_pixel, brawler_color, deviation):
        result = "Mii Brawler"
    elif core.is_within_deviation(gunner_pixel, gunner_color, deviation):
        result = "Mii Gunner"
    elif core.is_within_deviation(swordfighter_pixel, swordfighter_color, deviation):
        result = "Mii Swordfighter"

    return result


def _reset_in_game_detection_state():
    global resultDetectRetries, game_end_latched, pending_stock_ocr, stock_event_armed
    resultDetectRetries = 0
    game_end_latched = False
    pending_stock_ocr = None
    stock_event_armed = True


def _longest_run(mask):
    padded = np.concatenate(([False], mask, [False]))
    diffs = np.diff(padded.astype(np.int8))
    starts = np.where(diffs == 1)[0]
    ends = np.where(diffs == -1)[0]
    if starts.size == 0:
        return 0
    return int((ends - starts).max())


def end_outline_visible(img, scale_x, scale_y):
    """True if a long white row has a long black row 15-25px above it (GAME!/TIME! outline)."""
    arr = np.array(img)
    x0 = int(_END_OUTLINE_X[0] * scale_x)
    x1 = int(_END_OUTLINE_X[1] * scale_x)
    y0 = int(_END_OUTLINE_Y[0] * scale_y)
    y1 = int(_END_OUTLINE_Y[1] * scale_y)
    min_run = int(_END_MIN_RUN * scale_x)
    dy0 = max(1, int(_END_BLACK_ABOVE[0] * scale_y))
    dy1 = max(dy0, int(_END_BLACK_ABOVE[1] * scale_y))
    crop = arr[y0:y1, x0:x1]
    if crop.size == 0:
        return False
    white = np.all(crop >= _END_WHITE_MIN, axis=2)
    black = np.all(crop <= _END_BLACK_MAX, axis=2)
    for i in np.flatnonzero(white.sum(axis=1) >= min_run):
        if _longest_run(white[i]) < min_run:
            continue
        for dy in range(dy0, dy1 + 1):
            yb = i - dy
            if yb < 0:
                continue
            if black[yb].sum() >= min_run and _longest_run(black[yb]) >= min_run:
                return True
    return False


def _apply_stock_ocr(payload, img, scale_x, scale_y):
    img = np.array(img)
    x, y, w, h = (200, int(340 * scale_y),
                  int(1450 * scale_x), int(265 * scale_y))
    img = img[int(y):int(y + h), int(x):int(x + w)]
    img = core.stitch_text_regions(img, 50, (255, 255, 255), 50, 0.1)
    if not img.any():
        return None
    stocks = count_stock_numbers(img)
    if len(stocks) == 2:
        payload['players'][0]['stocks'] = stocks[0]
        payload['players'][1]['stocks'] = stocks[1]
        print("Stock taken. Stocks left:",
              payload['players'][0]['stocks'], " - ", payload['players'][1]['stocks'])
    return stocks


def detect_taken_stock(payload: dict, img, scale_x: float, scale_y: float):
    global pending_stock_ocr, stock_event_armed

    if payload.get('state') != 'in_game' or game_end_latched or resultDetectRetries > 0:
        pending_stock_ocr = None
        return

    if pending_stock_ocr is not None:
        _apply_stock_ocr(payload, *pending_stock_ocr)
        pending_stock_ocr = None

    region = (
        int(910 * scale_x),
        int(450 * scale_y),
        int(100 * scale_x),
        int(35 * scale_y)
    )
    target_color = (255, 255, 255)  # # ffffff in RGB
    deviation = 0.15
    confidence = core.get_color_match_in_region(
        img, region, target_color, deviation)
    core.print_with_time("Color region confidence: ", confidence,
                         " at function detect_taken_stock -", end=' ', debug_only=True)
    if confidence >= 0.9:
        if stock_event_armed:
            pending_stock_ocr = (img, scale_x, scale_y)
            stock_event_armed = False
    else:
        stock_event_armed = True
        if config.getboolean('settings', 'debug_mode', fallback=False):
            print("No match")


def count_stock_numbers(img):
    result = core.read_text(img, allowlist='123', low_text=0.3)
    if isinstance(result, list):
        result = ''.join(result)
    if not result or len(result) < 2:
        return [None]
    result = [int(x) for x in str(result) if x.isdigit()]
    if len(result) > 2:
        result = core.remove_neighbor_duplicates(result)
    return result


def detect_game_end(payload: dict, img, scale_x: float, scale_y: float):
    global resultDetectRetries, game_end_latched, pending_stock_ocr

    if not game_end_latched:
        hit = end_outline_visible(img, scale_x, scale_y)
        core.print_with_time(
            "End game outline match:", hit, end=' ', debug_only=True)
        if hit:
            game_end_latched = True
            pending_stock_ocr = None
            print("Game end detected")
        elif config.getboolean('settings', 'debug_mode', fallback=False):
            print("No match")
            return
        else:
            return
    process_game_end_data(img, scale_x, scale_y)
    resultDetectRetries += 1
    if any(player['stocks'] == 0 for player in payload['players']) or resultDetectRetries == 5:
        payload['state'] = "game_end"
        if previous_states[-1] != "game_end":
            previous_states.append("game_end")
        _reset_in_game_detection_state()


def _read_damage_region(img, x, y, w, h, pad_px=4):
    """Try reading numeric text from a region with padding and multiple OCR attempts."""
    # Slightly pad region to avoid clipping digit edges (clip to image bounds)
    img_w, img_h = img.size
    x1 = max(0, x - pad_px)
    y1 = max(0, y - pad_px)
    w1 = min(img_w - x1, w + 2 * pad_px)
    h1 = min(img_h - y1, h + 2 * pad_px)
    crop = img.crop((x1, y1, x1 + w1, y1 + h1))
    # Upscale small crops so EasyOCR sees larger text (often more reliable)
    if min(w1, h1) < 120:
        crop = crop.resize((w1 * 2, h1 * 2), Image.Resampling.LANCZOS)
    # Try several contrast/low_text combinations; use first non-empty result
    for contrast, low_text in [(1.5, 0.2), (2, 0.1), (2.5, 0.15)]:
        result = core.read_text(
            crop, region=None,
            allowlist="0123456789.%", contrast=contrast, low_text=low_text
        )
        if result:
            return result
    return None


def process_game_end_data(img, scale_x, scale_y):
    x, y, w, h = (
        int(510 * scale_x), int(920 * scale_y),
        int(165 * scale_x), int(80 * scale_y)
    )
    x1, y2, w2, h2 = (
        int(1250 * scale_x), int(920 * scale_y),
        int(165 * scale_x), int(80 * scale_y)
    )

    results = []
    results.append(_read_damage_region(img, x, y, w, h))
    results.append(_read_damage_region(img, x1, y2, w2, h2))

    payload['players'][0]['damage'] = ' '.join(
        results[0]) if results[0] else ''
    payload['players'][1]['damage'] = ' '.join(
        results[1]) if results[1] else ''

    # if failed to read damage for both players, skip
    if all(player['damage'] in ['', ' ', None] for player in payload['players']):
        return
    # if damage is read as empty, it means they've lost all of their stocks.
    for player in payload['players']:
        player['damage'] = player['damage'].replace(".%", "")
        if player['stocks'] and player['damage'] in ['', ' ', None]:
            player['stocks'] = 0
            core.print_with_time(
                str(player['name']), "has lost all of their stocks - ", end='')
            for player in payload['players']:
                if player['damage'] not in ['', ' ', None]:
                    print(str(player['name']), "wins!")
        time.sleep(core.refresh_rate)
    core.print_with_time(
        f"Damage count - Player 1: '{payload['players'][0]['damage']}' - Player 2: '{payload['players'][1]['damage']}'", debug_only=True)


states_to_functions = {
    None: [
        detect_stage_select_screen
        if not config.getboolean('settings', 'disable_stage_selection', fallback=False)
        else detect_character_select_screen
    ],
    "stage_select": [
        detect_selected_stage if not config.getboolean(
            'settings', 'disable_stage_selection', fallback=False) else None,
        detect_character_select_screen,
    ],
    "character_select": [
        detect_stage_select_screen if not config.getboolean(
            'settings', 'disable_stage_selection', fallback=False) else None,
        detect_versus_screen
    ],
    "in_game": [
        detect_versus_screen,
        detect_game_end, detect_taken_stock,
        detect_stage_select_screen if not config.getboolean(
            'settings', 'disable_stage_selection', fallback=False) else None
    ],
    "game_end": [
        detect_stage_select_screen if not config.getboolean(
            'settings', 'disable_stage_selection', fallback=False) else None,
        detect_selected_stage if not config.getboolean(
            'settings', 'disable_stage_selection', fallback=False) else None,
        detect_character_select_screen
    ]
}
