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
config = configparser.ConfigParser()
config.read('config.ini')

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

def detect_stage_select_screen():
    global config, payload, previous_states
    # Read the config file
    
    # Get the feed path from the config file
    feed_path = config.get('settings', 'feed_path')
    
    while True:
        try:
            # Verify the image
            img = Image.open(feed_path)  # Reopen the image after verification
            pixel1 = img.getpixel((596, 698))
            pixel2 = img.getpixel((1842, 54))
            break
        except (OSError, Image.UnidentifiedImageError) as e:
            if "truncated" in str(e) or "cannot identify image file" in str(e) or "could not create decoder object" in str(e):
                continue
            else:
                raise e
    
    # Define the target colors and deviation
    target_color1 = (85, 98, 107)  # #55626b in RGB
    target_color2 = (165, 2, 21)   # #a50215 in RGB
    deviation = 0.1
    
    # Check if the pixel color is within the deviation range
    def is_within_deviation(color1, color2, deviation):
        return all(abs(c1 - c2) / 255.0 <= deviation for c1, c2 in zip(color1, color2))
    
    if is_within_deviation(pixel1, target_color1, deviation) and is_within_deviation(pixel2, target_color2, deviation):
        print("Stage select screen detected")
        payload['state'] = "stage_select"
        if payload['state'] != previous_states[-1]:
            previous_states.append(payload['state'])
            # reset payload to original values
            payload['stage'] = None

def detect_selected_stage():
    global config, payload, previous_states
    # Read the config file
    
    # Get the feed path from the config file
    feed_path = config.get('settings', 'feed_path')
    
    while True:
        try:
            # Open the image
            img = Image.open(feed_path)
            pixel = img.getpixel((1842, 54))
            break
        except (OSError, Image.UnidentifiedImageError) as e:
            if "truncated" in str(e) or "cannot identify image file" in str(e) or "could not create decoder object" in str(e):
                continue
            else:
                raise e
    
    # Define the target color and deviation
    target_color = (75, 5, 7)  # #4b0507 in RGB
    deviation = 0.1
    
    # Check if the pixel color is within the deviation range
    def is_within_deviation(color1, color2, deviation):
        return all(abs(c1 - c2) / 255.0 <= deviation for c1, c2 in zip(color1, color2))
    
    if is_within_deviation(pixel, target_color, deviation):
        print("Stage selected")
        payload['stage'] = read_text(img, (110, 700, 500, 100))
        print("Selected stage:", payload['stage'])

def detect_character_select_screen():
    global config, payload, previous_states
    # Read the config file
    
    # Get the feed path from the config file
    feed_path = config.get('settings', 'feed_path')
    
    while True:
        try:
            # Open the image
            img = Image.open(feed_path)
            pixel = img.getpixel((433, 36))
            break
        except (OSError, Image.UnidentifiedImageError) as e:
            if "truncated" in str(e) or "cannot identify image file" in str(e) or "could not create decoder object" in str(e):
                continue
            else:
                raise e
    
    # Define the target color and deviation
    target_color = (230, 208, 24)  # #e6d018 in RGB
    deviation = 0.1
    
    # Check if the pixel color is within the deviation range
    def is_within_deviation(color1, color2, deviation):
        return all(abs(c1 - c2) / 255.0 <= deviation for c1, c2 in zip(color1, color2))
    
    if is_within_deviation(pixel, target_color, deviation):
        payload['state'] = "character_select"
        if payload['state'] != previous_states[-1]:
            previous_states.append(payload['state'])
            #clean up some more player information
            for player in payload['players']:
                player['stocks'] = None
                player['damage'] = None
                player['character'] = None
                player['name'] = None

    return

def unskew_image(image):
    
    # Apply edge detection
    edges = cv2.Canny(image, 50, 150, apertureSize=3)
    
    # Find contours
    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    
    # Find the minimum area rectangle
    rect = cv2.minAreaRect(np.concatenate(contours))
    angle = rect[-1]
    
    # Correct the angle
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle
    
    # Get the rotation matrix
    (h, w) = image.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    
    # Rotate the image
    rotated = cv2.warpAffine(np.array(image), M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    
    return Image.fromarray(rotated)

def read_text(img, region, unskew=False):
    global payload
    print("Attempting to read text...")
    # Define the area to read
    x, y, w, h = region
    cropped_img = img.crop((x, y, x + w, y + h))

    # Convert stage_img from PIL.Image to cv2
    cropped_img = cv2.cvtColor(np.array(cropped_img), cv2.COLOR_RGB2GRAY)
    
    # Initialize the reader
    reader = easyocr.Reader(['en'])
    
    # Use OCR to read the text from the image
    result = reader.readtext(cropped_img, paragraph=False)

    
    # Extract the text
    if result:
        result = ' '.join([res[1] for res in result])
    else: result = None

    # Release memory
    del cropped_img, reader
    gc.collect()

    return result

def detect_versus_screen():
    global config, payload, previous_states
    # Read the config file
    
    # Get the feed path from the config file
    feed_path = config.get('settings', 'feed_path')
    
    while True:
        try:
            # Open the image
            img = Image.open(feed_path)
            pixel = img.getpixel((30, 69))
            pixel2 = img.getpixel((1040, 55))
            break
        except (OSError, Image.UnidentifiedImageError) as e:
            if "truncated" in str(e) or "cannot identify image file" in str(e) or "could not create decoder object" in str(e):
                continue
            else:
                raise e
    
    # Define the target color and deviation

    target_color = (251, 53, 51)  # #FB3533 in RGB
    target_color2 = (33, 140, 254)  # #218CFE in RGB

    deviation = 0.2
    
    # Check if the pixel color is within the deviation range
    def is_within_deviation(color1, color2, deviation):
        return all(abs(c1 - c2) / 255.0 <= deviation for c1, c2 in zip(color1, color2))
    
    if is_within_deviation(pixel, target_color, deviation) and is_within_deviation(pixel2, target_color2, deviation):
        print("Versus screen detected")
        payload['state'] = "in_game"
        if payload['state'] != previous_states[-1]:
            #set initial game data, both players have 3 stocks
            for player in payload['players']:
                player['stocks'] = 3
            previous_states.append(payload['state'])
            c1 = payload['players'][0]['character'] = read_text(img, (110, 10, 870, 120), True)
            print("Player 1 character:", payload['players'][0]['character'])
            c2 = payload['players'][1]['character'] = read_text(img, (1070, 10, 870, 120), True)
            print("Player 2 character:", payload['players'][1]['character'])
            t1 = payload['players'][0]['name'] = read_text(img, (5, 155, 240, 50), True)
            print("Player 1 tag:", payload['players'][0]['name'])
            t2 = payload['players'][1]['name'] = read_text(img, (965, 155, 240, 50), True)
            print("Player 2 tag:", payload['players'][1]['name'])
            payload['players'][0]['character'], payload['players'][1]['character'], payload['players'][0]['name'], payload['players'][1]['name'] = c1, c2, t1, t2
    return img



def detect_taken_stock():
    global config, payload, previous_states
    # Read the config file
    
    # Get the feed path from the config file
    feed_path = config.get('settings', 'feed_path')
    
    while True:
        try:
            # Open the image
            img = Image.open(feed_path)
            break
        except (OSError, Image.UnidentifiedImageError) as e:
            if "truncated" in str(e) or "cannot identify image file" in str(e) or "could not create decoder object" in str(e):
                continue
            else:
                raise e
    
    # Define the region to check
    x, y, w, h = 905, 445, 105, 40
    region = img.crop((x, y, x + w, y + h))
    
    # Define the target color and deviation
    target_color = (255, 255, 255)  # #ffffff in RGB
    deviation = 0.1
    
    # Check if the region is filled with the target color within the deviation range
    def is_within_deviation(color1, color2, deviation):
        return all(abs(c1 - c2) / 255.0 <= deviation for c1, c2 in zip(color1, color2))
    
    pixels = region.getdata()
    if all(is_within_deviation(pixel, target_color, deviation) for pixel in pixels):
        print("Taken stock detected")
        payload['players'][0]['stocks'] = count_stock_numbers(img, (385, 340, 330, 265))
        payload['players'][1]['stocks'] = count_stock_numbers(img, (1225, 330, 330, 265))
        print("Stocks left:", payload['players'][0]['stocks'], payload['players'][1]['stocks'])

def count_stock_numbers(img, region):
    # Define the area to read
    x, y, w, h = region
    stock_img = img.crop((x, y, x + w, y + h))

    #convert stock_image from PIL.Image to cv2
    stock_img = cv2.cvtColor(np.array(stock_img), cv2.COLOR_RGB2GRAY)
    
    # Initialize the reader
    reader = easyocr.Reader(['en'])
    
    # Use OCR to read the text from the image
    result = reader.readtext(stock_img, paragraph=False, allowlist='123')
    
    # Extract the text
    if result:
        stock_number = result[0][1]
        if stock_number.isdigit():
            return int(stock_number) if int(stock_number) < 4 else 3 if int(stock_number) == 33 else 2 if int(stock_number) == 22 else 1
        return 1 #workaround because OCR fails to read the stock number accurately if it's 1
    return 1 #workaround because OCR fails to read the stock number accurately if it's 1

def detect_game_end():
    global config, payload, previous_states
    # Read the config file
    
    # Get the feed path from the config file
    feed_path = config.get('settings', 'feed_path')
    
    while True:
        try:
            # Load the main image
            main_img = cv2.imread(feed_path, cv2.IMREAD_GRAYSCALE)
            if main_img is None:
                continue #image may be corrupted, try again
            break
        except OSError as e:
            if "image file is truncated" in str(e):
                continue
            else:
                raise e

    
    # Crop the specific area
    x, y, w, h = 312, 225, 1300, 445
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
        process_game_end_data(main_img)
        payload['state'] = "game_end"
        if payload['state'] != previous_states[-1]:
            previous_states.append(payload['state'])

    
def process_game_end_data(main_img):
    global payload
    # Define the area to read
    x, y, w, h = 510, 920, 145, 80
    p1_damage_img = main_img[y:y+h, x:x+w]
    x, y, w, h = 1250, 920, 145, 80
    p2_damage_img = main_img[y:y+h, x:x+w]
    
    # Initialize the reader
    reader = easyocr.Reader(['en'])

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
        if player['stocks'] == 1 and player['damage'] == '':
            player['stocks'] = 0
    
    # Extract and print the text
    print("Damage read: Player 1: ", payload['players'][0]['damage'], " - Player 2: ", payload['players'][1]['damage'])


def run_detection():
    global payload, previous_states, images
    while True:
        if not payload['state']:
            detect_stage_select_screen()
        elif payload['state'] == "stage_select":
            detect_selected_stage()
            detect_character_select_screen()
        elif payload['state'] == "character_select":
            detect_stage_select_screen()
            detect_versus_screen()
            images = []
            gc.collect()
        elif payload['state'] == "in_game":
            detect_stage_select_screen()
            detect_taken_stock()
            detect_game_end()
        elif payload['state'] == "game_end":
            detect_stage_select_screen()
        refresh_rate = config.getfloat('settings', 'refresh_rate')
        time.sleep(refresh_rate)

async def send_data(websocket, path):
    global payload, config
    refresh_rate = config.getfloat('settings', 'refresh_rate')
    try:
        while True:
            await websocket.send(json.dumps(payload))
            await asyncio.sleep(refresh_rate)
    except websockets.exceptions.ConnectionClosedOK:
        # print("Connection closed normally")
        pass
    except websockets.exceptions.ConnectionClosedError as e:
        # print(f"Connection closed with error: {e}")
        pass
    except Exception as e:
        print(f"Unexpected error: {e}")

def start_websocket_server():
    async def start_server():
        async with websockets.serve(send_data, "localhost", config.getint('settings', 'server_port')):
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