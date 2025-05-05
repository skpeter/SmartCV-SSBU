print("Initializing...")
import configparser
from PIL import Image, ImageFile
ImageFile.LOAD_TRUNCATED_IMAGES=True
import cv2
import numpy as np
import threading
import time
import easyocr
import gc
import json
import websockets
import asyncio
import ssbu
import traceback
from tag_matching import findBestMatch
config = configparser.ConfigParser()
config.read('config.ini')
# Get the feed path from the config file
feed_path = config.get('settings', 'feed_path')
base_width = 1920
base_height = 1080

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
previous_states = [None] # list of previous states to be used for state change detection
reader = easyocr.Reader(['en'])

def is_within_deviation(color1, color2, deviation):
    return all(abs(c1 - c2) / 255.0 <= deviation for c1, c2 in zip(color1, color2))

def detect_stage_select_screen():
    global config, payload, previous_states, feed_path

    while True:
        try:
            # Verify the image
            img, scale_x, scale_y = capture_screen()
            pixel1 = img.getpixel((int(596 * scale_x), int(698 * scale_y)))
            pixel2 = img.getpixel((int(1842 * scale_x), int(54 * scale_y)))
            break
        except (OSError, Image.UnidentifiedImageError) as e:
            if "truncated" in str(e) or "cannot identify image file" in str(e) or "could not create decoder object" in str(e):
                time.sleep(0.25)
                continue
            else:
                raise e
    
    # Define the target colors and deviation
    target_color1 = (85, 98, 107)  # #55626b in RGB
    target_color2 = (200, 0, 0)   # #a50215 in RGB
    deviation = 0.1
    
    if is_within_deviation(pixel1, target_color1, deviation) and is_within_deviation(pixel2, target_color2, deviation):
        print("Stage select screen detected")
        payload['state'] = "stage_select"
        if payload['state'] != previous_states[-1]:
            previous_states.append(payload['state'])
            # reset payload to original values
            payload['stage'] = None

def capture_screen():
    img = Image.open(feed_path)
    actual_width, actual_height = img.size  # Reopen the image after verification
    scale_x = actual_width / base_width
    scale_y = actual_height / base_height
    return img,scale_x,scale_y

def detect_selected_stage():
    global config, payload, previous_states, feed_path
    
    while True:
        try:
            img, scale_x, scale_y = capture_screen()
            pixel = img.getpixel((int(1842 * scale_x), int(54 * scale_y)))
            break
        except (OSError, Image.UnidentifiedImageError) as e:
            if "truncated" in str(e) or "cannot identify image file" in str(e) or "could not create decoder object" in str(e):
                time.sleep(0.25)
                continue
            else:
                raise e
    
    # Define the target color and deviation
    target_color = (75, 5, 7)  # #4b0507 in RGB
    deviation = 0.1
        
    if is_within_deviation(pixel, target_color, deviation):
        print("Stage selected")
        stage = read_text(img, (int(110 * scale_x), int(700 * scale_y), int(500 * scale_x), int(100 * scale_y)))
        payload['stage'], _ = findBestMatch(stage, ssbu.stages)
        print("Selected stage:", payload['stage'])
        time.sleep(1)

def detect_character_select_screen():
    global config, payload, previous_states, feed_path
    
    while True:
        try:
            # Open the image
            img, scale_x, scale_y = capture_screen()
            pixel = img.getpixel((int(433 * scale_x), int(36 * scale_y)))
            break
        except (OSError, Image.UnidentifiedImageError) as e:
            if "truncated" in str(e) or "cannot identify image file" in str(e) or "could not create decoder object" in str(e):
                time.sleep(0.25)
                continue
            else:
                raise e
    
    # Define the target color and deviation
    target_color = (230, 208, 24)  # #e6d018 in RGB
    deviation = 0.1
    
    if is_within_deviation(pixel, target_color, deviation):
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

    return

def read_text(img, region, unskew=False):
    global payload, reader
    # print("Reading text...")
    # Define the area to read
    x, y, w, h = region
    cropped_img = img.crop((x, y, x + w, y + h))

    # Convert stage_img from PIL.Image to cv2
    cropped_img = cv2.cvtColor(np.array(cropped_img), cv2.COLOR_RGB2GRAY)
        
    # Use OCR to read the text from the image
    result = reader.readtext(cropped_img, paragraph=False)

    
    # Extract the text
    if result:
        result = ' '.join([res[1] for res in result])
    else: result = None

    # Release memory
    del cropped_img
    gc.collect()

    return result

def detect_versus_screen():
    global config, payload, previous_states, feed_path
    
    while True:
        try:
            img, scale_x, scale_y = capture_screen()
            pixel = img.getpixel((int(30 * scale_x), int(69 * scale_y)))
            pixel2 = img.getpixel((int(1040 * scale_x), int(55 * scale_y)))
            break
        except (OSError, Image.UnidentifiedImageError) as e:
            if "truncated" in str(e) or "cannot identify image file" in str(e) or "could not create decoder object" in str(e):
                time.sleep(0.25)
                continue
            else:
                raise e
    
    # Define the target color and deviation

    target_color = (251, 53, 51)  # #FB3533 in RGB
    target_color2 = (33, 140, 254)  # #218CFE in RGB

    deviation = 0.2
    
    if is_within_deviation(pixel, target_color, deviation) and is_within_deviation(pixel2, target_color2, deviation):
        print("Versus screen detected")
        payload['state'] = "in_game"
        if payload['state'] != previous_states[-1]:
            #set initial game data, both players have 3 stocks
            for player in payload['players']:
                player['stocks'] = 3
            previous_states.append(payload['state'])
            def read_characters_and_names():
                # Initialize the reader
                c1 = read_text(img, (int(110 * scale_x), int(10 * scale_y), int(870 * scale_x), int(120 * scale_y)), True)
                c1, score = findBestMatch(c1, ssbu.characters)
                if score < 0.75:
                    # Character is most likely a Mii
                    c1 = do_mii_recognition(img, 1, scale_x, scale_y)
                print("Player 1 character:", c1)
                c2 = read_text(img, (int(1070 * scale_x), int(10 * scale_y), int(870 * scale_x), int(120 * scale_y)), True)
                c2, score = findBestMatch(c2, ssbu.characters)
                if score < 0.75:
                    # Character is most likely a Mii
                    c2 = do_mii_recognition(img, 2, scale_x, scale_y)
                print("Player 2 character:", c2)
                t1 = read_text(img, (int(5 * scale_x), int(155 * scale_y), int(240 * scale_x), int(50 * scale_y)), True)
                print("Player 1 tag:", t1)
                t2 = read_text(img, (int(965 * scale_x), int(155 * scale_y), int(240 * scale_x), int(50 * scale_y)), True)
                print("Player 2 tag:", t2)
                payload['players'][0]['character'], payload['players'][1]['character'], payload['players'][0]['name'], payload['players'][1]['name'] = c1, c2, t1, t2
            threading.Thread(target=read_characters_and_names).start()
            time.sleep(2)
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
    
    if is_within_deviation(brawler_pixel, brawler_color, deviation):
        result = "Mii Brawler"
    elif is_within_deviation(gunner_pixel, gunner_color, deviation):
        result = "Mii Gunner"
    elif is_within_deviation(swordfighter_pixel, swordfighter_color, deviation):
        result = "Mii Swordfighter"

    return result


def detect_taken_stock():
    global config, payload, previous_states, feed_path
    
    while True:
        try:
            img, scale_x, scale_y = capture_screen()
            break
        except (OSError, Image.UnidentifiedImageError) as e:
            if "truncated" in str(e) or "cannot identify image file" in str(e) or "could not create decoder object" in str(e):
                time.sleep(0.25)
                continue
            else:
                raise e
    
    # Define the region to check
    x, y, w, h = int(905 * scale_x), int(445 * scale_y), int(105 * scale_x), int(40 * scale_y)
    region = img.crop((x, y, x + w, y + h))
    
    # Define the target color and deviation
    target_color = (255, 255, 255)  # #ffffff in RGB
    deviation = 0.1
    
    pixels = region.getdata()
    if all(is_within_deviation(pixel, target_color, deviation) for pixel in pixels):
        s1 = count_stock_numbers(img, (int(385 * scale_x), int(340 * scale_y), int(330 * scale_x), int(265 * scale_y)))
        s2 = count_stock_numbers(img, (int(1225 * scale_x), int(330 * scale_y), int(330 * scale_x), int(265 * scale_y)))
        if s1 == payload['players'][0]['stocks'] - 1 or s2 == payload['players'][1]['stocks'] - 1: #this ensures data will only be stored if there was only one stock taken. not gained, or lost, or multiple stocks taken
            payload['players'][0]['stocks'] = s1
            payload['players'][1]['stocks'] = s2
            print("Stock taken. Stocks left:", payload['players'][0]['stocks']," - ", payload['players'][1]['stocks'])

def count_stock_numbers(img, region):
    # Define the area to read
    global reader
    x, y, w, h = region
    stock_img = img.crop((x, y, x + w, y + h))

    #convert stock_image from PIL.Image to cv2
    stock_img = cv2.cvtColor(np.array(stock_img), cv2.COLOR_RGB2GRAY)
        
    # Use OCR to read the text from the image
    result = reader.readtext(stock_img, paragraph=False, allowlist='123', contrast_ths=0.7)
    
    # Extract the text
    if result:
        stock_number = result[0][1]
        if stock_number.isdigit():
            return int(stock_number) if int(stock_number) < 4 else 3 if int(stock_number) == 33 else 2 if int(stock_number) == 22 else 1
        return 1 # workaround because OCR fails to read the stock number accurately if it's 1
    return 1 # workaround because OCR fails to read the stock number accurately if it's 1

def detect_game_end():
    global config, payload, previous_states, base_width, base_height, feed_path
    
    while True:
        try:
            # Load the main image
            main_img = cv2.imread(feed_path, cv2.IMREAD_GRAYSCALE)
            height, width = main_img.shape
            scale_x = width / base_width
            scale_y = height / base_height
            if main_img is None:
                time.sleep(0.25)
                continue #image may be corrupted, try again
            break
        except OSError as e:
            if "image file is truncated" in str(e):
                time.sleep(0.25)
                continue
        except AttributeError as e:
            if "shape" in str(e):
                time.sleep(0.25)
                continue

            else:
                raise e

    
    # Crop the specific area
    x, y, w, h = int(312 * scale_x), int(225 * scale_y), int(1300 * scale_x), int(445 * scale_y)
    cropped_img = main_img[y:y+h, x:x+w]
    
    # Load the template images
    game_template = cv2.imread('img/GAME.png', cv2.IMREAD_GRAYSCALE)
    time_template = cv2.imread('img/TIME.png', cv2.IMREAD_GRAYSCALE)
    
    if game_template is None or time_template is None:
        raise FileNotFoundError("Template images not found")
    
    # Perform template matching
    res_game = cv2.matchTemplate(cropped_img, game_template, cv2.TM_CCOEFF_NORMED)
    res_time = cv2.matchTemplate(cropped_img, time_template, cv2.TM_CCOEFF_NORMED)
    
    # Check if the maximum correlation coefficient exceeds the threshold
    threshold = 0.5
    if np.max(res_game) >= threshold or np.max(res_time) >= threshold:
        print("Game end detected")
        process_game_end_data(main_img, scale_x, scale_y)
        payload['state'] = "game_end"
        if payload['state'] != previous_states[-1]:
            previous_states.append(payload['state'])

    
def process_game_end_data(main_img, scale_x, scale_y):
    global payload, reader
    # Define the area to read
    x, y, w, h = int(510 * scale_x), int(920 * scale_y), int(145 * scale_x), int(80 * scale_y)
    p1_damage_img = main_img[y:y+h, x:x+w]
    x, y, w, h = int(1250 * scale_x), int(920 * scale_y), int(145 * scale_x), int(80 * scale_y)
    p2_damage_img = main_img[y:y+h, x:x+w]
    
    results = []
    
    # Use OCR to read the text from the image
    result = reader.readtext(p1_damage_img)
    results.append(' '.join([res[1] for res in result]))
    result = reader.readtext(p2_damage_img)
    results.append(' '.join([res[1] for res in result]))

    payload['players'][0]['damage'] = results[0]
    payload['players'][1]['damage'] = results[1]

    # if player has one stock left and the damage recognizes as an empty string, they've lost all of their stocks.
    for player in payload['players']:
        if player['stocks'] < 3 and player['damage'] == '':
            player['stocks'] = 0
            print(str(player['name']) + " has lost all of their stocks")
            for player in payload['players']:
                if player['damage'] != '':
                    print(str(player['name']) + " Wins!")
            
    
    # Extract and print the text
    print("Damage read: Player 1: '", payload['players'][0]['damage'], "' - Player 2: '", payload['players'][1]['damage'], "'")


def run_detection():
    global payload, previous_states, feed_path
    while True:
        try:
            if payload['state'] == None:
                detect_stage_select_screen()
            elif payload['state'] == "stage_select":
                detect_selected_stage()
                detect_character_select_screen()
            elif payload['state'] == "character_select":
                detect_stage_select_screen()
                if payload['players'][0]['character'] == None: detect_versus_screen()
                gc.collect()
            elif payload['state'] == "in_game":
                detect_stage_select_screen()
                detect_taken_stock()
                detect_game_end()
            elif payload['state'] == "game_end":
                detect_stage_select_screen()
                detect_selected_stage()
                detect_character_select_screen()
            refresh_rate = config.getfloat('settings', 'refresh_rate')
        except Exception as e:
            print(f"Error: {str(e)}")
            print("Stack trace:")
            print(traceback.format_exc())
        time.sleep(refresh_rate)

async def send_data(websocket):
    global payload, config
    try:
        while True:
            data = json.dumps(payload)
            size = len(data.encode('utf-8'))
            if size > 1024 * 1024:  # 1MB
                print(f"Warning: Large payload size ({size} bytes)")
            refresh_rate = config.getfloat('settings', 'refresh_rate')
            await websocket.send(json.dumps(payload))
            await asyncio.sleep(refresh_rate)
    except websockets.exceptions.ConnectionClosedOK:
        # print("Connection closed normally by client")
        pass
    except websockets.exceptions.ConnectionClosedError as e:
        print(f"Connection closed with error: {e}")
        pass
    except Exception as e:
        print(f"Unexpected error: {e}")

def start_websocket_server():
    async def start_server():
        async with websockets.serve(
            send_data,
            "localhost",
            config.getint('settings', 'server_port'),
            ping_interval=60,  # Send ping every 20 seconds
            ping_timeout=90,   # Wait 10 seconds for pong response
            close_timeout=15   # Wait 10 seconds for close handshake
        ):
            await asyncio.Future()  # run forever

    asyncio.run(start_server())

if __name__ == "__main__":
    # Start the detection thread
    detection_thread = threading.Thread(target=run_detection)
    detection_thread.daemon = True
    detection_thread.start()
    
    # Start the websocket server thread
    websocket_thread = threading.Thread(target=start_websocket_server)
    websocket_thread.daemon = True
    websocket_thread.start()

    print("All systems go. Please head to the stage selection screen to start detection.")

    # Keep the main thread alive
    while True:
        time.sleep(1)