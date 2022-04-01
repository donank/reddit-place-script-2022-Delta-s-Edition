# imports
import os, random
import math
import requests
import json
import time
from io import BytesIO
from websocket import create_connection
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv
from PIL import ImageColor
from PIL import Image

# load env variables
load_dotenv()

# pixel drawing preferences
pixel_x_start = int(os.getenv('ENV_DRAW_X_START'))
pixel_y_start = int(os.getenv('ENV_DRAW_Y_START'))

# map of colors for pixels you can place
color_map = {
    "#FF4500": 2,  # bright red
    "#FFA800": 3,  # orange
    "#FFD635": 4,  # yellow
    "#00A368": 6,  # darker green
    "#7EED56": 8,  # lighter green
    "#2450A4": 12,  # darkest blue
    "#3690EA": 13,  # medium normal blue
    "#51E9F4": 14,  # cyan
    "#811E9F": 18,  # darkest purple
    "#B44AC0": 19,  # normal purple
    "#FF99AA": 23,  # pink
    "#9C6926": 25,  # brown
    "#000000": 27,  # black
    "#898D90": 29,  # grey
    "#D4D7D9": 30,  # light grey
    "#FFFFFF": 31,  # white
}


def rgb_to_hex(rgb):
    return ('#%02x%02x%02x' % rgb).upper()


def closest_color(target_rgb, rgb_colors_array_in):
    r, g, b, a = target_rgb
    print(r,g,b,a)
    if a < 255 or (r,g,b) == (69,42,0):
        return (69,42,0)
    color_diffs = []
    for color in rgb_colors_array_in:
        cr, cg, cb = color
        color_diff = math.sqrt((r - cr) ** 2 + (g - cg) ** 2 + (b - cb) ** 2)
        color_diffs.append((color_diff, color))
    return min(color_diffs)[1]


rgb_colors_array = []

for color_hex, color_index in color_map.items():
    rgb_array = ImageColor.getcolor(color_hex, "RGB")
    rgb_colors_array.append(rgb_array)

print("available colors (rgb): ", rgb_colors_array)

image_path = os.path.join(os.path.abspath(os.getcwd()), 'unknown.png')
im = Image.open(image_path)

pix = im.load()
print("image size: ", im.size)  # Get the width and hight of the image for iterating over
image_width, image_height = im.size

# test drawing image to file called new_image before drawing to r/place
current_r = 0
current_c = 0

while True:
    r = current_r
    c = current_c

    target_rgb = pix[r, c]
    new_rgb = closest_color(target_rgb, rgb_colors_array)
    # print("closest color: ", new_rgb)
    pix[r, c] = new_rgb

    current_r += 1

    if current_r >= image_width:
        current_c += 1
        current_r = 0

    if current_c >= image_height:
        print("done drawing image locally to new_image.png")
        break

new_image_path = os.path.join(os.path.abspath(os.getcwd()), 'new_image.png')
im.save(new_image_path)

# developer's reddit username and password
username = os.getenv('ENV_PLACE_USERNAME')
password = os.getenv('ENV_PLACE_PASSWORD')
# note: use https://www.reddit.com/prefs/apps
app_client_id = os.getenv('ENV_PLACE_APP_CLIENT_ID')
secret_key = os.getenv('ENV_PLACE_SECRET_KEY')

# global variables for script
access_token = None
current_timestamp = math.floor(time.time())
last_time_placed_pixel = math.floor(time.time())
access_token_expires_at_timestamp = math.floor(time.time())

# note: reddit limits us to place 1 pixel every 5 minutes, so I am setting it to 5 minutes and 30 seconds per pixel
pixel_place_frequency = 330


# method to draw a pixel at an x, y coordinate in r/place with a specific color
def set_pixel(access_token_in, x, y, color_index_in=18, canvas_index=0):
    print("placing pixel")

    url = "https://gql-realtime-2.reddit.com/query"

    payload = json.dumps({
        "operationName": "setPixel",
        "variables": {
            "input": {
                "actionName": "r/replace:set_pixel",
                "PixelMessageData": {
                    "coordinate": {
                        "x": x,
                        "y": y
                    },
                    "colorIndex": color_index_in,
                    "canvasIndex": canvas_index
                }
            }
        },
        "query": "mutation setPixel($input: ActInput!) {\n  act(input: $input) {\n    data {\n      ... on BasicMessage {\n        id\n        data {\n          ... on GetUserCooldownResponseMessageData {\n            nextAvailablePixelTimestamp\n            __typename\n          }\n          ... on SetPixelResponseMessageData {\n            timestamp\n            __typename\n          }\n          __typename\n        }\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n}\n"
    })
    headers = {
        'origin': 'https://hot-potato.reddit.com',
        'referer': 'https://hot-potato.reddit.com/',
        'apollographql-client-name': 'mona-lisa',
        'Authorization': 'Bearer ' + access_token_in,
        'Content-Type': 'application/json'
    }

    response = requests.request("POST", url, headers=headers, data=payload)

    print(response.text)

def get_board(bearer):
    print("Getting board")
    ws = create_connection("wss://gql-realtime-2.reddit.com/query")
    ws.send(json.dumps({"type":"connection_init","payload":{"Authorization":"Bearer "+bearer}}))
    ws.recv()
    ws.send(json.dumps({"id":"1","type":"start","payload":{"variables":{"input":{"channel":{"teamOwner":"AFD2022","category":"CONFIG"}}},"extensions":{},"operationName":"configuration","query":"subscription configuration($input: SubscribeInput!) {\n  subscribe(input: $input) {\n    id\n    ... on BasicMessage {\n      data {\n        __typename\n        ... on ConfigurationMessageData {\n          colorPalette {\n            colors {\n              hex\n              index\n              __typename\n            }\n            __typename\n          }\n          canvasConfigurations {\n            index\n            dx\n            dy\n            __typename\n          }\n          canvasWidth\n          canvasHeight\n          __typename\n        }\n      }\n      __typename\n    }\n    __typename\n  }\n}\n"}}))
    ws.recv()
    ws.send(json.dumps({"id":"2","type":"start","payload":{"variables":{"input":{"channel":{"teamOwner":"AFD2022","category":"CANVAS","tag":"0"}}},"extensions":{},"operationName":"replace","query":"subscription replace($input: SubscribeInput!) {\n  subscribe(input: $input) {\n    id\n    ... on BasicMessage {\n      data {\n        __typename\n        ... on FullFrameMessageData {\n          __typename\n          name\n          timestamp\n        }\n        ... on DiffFrameMessageData {\n          __typename\n          name\n          currentTimestamp\n          previousTimestamp\n        }\n      }\n      __typename\n    }\n    __typename\n  }\n}\n"}}))

    file = ""
    while True:
        temp = json.loads(ws.recv())
        if temp['type'] == 'data':
            msg = temp['payload']['data']['subscribe']
            if msg['data']['__typename'] == 'FullFrameMessageData':
                file = msg['data']['name']
                break;


    ws.close()

    img = BytesIO(requests.get(file, stream = True).content)
    print("Got image:", file)

    return img

def get_unset_pixel(img):
    x = 0
    y= 0
    pix2 = Image.open(img).convert('RGB').load()
    while True:
        x += 1

        if x >= image_width:
            y += 1
            x = 0

        if y >= image_height:
            break;

        print(x+pixel_x_start,y+pixel_y_start)
        print(x, y,"img",image_width,image_height)
        target_rgb = pix[x, y]
        new_rgb = closest_color(target_rgb, rgb_colors_array)
        if pix2[x+pixel_x_start,y+pixel_y_start] != new_rgb:
            print(pix2[x+pixel_x_start,y+pixel_y_start], new_rgb,new_rgb != (69,42,0), pix2[x,y] != new_rgb)
            if new_rgb != (69,42,0):
                print("Different Pixel found at:",x+pixel_x_start,y+pixel_y_start,"With Color:",pix2[x+pixel_x_start,y+pixel_y_start],"Replacing with:",new_rgb)
                break;
            else:
                print("TransparrentPixel")
    return x,y

# current pixel row and pixel column being drawn
current_r = 0
current_c = 0
# loop to keep refreshing tokens when necessary and to draw pixels when the time is right
while True:
    current_timestamp = math.floor(time.time())

    # refresh access token if necessary
    if access_token is None or current_timestamp >= expires_at_timestamp:
        print("refreshing access token...")

        headers = {
            'user-agent': 'Mozilla/5.0 (Macintosh; PPC Mac OS X 10_8_7 rv:5.0; en-US) AppleWebKit/533.31.5 (KHTML, like Gecko) Version/4.0 Safari/533.31.5',
        }

        data = {
            'grant_type': 'password',
            'username': username,
            'password': password
        }

        r = requests.post("https://ssl.reddit.com/api/v1/access_token",
                          data=data,
                          auth=HTTPBasicAuth(app_client_id, secret_key),
                          headers=headers)

        print("received response: ", r.text)

        response_data = r.json()

        access_token = response_data["access_token"]
        access_token_type = response_data["token_type"]  # this is just "bearer"
        access_token_expires_in_seconds = response_data["expires_in"]  # this is usually "3600"
        access_token_scope = response_data["scope"]  # this is usually "*"

        # ts stores the time in seconds
        expires_at_timestamp = current_timestamp + int(access_token_expires_in_seconds)

        print("received new access token: ", access_token)

    # draw pixel onto screen
    if True: #access_token is not None and current_timestamp >= last_time_placed_pixel + pixel_place_frequency:
        # get current pixel position from input image
        r, c = get_unset_pixel(get_board(access_token))

        quit()

        target_rgb = pix[r, c]
        # get converted color
        new_rgb = closest_color(target_rgb, rgb_colors_array)
        new_rgb_hex = rgb_to_hex(new_rgb)
        pixel_color_index = color_map[new_rgb_hex]

        print(pixel_color_index)

        # draw the pixel onto r/place
        set_pixel(access_token, pixel_x_start + r, pixel_y_start + c, pixel_color_index)
        last_time_placed_pixel = math.floor(time.time())

        current_r += 1
        current_c += 1

        # go back to first column when reached end of a row while drawing
        if current_r >= image_width:
            current_r = 0

        # exit when all pixels drawn
        if current_c >= image_height:
            print("done drawing image to r/place")
            current_c = 0
            exit(0)
    time.sleep(10)
