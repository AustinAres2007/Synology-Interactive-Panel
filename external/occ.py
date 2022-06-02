from pathlib import Path as _Path
from sip import CacheHandler
from typing import Union

import json as _json
import console

"""
OfflineCacheConstructor file, used for when offline mode is used within SiP.
self note: Try not to edit this again because making this was the hardest thing I have ever programmed (aside from learning the syntax of Obj-C 😂)
"""

class OfflineCacheConstructor:
    
    def __init__(self, cache_file: str, cache_handler: CacheHandler):
        self.cache_file = cache_file
        self.files = None
        self._c_handler = cache_handler
        
    def get_content(self, path: str='', dataset: dict=None, return_error=True, boolean=False, _old_name='root', _identifier=None) -> Union[bool, dict, None]:
        
        dirs = path.split('/')
        x = None
        
        if type(dataset) in [dict, list] and dirs[0]:
            
            if type(dataset) != dict:
                for i, item in enumerate(dataset):
                    x = i if dirs[0] in list(item) else x
                
            if dirs[0] in (dataset if type(dataset) == dict else (dataset[x] if x else [])):

                return self.get_content('/'.join(dirs[1:]), dataset.get(dirs[0]) if type(dataset) == dict else dataset[x].get(dirs[0]), return_error, boolean, dirs[0], _identifier) if not boolean else True
                
            else:
                
                if return_error:
                    return console.alert(f'Could not find key: "{dirs[0]}" Within dictionary name: "{_old_name}" with identifier of {_identifier}')
               
                return False if boolean else {}
        
        return dataset
        
        
    def _build_tree(self, tree_list):
        return {tree_list[0]: [[], self._build_tree(tree_list[1:])]} if tree_list else []
        
    def build_dir(self, folders: list or str, dataset: dict):
        folders = folders if isinstance(folders, list) else _Path(folders).parts # Gets the folders to be made
        
        if folders:
            
            flag = False
            n = 1
            where = ""
            
            for i, fd in enumerate(folders, start=n): # For each new folder in folders
                dir_contents = self.get_content('/'.join(folders[:i-1]), dataset, return_error=False, _identifier='1')
                dir_contents = dir_contents if type(dir_contents) == dict else dir_contents[1]
                
                if fd not in dir_contents:
                    flag = True
                    n = i
                    where = '/'.join(folders[:i-1])
                    
                    break
            
            if flag: # if any folders have been made
                data = self.get_content(where, dataset, _identifier='2')
                try:
                    data[folders[n-1]] = [[], self._build_tree(folders[n:])] # Adds a new folder to the path
                except TypeError:
                    data.append({folders[n-1]: [[], self._build_tree(folders[n:])] }) # Does the same as the try block, but this is only used for the root
                finally: return dataset # Return new structure
                
            return dataset
            
        raise ValueError('folders list argument is empty.')
        
    def dump_at_location(self, file: str, location: str, table: dict):
        
        location += '/' # Appends a slash at the end of the path
        dir = self.get_content(path=location, dataset=table, _identifier='3') # Gets the contents of the given folder
        dir.append(file) # Appends the filename to the folder contents (dir)
        
        return table
    
    def build_offline_structure(self):
        
        """
        
        Builds a dict upon the structure in occ.json.
        You cannot use this file directly, it is only used within sip.py
        
        No arguments can be given to this function.
        
        """
        
        folders = []
        main_data = []
        self._final_dict = {}
        
        def new_cache(): # Writes new occ.json file
            with open(self.cache_file, 'w+') as cr_cache_file:
                _json.dump({}, cr_cache_file, indent=5)
                
        try:
            with open(self.cache_file, 'r') as demo_file: # Only reading
                
                    data: dict = _json.loads(demo_file.read())
                    self.data = data # Main occ.json, unparsed
                    
                    for d, f in data.values():
                        folders.append(d) if d not in folders else None # For all folders in occ.json
                        main_data.append((d, f)) # For all the files in occ.json
                        
        except _json.decoder.JSONDecodeError as e: # This can occur if the user has edited occ.json
            print(f"Cache file corrupted. Erasing and restoring..")
            new_cache() # New cache
            self._c_handler.clear_cache() # Remove all files in the cache
            
        except FileNotFoundError: # If the cache does not exist, make a new one
            new_cache() 
            
        for folder in folders: # for each folder
            self._final_dict = self.build_dir(folder, self._final_dict) # Build a file structure upon each folder
        
        for folder, file in main_data: # Gets each folder & file and deposits it at the given location
            self._final_dict = self.dump_at_location(file, folder, self._final_dict)

    
        self.files = self._final_dict # This is the return value.
        return True
     
    @staticmethod   
    def change_cache_index(cache: str='occ.json', mode: str=None, ids: list=[], *args):
        cache_file = open(cache, 'r+')
        cache_contents: dict = _json.loads(cache_file.read())
        cache_file.truncate(0)
        cache_file.close()
        
        if mode == 'rm':
            for id in ids:
                try:
                    del cache_contents[str(id)]
                except KeyError:
                    continue
                    
        elif mode == 'ap':
            for ind, id in enumerate(ids):
                cache_contents[str(id)] = [args[0][ind][0], args[0][ind][1]]
        
        new_cache_file = open(cache, 'w')    
        _json.dump(cache_contents, new_cache_file, indent=5)
        new_cache_file.close()
