"""

Only Programmed on iPad Pro third generations, has NOT been tested with other models. On latest version of python avalible on Pythonista (Python 3.6)

Made by Austin Ares
"nas" module made by https://github.com/N4S4/synology-api go check them out.

PS: Modifications were made to the "nas" module to better support what I am making.
"""

# SiP Started development: 12 April, 2022 :: MFA or SMA (Old version of SiP) Started 16 January 2022

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
    When opening a file, it will try to open it as a folder and SiP will crash (Bug, Fixed)
    When opening a file, Pythonista will crash after downloading the image (Bug, Fixed)

     * Important

        Fix the make file / folder dialogue (Fixed)
        Fix ImageView sorting (Fixed)
        Fix ImageView downloading corruption (Done, but keeping an eye on it)
        When deleting an item, add another animation (Done)
        Open folders in offline mode (Done)
        For better usage with one hand, when in portrait, swipe left for the screen to move over a bit to you can reach more files. (Done)
        when in ImageView, when you tap on a file, actually open the file instead of just the start. (Done?)
        
    - Concepts

    * In Cache *

        ImgView can save photos for later without having to load them again, I would like to add a system where SiP can tick which photos
        it has saved in cache

        < Issues >

        When viewing an image with the same name as another image in the cache, it will load the image in the cache and not the actual image stored. This could be fixed with some type of identifier, but what that will be, I do not know. Possibly a timestamp

        < Final Goal >

        Make an offline mode, where if you cannot connect to the internet, you can still view photos / files from the cache.

'''

# Imports

try:
    import ui
    import console
    import os
    import dialogs
    import io
    import requests
    import objc_util
    import shutil
    import json

    from datetime import datetime
    from math import floor, pi
    from requests.exceptions import ConnectionError
    from threading import Thread
    from sys import argv, exit
    from time import sleep
    from concurrent.futures import ThreadPoolExecutor

    # Imports that are not native to Pythonista

    import config

    from external import occ, gestures
    from external.menu import set_menu, Action
    from external.sfsymbols import SymbolImage

    from hurry.filesize import size as s
    from hurry.filesize import alternative
    from nas import filestation
    from nas.auth import AuthenticationError

except ModuleNotFoundError as e:
    console.alert(str(e))


shutil.rmtree('localImgView', ignore_errors=True)
cfg = config.Config('sip-config.cfg')
w, h = ui.get_screen_size()

mode = ui.get_ui_style()
url = None

# Get login innfomation (Tries to read file args first, then tries config)

try:
    if len(argv) >= 5:
        url, port, user, passw, root = argv[1:]

    elif cfg['login']:
        try:
            url, port, user, passw, root = cfg['login']
        except ValueError:
            console.alert("Missing login infomation from sip-config.cfg"); exit(1)

    if not (url and port and user and root):
        console.hud_alert('One or more of the fields are empty.', 'error'); exit(1)
except config.KeyNotFoundError:
    console.alert('No login infomation found.'); exit(1)

# General Device Infomation

UIDevice = objc_util.ObjCClass('UIDevice')
UIDeviceCurrent = UIDevice.currentDevice()

orientation = UIDeviceCurrent.orientation()

UIImpactFeedbackGenerator = objc_util.ObjCClass('UIImpactFeedbackGenerator').new()
UIImpactFeedbackGenerator.prepare()

# SiP Configuration
required_config_keys = {mode, 'auto_mode', 'interval', 'debug', 'flex', 'spacing', 'scale', 'offset', 'anime_length', 'file_info', 'font', 'font_size', 'font_size_fi', 'files_per_row', 'cache'}

if not set(cfg.as_dict()).issuperset(required_config_keys):
    console.alert("Missing Configuration Keys."); exit(1)

spacing = cfg['spacing']
scale = cfg['scale']
offset = cfg['offset']

font = (cfg['font'], cfg['font_size'])
font_fi = (cfg['font'], cfg['font_size_fi'])

# UI Configuration

if cfg['auto_mode']:
    offset = 11 if str(UIDeviceCurrent.model()) == 'iPad' else 50
    scale = 3
    spacing = 80
    files_per_row = 6

# Global Variables

frame_val, extra, f_pos, default_height = 880, 50, 150, h*1/5

offline_contents, cache_folder, folder_img, asset_location, default_tb_args = 'occ.json', 'ImgView', 'folder_p.png', './assets', {'frame': (0,0,400,400), 'separator_color': cfg[mode]['fl_color'], 'bg_color': cfg[mode]['bk_color']}

assets = {os.path.splitext(file)[0]: ui.Image.named(f'{asset_location}/{file}') for file in os.listdir(asset_location) if os.path.splitext(file)[-1].lower()=='.png'}
audio_extensions = ['ogg', 'mp3', 'flac', 'alac', 'wav']
video_extensions = ['mov', 'mp4', 'mkv']
photo_extensions = ['png','jpeg','jpg','heic', 'gif']
unicode_file = ['txt', 'py', 'json', 'js', 'c', 'cpp', 'ini']
special_extensions = ['csv', 'pdf', 'docx']


# Synology Error Codes

errors = {
    119: 'Fatal Error, please reload SiP.',
    401: 'Path does not exist.',
    407: 'Missing permissions to this folder.',
    408: 'No folder exists with the given path.'
}

# Makes files (buttons) to be displayed within SiP

def make_buttons(*args):

    """
    What arguments should be passed:

        1.Metadata of the buttons
        2.How buttons should be displayed
        3.The SiP Scrollview to edit
        4.The long press function (Which is static)
    """
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

        item.flex = cfg['flex']
        item.autoresizing = cfg['flex']
        item.image = element[5]
        item.tint_color = element[6]
        item.name = element[7]
        item.action = element[2](item)

        yield item

# Shows a list dialog. This is only currently used to change the order of files.

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
            cell.text_label.text_color = cfg[mode]['fl_color']
            cell.text_label.font = font

            cell.background_color = cfg[mode]['bk_color']
            cell.selected_background_view = ui.View(background_color=cfg[mode]['tb_color'])

            return cell

    tbl = ui.TableView(name=title_name, **kwargs)
    tbl.data_source = tbl.delegate = TableViewDelegate()

    tbl.present(style='sheet', title_bar_color=cfg[mode]['tb_color'], hide_close_button=True, title_color=cfg[mode]['fl_color'])
    tbl.wait_modal()  # This method is what makes this a dialog(modal)

    return picked['picked']

# Handles (most) operations of the physical cache (Where saved files go) the offline cache is handled within occ.py (location: in the external folder within the cwd)

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

    def get_id_from_path(self, c, path: str, folder: bool=False):
        self._update_id_list()
        add = ['time', 'size']
        if not folder:
            _ = c.nas.get_file(path, additional=add)['data']['files']['additional']
            return _['time']['crtime']+_['size']
        else:
            folder_raw = c.nas.get_file_list(path, additional=add, sort_by='name')['data']['files']
            return [str(additional['additional']['time']['crtime']+additional['additional']['size']) for additional in folder_raw]


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

# Main SiP Class

class SInteractivePanel(ui.View):
    # Initialisation (from __init__() to connect())
    def __init__(self):

        # Starting point for Sip

        # Sets up varibles and the main file display area (ui.ScrollView())

        self.fpr = cfg['files_per_row']
        self.text = 'Loading'
        self.background_color = cfg[mode]['bk_color'] # Background color of View
        self.name = root
        self.flex = cfg['flex']
        self.frame = (0, 0, frame_val, frame_val)
        self.center = (frame_val/2, frame_val/2)

        # Make new scroll view

        self.scroll_view = ui.ScrollView()
        self.tint_color = cfg[mode]['fl_color']

        self.button_types = {}
        self.forbidden_files = []
        self.bnts = []
        self.copied = []
        self.order = self.item = self.nas = self.last_folder = None
        self.adjusted = self.has_loaded = self.off = self.photoview = self.load_buffer = False

        # Define the scrollable area, only done on initialisation, when going through folders, it's done in render_view

        self.scroll_view.frame = self.frame
        self.scroll_view.content_size = (w, h)
        self.scroll_view.flex = cfg['flex']

        self.file_display_formula = (frame_val*1/offset, spacing, frame_val/(scale*2), frame_val/(scale*2)+extra, self.fpr)

        self.add_subview(self.scroll_view) # Display the files in the root
        gestures.tap(self, lambda *_: self.exit(), 1,2)


        self.left_button_items = [ui.ButtonItem(image=ui.Image.named('iob:chevron_left_32'), tint_color=cfg[mode]['fl_color'], action=lambda _: self.right_handler()), ui.ButtonItem(image=ui.Image.named('typb:Grid'), tint_color=cfg[mode]['fl_color'], action=lambda _: self.change_order()), ui.ButtonItem(image=ui.Image.named('typb:Refresh'), tint_color=cfg[mode]['fl_color'], action=lambda _: self.reload_full())]

        self.right_button_items = [ui.ButtonItem(image=ui.Image.named('typb:Views'), tint_color=cfg[mode]['fl_color'], action=lambda _: gestures.ImagePickerDialogue(self))]
        self.render_view(root)

    # Does quite a lot of the initialisation work. And of course, connects to the NAS, and if it cant, offline mode is enabled.
    def connect(self):
        try:
            @ui.in_background
            def current_folder_options(*args):
                if args[0].state == 1:
                    action = console.alert(f'"{self.name}" Options', '', 'New File', 'New Folder', 'More..')
                    if action in [1, 2]:
                        self.make_media(int(action))
                else:
                    more_actions = console.alert(f'More "{self.name}" Options', '', 'Paste', 'Import File')
                    
                    if more_actions == 1:
                        self.paste_files()
                    else:
                        self.import_file()
                    
            self.offline_mode = False

            self.cache = CacheHandler()
            self.cache.check_files()
            self.offline_files = occ.OfflineCacheConstructor(offline_contents, self.cache)
            self.offline_files.build_offline_structure()

            self.nas = filestation.FileStation(url, int(port), user, passw, secure=True, debug=bool(cfg['debug']))

            gestures.drop(self.scroll_view, self.drop_file, str,
                animation_func=lambda: ui.animate(self.file_visability_on, duration=0.6),
                onBegin_func=lambda: ui.animate(self.file_visability_off, duration=0.6)
            )
            gestures.long_press(self.scroll_view, lambda *args: current_folder_options(*args))
            gestures.swipe(self.scroll_view, lambda *a: self.right_handler(), gestures.RIGHT)
            gestures.swipe(self.scroll_view, lambda *a: self.adjust(), gestures.LEFT)

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

        except TypeError:
            return console.alert('The NAS port contains a character. Numbers only.')

    # System essential stuff (from layout() to exit())
    def layout(self):

        orientation = UIDevice.currentDevice().orientation()
        offset = 20 if orientation != 3 else 10

        self.fpr = floor((self.width-spacing)/(frame_val/(scale*2)+15))
        self.file_display_formula = (frame_val*1/offset, spacing, frame_val/(scale*2), frame_val/(scale*2)+extra, self.fpr)

    def exit(self):
        try:
            self.close()
            self.nas.logout() if not self.offline_mode else None
        except AttributeError:
            return
     
    # Animation Stuff (from file_visability_on() to cannot_move())  
    def file_visability_on(self):
        self.scroll_view.alpha = 1.0
        
    def file_visability_off(self):
        self.scroll_view.alpha = 0.5

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
        self.button_tapped.transform = ui.Transform.scale(100.0, 100.0)#.concat(ui.Transform.rotation(pi/2))
    
    def adjust(self): 
        ui.animate(lambda: setattr(self.scroll_view, 'transform', ui.Transform.translation(-320, 0)), cfg['anime_length']+.1)
        ui.animate(lambda: setattr(self.scroll_view, 'transform', ui.Transform.translation(-335, 0)), cfg['anime_length'])
        ui.animate(lambda: setattr(self.scroll_view, 'transform', ui.Transform.translation(-400, 0)), cfg['anime_length']+.25)
        
        self.adjusted = True
        
    def move_default(self):
        ui.animate(lambda: setattr(self.scroll_view, 'transform', ui.Transform.translation(-310, 0)), cfg['anime_length']+.1)
        ui.animate(lambda: setattr(self.scroll_view, 'transform', ui.Transform.translation(-325, 0)), cfg['anime_length'])
        ui.animate(lambda: setattr(self.scroll_view, 'transform', ui.Transform.translation(0, 0)), cfg['anime_length']+.25)
            
        self.adjusted = False
    
    def delete_animation(self, item):
        def _():
            item.alpha = 0
            
        ui.animate(lambda: setattr(item, 'transform', ui.Transform.scale(1.25, 1.25)), cfg['anime_length']+0.6)
        ui.animate(lambda: setattr(item, 'transform', ui.Transform.rotation(pi*2)), cfg['anime_length'])
        ui.animate(lambda: setattr(item, 'transform', ui.Transform.scale(0.90, 0.90)), cfg['anime_length']+0.25)
        ui.animate(_, cfg['anime_length'])
        ui.animate(lambda: setattr(item, 'transform', ui.Transform.scale(0.50, 0.50)), cfg['anime_length'])
        
    def render_default(self):
        ui.animate(lambda: setattr(self.scroll_view, 'transform', ui.Transform.scale(0.91, 0.91)), cfg['anime_length']+0.1)
        ui.animate(lambda: setattr(self.scroll_view, 'transform', ui.Transform.scale(0.95, 0.95)), cfg['anime_length'])
        ui.animate(lambda: setattr(self.scroll_view, 'transform', ui.Transform.scale(1, 1)), cfg['anime_length']+0.5)

    
    def cannot_move(self):
        ui.animate(lambda: setattr(self.scroll_view, 'transform', ui.Transform.translation(-100, 0)), cfg['anime_length']+0.5)
        ui.animate(lambda: setattr(self.scroll_view, 'transform', ui.Transform.translation(-25, 0)), cfg['anime_length']+0.1)
        ui.animate(lambda: setattr(self.scroll_view, 'transform', ui.Transform.translation(-75, 0)), cfg['anime_length']+0.5)
        ui.animate(lambda: setattr(self.scroll_view, 'transform', ui.Transform.translation(0, 0)), cfg['anime_length']+0.6)
     
    # File Navigation (from render_view() to right_handler())   
    @ui.in_background
    def render_view(self, sender):
        sender = sender if sender != '/' else root
        if not self.load_buffer:
            if not self.photoview and (isinstance(sender, ui.Button) and sender.image.name.endswith(folder_img)) or isinstance(sender, str):
                bnts = 0
                borders = 1 if bool(cfg['debug']) else 0
                try:
                    self.load_buffer = True
                    self.left_button_items[0].enabled = False
                    button_metadata = False

                    path = sender.name if isinstance(sender, ui.Button) else sender

                    ico = lambda nm, is_f: assets[folder_img.split('.')[0]] if is_f else (assets['file'] if nm in unicode_file else (assets['photo'] if nm in photo_extensions else (assets['video'] if nm in video_extensions else (assets['audio'] if nm in audio_extensions else assets['file']))))


                    try:
                        
                        # Todo with animations
                        
                        if isinstance(sender, str):
                            ui.animate(self.animation_off_without_transform, cfg['anime_length'])
                            
                        elif not isinstance(sender, str):
                            self.button_tapped = sender
                            
                            ui.animate(self.animation_off_without_transform, cfg['anime_length']-0.1)
                            ui.animate(self.animation_off, cfg['anime_length']+0.5)
                                
                            self.button_tapped.transform = ui.Transform.scale(1, 1)
                            
                        # Get folder contents
                        if not self.offline_mode:
                            self.button_types = {}

                            contents_d = self.nas.get_file_list(path, additional=['size', 'time'], sort_by=self.order)
                            contents = contents_d['data']['files']

                        else:
                            button_metadata = []
                            f_ids = []

                            for item in self.offline_files.get_content(path[1:], self.offline_files.files):
                                if item:
                                    c_data = (False, item) if type(item) == str else (True, list(item)[0])
                                    button_metadata.append([borders, cfg[mode]['fl_color'], lambda _: self.render_view, h*1/8, c_data[1], ico(c_data[1].split('.')[-1].lower(), c_data[0]), cfg[mode]['fl_color'], f'{path}/{c_data[1]}', c_data[0]])
                                    f_ids.append(1 if c_data[0] else int(str(c_data[1]).split('-')[0]))

                    except AttributeError:
                        self.exit()
                    except KeyError:
                        try:
                            error_code = contents_d['error']['code']
                            console.hud_alert(errors[error_code], 'error')

                        except KeyError:
                            print(error_code)
                            return console.hud_alert(errors[119], 'error')

                        else:
                            return self.render_view(os.path.dirname(self.name))
                    except ConnectionError:
                        return console.hud_alert(f"Timed out connection, this prompt will continue until you shutdown the script.", 'error')

                    try:
                        button_metadata = ([borders, cfg[mode]['fl_color'], lambda _: self.render_view, h*1/8, item['name'], ico(item['name'].split('.')[-1].lower(), item['isdir']), cfg[mode]['fl_color'], item['path']] for item in contents) if not button_metadata else button_metadata
                    except UnboundLocalError:
                        return

                    file_id_list = f_ids if self.offline_mode else [id_stamp['additional']['time']['crtime']+id_stamp['additional']['size'] for id_stamp in contents]
                    
                    buttons = make_buttons(button_metadata, self.file_display_formula, self.scroll_view, self.forbidden_files, file_id_list)
            
                    dir_status = {}
                
                    for item in button_metadata if self.offline_mode else contents:
                        dir_status[item[4] if self.offline_mode else item['name']] = item[8] if self.offline_mode else item['isdir']
                    
                    for ind, bnt in enumerate(buttons):
                        id_ = file_id_list[ind]
                        if str(id_) in self.forbidden_files:
                            continue
                        folder = str(bnt.image.name).endswith(folder_img)
                        self.button_types[bnt.title] = folder

                        file_label_position_y = 145
                        file_label_position_x = (25 if folder else 35)

                        file_lable = ui.Label(height=20, flex=cfg['flex'], text=bnt.title, text_color=cfg[mode]['fl_color'], border_width=borders, font=font)
                        id_label = ui.Label(text=str(id_), alpha=0)
                        
                        bnts += 1
                        bnt.add_subview(file_lable)

                        file_lable.x = file_label_position_x
                        file_lable.y = file_label_position_y+10
                        file_lable.width = 160-file_lable.x

                        cache_check = ui.ImageView(image=assets['cache' if self.cache.id_in_list(id_) else 'cache_nf'], height=20, width=25, x=file_label_position_x-26, y=file_label_position_y+10, border_width=borders)

                        if (not folder and not self.offline_mode) and cfg['file_info']:
                            unix_stamp = int(contents[ind]['additional']['time']['crtime'])

                            size_lable = ui.Label(height=15, flex=cfg['flex'], text=s(contents[ind]['additional']['size'], system=alternative), text_color=cfg[mode]['fi_color'], border_width=borders, font=font_fi)
                            time_lable = ui.Label(height=15, flex=cfg['flex'], text=str(datetime.fromtimestamp(unix_stamp))[:10], text_color=cfg[mode]['fi_color'], border_width=borders, font=font_fi)

                            size_lable.x = file_label_position_x
                            time_lable.y = size_lable.y = file_label_position_y+25
                            size_lable.width = 44

                            time_lable.x = file_label_position_x+45
                            time_lable.width = 80

                            cache_check.y = file_label_position_y+13
                            file_lable.y = file_label_position_y+3

                            bnt.add_subview(size_lable)
                            bnt.add_subview(time_lable)

                        bnt.alpha = 0
                        bnt.transform = ui.Transform.scale(0.70, 0.70)
                        bnt.add_subview(cache_check)
                        bnt.add_subview(id_label)
                        
                        self.scroll_view.add_subview(bnt)
                    
                    ui.animate(self.animation_on, cfg['anime_length'])
                    
                    def get_id(path: str, bnt):
                        try:
                            id_data = self.nas.get_file_info(path, additional=['size', 'time'])['data']['files'][0]['additional']
                            return id_data['size']+id_data['time']['crtime']
                        except AttributeError:
                            return bnt.subviews[-1].text
                        
                    for i, subview in enumerate(self.scroll_view.subviews):
                        try:
                            is_folder = subview.image.name.endswith(folder_img)
                            children = [
                                Action(title='Delete', handler=lambda *args: self.delete_file(f'{path}/{args[0].title}', args[0], args[0].subviews[-1].text), image=SymbolImage('minus.rectangle.portrait'), attributes=Action.DESTRUCTIVE),
                                Action(title='Rename', handler=lambda *args: self.rename_file(f'{path}/{args[0].title}'), image=SymbolImage('pencil')),
                                Action(title='Open', handler=lambda *args: self.open_file(file=not args[0].image.name.endswith(folder_img), **{"id": None if is_folder else get_id(f'{path}/{args[0].title}', args[0]), "path": f'{path}/{args[0].title}'}), image=SymbolImage('filemenu.and.cursorarrow')),
                                Action(title='Copy', handler=lambda *args: self.copied.append(f'{path}/{args[0].title}'), image=SymbolImage('doc.on.doc'))
                            ]

                            if is_folder:
                                del children[4:]
                            if self.offline_mode:
                                children = [children[2]]
                                
                            set_menu(subview, children, long_press=True)

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

                            subview.alpha = 1
                            ui.animate(lambda: setattr(subview, 'transform', ui.Transform.scale(0.91, 0.91)), cfg['anime_length']+0.1)
                            ui.animate(lambda: setattr(subview, 'transform', ui.Transform.scale(0.95, 0.95)), cfg['anime_length'])
                            ui.animate(lambda: setattr(subview, 'transform', ui.Transform.scale(1, 1)), cfg['anime_length']+0.5)

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
                    self.adjusted = self.load_buffer = False
                    self.left_button_items[0].enabled = True
                    
                    
                    self.render_default()
                        
            elif sender.image.name.split('.')[-1] in unicode_file+special_extensions+photo_extensions+audio_extensions+video_extensions:
                try:
                    sender.enabled = False
                    if not self.offline_mode:
                        try:
                            f_data = self.nas.get_file_info(f'{self.name}/{sender.title}', additional=['time', 'size'])['data']['files'][0]['additional']
                            f_id = int(f_data['time']['crtime']+f_data['size'])
                        except requests.exceptions.SSLError:
                            console.alert('Timed out')
                            self.exit()
                    else:
                        f_id = sender.title.split('-')[0]

                    self.open_file(file=True, **{
                        'id': f_id,
                        'path': f'{self.name}/{sender.title}'
                    })
                finally:
                    sender.enabled = True
    
    def change_order(self):
        nas_order = {'File Owner': 'user', 'File Group': 'group', 'File Size': 'size', 'File Name': 'name', 'Creation Time': 'crtime', 'Last Modified': 'mtime', 'Last Accessed': 'atime', 'Last Change': 'ctime', 'POSIX Permissions': 'posix'}
        order = show_list_dialog(list(nas_order), 'Sort files by')

        self.order = nas_order[order] if order else self.order
        
    def reload_full(self):
        self.layout()
        self.render_view(self.name)
        
    def right_handler(self):
        
        if not self.adjusted:
            path = '/'.join(str(self.name).split('/')[:-1])
            
            if path:
                self.last_folder = self.name
                self.render_view(path)
            else:
                self.cannot_move()
        else:
            self.move_default()
        
    # Handles keyboard input (from get_key_commands() to key_command())  
    def get_key_commands(self):
        return [{'input': 'q'}, {'input': 'e'}, {'input': 'g', 'modifiers': 'cmd'}, {'input': 'v', 'modifiers': 'cmd'}, {'input': 'n', 'modifiers': 'cmd'}, {'input': 'c', 'modifiers': 'cmd'}]

    def key_command(self, sender):
        key = sender['input']
        if key == 'q':
            self.right_handler()
        elif key == 'e' and self.last_folder:
            self.render_view(self.last_folder)
        elif key == 'g':
            path = console.input_alert('What path do you want to go to?', '')
            self.render_view(path) if path else None
        elif key == 'v':
            self.paste_files()
        elif key == 'n':
            self.make_media()
        elif key == 'c':
            self.exit()
    
    # Handles file operations (from rename_file() to open_file())
    def rename_file(self, file):
        name = str(console.input_alert('Please chose new name.'))
        self.nas.rename_folder(file, name)

        self.render_view(self.name)

    @ui.in_background
    def delete_file(self, file, button, id):
        
        self.nas.start_delete_task(file)
        self.delete_animation(button)
        self.forbidden_files.append(id)
        console.hud_alert(f'Deleted "{file}"')
    
    def import_file(self):
        try:
            path = dialogs.pick_document(types=['public.data'])
            filename = f'M-{os.path.basename(path)}'
        
            shutil.move(path, filename)
            self.nas.upload_file(self.name, filename)
            os.remove(filename)   
        except TypeError:
            return
    
    def paste_files(self):
        if self.copied:
            try:
                self.nas.start_copy_move(self.copied, self.name)
                console.alert(f'Copied {len(self.copied)} item(s) to "{self.name}"')
            except filestation.UploadError:
                console.alert('A file that was being pasted already existed at this location.')
    
    def drop_file(self, *args):
        if self.name != os.path.dirname(args[0]):
            try:
                self.nas.start_copy_move(args[0], self.name)
                self.render_view(self.name)
            except filestation.UploadError:
                console.alert(f'File: "{args[0]}" already exists at this location.')
              
    def make_media(self, file_or_folder: int):
        if self.offline_mode:
            return console.alert("Cannot make media while in offline mode.")
        name = console.input_alert(f'Media Name', '')

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
                        else:
                            true_name = f"./{cache_folder}/{true_name}"

                        console.quicklook(true_name)
                        if cfg['cache']:
                            occ.OfflineCacheConstructor.change_cache_index(offline_contents, 'ap', [id], [[str(self.name)[1:], f"{id}-{true_name}"]])
                            shutil.move(true_name, f'./{cache_folder}/{id}-{true_name}') if not self.offline_mode else None
                    else:
                        actual_file_ = self.cache.get_file_from_id(id)
                        path = f'./{cache_folder}/{id}-{actual_file_}'

                        console.quicklook(path)

                else:
                    console.alert('Cannot open this file.')

            else:
                if not self.offline_mode:
                    possible_files = self.nas.get_file_list(true_path)
                    files = possible_files['data']['files']
                    get_files = lambda: (file['name'] for file in files if not file['isdir'] and str(file['name'].split('.')[-1]).lower() in photo_extensions+audio_extensions+video_extensions+unicode_file)
    
                    self._files = get_files()
    
                    c = [item for item in get_files()]
                    self._s_dir = true_name
    
                    if bool(c):
                        self._img_folder = cache_folder if cfg['cache'] else 'localImgView'
                        self.img_view = ImgViewMain(self)
                        self.img_view.present('fullscreen', title_bar_color=cfg[mode]['tb_color'], title_color=cfg[mode]['fl_color'], hide_close_button=True)
    
                    else:
                        self.render_view(true_path)
                else:
                    self._s_dir = true_path
                    offline_img_view = ImgViewOffline(self)
                    offline_img_view.present('fullscreen', title_bar_color=cfg[mode]['tb_color'], title_color=cfg[mode]['fl_color'], hide_close_button=True)
                    

# ImageView classes. The main class and the delegate, of which the delegate does most of the work.

class ImgViewMain(ui.View):
    def __init__(self, s: SInteractivePanel):
        self.frame = (0, 0, 500, 500)
        self.name = s._s_dir
        self.s = s

        self.tb = ui.TableView(flex=cfg['flex'], frame=self.frame)
        self.tb.data_source = self.tb.delegate = ImgViewDelegate(sip=s)
        self.tb.bg_color = cfg[mode]['bk_color']
        self.tb.separator_color = cfg[mode]['fl_color']

        gestures.long_press(self, lambda *a: self.close())

        self.add_subview(self.tb)
        
    def will_close(self):    
        shutil.rmtree('localImgView', onerror=self.tb.delegate.write_occ)
        
# ImageView Delegate

class ImgViewDelegate(ui.ListDataSource):


    def __init__(self, sip: SInteractivePanel):
        all_extensions = photo_extensions+audio_extensions+video_extensions+unicode_file

        self.img_folder = sip._img_folder
        self.sip = sip
        self.files = [file for file in sip._files if str(file).split('.')[-1].lower() in all_extensions]
        self.added_files = []
        self.cache_name = {}
        self.threads_finished = 0
        self.ids_in_order = sip.cache.get_id_from_path(sip, f'{sip.name}/{sip._s_dir}', True)

        ui.ListDataSource.__init__(self, self.files)
        files_id_fetch = sip.nas.get_file_list(f'{sip.name}/{sip._s_dir}', additional=['time', 'size'])['data']['files']

        ids = {item_sctr['name']: int(item_sctr['additional']['time']['crtime']+item_sctr['additional']['size']) for item_sctr in files_id_fetch if item_sctr['name'].split('.')[-1].lower() in all_extensions}

        if cfg['cache']:
            file_cache = open(offline_contents, 'r+' if os.path.isfile(offline_contents) else "w+", encoding='utf-8')
            try:
                self.local_cache = json.loads(str(file_cache.read()))
            except json.decoder.JSONDecodeError:
                self.local_cache = {}
            finally:
                file_cache.truncate(0)
                file_cache.write('{}')
                file_cache.close()
        else:
            os.mkdir(self.img_folder)
            self.local_cache = {}
        
        self.temp_cache = {}
        
        def get_image(url, fn, id: int=None): # Downloads an Image
            try:
                filename = f'{id}-{fn}'
                self.cache_name[fn] = filename

                with open(f'./{self.img_folder}/{filename}', 'wb') as file:
                    try:
                        with io.BytesIO(requests.get(url).content) as b: # Download Image from URL
                            file.write(b.getvalue())
                    except requests.exceptions.ConnectionError:
                        console.alert("I'm sorry but the connection was lost. (Timeout) This can happen while opening too many photos within ImageView, working on a fix.'")
                    else:
                        full_name = f'{self.sip.name}/{self.sip._s_dir}'[1:]
                        self.added_files.append(fn)
                        self.temp_cache[str(id)] = [full_name, filename]

                        self.threads_finished += 1
                        
                        if self.threads_finished == len(download_urls):
                            console.hud_alert("Finished Downloading folder.")
                            
            except requests.exceptions.ChunkedEncodingError:
                console.alert("Could not download file. Did you shut down your iPad\nwhile ImageView was open?")
                self.sip.img_view.close()

        if not os.path.isdir(self.img_folder):
            os.mkdir(self.img_folder)

        download_urls = [(sip.nas.get_download_url(f"{sip.name}/{sip._s_dir}/{name}"), name, ids[name]) for name in ids.keys() if int(ids[name]) not in sip.cache.get_all_ids() and name.split('.')[-1].lower() in all_extensions]

        self.added_files = [file for file in ids.keys() if ids[file] in sip.cache.get_all_ids()]
        self.cache_name = {file: f"{ids[file]}-{file}" for file in ids.keys() if ids[file] in sip.cache.get_all_ids()}

        try:
            tpe = ThreadPoolExecutor(max_workers=8)
            {tpe.submit(get_image, url[0], url[1], url[2]): url for url in download_urls}
            tpe.shutdown(wait=False)

        except Exception as e:
            console.alert(f"Error: {e}")
    
    def write_occ(self, *args):
        with open(offline_contents, 'w') as write_cache:
            
            # Not using dict comprehension here because I just have a funny feeling it won't work.
            for key in self.ids_in_order:
                if str(key) in self.temp_cache:
                    self.local_cache[str(key)] = self.temp_cache[str(key)]
            
            json.dump(self.local_cache, write_cache, indent=5)
            
    def tableview_number_of_rows(self, tableview, section):
        return len(self.files)

    def tableview_cell_for_row(self, tableview, section, row):
        cell = ui.TableViewCell(style='subtitle')
        cell.text_label.text = self.files[row]
        cell.text_label.text_color = cfg[mode]['fl_color']
        cell.text_label.font = font
        cell.background_color = cfg[mode]['bk_color']

        cell.selected_background_view = ui.View(background_color=cfg[mode]['tb_color'])

        return cell

    @ui.in_background
    def tableview_did_select(self, tableview, section, row):
        if self.added_files and len(self.added_files)-1 >= row:
            folder_contents = [f'./{self.img_folder}/{self.cache_name[f]}' for f in self.files if f in list(self.cache_name)]
            console.quicklook(folder_contents[row:])
        else:
            print('This image has not downloaded yet.')

# Most of this is just copy & paste from ImgViewMain and the delegate lol, works absolutely fine, so I see no need to change anything (PS: it was just a lot more simple to just make another class than to edit ImgView, ImgView is already complicated enough)

class ImgViewOffline(ui.View):
    def __init__(self, sip):
        self.frame = (0, 0, 500, 500)
        self.name = sip._s_dir
        
        tb = ui.TableView(flex=cfg['flex'], frame=self.frame)
        tb.data_source = tb.delegate = ImgViewOfflineDelegate(sip)
        tb.bg_color = cfg[mode]['bk_color']
        tb.separator_color = cfg[mode]['fl_color']  
        
        gestures.long_press(self, lambda *a: self.close())

        self.add_subview(tb)

class ImgViewOfflineDelegate(ui.ListDataSource):
    def __init__(self, sip):
        self.files = [f'{cache_folder}/{item}' for item in sip.offline_files.get_content(sip._s_dir[1:], sip.offline_files.files) if isinstance(item, str) and item.split('.')[-1] in photo_extensions+audio_extensions+video_extensions+unicode_file]
        ui.ListDataSource.__init__(self, self.files)
        
    def tableview_number_of_rows(self, tableview, section):
        return len(self.files)
    
    def tableview_cell_for_row(self, tableview, section, row):
        cell = ui.TableViewCell(style='subtitle')
        cell.text_label.text = self.files[row]
        cell.text_label.text_color = cfg[mode]['fl_color']
        cell.text_label.font = font
        cell.background_color = cfg[mode]['bk_color']

        cell.selected_background_view = ui.View(background_color=cfg[mode]['tb_color'])

        return cell
      
    @ui.in_background
    def tableview_did_select(self, tableview, section, row):
        console.quicklook(self.files[row:])
        
# If this is the main script, start SiP

if __name__ == '__main__':
    View = SInteractivePanel() # Make an instance of the main script

    View.connect() # Establish connection to NAS
    View.present('fullscreen', hide_close_button=True, title_bar_color=cfg[mode]['tb_color'], title_color=cfg[mode]['fl_color']) # Display initialised screen content
