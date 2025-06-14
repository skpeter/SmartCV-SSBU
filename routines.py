client_name = "smartcv-ssbu"
import configparser
import threading
import time
import numpy as np
import ssbu
import core.core as core
from core.matching import findBestMatch
config = configparser.ConfigParser()
config.read('config.ini')
# Get the feed path from the config file
feed_path = config.get('settings', 'feed_path')
base_width = 1920
base_height = 1080
previous_states = [None]

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

def detect_stage_select_screen(payload:dict, img, scale_x:float, scale_y:float):
    img, scale_x, scale_y = core.capture_screen()
    pixel1 = img.getpixel((int(596 * scale_x), int(698 * scale_y)))
    pixel2 = img.getpixel((int(1842 * scale_x), int(54 * scale_y)))
    
    # Define the target colors and deviation
    target_color1 = (85, 98, 107)  # #55626b in RGB
    target_color2 = (200, 0, 0)   # #a50215 in RGB
    deviation = 0.1
    if config.getboolean('settings', 'debug_mode', fallback=False) == True:
        core.print_with_time("Got 1st color code ", pixel1, " at function detect_stage_select_screen")
        core.print_with_time("Got 2nd color code ", pixel2, " at function detect_stage_select_screen -", end=' ')
    if core.is_within_deviation(pixel1, target_color1, deviation) and core.is_within_deviation(pixel2, target_color2, deviation):
        print("Stage select screen detected")
        payload['state'] = "stage_select"
        if payload['state'] != previous_states[-1]:
            previous_states.append(payload['state'])
            # reset payload to original values
            #clean up some more player information
            for player in payload['players']:
                player['stocks'] = None
                player['damage'] = None
                player['character'] = None
                player['name'] = None
    else:
        if config.getboolean('settings', 'debug_mode', fallback=False) == True:
            print("No match")

def detect_selected_stage(payload:dict, img, scale_x:float, scale_y:float):    
    img, scale_x, scale_y = core.capture_screen()
    pixel = img.getpixel((int(1842 * scale_x), int(54 * scale_y)))
    
    # Define the target color and deviation
    target_color = (75, 5, 7)  # #4b0507 in RGB
    deviation = 0.1
        
    if config.getboolean('settings', 'debug_mode', fallback=False) == True:
        core.print_with_time("Got color code ", pixel, " at function detect_selected_stage -", end=' ')
    if core.is_within_deviation(pixel, target_color, deviation):
        stage = core.read_text(img, (int(110 * scale_x), int(700 * scale_y), int(500 * scale_x), int(100 * scale_y)))
        if stage: payload['stage'], _ = findBestMatch(stage, ssbu.stages)
        print("Selected stage:", payload['stage'])
        time.sleep(1)
    else:
        if config.getboolean('settings', 'debug_mode', fallback=False) == True:
            print("No match")

def detect_character_select_screen(payload:dict, img, scale_x:float, scale_y:float):
    img, scale_x, scale_y = core.capture_screen()
    pixel = img.getpixel((int(433 * scale_x), int(36 * scale_y)))
    
    # Define the target color and deviation
    target_color = (230, 208, 24)  # #e6d018 in RGB
    deviation = 0.1
    if config.getboolean('settings', 'debug_mode', fallback=False) == True:
        core.print_with_time("Got color code ", pixel, " at function detect_character_select_screen -", end=' ')
    if core.is_within_deviation(pixel, target_color, deviation):
        payload['state'] = "character_select"
        print("Character select screen detected")
        if payload['state'] != previous_states[-1]:
            previous_states.append(payload['state'])
            #clean up some more player information
            for player in payload['players']:
                player['stocks'] = None
                player['damage'] = None
                player['character'] = None
                player['name'] = None
    else:
        if config.getboolean('settings', 'debug_mode', fallback=False) == True:
            print("No match")
    return

def detect_versus_screen(payload:dict, img, scale_x:float, scale_y:float):
    if payload['players'][0]['character']: return

    img, scale_x, scale_y = core.capture_screen()
    pixel = img.getpixel((int(30 * scale_x), int(69 * scale_y)))
    pixel2 = img.getpixel((int(1040 * scale_x), int(55 * scale_y)))
    
    # Define the target color and deviation

    target_color = (251, 53, 51)  # #FB3533 in RGB
    target_color2 = (33, 140, 254)  # #218CFE in RGB
    target_color3 = (255, 194, 33)  # #FFC221 in RGB
    target_color4 = (41, 176, 80)  # #29B050 in RGB

    deviation = 0.2
    
    if config.getboolean('settings', 'debug_mode', fallback=False) == True:
        core.print_with_time("Got color code ", pixel, " at function detect_versus_screen -", end=' ')
    if (core.is_within_deviation(pixel, target_color, deviation) or core.is_within_deviation(pixel, target_color2, deviation) or core.is_within_deviation(pixel, target_color3, deviation)) and (core.is_within_deviation(pixel2, target_color2, deviation) or core.is_within_deviation(pixel2, target_color3, deviation) or core.is_within_deviation(pixel2, target_color4, deviation)):
        print("Versus screen detected")
        payload['state'] = "in_game"
        if payload['state'] != previous_states[-1]:
            #set initial game data, both players have 3 stocks
            for player in payload['players']:
                player['stocks'] = 3
            previous_states.append(payload['state'])
            def read_characters_and_names(payload:dict, img, scale_x:float, scale_y:float):
                # Initialize the reader
                c1 = core.read_text(img, (int(110 * scale_x), int(10 * scale_y), int(870 * scale_x), int(120 * scale_y)))
                c1, score = findBestMatch(c1, ssbu.characters)
                if score < 0.75:
                    # Character is most likely a Mii
                    c1 = do_mii_recognition(img, 1, scale_x, scale_y)
                core.print_with_time("Player 1 character:", c1)
                c2 = core.read_text(img, (int(1070 * scale_x), int(10 * scale_y), int(870 * scale_x), int(120 * scale_y)))
                c2, score = findBestMatch(c2, ssbu.characters)
                if score < 0.75:
                    # Character is most likely a Mii
                    c2 = do_mii_recognition(img, 2, scale_x, scale_y)
                core.print_with_time("Player 2 character:", c2)
                t1 = core.read_text(img, (int(5 * scale_x), int(155 * scale_y), int(240 * scale_x), int(50 * scale_y)))
                core.print_with_time("Player 1 tag:", t1)
                t2 = core.read_text(img, (int(965 * scale_x), int(155 * scale_y), int(240 * scale_x), int(50 * scale_y)))
                core.print_with_time("Player 2 tag:", t2)
                payload['players'][0]['character'], payload['players'][1]['character'], payload['players'][0]['name'], payload['players'][1]['name'] = c1, c2, t1, t2
            threading.Thread(target=read_characters_and_names, args=(payload, img, scale_x, scale_y)).start()
            time.sleep(2)
    else:
        if config.getboolean('settings', 'debug_mode', fallback=False) == True:
            print("No match")
    return img

def do_mii_recognition(img, player: int, scale_x, scale_y):
    result = None
    offset_x = 0 if player == 1 else int(960 * scale_x)
    brawler_pixel = img.getpixel((int(190 * scale_x + offset_x), int(550 * scale_y))) # his left gauntlet
    gunner_pixel = img.getpixel((int(840 * scale_x + offset_x), int(770 * scale_y))) # the corner of her vest
    swordfighter_pixel = img.getpixel((int(334 * scale_x + offset_x), int(789 * scale_y))) # above his belt

    # Define the target colors and deviation
    brawler_color = (253, 46, 45) # #55626b in RGB
    gunner_color = (240, 175, 58) # #f0af3a in RGB
    swordfighter_color = (22, 63, 148) # #163f94 in RGB
    deviation = 0.1
    if config.getboolean('settings', 'debug_mode', fallback=False) == True:
        core.print_with_time("Got color code ", brawler_color, " at function do_mii_recognition")
    if config.getboolean('settings', 'debug_mode', fallback=False) == True:
        core.print_with_time("Got color code ", gunner_color, " at function do_mii_recognition")
    if config.getboolean('settings', 'debug_mode', fallback=False) == True:
        core.print_with_time("Got color code ", swordfighter_color, " at function do_mii_recognition")
    if core.is_within_deviation(brawler_pixel, brawler_color, deviation):
        result = "Mii Brawler"
    elif core.is_within_deviation(gunner_pixel, gunner_color, deviation):
        result = "Mii Gunner"
    elif core.is_within_deviation(swordfighter_pixel, swordfighter_color, deviation):
        result = "Mii Swordfighter"

    return result


def detect_taken_stock(payload:dict, img, scale_x:float, scale_y:float):    
    img, scale_x, scale_y = core.capture_screen()
    
    # Define the region to check
    region = int(905 * scale_x), int(445 * scale_y), int(105 * scale_x), int(40 * scale_y)
    target_color = (255, 255, 255)  # #ffffff in RGB
    deviation = 0.1
    
    if config.getboolean('settings', 'debug_mode', fallback=False) == True:
        core.print_with_time("Color region confidence: ",core.get_color_match_in_region(img, region, target_color, deviation), " at function detect_taken_stock -", end=' ')
    if core.get_color_match_in_region(img, region, target_color, deviation) >= 0.9:
        
        img = np.array(img)
        x,y,w,h = (400, int(340 * scale_y), int(1250 * scale_x), int(265 * scale_y))
        img = img[int(y):int(y+h), int(x):int(x+w)]
        img = core.stitch_text_regions(img, 195, (255,255,255), 75, 0.05)
        stocks = count_stock_numbers(img)
        if len(stocks) == 2:
            payload['players'][0]['stocks'] = stocks[0]
            payload['players'][1]['stocks'] = stocks[1]
            print("Stock taken. Stocks left:", payload['players'][0]['stocks']," - ", payload['players'][1]['stocks'])
    else:
        if config.getboolean('settings', 'debug_mode', fallback=False) == True:
            print("No match")

def count_stock_numbers(img):
    result = core.read_text(img, allowlist='123', low_text=0.3)
    if not result or len(result) < 2: return [None]
    result = [int(x) for x in str(result) if x.isdigit()]
    if len(result) > 2: result = core.remove_neighbor_duplicates(result)
    return result

def detect_game_end(payload:dict, img, scale_x:float, scale_y:float):
    img, scale_x, scale_y = core.capture_screen()
    
    # Crop the specific area
    x, y, w, h = int(312 * scale_x), int(225 * scale_y), int(1300 * scale_x), int(445 * scale_y)
    match_score1 = core.detect_image(img, 'img/GAME.png', (x, y, w, h))
    match_score2 = core.detect_image(img, 'img/TIME.png', (x, y, w, h))
        
    # Check if the maximum correlation coefficient exceeds the threshold
    threshold = 0.5
    if config.getboolean('settings', 'debug_mode', fallback=False) == True:
        core.print_with_time("Game template matching results:", match_score1, match_score2, end=' ')
    if match_score1 >= threshold or match_score1 >= threshold:
        print("Game end detected")
        process_game_end_data(img, scale_x, scale_y)
        payload['state'] = "game_end"
        if payload['state'] != previous_states[-1]:
            previous_states.append(payload['state'])
    else:
        if config.getboolean('settings', 'debug_mode', fallback=False) == True:
            print("No match")

    
def process_game_end_data(img, scale_x, scale_y):
    x, y, w, h = int(510 * scale_x), int(920 * scale_y), int(145 * scale_x), int(80 * scale_y)
    x1, y2, w2, h2 = int(1250 * scale_x), int(920 * scale_y), int(145 * scale_x), int(80 * scale_y)
    
    results = []
    
    results = []
    results.append(core.read_text(img, (x, y, w, h), allowlist="0123456789%"))
    results.append(core.read_text(img, (x1, y2, w2, h2), allowlist="0123456789%"))

    payload['players'][0]['damage'] = results[0]
    payload['players'][1]['damage'] = results[1]

    # if player has one stock left and the damage recognizes as an empty string, they've lost all of their stocks.
    for player in payload['players']:
        if player['stocks'] and player['stocks'] < 3 and player['damage'] in ['',' ',None]:
            player['stocks'] = 0
            core.print_with_time(str(player['name']), "has lost all of their stocks - ", end='')
            for player in payload['players']:
                if player['damage'] not in ['',' ',None]:
                    print(str(player['name']), "wins!")
                    player['damage'].replace("%", "")
    if config.getboolean('settings', 'debug_mode', fallback=False) == True:
        core.print_with_time(f"Damage count - Player 1: '{payload['players'][0]['damage']}' - Player 2: '{payload['players'][1]['damage']}'")
    
    
states_to_functions = {
    None: [
        detect_stage_select_screen
        if not config.getboolean('settings', 'disable_stage_selection', fallback=False)
        else detect_character_select_screen
    ],
    "stage_select": [
        detect_selected_stage if not config.getboolean('settings', 'disable_stage_selection', fallback=False) else None,
        detect_character_select_screen,
    ],
    "character_select": [
        detect_versus_screen,
        detect_stage_select_screen if not config.getboolean('settings', 'disable_stage_selection', fallback=False) else None
    ],
    "in_game": [
        detect_taken_stock, detect_game_end,
        detect_stage_select_screen if not config.getboolean('settings', 'disable_stage_selection', fallback=False) else None
    ],
    "game_end": [
        detect_stage_select_screen if not config.getboolean('settings', 'disable_stage_selection', fallback=False) else None,
        detect_selected_stage if not config.getboolean('settings', 'disable_stage_selection', fallback=False) else None,
        detect_character_select_screen
    ]
}
