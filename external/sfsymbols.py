import ui, clipboard, re, dialogs
from objc_util import *

UIImage = ObjCClass('UIImage')
UIImageSymbolConfiguration = ObjCClass('UIImageSymbolConfiguration')

UIImagePNGRepresentation = c.UIImagePNGRepresentation
UIImagePNGRepresentation.restype = c_void_p
UIImagePNGRepresentation.argtypes = [c_void_p]

#WEIGHTS
ULTRALIGHT, THIN, LIGHT, REGULAR, MEDIUM, SEMIBOLD, BOLD, HEAVY, BLACK = range(1, 10)
# SCALES
SMALL, MEDIUM, LARGE = 1, 2, 3

def SymbolImage(
    name,
    point_size=None, weight=None, scale=None,
    color=None, 
    rendering_mode=ui.RENDERING_MODE_AUTOMATIC
):
    ''' Create a ui.Image from an SFSymbol name. Optional parameters:
        * `point_size` - Integer font size
        * `weight` - Font weight, one of ULTRALIGHT, THIN, LIGHT, REGULAR, MEDIUM, SEMIBOLD, BOLD, HEAVY, BLACK
        * `scale` - Size relative to font size, one of SMALL, MEDIUM, LARGE 
        
    Run the file to see a symbol browser.'''
    objc_image = ObjCClass('UIImage').systemImageNamed_(name)
    conf = UIImageSymbolConfiguration.defaultConfiguration()
    if point_size is not None:
        conf = conf.configurationByApplyingConfiguration_(
            UIImageSymbolConfiguration.configurationWithPointSize_(point_size))
    if weight is not None:
        conf = conf.configurationByApplyingConfiguration_(
            UIImageSymbolConfiguration.configurationWithWeight_(weight))
    if scale is not None:
        conf = conf.configurationByApplyingConfiguration_(
            UIImageSymbolConfiguration.configurationWithScale_(scale))
    objc_image = objc_image.imageByApplyingSymbolConfiguration_(conf)
    
    image = ui.Image.from_data(
        nsdata_to_bytes(ObjCInstance(UIImagePNGRepresentation(objc_image)))
    ).with_rendering_mode(rendering_mode)
    if color:
        image = image.imageWithTintColor_(UIColor.colorWithRed_green_blue_alpha_(*ui.parse_color(color)))
    return image
