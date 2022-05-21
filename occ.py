from pathlib import Path as _Path
from sip import CacheHandler
from typing import Union

import json as _json
import console

"""
OfflineCacheConstructor file, used for when offline mode is used within SiP.
"""

class OfflineCacheConstructor:
    
    def __init__(self, cache_file: str, cache_handler: CacheHandler):
        self.cache_file = cache_file
        self.files = None
        self._c_handler = cache_handler
        
    def get_content(self, path: str='', dataset: dict=None, return_error=True, boolean=False, seperator: str='/', _old_name='root', _identifier=None) -> Union[bool, dict, None]:
        
        dirs = path.split(seperator)
        x = None
        
        if type(dataset) in [dict, list] and dirs[0]:
            
            if type(dataset) != dict:
                for i, item in enumerate(dataset):
                    x = i if dirs[0] in list(item) else x
                
            if dirs[0] in (dataset if type(dataset) == dict else (dataset[x] if x else [])):

                return self.get_content(seperator.join(dirs[1:]), dataset.get(dirs[0]) if type(dataset) == dict else dataset[x].get(dirs[0]), return_error, boolean, seperator, dirs[0], _identifier=_identifier) if not boolean else True
                
            else:
                
                if return_error:
                    return console.alert(f'Could not find key: "{dirs[0]}" Within dictionary name: "{_old_name}" with identifier of {_identifier}')
               
                return False if boolean else {}
        
        return dataset
        
        
    def _build_tree(self, tree_list):
        return {tree_list[0]: [[], self._build_tree(tree_list[1:])]} if tree_list else []
        
    def build_dir(self, folders: list or str, dataset: dict):
        folders = folders if isinstance(folders, list) else _Path(folders).parts
        
        if folders:
            
            flag = False
            n = 1
            where = ""
            
            for i, fd in enumerate(folders, start=n):
                dir_contents = self.get_content('/'.join(folders[:i-1]), dataset, return_error=False, _identifier='0')
                dir_contents = dir_contents if type(dir_contents) == dict else dir_contents[1]
                
                if fd not in dir_contents:
                    flag = True
                    n = i
                    where = '/'.join(folders[:i-1])
                    
                    break
            
            if flag:
                data = self.get_content(where, dataset, _identifier='1')
                try:
                    data[folders[n-1]] = [[], self._build_tree(folders[n:])]
                except TypeError:
                    data.append({folders[n-1]: [[], self._build_tree(folders[n:])] })
                finally: 
                    return dataset
            return dataset
            
        raise ValueError('folders list argument is empty.')
        
    def dump_at_location(self, file: str, location: str, table: dict):
        
        location += '/'
        dir = self.get_content(path=location, dataset=table, _identifier='3')
        dir.append(file)
        
        return table
    
    def build_offline_structure(self):
        
        folders = []
        main_data = []
        self._final_dict = {}
        
        def new_cache():
            with open(self.cache_file, 'w+') as cr_cache_file:
                _json.dump({}, cr_cache_file, indent=5)
                
        try:
            with open(self.cache_file, 'r') as demo_file:
                
                    data: dict = _json.loads(demo_file.read())
                    self.data = data
                    
                    for d, f in data.values():
                        folders.append(d) if d not in folders else None
                        main_data.append((d, f))
        except _json.decoder.JSONDecodeError as e:
            print(f"Cache file corrupted. (occ.json within where this program is stored)")
            new_cache()
            self._c_handler.clear_cache()
            
        except FileNotFoundError:
            new_cache()
            
        for folder in folders:
            self._final_dict = self.build_dir(folder, self._final_dict)
        
        for folder, file in main_data:
            self._final_dict = self.dump_at_location(file, folder, self._final_dict)

    
        self.files = self._final_dict
        return True
        
    def change_cache_index(self, mode: str=None, ids: list=[], *args):
        cache_file = open(self.cache_file, 'r+')
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
                
        new_cache_file = open(self.cache_file, 'w')    
        _json.dump(cache_contents, new_cache_file, indent=5)
        new_cache_file.close()

if __name__ == '__main__':
    print("Commensing run test.")
    
    test_obj = OfflineCacheConstructor("occ.json")
    test_obj.build_offline_structure()
    
    _path = input('Please input a path to commence final test upon: ')

    print(f"FINAL TEST FROM PATH: {_path}\n\n: {test_obj.get_content(_path, test_obj.files)}")
    
    
