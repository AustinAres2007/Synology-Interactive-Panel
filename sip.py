"""

Only Programmed on iPad Pro third generations, has NOT been tested with other models. On latest version of python avalible on Pythonista (Python 3.6)

Made by Austin Ares 
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
    Add digital left / right buttons on PhotoView to navigate through images (Function, Removed)
    Add copy and paste ability (Function, Done)
    Add a way to view a download status (Function, Done)
    Add timestamps of when the file was created (Function, Done)
    Add a way to listen to audio & video within SiP (Function, Done)
    Edit text files (Function)
    Add login infomation to sip-config.cfg (Function)
    Upload files from iCloud / Local storage to NAS (Feature)
    
    - Bugs / Issues

    ? at the end = Possibly fixed.
    
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
    When downloading photos to be viewed within ImgView, if the user shuts down pythonista, the files that were being downloaded will be empty, and will still be within ImgView cache (I.E: Corrupted/Empty). And the images that were downloaded would not be updated in the occ.json index. (Major Bug, Fixed)
    When uploading files en masse, the file IDs can be very similar or identical, it is fine if they are similar, but if they are identical, this will override the last file with the same ID, this is obviouly catastropic as you could be missing 10s or 100s of files from the cache. (Major Bug, Fixed)
    When loading a big files (I'd say over 50 MBs) It loads the file, but there is no indicator, and SiP does not respond. Find a way to fix this. (Issue, Fixed)
    When using ImageView with a lot of files, there can be connection issues and long load times (Issue, Fixed)
    
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

from datetime import datetime
from math import floor
from requests.exceptions import ConnectionError
from threading import Thread
from sys import argv, exit
from time import sleep
from concurrent.futures import ThreadPoolExecutor
from math import pi

try:
    import config
    
    from hurry.filesize import size as s
    from hurry.filesize import verbose, alternative
    from nas import filestation
    from nas.auth import AuthenticationError
    from external import occ, gestures
    
except ModuleNotFoundError as e:
    print(e)
    print(f'"config", "nas", "hurry" or "occ" module not found.\n\nActual Error: {e}'); exit(1)


cfg = config.Config('sip-config.cfg')
w, h = ui.get_screen_size()

mode = ui.get_ui_style()

file_colour = cfg[mode]['fl_color']
background_color = cfg[mode]['bk_color']
title_bar_color = cfg[mode]['tb_color']
file_info_color = cfg[mode]['fi_color']

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

UIDevice = objc_util.ObjCClass('UIDevice')
UIDeviceCurrent = UIDevice.currentDevice()

orientation = UIDeviceCurrent.orientation()

UIImpactFeedbackGenerator = objc_util.ObjCClass('UIImpactFeedbackGenerator').new()
UIImpactFeedbackGenerator.prepare()

default_height = h*1/5

files_per_row = cfg['files_per_row'],
auto_mode = cfg['auto_mode']
interval = cfg['interval']
debug = cfg['debug']
flex = cfg['flex']
spacing = cfg['spacing']
scale = cfg['scale']
offset = cfg['offset']
animation_length = cfg['anime_length']
file_info = cfg['file_info']

font = (cfg['font'], cfg['font_size'])
font_fi = (cfg['font'], cfg['font_size_fi'])

if auto_mode:
    offset = 11 if str(UIDeviceCurrent.model()) == 'iPad' else 50
    scale = 3
    spacing = 80
    files_per_row = 6

frame_val = 880 # Default 880
extra = 50 # Default: 50
f_pos = 150 # Default 150

assets = {os.path.splitext(file)[0]: ui.Image.named(f'{asset_location}/{file}') for file in os.listdir(asset_location) if os.path.splitext(file)[-1].lower()=='.png'}

audio_extensions = ['ogg', 'mp3', 'flac', 'alac', 'wav']
video_extensions = ['mov', 'mp4', 'mkv']
photo_extensions = ['png','jpeg','jpg','heic', 'gif']
unicode_file = ['txt', 'py', 'json', 'js', 'c', 'cpp', 'ini']
special_extensions = ['csv', 'pdf', 'docx']

errors = {
    119: 'Fatal Error, please reload SiP',
    401: 'Path does not exist',
    407: 'Missing permissions to this folder'
}

def make_buttons(*args):

    fpr = args[1][-1]
    
    for subview in args[2].subviews:
        args[2].remove_subview(subview)
        
    old_dim = args[1]
    y = spacing
    
    for i, element in enumerate(args[0]):
        item = ui.Button()
            
        if i % fpr == 0 and i != 0:
            y += f_pos+extra
            x = args[1][0]
            
        elif args[1]:
            divisor = 0+(1 if fpr <= 3 else (2*(fpr-3)))
            x = (old_dim[0]+old_dim[2]+(spacing/divisor)+15) 
        
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
folder_img = 'folder_p.png'
default_tb_args = {'frame': (0,0,400,400), 'separator_color': file_colour, 'bg_color': background_color}

def show_list_dialog(items: list, title_name: str, header: str=None):
    picked = {'picked': None}
    kwargs = default_tb_args
    
    class TableViewDelegate(ui.ListDataSource):
    
        def __init__(self):
            ui.ListDataSource.__init__(self, items)
            
        def tableview_number_of_rows(self, *args):
            return len(items)
            
        def tableview_did_select(self, tableview, section, row):
            picked['picked'] = tableview.data_source.items[row]
            tableview.close()
        
        def tableview_title_for_header(self, *args):
            return header
        
        def tableview_cell_for_row(self, tb, s, r):
            cell = ui.TableViewCell()
            cell.text_label.text = items[r]
            cell.text_label.text_color = file_colour
            cell.text_label.font = font
            
            cell.background_color = background_color
            cell.selected_background_view = ui.View(background_color=title_bar_color)
        
            return cell
            
    tbl = ui.TableView(name=title_name, **kwargs)
    tbl.data_source = tbl.delegate = TableViewDelegate()       

    tbl.present(style='sheet', title_bar_color=title_bar_color, hide_close_button=True, title_color=file_colour)
    tbl.wait_modal()  # This method is what makes this a dialog(modal)
    
    return picked['picked']

class CacheHandler:
    
    def __init__(self):
        os.mkdir(cache_folder) if not os.path.isdir(f'./{cache_folder}') else None
        self.ids = {}
        
    def _update_id_list(self) -> None:
        try:
            self.ids = {int(file.split('-')[0]): '-'.join(file.split('-')[1:]) for file in os.listdir(f'./{cache_folder}') if str(file).split('.')[-1].lower() in photo_extensions+unicode_file+special_extensions+audio_extensions+video_extensions}
        except FileNotFoundError:
            os.mkdir(cache_folder); return self._update_id_list()
            
    def get_all_ids(self) -> list:
        self._update_id_list(); return self.ids
    
    def id_in_list(self, id: int) -> bool:
        self._update_id_list(); return int(id) in list(self.ids) or int(id) == 1 if int(id) else True

    def get_file_from_id(self, id: int) -> str:
        self._update_id_list(); return self.ids[int(id)] if self.id_in_list(int(id)) else 0
    
    @staticmethod
    def check_files():
        try:
            file_ids = []
            for file in os.listdir(f'./{cache_folder}'):
                path = f'./{cache_folder}/{file}'
                if os.stat(path).st_size == 0:
                    os.remove(path)
                    file_ids.append(str(file).split('-')[0])
            
            if file_ids:
                occ.OfflineCacheContructor.change_cache_index(offline_contents, mode='rm', ids=file_ids)
                
        except FileNotFoundError:
            os.mkdir(cache_folder)
    
    @staticmethod
    def clear_cache():
        shutil.rmtree(f'./{cache_folder}')
        os.mkdir(cache_folder)


class SInteractivePanel(ui.View):
    def __init__(self):
        
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
        self.has_loaded = self.off = self.photoview = self.load_buffer = self.download = False    
        
        # Define the scrollable area, only done on initialisation, when going through folders, it's done in render_view
                
        self.scroll_view.frame = self.frame
        self.scroll_view.content_size = (w, h)
        self.scroll_view.flex = flex

        self.file_display_formula = (frame_val*1/offset, spacing, frame_val/(scale*2), frame_val/(scale*2)+extra, self.fpr)
        
        self.order = 'name'
        
        self.left_button_items = [ui.ButtonItem(image=ui.Image.named('iob:chevron_left_32'), tint_color=file_colour, action=lambda _: self.go_back()), ui.ButtonItem(image=ui.Image.named('typb:Grid'), tint_color=file_colour, action=lambda _: self.change_order()), ui.ButtonItem(image=ui.Image.named('typb:Refresh'), tint_color=file_colour, action=lambda _: self.reload_full())]
        
        self.right_button_items = [ui.ButtonItem(image=ui.Image.named('typb:Write'), tint_color=file_colour, action=lambda _: self.make_media()), ui.ButtonItem(image=ui.Image.named('typb:Archive'), tint_color=file_colour, action=lambda _: self.import_foreign_media())]
        
        self.add_subview(self.scroll_view) # Display the files in the root
        gestures.tap(self, lambda *_: self.exit(), 1,2)
        
        self.render_view(root)
    
    def reload_full(self):
        self.layout()
        self.render_view(self.name)
            
    def get_name(self):
        return self.name
        
    def drop(self, *args):
        if self.name != os.path.dirname(args[0]):
            try:
                self.nas.start_copy_move(args[0], self.name)
                self.render_view(self.name)
            except filestation.UploadError:
                console.alert(f'File: "{args[0]}" already exists at this location.')
                 
    def layout(self):
        
        orientation = UIDevice.currentDevice().orientation()
        offset = 20 if orientation != 3 else 10
        
        self.fpr = floor((self.width-spacing)/(frame_val/(scale*2)+15))
        self.file_display_formula = (frame_val*1/offset, spacing, frame_val/(scale*2), frame_val/(scale*2)+extra, self.fpr)
        
            
    
    def change_order(self):
        nas_order = {'File Owner': 'user', 'File Group': 'group', 'File Size': 'size', 'File Name': 'name', 'Creation Time': 'crtime', 'Last Modified': 'mtime', 'Last Accessed': 'atime', 'Last Change': 'ctime', 'POSIX Permissions': 'posix'}
        order = show_list_dialog(list(nas_order), 'Sort files by')
        
        self.order = nas_order[order] if order else self.order
        
    def nas_console(self):
        command = console.input_alert('Debug Console')
            
        if command == 'clear':
            
            os.remove(offline_contents)
            shutil.rmtree(f'./{cache_folder}')
            os.mkdir(cache_folder)
            
            print('Cleared ImageView Cache')
        elif command == 'reload':
            self.render_view(self.name)
            
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
    
    def file_visability_on(self):
        self.scroll_view.alpha = 1.0
    def file_visability_off(self):
        self.scroll_view.alpha = 0.5
        
            
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
            self.cache.check_files()
            self.offline_files = occ.OfflineCacheConstructor(offline_contents, self.cache)
            self.offline_files.build_offline_structure()
            
            self.nas = filestation.FileStation(url, port, user, passw, secure=True, debug=debug)
            
            gestures.drop(self.scroll_view, self.drop, str, 
                animation_func=lambda: ui.animate(self.file_visability_on, duration=0.6), 
                onBegin_func=lambda: ui.animate(self.file_visability_off, duration=0.6)
            )
            
            gestures.long_press(self.scroll_view, lambda data: self.context_menu(**{
            'path': None,
            'data': data,
            'is_folder': None
            }))
            
            gestures.swipe(self.scroll_view, lambda *a: self.go_back(), gestures.LEFT)
            
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
      
    def animation_off_without_transform(self):
        for x in range(10, 0, -1):
            self.scroll_view.alpha = round(x/10)
       

    def animation_off(self):
        self.scroll_view.transform = ui.Transform.scale(0.85, 0.85)
        self.button_tapped.transform = ui.Transform.scale(100.0, 100.0)
 
        
    @ui.in_background
    def render_view(self, sender):
        sender = sender if sender != '/' else root
        if not self.load_buffer:
            if not self.photoview and (isinstance(sender, ui.Button) and sender.image.name.endswith(folder_img)) or isinstance(sender, str):
                bnts = 0
                try:
                    self.load_buffer = True
                    self.left_button_items[0].enabled = False
                    button_metadata = False
                    
                    path = sender.name if isinstance(sender, ui.Button) else sender
                    
                    borders = 1 if debug else 0
                    ico = lambda nm, is_f: assets['folder_p'] if is_f else (assets['file'] if nm in unicode_file else (assets['photo'] if nm in photo_extensions else (assets['video'] if nm in video_extensions else (assets['audio'] if nm in audio_extensions else assets['file']))))
                    
                    
                    try:
                        if isinstance(sender, str):
                            ui.animate(self.animation_off_without_transform, animation_length)
                        else:
                            self.button_tapped = sender
                            
                            ui.animate(self.animation_off_without_transform, animation_length-0.1)
                            self.button_tapped.transform = ui.Transform.scale(1, 1)
                            ui.animate(self.animation_off, animation_length+0.5)                 
                            
                        if not self.offline_mode:
                            contents_d = self.nas.get_file_list(path, additional=['size', 'time'], sort_by=self.order) 
                            contents = contents_d['data']['files']
                
                        else:
                            button_metadata = []
                            f_ids = []
                            
                            for item in self.offline_files.get_content(path[1:], self.offline_files.files):
                                if item:
                                    c_data = (False, item) if type(item) == str else (True, list(item)[0])
                                    button_metadata.append([borders, file_colour, lambda _: self.render_view, h*1/8, c_data[1], ico(c_data[1].split('.')[-1].lower(), c_data[0]), file_colour, f'{path}/{c_data[1]}', c_data[0]])
                                    f_ids.append(1 if c_data[0] else int(str(c_data[1]).split('-')[0]))
                            
                    except AttributeError:
                        self.exit()
                    except KeyError:
                        try:
                            error_code = contents_d['error']['code']
                            console.hud_alert(errors[error_code], 'error')
                        
                        except KeyError:
                            return console.hud_alert(errors[119], 'error')
    
                        else:
                            return self.render_view(os.path.dirname(self.name))
                    except ConnectionError:
                        return console.hud_alert(f"Timed out connection, this prompt will continue until you shutdown the script.", 'error')
                    
                    try:
                        button_metadata = ([borders, file_colour, lambda _: self.render_view, h*1/8, item['name'], ico(item['name'].split('.')[-1].lower(), item['isdir']), file_colour, item['path']] for item in contents) if not button_metadata else button_metadata
                    except UnboundLocalError:
                        return
                        
                    file_id_list = f_ids if self.offline_mode else [id_stamp['additional']['time']['crtime']+id_stamp['additional']['size'] for id_stamp in contents]
                    buttons = make_buttons(button_metadata, self.file_display_formula, self.scroll_view)
                    dir_status = {}
                    
                    for item in button_metadata if self.offline_mode else contents:
                        dir_status[item[4] if self.offline_mode else item['name']] = item[8] if self.offline_mode else item['isdir']
    
                    for ind, bnt in enumerate(buttons):
                        
                        folder = str(bnt.image.name).endswith(folder_img)
                        id_ = file_id_list[ind]
                        borders = 1 if debug else 0
                    
                        file_label_position_y = 145
                        file_label_position_x = (25 if folder else 35)
                        
                        file_lable = ui.Label(height=20, flex=flex, text=bnt.title, text_color=file_colour, border_width=borders, font=font)
                            
                        bnts += 1
                        bnt.add_subview(file_lable)
                        
                        file_lable.x = file_label_position_x
                        file_lable.y = file_label_position_y+10
                        file_lable.width = 160-file_lable.x
                        
                        cache_check = ui.ImageView(image=assets['cache' if self.cache.id_in_list(id_) else 'cache_nf'], height=20, width=25, x=file_label_position_x-26, y=file_label_position_y+10, border_width=borders)  
                        
                        if (not folder and not self.offline_mode) and file_info: 
                            unix_stamp = int(contents[ind]['additional']['time']['crtime'])
            
                            size_lable = ui.Label(height=15, flex=flex, text=s(contents[ind]['additional']['size'], system=alternative), text_color=file_info_color, border_width=borders, font=font_fi)
                            time_lable = ui.Label(height=15, flex=flex, text=str(datetime.fromtimestamp(unix_stamp))[:10], text_color=file_info_color, border_width=borders, font=font_fi)
                            
                            size_lable.x = file_label_position_x
                            time_lable.y = size_lable.y = file_label_position_y+25
                            size_lable.width = 44 
                            
                            time_lable.x = file_label_position_x+45
                            time_lable.width = 80
                            
                            cache_check.y = file_label_position_y+13
                            file_lable.y = file_label_position_y+3
                            
                            bnt.add_subview(size_lable)
                            bnt.add_subview(time_lable)
                    
                        bnt.add_subview(cache_check)
                        self.scroll_view.add_subview(bnt)
                    
                    for o in range(bnts):
                        try:
                            subview = self.scroll_view.subviews[o]
                            is_folder = subview.image.name.endswith(folder_img)
                            
                            gestures.long_press(subview, lambda data: self.context_menu(**{
                                'is_folder': is_folder, 
                                'path': str(data.view.name),
                                'data': data},
                                
                            ), minimum_press_duration=0.5)
                            
                            gestures.drag(
                                subview, 
                                subview.name
                            ) if not is_folder else None
                            
                            def pointerInteraction_styleForRegion_(_self, _cmd, _interaction, _region):
                                return
                           
                            gestures.UIPointer(subview, {
                                "pointerInteraction_willEnterRegion_animator_": subview, 
                                "pointerInteraction_willExitRegion_animator_": subview
                            })
                            
                        except IndexError:
                            return console.alert("Fatal Error")
                            
                          
                    i = len(self.scroll_view.subviews)
                    er = i%self.fpr 
                    r = round(i/self.fpr+er)+1
                    
                    self.scroll_view.content_size = (w/self.fpr, (default_height*r)+(((f_pos-default_height)+extra)*r)+f_pos)
                    self.name = path
                    
                    if not self.scroll_view.subviews:
                        self.scroll_view.add_subview(ui.Label(text='No files', x=self.center[0]*0.9, y=self.center[1]*0.6, alignment=ui.ALIGN_LEFT, font=font, text_color='#bcbcbc'))
                    
                finally:
                    self.load_buffer = False
                    self.left_button_items[0].enabled = True
                    
                    ui.animate(self.animation_on, animation_length)
                    
                    ui.animate(lambda: setattr(self.scroll_view, 'transform', ui.Transform.scale(0.91, 0.91)), animation_length+0.1)
                    ui.animate(lambda: setattr(self.scroll_view, 'transform', ui.Transform.scale(0.95, 0.95)), animation_length)
                    ui.animate(lambda: setattr(self.scroll_view, 'transform', ui.Transform.scale(1, 1)), animation_length+0.5)
                    
            elif sender.image.name.split('.')[-1] in unicode_file+special_extensions+photo_extensions+audio_extensions+video_extensions:
                try:
                    sender.enabled = False
                    if not self.offline_mode:
                        f_data = self.nas.get_file_info(f'{self.name}/{sender.title}', additional=['time', 'size'])['data']['files'][0]['additional']
                        f_id = int(f_data['time']['crtime']+f_data['size']) 
                    else:
                        f_id = sender.title.split('-')[0]
                
                    self.open_file(file=True, **{
                        'id': f_id,
                        'path': f'{self.name}/{sender.title}'
                    })
                finally:
                    sender.enabled = True
                
            
    
    def go_back(self):
        path = '/'.join(str(self.name).split('/')[:-1])
        
        if path:
            self.last_folder = self.name
            self.render_view(path)
        
    def estimate_download(self, file) -> int:
        x_old = 0
        data = []
        time = int(interval/5)
        
        for y in range(time):
            sleep(1)
            
            x: int = int(os.stat(f'./output/{os.path.basename(file)}').st_size)
            bytes: int = x-x_old
            data.append(bytes)
            x_old = x
        
        return max(set(data), key=data.count)
            
    def check_download_status(self, file) -> None:
        size: int = int(self.nas.get_file_info(file, additional=['size'])['data']['files'][0]['additional']['size'])
        current_size = scnd_counter = start = counter = 0
        estimate = None
        
        while round(current_size*100) != 100:
            sleep(0.1)
            if scnd_counter % int(interval) == 0:
                estimate = self.estimate_download(file)
                scnd_counter += 1
                counter = 0

 
            elif counter == 10:
                try:
                    downloaded: int = int(os.stat(f'./output/{os.path.basename(file)}').st_size)
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
        console.hud_alert(f'Finished Download') 
    
    def get_id(self, path: str):
        id_data = self.nas.get_file_info(path, additional=['size', 'time'])['data']['files'][0]['additional']
        return id_data['size']+id_data['time']['crtime']
        
    @ui.in_background
    def context_menu(self,**kwargs):
        
        if kwargs['data'].state != 1:
            return
            
        is_folder = kwargs['is_folder'] 
        path = kwargs['path'] if kwargs['path'] else self.name
    
        UIImpactFeedbackGenerator.impactOccurred()
        
        if not self.photoview and not self.offline_mode:
            items = ['Download', 'Delete', 'Rename', 'Open', 'Copy', 'Download Status' if self.download else ''] if is_folder is False else (['Delete', 'Rename', 'Open', 'Paste'] if is_folder else ['Paste'])
            option = show_list_dialog(items, f'"{os.path.basename(path)}" Options')
            
        
            if option == 'Delete':
                self.delete_file(path)
            elif option == 'Rename':
                self.rename_file(path)
            elif option == 'Download':
                self.download_file(path)
            elif option == 'Open':
                self.open_file(folder=is_folder, **{
                    'id': None if is_folder else self.get_id(kwargs['path']), 
                    'path': path
                })
            elif option == 'Copy':
                self.copied.append(path)
            elif option == 'Paste':
                self.paste_item(path)
            elif option == 'Download Status':
                console.alert(self.download) 
        elif self.offline_mode:
            console.alert('Cannot use item actions when in offline mode.')
                   
    def paste_item(self, path):
        if self.copied:
            try:
                self.nas.start_copy_move(self.copied, path)
                console.alert(f'Copied {len(self.copied)} item(s) to "{path}"')
            except filestation.UploadError:
                console.alert('A file that was being pasted already existed at this location.')
    
    def display_central_text(self):
        off = self.off
        self.subviews[0].text = self.text
        
        ui.animate(self.animation_off if off else self.animation_on, animation_length)
        ui.animate(self.animation_off_ld if not off else self.animation_on_ld, animation_length)
        
    def rename_file(self, file):
        name = str(console.input_alert('Please chose new name.'))
        self.nas.rename_folder(file, name)
    
        self.render_view(self.name)
        
    @ui.in_background    
    def delete_file(self, file):
        console.hud_alert(f'Deleted "{file}"')
        self.nas.start_delete_task(file)
        
        self.render_view(self.name)
    
    def download_file(self, file):
        Thread(target=self.nas.get_file, args=(file,), name='a').start()
        console.hud_alert(f'Downloading "{file}"')
        Thread(target=self.check_download_status, args=(file,), name='b').start()
    
    def get_key_commands(self):
        return [{'input': 'q'}, {'input': 'e'}, {'input': 't', 'modifiers': 'cmd'}, {'input': 'g', 'modifiers': 'cmd'}, {'input': 'v', 'modifiers': 'cmd'}, {'input': 'n', 'modifiers': 'cmd'}]
    
    def key_command(self, sender):
        if sender['input'] == 'q':
            self.go_back()
        elif sender['input'] == 'e' and self.last_folder:
            self.render_view(self.last_folder)
        elif sender['input'] == 't' and sender['modifiers'] == 'cmd':
            self.nas_console()
        elif sender['input'] == 'g' and sender['modifiers'] == 'cmd':
            path = console.input_alert('What path do you want to go to?', '')
            self.render_view(path) if path else None
        elif sender['input'] == 'v' and sender['modifiers'] == 'cmd':
            self.paste_item(self.name)
        elif sender['input'] == 'n' and sender['modifiers'] == 'cmd':
            self.make_media()
        
    
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
    def open_file(self, file=None, **kwargs):
        
        def download_progress(file, ori_size):
            while (os.stat(file).st_size/ori_size)*100 < 100:
                sleep(1)
                
                current_size = os.stat(file).st_size
                print(f'{file} > {round((current_size/ori_size)*100)}%')
        try:
            os.mkdir('output')
        except FileExistsError:
            pass
        finally:
            
            id = kwargs['id']
            true_path = kwargs['path'] 
            true_name = os.path.basename(true_path) 
            
            if file:
                 
                file_extension = true_name.split('.')[-1].lower() 
                
                if file_extension in photo_extensions+unicode_file+special_extensions+video_extensions+audio_extensions:
                    
                    if id and not self.cache.id_in_list(id):
                        if not self.offline_mode: 
                            size = self.nas.get_file_info(true_path, additional=['size'])['data']['files'][0]['additional']['size']
                            download = False
            
                            if size >= 838860800: # 800 MBs
                                return console.alert('This file is too large.')
                                
                            elif size >= 22*(10**6): # 22 MBs
                                format_size = s(int(size), system=alternative)
                                download = console.alert(f'This file is quite large ({format_size}) do you want to download?', '', 'Yes')
                                if not download:
                                    return
                                    
                            with open(true_name, 'w+'):
                                pass
                                
                            Thread(target=download_progress, args=(true_name,size,)).start() if download else None 
                            
                            try:
                                self.nas.get_file(true_path, in_root=True)
                            except requests.exceptions.ChunkedEncodingError:
                                return console.alert("Lost connection, did you shutdown your device while media was downloading?")
                            occ.OfflineCacheConstructor.change_cache_index(offline_contents, 'ap', [id], [[str(self.name)[1:], f"{id}-{true_name}"]])
                        else:
                            true_name = f"./{cache_folder}/{true_name}"
                            
                        console.quicklook(true_name)
                            
                        shutil.move(true_name, f'./{cache_folder}/{id}-{true_name}') if not self.offline_mode else None
                    else:
                        actual_file_ = self.cache.get_file_from_id(id)
                        path = f'./{cache_folder}/{id}-{actual_file_}'
                        
                        console.quicklook(path)
                         
                else:
                    console.alert('Cannot open this file.')
                    
            else:
                files = self.nas.get_file_list(true_path)['data']['files']
                get_files = lambda: (file['name'] for file in files if not file['isdir'] and str(file['name'].split('.')[-1]).lower() in photo_extensions+audio_extensions+video_extensions+special_extensions)
                
                self._files = get_files()
                
                c = [item for item in get_files()]
                self._s_dir = true_name
                
                if bool(c):
                    
                    self.img_view = ImgViewMain(self)
                    self.img_view.present('fullscreen', title_bar_color=title_bar_color, title_color=file_colour, hide_close_button=True)
                      
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
    
        gestures.tap(self, lambda *a: self.close(), 1,2)
        
        self.add_subview(tb)   
    
class ImgViewDelegate(ui.ListDataSource):
    
   
    def __init__(self, sip: SInteractivePanel):
        all_extensions = photo_extensions+audio_extensions+video_extensions
                
        self.sip = sip
        self.files = [file for file in sip._files if str(file).split('.')[-1].lower() in all_extensions]
        self.added_files = []
        self.cache_name = {}
        self.threads_finished = 0
        
        ui.ListDataSource.__init__(self, self.files)
        files_id_fetch = sip.nas.get_file_list(f'{sip.name}/{sip._s_dir}', additional=['time', 'size'])['data']['files']
        
        ids = {item_sctr['name']: int(item_sctr['additional']['time']['crtime']+item_sctr['additional']['size']) for item_sctr in files_id_fetch if item_sctr['name'].split('.')[-1].lower() in all_extensions}
        
        file_cache = open(offline_contents, 'r+' if os.path.isfile(offline_contents) else "w+", encoding='utf-8')
        
        try:
            local_cache = json.loads(str(file_cache.read()))
        except json.decoder.JSONDecodeError:
            local_cache = {}
        finally:
            file_cache.truncate(0)
            file_cache.write('{}')
            file_cache.close()
                    
        def get_image(url, fn, id: int=None): # Downloads an Image
            try:
                filename = f'{id}-{fn}'
                self.cache_name[fn] = filename
                
                with open(f'./{cache_folder}/{filename}', 'wb') as file:
                    try:
                        with io.BytesIO(requests.get(url).content) as b: # Download Image from URL
                            file.write(b.getvalue())
                    except requests.exceptions.ConnectionError:
                        console.alert("I'm sorry but the connection was lost. (Timeout) This can happen while opening too many photos within ImageView, working on a fix.'")
                    else:
                        full_name = f'{self.sip.name}/{self.sip._s_dir}'[1:]
                        self.added_files.append(fn)
                        local_cache[str(id)] = [full_name, filename]
                        
                        self.threads_finished += 1
                        
                        if self.threads_finished >= len(ids):
                            with open(offline_contents, 'w') as write_cache:
                                json.dump(local_cache, write_cache, indent=5)
                
            except requests.exceptions.ChunkedEncodingError:
                console.alert("Could not download file. Did you shut down your iPad\nwhile ImageView was open?")
                self.sip.img_view.close()
        
        if not os.path.isdir(cache_folder):
            os.mkdir(cache_folder)
        
        download_urls = [(sip.nas.get_download_url(f"{sip.name}/{sip._s_dir}/{name}"), name, ids[name]) for name in ids.keys() if int(ids[name]) not in sip.cache.get_all_ids() and name.split('.')[-1].lower() in all_extensions]
        
        self.added_files = [file for file in ids.keys() if ids[file] in sip.cache.get_all_ids()]
        self.cache_name = {file: f"{ids[file]}-{file}" for file in ids.keys() if ids[file] in sip.cache.get_all_ids()}
        
        try:
            tpe = ThreadPoolExecutor(max_workers=8)
            {tpe.submit(get_image, url[0], url[1], url[2]): url for url in download_urls}
            tpe.shutdown(wait=False)
                    
        except Exception as e:
            console.alert(f"Error: {e}")

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
            
if __name__ == '__main__':
    View = SInteractivePanel() # Make an instance of the main script
    
    View.connect() # Establish connection to NAS
    View.present('fullscreen', hide_close_button=True, title_bar_color=title_bar_color, title_color=file_colour) # Display initialised screen content
