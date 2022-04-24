"""
Only Programmed on iPad Pro third generations, has NOT been tested with other models.

Made by Austin Ares, 
"nas" module made by https://github.com/N4S4/synology-api go check them out.

PS: Modifications were made to the "nas" module to better support what I am making.
"""

import ui
import console
import os
import dialogs
import motion
import threading
import io
import requests


from requests.exceptions import ConnectionError
from threading import Thread
from sys import argv
from nas import filestation
from time import sleep
from hurry.filesize import size as s
from hurry.filesize import verbose


w,h = ui.get_screen_size()
root = argv[5]

asset_location = './assets'

folder = ui.Image.named(f'{asset_location}/folder.png')
file = ui.Image.named(f'{asset_location}/file.png')
login = ui.Image.named(f'{asset_location}/login.png')
opt = ui.Image.named(f'{asset_location}/more.png')

averg = lambda data_set: max(set(data_set), key = data_set.count)
contents = lambda dir_c: ((file.title, file.subviews[1].title) for file in dir_c)
    
blunt = False
file_colour = 'black'
default_width = w*1/7
default_height = h*1/5
spacing = 70
font = ('<system>', 17)
interval = 30

photo_extensions = ['png','jpeg','jpg','heic']
unicode_file = ['txt', 'py', 'json', 'js', 'c', 'cpp']

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
        
        item.image = element[5]
        item.tint_color = element[6]
        item.name = element[7]
        item.action = element[2](item)
        
        yield item

class SInteractivePanel(ui.View):
    def __init__(self):
        try:
            self.background_color = '#f5f5f5' # Background color of View
            self.name = root 
            # Make new scroll view
            self.scroll_view = ui.ScrollView()
            
            # Define dimentions
            
            self.update_interval = 0.2
            motion.start_updates() # Start motion updates for update() to use
            
            self.avg = self.bnts = []
            self.last_folder = None
            self.is_pointing = self.download = False
            
            # Define the scrollable area, only done on initialisation, when going through folders, it's done in render_view
            
            self.scroll_view.height = h
            self.scroll_view.width = w
            self.scroll_view.content_size = (w, h)
            self.file_display_formula = (self.width/3, spacing, default_width, default_height)
            
            # Esablish connection, this will continue until script is closed
            
            files = [[1, file_colour, lambda _:self.render_view, h*1/8, 'Login', login, file_colour, root]]
            
            # What buttons to register on start up, only login for now.
            button_contants = [
                [1, 'black', lambda  _:self.render_view, h*1/8, 'Test', (self.x-100, self.y-100, 1, 1),None, file_colour, 'Test']
            ]
            
            buttons = make_buttons(files, self.file_display_formula, self.scroll_view)
            self.scroll_view.content_size = (w, (210*round((len(files)/2)))+spacing) # Actual scrollable size definition
            
            for bnt in buttons: # Add the buttons (Again, only the login button)
                self.scroll_view.add_subview(bnt) 
            
            self.add_subview(self.scroll_view) # Display the files in the root
            
        except ConnectionError: # If no connection
            console.alert('No Connection')
    
    def connect(self):
        self.nas = filestation.FileStation(argv[1], int(argv[2]), argv[3], argv[4], secure=True, debug=True)
    
    def animation_on(self):
        for x in range(0, 10):
            self.scroll_view.alpha = round(x/10)
            
    def animation_off(self):
        for x in range(10, 0, -1):
            self.scroll_view.alpha = round(x/10)  
                
    @ui.in_background
    def render_view(self, sender):
        if (isinstance(sender, ui.Button) and (sender.title == 'Login' or sender.image.name.endswith('folder.png'))) or isinstance(sender, str):
            
            ui.animate(self.animation_off, 0.3)  
            path = sender.name if isinstance(sender, ui.Button) else sender
            
            contents = self.nas.get_file_list(path)['data']['files']
            button_metadata = ([0, file_colour, lambda _: self.render_view, h*1/8, item['name'], file if not item['isdir'] else folder, file_colour, item['path']] for item in contents)
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
                
                self.bnts[ind].x = -20
                self.bnts[ind].y = -35
                self.bnts[ind].width = self.bnts[ind].height = 100
                self.bnts[ind].image = opt
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
            
            ui.animate(self.animation_on, 0.3)
            self.bnts = []
            
    @ui.in_background
    def update(self):
        i = motion.get_attitude()[0]
        y = motion.get_attitude()[1]
        
        if y < -0.15 and not self.is_pointing:
            path = '/'.join(str(self.name).split('/')[:-1])
            self.is_pointing = True
            self.position = 'left'
            
            if path:
                self.last_folder = self.name
                self.render_view(path)
                        
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

        
    def estimate_download(self, sender_data):
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
        
        items = ['Download', 'Delete', 'Rename', 'Open'] if not sender.title == 'True' else ['Delete', 'Rename', 'Open']
        option = dialogs.list_dialog(title=sender.name, items=items)
        
        if option == 'Delete':
            self.delete_file(sender)
        elif option == 'Rename':
            self.rename_file(sender)
        elif option == 'Download':
            self.download_file(sender)
        elif option == 'Open':
            self.open_file(sender)
    
    def rename_file(self, sender_data):
        name = str(console.input_alert('Please chose new name.'))
        self.nas.rename_folder(sender_data.name, name)
        
        self.render_view(self.name)
        
    def delete_file(self, sender_data):
        console.hud_alert(f'Deleted "{sender_data.name}"')
        self.nas.start_delete_task(sender_data.name)
        
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
            
    @ui.in_background
    def open_file(self, sender_data):
        try:
            path = self.name
            os.mkdir('output')
        except FileExistsError:
            pass
        finally:
            
            if sender_data.title == 'False':
                link = self.nas.get_download_url(f'{path}/{sender_data.name}')
                
                with open(sender_data.name, 'wb') as file:
                    with io.BytesIO(requests.get(link).content) as data:
                        file.write(data.getvalue())
                
                console.quicklook(sender_data.name)
                os.remove(sender_data.name)
                    
            else:
                files = self.nas.get_file_list(f'{self.name}/{sender_data.name}')['data']['files']
                self._files = (file['name'] for file in files if not file['isdir'] and str(file['name'].split('.')[-1]).lower() in photo_extensions)
                self._s_dir = sender_data.name
                PhotoView(main=self).present('full_screen')


# PhotoView class: only used when opening a folder
class PhotoView(ui.View):
    def __init__(self, main: SInteractivePanel): # Initialise PhotoView
        
        
        self.update_interval = 0.1 # Call class mathod update every tenth of a second
        self.main_class = main # Make it so SInteractivePanel (main class) can be refered too
        self.files = [file for file in self.main_class._files] # Make a list of the filenames, from directory we are currently in
        self.reletive_position = 0 # What file we are in currently, will start at the first file of the directory
        self.imgs = [] # Images to be displayed
        
        self.flag = False # Flag for scrolling through images
        default_img = self.get_image(main.nas.get_download_url(f'{main.name}/{main._s_dir}/{self.files[self.reletive_position]}')) # Download first Image to be displayed
        self.photo_view = ui.ImageView(image=self.imgs[0], width=710, height=710) # Initialise the ImageView

        self.add_subview(self.photo_view) # Add as a subview
        
        for x in range(self.reletive_position+1, len(self.files)): # Iterate for every file in the directory (that is an image)
            try:
                Thread(target=self.get_image, args=(main.nas.get_download_url(f'{main.name}/{main._s_dir}/{self.files[x]}'),)).start() # Download the Image
            except IndexError: # Dunno why this exception in here, thoughts it may break
                break
    
    def get_image(self, url): # Downloads an Image, and saves it to self.imgs to be displayed
        
        with io.BytesIO(requests.get(url).content) as b: # Download Image from URL
            img = ui.Image.from_data(b.getvalue(), 3) # Translate bytes into _ui.Image, as this is what pythonista can display within ImageView
        
        self.imgs.append(img) 
    
    def animation_on_(self): # Turns on the screen, do NOT call directly if you want a smooth transition
        for x in range(0, 10):
            self.photo_view.alpha += .1
            
    def animation_off_(self): # Turns off the screen, do NOT call directly if you want a smooth transition
        for _ in range(10):
            self.photo_view.alpha -= .1
    
    def anime_on_buffer(self): # Is a buffer for turning on the screen
        ui.animate(self.animation_on_, .3)
        
    def show(self): # Call directly if you want no switch animation, rmember to change self.s_img to a _ui.Image type
        self.photo_view.image = self.s_img
        
    def display_new(self, img: ui.Image): # Displays images onto screen
    
        self.s_img = img
        
        ui.animate(self.animation_off_, .3) # Make PhotoView fully transparent, so the image can change gracefully
        ui.delay(self.show, .3) # Actually display new image
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
                
                self.display_new(self.imgs[self.reletive_position-1]) # Display leftmost image from the list
                self.reletive_position -= 1
                self.flag = True
                
            elif position == 'right' and not self.flag:
                
                # If the user tilts the device right (from landscape)
                
                self.display_new(self.imgs[self.reletive_position+1]) # Display rightmost image from the list
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
            self.display_new(self.imgs[self.reletive_position])
            
    
    def get_key_commands(self):
        return [{'input': 'right'}, {'input': 'left'}, {'input': 's'}] # Which shortcuts are allowed
    
    def key_command(self, sender):
        try:
            # Handles keyboard input, which was defined in the class method get_key_commands
            if sender['input'] == 'right':            
                
                # If the user presses the right arrow key, show image to the right of the list
                self.display_new(self.imgs[self.reletive_position+1])
                self.reletive_position += 1
                
            elif sender['input'] == 'left':
                
                # If the user presses the left arrow key, show image to the left of the list
                self.display_new(self.imgs[self.reletive_position-1])
                self.reletive_position -= 1
                
            elif sender['input'] == 's':
                # Handles letter "s" shortcut
                filename = f'{self.files[self.reletive_position]}.png' # Get name of file that is being displayed
                
                # Write a file where the image can be quicklooked
                with open(filename, 'wb') as tmp_file:
                    tmp_file.write(self.photo_view.image.to_png())
                
                console.quicklook(filename) # Display image
                os.remove(filename) # Remove temp file
                    
        except IndexError:
            
            # If user reaches end of the list of photos, wrap around to first image
            self.reletive_position = 0
            self.display_new(self.imgs[self.reletive_position])
            
            
        
    
    
View = SInteractivePanel() # Make an instance of the main script

View.connect() # Establish connection to NAS
View.present('full_screen') # Display initialised screen content
