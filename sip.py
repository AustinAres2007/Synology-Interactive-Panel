"""
Only Programmed on iPad Pro third generations, has NOT been tested with other models. On latest version of python avalible on Pythonista (Python 3.6)

Made by Austin Ares, 
"nas" module made by https://github.com/N4S4/synology-api go check them out.

PS: Modifications were made to the "nas" module to better support what I am making.
"""

'''
TODO: 
    
    - Features / Changes / Functions
    
    Make files / folders from SiP, (Feature, Done)
    Open text files (text or source code), (Feature, Done)
    Get file infomation (Impliment into PhotoView), (Feature, Done)
    Add keyboard shortcuts for browsing through files, (Feature, Done)
    Add proper login form (Feature, Done)
    Make digital buttons for browsing through directories (Feature, Done)
    Be able to import photos / files from the camera roll and iCloud (Feature, Done)
    Open file by default when tapping on it (Change, Done)
    When going into more options on a folder and tapping "Open" just open the folder, don't return an error (Change, Done)
    When opening an empty directory, there is no indication that the folder is empty, and could be mistaken that SiP has crashed (Change, Done)
    Add digital left / right buttons on PhotoView to navigate through images (Function, Done)
    Add copy and paste ability (Function, Done)
    Add a way to view a download status (Function, Done)
    Add timestamps of when the file was created (Function)
    Add a way to listen to audio within SiP (Function)
    
    - Bugs / Issues

    When logged in with an account that is missing permissions, it returns no graceful error. (Bug, Fixed)
    When spamming Q or E (To go back a directory, or to go forward) when done enough, SiP will freeze. (Bug, Fixed)
    When using motion controls with PhotoView, SiP will also respond to these. (Bug, Fixed)
    When renaming a file, any file, SiP will freeze. (Bug, Fixed)
    Cannot open PDF files. (Bug, Fixed)
    When the remainder of files in a directory is 2, the you can overshoot the files a little bit (Issue, Fixed)
    When switching SiP to portrait mode, the files misalign a little bit (Bug)
    on iPhone, scrolling does not work properly when near the end of a directory (Bug, Fixed)
    When opening / making files with a foreign character (Example: A Chinese or Japanese character) the file cannot open (Bug, Temp Fix)
    The name of a file is not centered properly, this is because the asset for files are smaller than folders (Bug, Fixed)
    When downloading photos to be viewed within ImgView, if the user shuts down pythonista, the files that were being downloaded will be empty, and will still be within ImgView cache (I.E: Corrupted/Empty). And the images that were downloaded would not be updated in the occ.json index. (Major Bug)
    When uploading files en masse, the file IDs can be very similar or identical, it is fine if they are similar, but if they are identical, this will override the last file with the same ID, this is obviouly catastropic as you could be missing 10s or 100s of files from the cache. (Major Bug, Fixed)
    
    - Concepts
    
    * In Cache *
        
        ImgView can save photos for later without having to load them again, I would like to add a system where SiP can tick which photos 
        it has saved in cache
        
        < Issues >
        
        When viewing an image with the same name as another image in the cache, it will load the image in the cache and not the actual image stored. This could be fixed with some type of identifier, but what that will be, I do not know. Possibly a timestamp
        
        < Final Goal >
        
        Make an offline mode, where if you cannot connect to the internet, you can still view photos / files from the cache.
        
'''

import ui
import console 
import os
import dialogs
import io
import requests
import objc_util
import photos
import shutil
import json

from math import floor
from requests.exceptions import ConnectionError
from threading import Thread
from sys import argv, exit
from time import sleep

try:
    import config
    import occ
    
    from hurry.filesize import size as s
    from hurry.filesize import verbose
    from nas import filestation
    from nas.auth import AuthenticationError
    
except ModuleNotFoundError as e:
    print(f'"config", "nas", "hurry" or "occ" module not found.\n\nActual Error: {e}'); exit(1)

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

UIDevice = objc_util.ObjCClass('UIDevice').currentDevice()
orientation = UIDevice.orientation()
    
default_height = h*1/5

files_per_row = cfg['files_per_row']
auto_mode = cfg['auto_mode']
font = (cfg['font'], cfg['font_size'])
interval = cfg['interval']
debug = cfg['debug']
flex = cfg['flex']
spacing = cfg['spacing']
scale = cfg['scale']
offset = cfg['offset']
animation_length = cfg['anime_length']
style = cfg['orientation']

if style == 'panel' and auto_mode:
    offset = 16 if str(UIDevice.model()) == 'iPad' else 50
    scale = 3
    spacing = 50
    files_per_row = 6
    
elif style == 'full_screen' and auto_mode:
    offset = 25
    scale = 3
    spacing = 65
    files_per_row = 3
    
elif style not in ('full_screen', 'panel') and auto_mode:
    console.alert(f'Orientation setting: {style} not supported. Only full_screen, and panel are supported.')
else:
    pass

frame_val = 1020
        

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

print(f' < Debug Config > \n\nSpacing: {spacing}\nFiles Per Row: {files_per_row}\nWidth: {w}\nHeight: {h}\n\n-----\n\n') if debug else None

def make_buttons(*args):

    fpr = args[1][-1]
    
    for subview in args[2].subviews:
        args[2].remove_subview(subview)
        
    old_dim = args[1]
    y = spacing
    
    for i, element in enumerate(args[0]):
        item = ui.Button()
            
        if i % fpr == 0 and i != 0:
            y += 200
            x = args[1][0]
            
        elif args[1]:
            divisor = 0+(1 if fpr <= 3 else (2*(fpr-3)))
            x = (old_dim[2]+old_dim[0]+spacing/divisor) 
        
        item.border_width = int(element[0])
        item.border_color = element[1]
        item.title = element[4]
        item.frame = (x, y, args[1][2], args[1][3]) if i else args[1]
        
        old_dim = item.frame if i else args[1]
    
        item.flex = flex
        item.autoresizing = flex
        item.image = element[5]
        item.tint_color = element[6]
        item.name = element[7]
        item.action = element[2](item)
        
        yield item

offline_contents = 'occ.json'
cache_folder = 'ImgView'

class CacheHandler:
    
    def __init__(self):
        os.mkdir(cache_folder) if not os.path.isdir(f'./{cache_folder}') else None
        self.ids = {}
        
    def _update_id_list(self) -> None:
        try:
            self.ids = {int(file.split('-')[0]): '-'.join(file.split('-')[1:]) for file in os.listdir(f'./{cache_folder}') if str(file).split('.')[-1].lower() in photo_extensions+unicode_file+special_extensions}
        except FileNotFoundError:
            os.mkdir(cache_folder); return self._update_id_list()
            
    def get_all_ids(self) -> list:
        self._update_id_list(); return self.ids
    
    def id_in_list(self, id: int) -> bool:
        self._update_id_list(); return int(id) in list(self.ids) or int(id) == 1 if int(id) else True

    def get_file_from_id(self, id: int) -> str:
        self._update_id_list(); return self.ids[int(id)] if self.id_in_list(int(id)) else 0
     
class SInteractivePanel(ui.View):
    def __init__(self):
        try:
            self.fpr = files_per_row
            self.text = 'Loading'
            self.background_color = background_color # Background color of View
            self.name = root 
            self.flex = flex
            self.frame = (0, 0, frame_val, frame_val)
            self.center = (frame_val/2, frame_val/2)
            
            # Make new scroll view
            
            self.scroll_view = ui.ScrollView()
            self.tint_color = file_colour
 
            self.bnts = []
            self.copied = []
            self.item = self.nas = self.last_folder = None
            self.off = self.photoview = self.load_buffer = self.is_pointing = self.download = False
            
            self.file_display_formula = (frame_val*1/offset, spacing, frame_val/(scale*2), frame_val/(scale*2), self.fpr)
            
            # Define the scrollable area, only done on initialisation, when going through folders, it's done in render_view
            
            self.scroll_view.frame = self.frame
            self.scroll_view.content_size = (w, h)
            self.scroll_view.flex = flex
            
            # Esablish connection, this will continue until script is closed
            
            self.left_button_items = [ui.ButtonItem(image=ui.Image.named('iob:chevron_left_32'), tint_color=file_colour, action=lambda _: self.go_back(), enabled=True), ui.ButtonItem(image=ui.Image.named('typb:Spanner'), tint_color=file_colour, action=lambda _: self.nas_console(), enabled=True)]
            self.right_button_items = [ui.ButtonItem(image=ui.Image.named('typb:Write'), tint_color=file_colour, action=lambda _: self.make_media(), enabled=True), ui.ButtonItem(image=ui.Image.named('typb:Archive'), tint_color=file_colour, action=lambda _: self.import_foreign_media(), enabled=True)]
            

            self.add_subview(ui.Label(name='ld', text=self.text, x=self.center[0], y=self.center[1]/2, alignment=ui.ALIGN_LEFT, font=font,   text_color=file_colour))
            
            
            self.subviews[0].alpha = 0.0
            self.add_subview(self.scroll_view) # Display the files in the root
            
        except ConnectionError: # If no connection
            console.alert('No Connection')
            self.close()
        
    def layout(self):
        self.fpr = floor((self.width-spacing)/(frame_val/(scale*2)))
        self.file_display_formula = (frame_val*1/offset, spacing, frame_val/(scale*2), frame_val/(scale*2), self.fpr)
        
        self.render_view(self.name)
    
    
    def nas_console(self):
        command = console.input_alert('Debug Console')
            
        if command == 'clear':
            
            os.remove(offline_contents)
            shutil.rmtree(f'./{cache_folder}')
            os.mkdir(cache_folder)
            
            print('Cleared ImageView Cache')
                
    def make_media(self):
        if self.offline_mode:
            return console.alert("Cannot make media while in offline mode.")
            
        file_or_folder = console.alert('New', '', 'File', 'Folder')
        name = console.input_alert('Media Name', '')
        
        if file_or_folder == 2:
            self.nas.create_folder(folder_path=self.name, name=name)
            console.hud_alert(f'Made new folder: {name} at {self.name}')
        else:
            text = dialogs.text_dialog(name)
            
            try:
                with open(name, 'w+', encoding='utf-8') as tmp_file:
                    tmp_file.write(text if text else '')
            
                self.nas.upload_file(self.name, name) 
                os.remove(name)
            
                console.hud_alert('Uploaded Successfully')
            except filestation.UploadError:
                console.alert('Upload failed, cannot upload files with foreign letters, in the name of the file or the contents.')
                
        self.render_view(self.name)
        
    def exit(self):
        try:
            self.close()
            self.nas.logout() if not self.offline_mode else None
        except AttributeError:
            return
            
    def connect(self):
        try:

            self.offline_mode = False
            self.cache = CacheHandler()
            self.offline_files = occ.OfflineCacheConstructor(offline_contents)
            self.offline_files.build_offline_structure()
            
            self.nas = filestation.FileStation(url, port, user, passw, secure=True, debug=debug)
            
            self.render_view(root)
        except AuthenticationError:
            console.alert('Invalid username / password')
            self.exit()
            
        except ConnectionError:
            choice = console.alert('No Internet connection, do you want to go into offline mode?', '', 'Yes')
            
            if choice == 1:
                try:
                    self.offline_mode = True
                    
                    if not self.offline_files.files:
                        raise FileNotFoundError('No cache')
                        
                    self.render_view(root)
    
                except FileNotFoundError:
                    console.alert("Offline Cache is empty.")
                    return self.exit()
        
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
                button_metadata = False
                
                path = sender.name if isinstance(sender, ui.Button) else sender
                
                borders = 1 if debug else 0
                ico = lambda nm, is_f: assets['folder'] if is_f else (assets['file'] if nm in unicode_file else (assets['photo'] if nm in photo_extensions else (assets['video'] if nm in video_extensions else (assets['audio'] if nm in audio_extensions else assets['file']))))
                
                
                try:
                    ui.animate(self.animation_off, animation_length)  
                    ui.animate(self.animation_on_ld, animation_length-.1)
                    
                    if not self.offline_mode:
                        contents_d = self.nas.get_file_list(path, additional=['size', 'time']) 
                        contents = contents_d['data']['files']
            
                    else:
                        button_metadata = []
                        f_ids = []
                        
                        for item in self.offline_files.get_content(path[1:], self.offline_files.files):
                            if item:
                                c_data = (False, item) if type(item) == str else (True, list(item)[0])
                                button_metadata.append([borders, file_colour, lambda _: self.render_view, h*1/8, c_data[1], ico(c_data[1].split('.')[-1], c_data[0]), file_colour, f'{path}/{c_data[1]}', c_data[0]])
                                f_ids.append(1 if c_data[0] else int(str(c_data[1]).split('-')[0]))
                        
                except AttributeError:
                    self.exit()
                except KeyError:
                    if contents_d['error']['code'] == 119:
                        console.hud_alert(f'Error, please reload script (Error code 119, cannot be fixed by author. Only Synology can fix this)'); self.exit()
                    else:
                        console.hud_alert(f"you are missing permissions to this directory.", 'error', 3.5); self.exit()
                
                button_metadata = ([borders, file_colour, lambda _: self.render_view, h*1/8, item['name'], ico(item['name'].split('.')[-1], item['isdir']), file_colour, item['path']] for item in contents) if not button_metadata else button_metadata
                
                file_id_list = f_ids if self.offline_mode else [id_stamp['additional']['time']['crtime']+id_stamp['additional']['size'] for id_stamp in contents]
                buttons = make_buttons(button_metadata, self.file_display_formula, self.scroll_view)
                dir_status = {}
                
                for item in button_metadata if self.offline_mode else contents:
                    dir_status[item[4] if self.offline_mode else item['name']] = item[8] if self.offline_mode else item['isdir']
            
                for ind, bnt in enumerate(buttons):
                    id_ = file_id_list[ind]
                    file_label_position_y = 150
                    file_label_position_x = (30 if str(bnt.image.name).endswith('folder.png') else 40)
                
                    file_lable = ui.Label(height=30)
                    self.bnts.append(ui.Button(height=25, width=25))
                    
                    bnt.add_subview(file_lable)
                    bnt.add_subview(self.bnts[ind])
            
                    
                    file_lable.text = bnt.title
                    file_lable.x = file_label_position_x
                    file_lable.y = file_label_position_y-4  
                    file_lable.width = 160-file_lable.x
                    
                    file_lable.font = font
                    file_lable.text_color = file_colour
                    file_lable.flex = flex
                    file_lable.border_width = 1 if debug else 0
                    file_lable.line_break_mode = ui.LB_TRUNCATE_TAIL
                    
                    cache_check = ui.ImageView(image=assets['cache' if self.cache.id_in_list(id_) else 'cache_nf'], height=20, width=25, x=file_label_position_x-25, y=file_label_position_y, border_width=borders)  
                    
                    self.bnts[ind].x = 15
                    self.bnts[ind].y = 5
                    self.bnts[ind].flex = flex
                    self.bnts[ind].border_width = 1 if debug else 0
                    self.bnts[ind].image = assets['opt']
                    self.bnts[ind].title = str(dir_status[bnt.title])
                    self.bnts[ind].name = bnt.title
                    self.bnts[ind].action = lambda _: self.context_menu(self.bnts[ind])
                    
                    bnt.add_subview(cache_check)
                    self.scroll_view.add_subview(bnt)
                
                for o, a in enumerate(self.bnts):
                    a.action = lambda a: self.context_menu(a)    
                    self.scroll_view.subviews[o].add_subview(a)
                    
                i = len(self.scroll_view.subviews)
                r = round(i/self.fpr+i%self.fpr)-(2 if i%self.fpr==2 else 0)
                
                
                self.scroll_view.content_size = (w/self.fpr, (default_height*r)+((200-default_height)*r)+200)
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
            if not self.offline_mode:
                f_data = self.nas.get_file_info(f'{self.name}/{sender.title}', additional=['time', 'size'])['data']['files'][0]['additional']
                f_id = int(f_data['time']['crtime']+f_data['size']) 
            else:
                f_id = sender.title.split('-')[0]
            
            self.open_file(sender, True, f_id)
            
    
    def go_back(self):
        path = '/'.join(str(self.name).split('/')[:-1])
        
        if path:
            self.last_folder = self.name
            self.render_view(path)
        
    def estimate_download(self, sender_data) -> int:
        x_old = 0
        data = []
        time = int(interval/5)
        
        for y in range(time):
            sleep(1)
            
            x: int = int(os.stat(f'./output/{sender_data.name}').st_size)
            bytes: int = x-x_old
            data.append(bytes)
            x_old = x
        
        return averg(data)
            
    def check_download_status(self, sender) -> None:
        self.nas.start_dir_size_calc(f'{self.name}/{sender.name}')
        
        size: int = int(self.nas.get_dir_status()['data']['total_size'])
        current_size = scnd_counter = start = counter = 0
        estimate = None
        
        while round(current_size*100) != 100:
            sleep(0.1)
            if scnd_counter % int(interval) == 0:
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
        console.alert(f'Finished Download') 
    
    @ui.in_background
    def context_menu(self, sender):
        if not self.photoview and not self.offline_mode:
            items = ['Download', 'Delete', 'Rename', 'Open', 'Info', 'Copy', 'Download Status' if self.download else ''] if not sender.title == 'True' else ['Delete', 'Rename', 'Open', 'Info', 'Paste' if self.copied else '']
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
            elif option == 'Copy':
                self.copy_file(sender)
            elif option == 'Paste':
                self.paste_item(sender)
            elif option == 'Download Status':
                self.display_download_status(sender)
        elif self.offline_mode:
            console.alert('Cannot use item actions when in offline mode.')
            
                
                
    @ui.in_background
    def display_download_status(self, *args):
        console.alert(self.download) 
                   
    def paste_item(self, sender):
        self.nas.start_copy_move(self.copied, f'{self.name}/{sender.name}')
        console.hud_alert(f'Copied {len(self.copied)} items to "{self.name}/{sender.name}"', duration=1.0)
 
    def copy_file(self, sender):
        self.copied.append(f'{self.name}/{sender.name}')
        
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
        return [{'input': 'q'}, {'input': 'e'}, {'input': 't', 'modifiers': 'cmd'}]
    
    def key_command(self, sender):
        
        if sender['input'] == 'q':
            self.go_back()
        elif sender['input'] == 'e' and self.last_folder:
            self.render_view(self.last_folder)
        elif sender['input'] == 't' and sender['modifiers'] == 'cmd':
            self.nas_console()
    
    def import_foreign_media(self):
        if self.offline_mode:
            return console.alert('Cannot upload local file to NAS while in offline mode.')
            
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
    def open_file(self, sender_data, file=None, id: int=None):
        
        def open_text(name):
            try:
                with open(name, 'r') as r_file:
                    dialogs.text_dialog(title=name, text=r_file.read())
            except FileNotFoundError:
                # TODO: Test if this actually works.
                
                id = str(os.path.basename(name)).split('-')[0]
                self.offline_files.remove_cache_index('rm', [id])
                         
        try:
            os.mkdir('output')
        except FileExistsError:
            pass
        finally:
                
            true_path = f'{self.name}/{sender_data.name}' if not file else sender_data.name
            true_name = sender_data.name if not file else sender_data.title
            
            if sender_data.title == 'False' or file:
                 
                file_extension = true_name.split('.')[-1].lower() 
                
                if file_extension in photo_extensions+unicode_file+special_extensions:
                    
                    if id and not self.cache.id_in_list(id):
                        if not self.offline_mode:
                            link = self.nas.get_download_url(true_path) 
                            
                            with open(true_name, 'wb') as file:
                                with io.BytesIO(requests.get(link).content) as data:
                                    file.write(data.getvalue())
                            
                            self.offline_files.change_cache_index('ap', [id], [[str(self.name)[1:], f"{id}-{true_name}"]])
                        else:
                            true_name = f"./{cache_folder}/{true_name}"
                            
                        if file_extension in photo_extensions+special_extensions:
                            console.quicklook(true_name)
                        else:
                            open_text(true_name)
                            
                        shutil.move(true_name, f'./{cache_folder}/{id}-{true_name}') if not self.offline_mode else None
                    else:
                        actual_file_ = self.cache.get_file_from_id(id)
                        path = f'./{cache_folder}/{id}-{actual_file_}'
                        
                        if file_extension in photo_extensions+special_extensions:
                            console.quicklook(path)
                        else:
                            open_text(path)
                         
                else:
                    console.alert('Cannot open this file.')
                    
            else:
                files = self.nas.get_file_list(true_path)['data']['files']
                get_files = lambda: (file['name'] for file in files if not file['isdir'] and str(file['name'].split('.')[-1]).lower() in photo_extensions)
                
                self._files = get_files()
                
                c = [item for item in get_files()]
                self._s_dir = sender_data.name
                
                if bool(c):
                    
                    self.img_view = ImgViewMain(self)
                    self.img_view.present(style, title_bar_color=title_bar_color, title_color=file_colour, hide_close_button=True)
                      
                else:
                    self.render_view(true_path)


class ImgViewMain(ui.View):
    def __init__(self, s: SInteractivePanel):
        self.frame = (0, 0, 500, 500)
        self.name = s._s_dir
        self.s = s
        tb = ui.TableView(flex='wh', frame=self.frame)
        tb.data_source = tb.delegate = ImgViewDelegate(sip=s)
        tb.bg_color = background_color
        tb.separator_color = file_colour
        
    
        self.add_subview(tb)   

class ImgViewDelegate(ui.ListDataSource):
        
    def __init__(self, sip: SInteractivePanel):
                
        self.sip = sip
        self.files = [file for file in sip._files]
        self.added_files = []
        self.cache_name = {}
        
        threads = []
        files_id_fetch = sip.nas.get_file_list(f'{sip.name}/{sip._s_dir}', additional=['time', 'size'])['data']['files']
        
        ids = {item_sctr['name']: int(item_sctr['additional']['time']['crtime']+item_sctr['additional']['size']) for item_sctr in files_id_fetch}
        
        file_cache = open(offline_contents, 'r+' if os.path.isfile(offline_contents) else "w+", encoding='utf-8')
        
        try:
            local_cache = json.loads(str(file_cache.read()))
        except json.decoder.JSONDecodeError:
            local_cache = {}
        finally:
            file_cache.truncate(0)
            file_cache.write('{}')
            file_cache.close()
        
        def get_image(url, fn): # Downloads an Image
            if not os.path.isdir(cache_folder):
                os.mkdir(cache_folder)
            
            try:
                main_data = self.sip.nas.get_file_info(f'{self.sip.name}/{self.sip._s_dir}/{fn}', additional=['time', 'size'])['data']['files'][0]['additional']
                unix_stamp = main_data['time']['crtime']
                file_size = main_data['size']
                
                file_id = unix_stamp+file_size
                
                self.cache_name[fn] = f'{file_id}-{fn}'
                
                with open(f'./{cache_folder}/{file_id}-{fn}', 'wb') as file:
                    with io.BytesIO(requests.get(url).content) as b: # Download Image from URL
                        file.write(b.getvalue())
                
                self.added_files.append(fn)
                f = f'{self.sip.name}/{self.sip._s_dir}'
                local_cache[str(file_id)] = [f[1:], f'{file_id}-{fn}']
                
            except requests.exceptions.ChunkedEncodingError:
                console.alert("Could not download file. Did you shut down your iPad\nwhile ImageView was open?")
                self.sip.img_view.close() 
            finally:
                threads.remove(file_id)
        
        for fn in self.files: # Iterate for every file in the directory (that is an image)
            try:
                if not os.path.isfile(f'./{cache_folder}/{ids[fn]}-{fn}'):
                    Thread(target=get_image, args=(sip.nas.get_download_url(f'{sip.name}/{sip._s_dir}/{fn}'), fn,)).start()
                    threads.append(ids[fn])
            
                else:
                    self.cache_name[fn] = f'{ids[fn]}-{fn}'
                    self.added_files.append(fn)
                
            except IndexError: # Dunno why this exception in here, thoughts it may break
                break
        
        def _check_threads():
            while threads:
                sleep(1)
            else: 
                with open(offline_contents, 'w') as write_cache:
                    json.dump(local_cache, write_cache, indent=5)
                    
        Thread(target=_check_threads).start()
        ui.ListDataSource.__init__(self, self.files)

    def tableview_number_of_rows(self, tableview, section):
        return len(self.files)

    def tableview_cell_for_row(self, tableview, section, row):
        cell = ui.TableViewCell()
        cell.text_label.text = self.files[row]
        cell.text_label.text_color = file_colour
        cell.text_label.font = font
        
        cell.background_color = background_color
        cell.selected_background_view = ui.View(background_color=title_bar_color)
        
        return cell
        
    def tableview_title_for_header(self, tableview, section):
        # Return a title for the given section.
        return 'Images'
    
    @ui.in_background
    def tableview_did_select(self, tableview, section, row):
        
        if self.added_files and len(self.added_files)-1 >= row:
            folder_contents = [f'./{cache_folder}/{self.cache_name[file]}' for file in self.added_files]
            console.quicklook(folder_contents)
        else:
            print('This image has not downloaded yet.')
    

View = SInteractivePanel() # Make an instance of the main script

View.connect() # Establish connection to NAS
View.present(style, hide_close_button=True, title_bar_color=title_bar_color, title_color=file_colour) # Display initialised screen content
