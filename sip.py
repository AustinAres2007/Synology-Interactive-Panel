"""
Only Programmed on iPad Pro third generations, has NOT been tested with other models. On latest version of python avalible on Pythonista (Python 3.6)

Made by Austin Ares, 
"nas" module made by https://github.com/N4S4/synology-api go check them out.

PS: Modifications were made to the "nas" module to better support what I am making.
"""

'''
TODO: 
    
    - Features / Changes
    
    Make files / folders from SiP, (Feature, Done)
    Open text files (text or source code), (Feature, Done)
    Get file infomation (Impliment into PhotoView), (Feature, Done)
    Add keyboard shortcuts for browsing through files, (Feature, Done)
    Add proper login form (Feature, Done)
    Make digital buttons for browsing through directories (Feature, Done)
    Be able to import photos / files from the camera roll and iCloud (Feature, Done)
    Add a button where you can take a photo, and the photo will save to the directory you are in (Gimmick)
    Open file by default when tapping on it (Change, Done)
    When going into more options on a folder and tapping "Open" just open the folder, don't return an error (Change, Done)
    When opening an empty directory, there is no indication that the folder is empty, and could be mistaken that SiP has crashed (Change, Done)
    Add "Clear" option to the more menu of folders. This will clear the whole directory (Feature)
    
    - Bugs / Issues
    
    When logged in with an account that is missing permissions, it returns no graceful error. (Bug, Fixed)
    When spamming Q or E (To go back a directory, or to go forward) when done enough, SiP will freeze. (Bug, Fixed)
    When using motion controls with PhotoView, SiP will also respond to these. (Bug, Fixed)
    When renaming a file, any file, SiP will freeze. (Bug, Fixed)
    Cannot open PDF files. (Bug, Fixed)
    When the remainder of files in a directory is 2, the you can overshoot the files a little bit (Issue)
    
'''

import ui
import console 
import os
import dialogs
import motion
import io
import requests
import objc_util
import photos
import shutil

from nas.auth import AuthenticationError
from requests.exceptions import ConnectionError
from threading import Thread
from sys import argv, exit
from time import sleep
from hurry.filesize import size as s
from hurry.filesize import verbose

try:
    import config
    
    from nas import filestation
    from nas.auth import AuthenticationError
    
except ModuleNotFoundError as e:
    print(f'"config" or "nas" module not found.\n\nActual Error: {e}'); exit(1)
    
cfg = config.Config('sip-config.cfg')
w, h = ui.get_screen_size()

mode_ = objc_util.ObjCClass('UITraitCollection').currentTraitCollection()
mode = 'dark' if mode_.userInterfaceStyle() == 2 else 'light'

file_colour = cfg[mode]['fl_color'] 
background_color = cfg[mode]['bk_color'] 
title_bar_color = cfg[mode]['tb_color'] 

if len(argv) >= 5:
    
    url = argv[1]
    port = argv[2]
    user = argv[3]
    passw = argv[4]
    root = argv[5]
    
else:
    
    fields = [
        {'type': 'url', 'key': 'nas-url', 'title': 'Synology URL  ', 'placeholder': 'example.synology.me', 'tint_color': file_colour},
        {'type': 'number', 'key': 'nas-port', 'value': '5001', 'title': 'Synology Port     ', 'placeholder': '5001', 'tint_color': file_colour},
        {'type': 'text', 'key': 'nas-user', 'title': 'Synology User   ', 'placeholder': 'Username', 'tint_color': file_colour},
        {'type': 'password', 'key': 'nas-password', 'title': 'Username Pass     ', 'placeholder': 'Password', 'tint_color': file_colour},
        {'type': 'text', 'key': 'nas-root', 'title': 'Synology Root     ', 'placeholder': 'Root directory', 'tint_color': file_colour}   
    ]
    
    login_form = dialogs.form_dialog(title='Login', fields=fields)
    
    if login_form:
        try:
            url = login_form['nas-url']
            port = int(login_form['nas-port'])
            user = login_form['nas-user']
            passw = login_form['nas-password']
            root = login_form['nas-root']
            
            if (url and port and user and passw and root):
                pass
            else:
                console.hud_alert('One or more of the fields are empty.', 'error'); exit(1)
                
        except ValueError:
            console.hud_alert('The port contains a character.', 'error'); exit(1)
    else:
        exit(0)
    
asset_location = './assets'

averg = lambda data_set: max(set(data_set), key = data_set.count)
contents = lambda dir_c: ((file.title, file.subviews[1].title) for file in dir_c)
orientation = objc_util.ObjCClass('UIDevice').currentDevice().orientation()

default_width = w*1/7 if orientation == 3 else w*1/5
default_height = h*1/5

print(default_width/2)
spacing = cfg['spacing']
font = (cfg['font'], cfg['font_size'])
interval = cfg['interval']
debug = cfg['debug']
blunt = cfg['blunt']

animation_length = cfg['anime_length']

motion_controls = cfg['motion_controls']
picker = 'black'
assets = {}

for file in os.listdir(asset_location):
    fd = file.split('.')
    if fd[-1] == 'png':
        assets[fd[0]] = ui.Image.named(f'{asset_location}/{file}')

audio_extensions = ['ogg', 'mp3', 'flac', 'alac', 'mp2', 'wav', 'aup']
video_extensions = ['mov', 'mp4', 'mkv']
photo_extensions = ['png','jpeg','jpg','heic', 'gif']
unicode_file = ['txt', 'py', 'json', 'js', 'c', 'cpp', 'ini']
special_extensions = ['csv', 'pdf', 'docx']

def make_buttons(*args):
    for subview in args[2].subviews:
        args[2].remove_subview(subview)
        
    old_dim = args[1]
    
    x = 0
    y = spacing
    
    for i, element in enumerate(args[0]):
        item = ui.Button()
            
        if i % 3 == 0 and i != 0:
            y += 210
            x = args[1][0]
        elif args[1]:
            x = (old_dim[2]+old_dim[0]+spacing) 
        
        item.border_width = int(element[0])
        item.border_color = element[1]
        item.title = element[4]
        item.frame = (x, y, default_width, default_height) if i else args[1]
        old_dim = item.frame if i else args[1]
        
        item.autoresizing = 'WH'
        item.image = element[5]
        item.tint_color = element[6]
        item.name = element[7]
        item.action = element[2](item)
        
        yield item

class SInteractivePanel(ui.View):
    def __init__(self):
        try:
            
            self.text = 'Loading'
            self.center = (w/2, h/2)
            self.background_color = background_color # Background color of View
            self.name = root 
            # Make new scroll view
            self.scroll_view = ui.ScrollView()
            
            # Define dimentions
            
            self.update_interval = 0.2 if motion_controls else 0
            self.tint_color = file_colour
            motion.start_updates() if motion_controls else None # Start motion updates for update() to use
            
            self.avg = self.bnts = []
            self.nas = self.last_folder = None
            self.off = self.photoview = self.load_buffer = self.is_pointing = self.download = False
            
            # Define the scrollable area, only done on initialisation, when going through folders, it's done in render_view
            
            self.scroll_view.height = h
            self.scroll_view.width = w
            self.scroll_view.content_size = (w, h)
            self.file_display_formula = (self.width/3, spacing, default_width, default_height)
            # Esablish connection, this will continue until script is closed
            
            self.left_button_items = [ui.ButtonItem(image=ui.Image.named('iob:chevron_left_32'), tint_color=file_colour, action=lambda _: self.go_back(), enabled=True)]
            self.right_button_items = [ui.ButtonItem(image=ui.Image.named('typb:Write'), tint_color=file_colour, action=lambda _: self.make_media(), enabled=True), ui.ButtonItem(image=ui.Image.named('typb:Archive'), tint_color=file_colour, action=lambda _: self.import_foreign_media(), enabled=True)]
            
            x = (self.center[0 if orientation == 3 else 1]/2)+.5
            self.add_subview(ui.Label(name='ld', text=self.text, x=x, y=self.center[1]/2, alignment=ui.ALIGN_CENTER, font=font, text_color=file_colour))
            
            
            self.subviews[0].alpha = 0.0
            self.add_subview(self.scroll_view) # Display the files in the root
            self.render_view(root)
        except ConnectionError: # If no connection
            console.alert('No Connection')
    
    def make_media(self):
        file_or_folder = console.alert('New', '', 'File', 'Folder')
        name = console.input_alert('Media Name', '')
        
        if file_or_folder == 2:
            self.nas.create_folder(folder_path=self.name, name=name)
            console.hud_alert(f'Made new folder: {name} at {self.name}')
        else:
            text = dialogs.text_dialog(name)
            with open(name, 'w+') as tmp_file:
                tmp_file.write(text)
            
            self.nas.upload_file(self.name, name)
            os.remove(name)
            
            console.hud_alert('Uploaded Successfully')
            
        self.render_view(self.name)
            
        
    def connect(self):
        try:
            self.nas = filestation.FileStation(url, port, user, passw, secure=True, debug=debug)
        except AuthenticationError:
            return console.alert('Invalid username / password')
        except ConnectionError:
            return console.alert('No Internet connection')
    
    def animation_on_ld(self):
        for x in range(0, 10):
            self.subviews[0].alpha = round(x/10)
            
    def animation_off_ld(self):
        for x in range(10, 0, -1):
            self.subviews[0].alpha = round(x/10)
                            
    def animation_on(self):
        for x in range(0, 10):
            self.scroll_view.alpha = round(x/10)
            
    def animation_off(self):
        for x in range(10, 0, -1):
            self.scroll_view.alpha = round(x/10)  
                
    @ui.in_background
    def render_view(self, sender):
        if not self.load_buffer and not self.photoview and (isinstance(sender, ui.Button) and (sender.title == 'Login' or sender.image.name.endswith('folder.png'))) or isinstance(sender, str) :
            try:
                self.subviews[0].text = 'Loading'
                self.load_buffer = True
                path = sender.name if isinstance(sender, ui.Button) else sender
                
                try:
                    ui.animate(self.animation_off, animation_length)  
                    ui.animate(self.animation_on_ld, animation_length-.1)
                    
                    contents_d = self.nas.get_file_list(path)
                    contents = contents_d['data']['files']
                    
                except AttributeError:
                    return console.alert('No connection to NAS, typo?')
                except KeyError:
                    if contents_d['error']['code'] == 119:
                        console.hud_alert(f'Error, please reload script (Error code 119, cannot be fixed by author. Only Synology can fix this)')
                    else:
                        console.hud_alert(f"you are missing permissions to this directory.", 'error', 3.5) 
                    
                button_metadata = ([0, file_colour, lambda _: self.render_view, h*1/8, item['name'], assets['folder'] if item['isdir'] else (assets['file'] if item['name'].split('.')[-1].lower() in unicode_file else (assets['photo'] if item['name'].split('.')[-1].lower() in photo_extensions else (assets['video'] if item['name'].split('.')[-1].lower() in video_extensions else (assets['audio'] if item['name'].split('.')[-1].lower() in audio_extensions else assets['file'])))), file_colour, item['path']] for item in contents)
                buttons = make_buttons(button_metadata, self.file_display_formula, self.scroll_view)
                dir_status = {}
                
                for item in contents:
                    dir_status[item['name']] = item['isdir']
                
                for ind, bnt in enumerate(buttons):
                    file_lable = ui.Label()
                    
                    wdt = ((len(bnt.title) / len(bnt.title)*2.1)) if len(bnt.title) > 8 else (len(bnt.title) / 7)
        
                    self.bnts.append(ui.Button())
                    
                    file_lable.text = bnt.title
                    file_lable.x = bnt.width*wdt/10
                    file_lable.y = bnt.height*.65
                    file_lable.alignment = ui.ALIGN_RIGHT
                    file_lable.line_break_mode = ui.LB_TRUNCATE_TAIL                
                    file_lable.font = font
                    file_lable.text_color = file_colour
                    
                    self.bnts[ind].x = -20
                    self.bnts[ind].y = -35
                    self.bnts[ind].width = self.bnts[ind].height = 100
                    self.bnts[ind].image = assets['opt']
                    self.bnts[ind].title = str(dir_status[bnt.title])
                    self.bnts[ind].name = bnt.title
                    self.bnts[ind].action = lambda _: self.context_menu(self.bnts[ind])
                    
                    bnt.add_subview(file_lable)
                    bnt.add_subview(self.bnts[ind])
                    
                    self.scroll_view.add_subview(bnt)
                
                for o, a in enumerate(self.bnts):
                    a.action = lambda a: self.context_menu(a)    
                    self.scroll_view.subviews[o].add_subview(a)
                    
                i = len(self.scroll_view.subviews)
                r = round(i/3+i%3)
                
                self.scroll_view.content_size = (w, (default_height*r)+((210-default_height)*r)+210)
                self.name = path
                
                ui.animate(self.animation_off_ld, animation_length-.1)
                ui.animate(self.animation_on, animation_length)
                
                if not self.scroll_view.subviews:
                    self.scroll_view.add_subview(ui.Label(text='No files', x=self.center[0]*0.9, y=self.center[1]*0.6, alignment=ui.ALIGN_LEFT, font=font, text_color='#bcbcbc'))
                    
                self.bnts = []
                
            except ConnectionError:
                console.hud_alert(f"Timed out connection", 'error', 3.5)
                self.close()
                
            finally:
                self.load_buffer = False
                
                ui.animate(self.animation_off_ld, animation_length-.1)
                ui.animate(self.animation_on, animation_length)
                
        elif sender.image.name.split('.')[-1] in unicode_file+special_extensions+photo_extensions:
            sender.enabled = False
            self.open_file(sender, True)
            
    
    def go_back(self):
        path = '/'.join(str(self.name).split('/')[:-1])
        
        if path:
            self.last_folder = self.name
            self.render_view(path)
            
    @ui.in_background
    def update(self):
        i = motion.get_attitude()[0]
        y = motion.get_attitude()[1]
        
        if y < -0.15 and not self.is_pointing:
            self.is_pointing = True
            self.position = 'left'
            
            self.go_back()
              
        elif self.is_pointing and (y < -0.15 or y > 0.18 or i > -0.2):
            self.pointing = False
            
        elif y > 0.18 and not self.is_pointing:
            self.position = 'right'
            if self.last_folder:
                
                self.render_view(self.last_folder)
                
                self.is_pointing = True
                self.last_folder = None
            
        elif i > -0.2:
            self.position = 'up'
            if self.download and not self.is_pointing:
                console.alert(str(self.download))
                self.is_pointing = True
                 
        else:
            self.position = None
            self.is_pointing = False

        
    def estimate_download(self, sender_data) -> int:
        x_old = 0
        data = []
        time = int(interval/5)
        
        # TODO: Instead of using the View name as the display, use something else, and not a print statment, this is temporary
        print(f'Estimating, wait {time} second(s)')
        
        for y in range(time):
            sleep(1)
            
            x: int = int(os.stat(f'./output/{sender_data.name}').st_size)
            bytes: int = x-x_old
            data.append(bytes)
            x_old = x
        
        avg = averg(data)
        self.avg.append(avg)
        
        return avg
            
    def check_download_status(self, sender) -> None:
        self.nas.start_dir_size_calc(f'{self.name}/{sender.name}')
        
        size: int = int(self.nas.get_dir_status()['data']['total_size'])
        scnd_counter = start = counter = 0
        estimate = None
        current_size = 0
        
        while round(current_size*100) != 100:
            sleep(0.1)
            if scnd_counter % int(interval) == 0 and not blunt:
                estimate = self.estimate_download(sender)
                scnd_counter += 1
                counter = 0

 
            elif counter == 10:
                try:
                    downloaded: int = int(os.stat(f'./output/{str(sender.name).split("/")[-1]}').st_size)
                    bytes: int = estimate or int(downloaded-start)
                    data_per_second: str = s(bytes, system=verbose)

                    current_size: int = downloaded/size
                    time_estimate: str = str((int(size-downloaded)/int(bytes))/60)
                                        
                    self.download = f'{data_per_second}\S | {time_estimate.split(".")[0]} Minutes & {time_estimate.split(".")[1][0:2]} Remaining | {str(round(current_size*100))}% Finished'
                    
                    counter = 0
                    start = downloaded
                    scnd_counter += 1
                except ZeroDivisionError:
                    pass
                
            else:
                counter += 1
        
        self.download = False
        avg_speed = s(averg(self.avg), system=verbose)
        console.alert(f'Finished Download, average download speed was {avg_speed}') 
    
    @ui.in_background
    def context_menu(self, sender):
        if not self.photoview:
            items = ['Download', 'Delete', 'Rename', 'Open', 'Info'] if not sender.title == 'True' else ['Delete', 'Rename', 'Open', 'Info']
            option = dialogs.list_dialog(title=sender.name, items=items)
        
            
            if option == 'Delete':
                self.delete_file(sender)
            elif option == 'Rename':
                self.rename_file(sender)
            elif option == 'Download':
                self.download_file(sender)
            elif option == 'Open':
                self.open_file(sender)
            elif option == 'Info':
                self.get_infomation(sender)
    
    def get_infomation(self, sender):
        try:
            self.nas.start_dir_size_calc(f'{self.name}/{sender.name}')
            filesize = self.nas.get_dir_status()['data']['total_size']
            
            console.alert(f'{sender.name}\n{s(filesize, system=verbose)}\n{self.name}/{sender.name}')
        except Exception as e:
            console.alert(e)
            
    
    def display_central_text(self):
        off = self.off
        self.subviews[0].text = self.text
        
        ui.animate(self.animation_off if off else self.animation_on, animation_length)
        ui.animate(self.animation_off_ld if not off else self.animation_on_ld, animation_length)
        
    def rename_file(self, sender_data):
        name = str(console.input_alert('Please chose new name.'))
        print(f'{self.name}/{sender_data.name}', name)
        
        self.nas.rename_folder(f'{self.name}/{sender_data.name}', name)
    
        self.render_view(self.name)
        
    @ui.in_background    
    def delete_file(self, sender_data):
        console.hud_alert(f'Deleted "{sender_data.name}"')
        self.nas.start_delete_task(f'{self.name}/{sender_data.name}')
        
        self.render_view(self.name)
    
    def download_file(self, sender_data):
        path = f'{self.name}/{sender_data.name}'
        Thread(target=self.nas.get_file, args=(path,), name='a').start()
        console.hud_alert(f'Downloading "{sender_data.name}"')
        Thread(target=self.check_download_status, args=(sender_data,), name='b').start()
    
    def display_media(self, path: str):
        if path.split('.')[-1] in unicode_file:
            console.open_in(path)
        else:
            console.quicklook(path)
    
    def get_key_commands(self):
        return [{'input': 'q'}, {'input': 'e'}]
    
    def key_command(self, sender):
        if sender['input'] == 'q':
            self.go_back()
        elif sender['input'] == 'e' and self.last_folder:
            self.render_view(self.last_folder)
    
    def import_foreign_media(self):
        
        path = self.name
        self.off = True
        self.text = 'Wait.'
        
        ui.animate(self.display_central_text, animation_length)
        
        images = photos.pick_asset(title='Pick Media', multi=True) 
        path = self.name
        
        if os.path.isdir('./cache'):
            shutil.rmtree('./cache')
            
        os.mkdir('./cache')
       
        if images and len(images) <= 10:
            
            for photo in images:
                fn = str(photo.local_id).split('/')[0]
                bytes = photo.get_image_data()
                
                with open(f'./cache/{fn}.jpg', 'wb') as temp_file:
                    for ch in bytes:
                        temp_file.write(ch)
            
            for img in os.listdir('./cache'):
                self.nas.upload_file(path, f'./cache/{img}')
                
            shutil.rmtree('./cache')
            
        elif not images:
            pass
        else:
            console.hud_alert('Cannot download more than 10 local images at a time.', 'error')
        
        self.render_view(path)  
                                         
    @ui.in_background
    def open_file(self, sender_data, file=None):
        try:
            os.mkdir('output')
        except FileExistsError:
            pass
        finally:
            
            status = self.nas.get_file_info(sender_data.name) if file else False
            f = True if file and not status['data']['files'][0]['isdir'] else False
            true_name = sender_data.name if not f else sender_data.title
            true_path = f'{self.name}/{sender_data.name}' if not f else sender_data.name
            
            folder_bool = self.nas.get_file_info(true_path)['data']['files'][0]['isdir']
            
            if sender_data.title == 'False' or not folder_bool:
                
                
                link = self.nas.get_download_url(true_path)
                file_extension = str(true_name).split('.')[-1].lower() 
                
                if file_extension in photo_extensions+unicode_file+special_extensions:
                    
                    with open(true_name, 'wb') as file:
                        with io.BytesIO(requests.get(link).content) as data:
                            file.write(data.getvalue())
                
                    if file_extension in photo_extensions+special_extensions:
                        console.quicklook(true_name)
                    else:
                        with open(true_name, 'r') as r_file:
                            dialogs.text_dialog(title=true_name, text=r_file.read())
                        
                    os.remove(true_name)
                    sender_data.enabled = True 
                    
                else:
                    console.alert('Cannot open this file.')
                    
            else:
                files = self.nas.get_file_list(true_path)['data']['files']
                self._files = (file['name'] for file in files if not file['isdir'] and str(file['name'].split('.')[-1]).lower() in photo_extensions+special_extensions)
                
                c = (file['name'] for file in files if not file['isdir'] and str(file['name'].split('.')[-1]).lower() in photo_extensions+special_extensions)
                c = [item for item in c]
                
                self._s_dir = sender_data.name
                
                if bool(c):
                    console.hud_alert("Please Wait...", 'success', 2)
            
                    self.photoview = True
                    PhotoView(main=self).present('full_screen')
                else:
                    self.render_view(true_path)

                    


# PhotoView class: only used when opening a folder
class PhotoView(ui.View):
    def __init__(self, main: SInteractivePanel): # Initialise PhotoView
        
        self.update_interval = 0.1 if motion_controls else 0 # Call class mathod update every tenth of a second
        self.main_class = main # Make it so SInteractivePanel (main class) can be refered too
        self.files = [file for file in self.main_class._files] # Make a list of the filenames, from directory we are currently in
        self.reletive_position = 0 # What file we are in currently, will start at the first file of the directory
        
        self.loading = False
        self.imgs = [] # Image Metadata
        self.filenames = []
        self.flag = False # Flag for scrolling through images
        
        self.get_image(main.nas.get_download_url(f'{main.name}/{main._s_dir}/{self.files[self.reletive_position]}'),self.files[self.reletive_position]) # Download first Image to be displayed
        self.photo_view = ui.ImageView(image=self.imgs[0], width=710, height=710) # Initialise the ImageView

        self.add_subview(self.photo_view) # Add as a subview
        
        for x in range(self.reletive_position+1, len(self.files)): # Iterate for every file in the directory (that is an image)
            try:
                Thread(target=self.get_image, args=(main.nas.get_download_url(f'{main.name}/{main._s_dir}/{self.files[x]}'), self.files[x],)).start() # Download the Image
            except IndexError: # Dunno why this exception in here, thoughts it may break
                break
    
    def get_image(self, url, fn): # Downloads an Image
        
        with io.BytesIO(requests.get(url).content) as b: # Download Image from URL
            img = ui.Image.from_data(b.getvalue(), 3) # Translate bytes into _ui.Image
        
        self.filenames.append(fn)
        self.imgs.append(img) 
    
    def animation_on_(self): # Turns on the screen, do NOT call directly if you want a smooth transition
        for x in range(0, 10):
            self.photo_view.alpha += .1
        self.loading = False
            
    def animation_off_(self): # Turns off the screen, do NOT call directly if you want a smooth transition
        for _ in range(10):
            self.photo_view.alpha -= .1
    
    def anime_on_buffer(self): # Is a buffer for turning on the screen
        ui.animate(self.animation_on_, .3)
        
    def show(self): # Call directly if you want no switch animation, rmember to change self.s_img to a _ui.Image type
        self.photo_view.image = self.s_img
        
    def display_new(self, img: ui.Image, pos): # Displays images onto screen
        
        self.loading = True
        self.s_img = img
        self.name = self.filenames[pos]
        
        ui.animate(self.animation_off_, animation_length) # Make PhotoView fully transparent, so the image can change gracefully
        ui.delay(self.show, animation_length) # Actually display new image
        ui.delay(self.anime_on_buffer, 0.7) # Turn on PhotoView
        
    def update(self):
        
        """
        Handles motion controls for PhotoView, but all calculations are done in SinteractivePanel.update
        This is very buggy, and I am looking for a fix / alternative, only works well if the use is sitting / standing still.
        """
        
        # self.flag: Keeps the user from trying to scroll through images too fast
        
        position = self.main_class.position # Get the users tilt
        
        try:
            if position == 'left' and not self.flag:
                
                # If the user tilts the device left (from landscape)
                
                self.display_new(self.imgs[self.reletive_position-1], self.reletive_position-1) # Display leftmost image from the list
                self.reletive_position -= 1
                self.flag = True
                
            elif position == 'right' and not self.flag:
                
                # If the user tilts the device right (from landscape)
                
                self.display_new(self.imgs[self.reletive_position+1], self.reletive_position+1) # Display rightmost image from the list
                self.reletive_position += 1
                self.flag = True 
                
            elif position == 'up' and not self.flag:
                # If the user tilts the device right (from landscape), this does nothing as of now.
                self.flag = True
            
            elif not position:
                self.flag = False # If the user returns the device to a neutral state, reset the self.flag variable
                
        except IndexError:
            
            # If user reaches end of the list of photos, wrap around to first image
            self.reletive_position = 0
            self.display_new(self.imgs[self.reletive_position], 0)
            
    
    def get_key_commands(self):
        return [{'input': 'right'}, {'input': 'left'}, {'input': 's'}, {'input': 'x', 'modifiers': 'cmd'}] # Which shortcuts are allowed
    
    def key_command(self, sender):
        try:

            # Handles keyboard input, which was defined in the class method get_key_commands
            if sender['input'] == 'right' and not self.loading:            
                
                # If the user presses the right arrow key, show image to the right of the list
                self.display_new(self.imgs[self.reletive_position+1], self.reletive_position+1)
                self.reletive_position += 1
                
            elif sender['input'] == 'left' and not self.loading:
                
                # If the user presses the left arrow key, show image to the left of the list
                self.display_new(self.imgs[self.reletive_position-1], self.reletive_position-1)
                self.reletive_position -= 1
                
            elif sender['input'] == 's' and not self.loading:
                # Handles letter "s" shortcut
                filename = f'{self.filenames[self.reletive_position]}.png' # Get name of file that is being displayed
                
                # Write a file where the image can be quicklooked
                with open(filename, 'wb') as tmp_file:
                    tmp_file.write(self.photo_view.image.to_png())
                
                console.quicklook(filename) # Display image
                os.remove(filename) # Remove temp file
                
            elif sender['input'] == 'x' and sender['modifiers'] == 'cmd':
                self.close()
                
                    
        except IndexError:
            
            # If user reaches end of the list of photos, wrap around to first image
            self.reletive_position = 0
            self.display_new(self.imgs[self.reletive_position], 0)
    
    def will_close(self):
        self.main_class.photoview = False
            
View = SInteractivePanel() # Make an instance of the main script

View.connect() # Establish connection to NAS
View.present(cfg['orientation'], hide_close_button=True, title_bar_color=title_bar_color, title_color=file_colour) # Display initialised screen content
