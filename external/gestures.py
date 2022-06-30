# coding: utf-8

"""
Gestures wrapper for iOS

# Gestures for the Pythonista iOS app
 
This is a convenience class for enabling gestures, including drag and drop
support, in Pythonista UI applications. Main intent here has been to make
them Python friendly, hiding all the Objective-C details.

Run the file on its own to see a demo of the supported gestures.

![Demo image](https://raw.githubusercontent.com/mikaelho/pythonista-gestures/master/gestures.jpg)

## Installation

Copy from [GitHub](https://github.com/mikaelho/pythonista-gestures), or

    pip install pythonista-gestures

with [stash](https://github.com/ywangd/stash).

## Versions:

* 1.3 - Add `first` to declare priority for the gesture, and an option to use
  the fine-tuning methods with ObjC gesture recognizers.
* 1.2 - Add drag and drop support.  
* 1.1 - Add distance parameters to swipe gestures.
* 1.0 - First version released to PyPi. 
  Breaks backwards compatibility in syntax, adds multi-recognizer coordination,
  and removes force press support.

## Usage

For example, do something when user swipes left on a Label:
 
    import gestures

    def swipe_handler(data):
        print(f‘I was swiped, starting from {data.location}')
     
    label = ui.Label()
    gestures.swipe(label, swipe_handler, direction=gestures.LEFT)

Your handler method gets one `data` argument that always contains the
attributes described below. Individual gestures may provide more
information; see the API documentation for the methods used to add different
gestures.
  
* `recognizer` - (ObjC) recognizer object
* `view` - (Pythonista) view that was gestured at
* `location` - Location of the gesture as a `ui.Point` with `x` and `y`
  attributes
* `state` - State of gesture recognition; one of
  `gestures.POSSIBLE/BEGAN/RECOGNIZED/CHANGED/ENDED/CANCELLED/FAILED`
* `began`, `changed`, `ended`, `failed` - convenience boolean properties to 
  check for these states
* `number_of_touches` - Number of touches recognized

For continuous gestures, check for `data.began` or `data.ended` in the handler 
if you are just interested that a pinch or a force press happened.

All of the gesture-adding methods return an object that can be used
to remove or disable the gesture as needed, see the API. You can also remove
all gestures from a view with `remove_all_gestures(view)`.

## Fine-tuning gesture recognition

By default only one gesture recognizer will be successful.

If you just want to say "this recognizer goes first", the returned object
contains an easy method for that:
    
    doubletap(view, handler).first()

You can set priorities between recognizers
more specifically by using the `before` method of the returned object.
For example, the following ensures that the swipe always has a chance to happen
first:
    
    swipe(view, swipe_handler, direction=RIGHT).before(
        pan(view, pan_handler)
    )
    
(For your convenience, there is also an inverted `after` method.)

You can also allow gestures to be recognized simultaneously using the
`together_with` method. For example, the following enables simultaneous panning
and zooming (pinching):
    
    panner = pan(view, pan_handler)
    pincher = pinch(view, pinch_handler)
    panner.together_with(pincher)
    
All of these methods (`before`, `after` and `together_with`) also accept an
ObjCInstance of any gesture recognizer, if you need to fine-tune co-operation
with the gestures of some built-in views.

## Drag and drop

This module supports dragging and dropping both within a Pythonista app and
between Pythonista and another app (only possible on iPads). These two cases
are handled differently:
    
* For in-app drops, Apple method of relaying objects is skipped completely,
  and you can refer to _any_ Python object to be dropped to the target view.
* For cross-app drops, we have to conform to Apple method of managing data.
  Currently only plain text and image drops are supported, in either direction.
* It is also good to note that `ui.TextField` and `ui.TextView` views natively
  act as receivers for both in-app and cross-app plain text drag and drop.

View is set to be a sender for a drap and drop operation with the `drag`
function. Drag starts with a long press, and can end in any view that has been
set as a receiver with the `drop` function. Views show the readiness to receive
data with a green "plus" sign. You can accept only specific types of data;
incompatible drop targets show a grey "forbidden" sign.

Following example covers setting up an in-app drag and drop operation between
two labels. To repeat, in the in-app case, the simple string could replaced by
any Python object of any complexity, passed by reference:
    
    drag(sender_label, "Important data")
    
    drop(receiver_label,
        lambda data, sender, receiver: setattr(receiver, 'text', data),
        accept=str)

See the documentation for the two functions for details.

## Using lambdas

If there in existing method that you just want to trigger with a gesture,
often you do not need to create an extra handler function.
This works best with the discrete `tap` and `swipe` gestures where we do not
need to worry with the state of the gesture.

    tap(label, lambda _: setattr(label, 'text', 'Tapped'))

For continuous gestures, the example below triggers some kind of a hypothetical
database refresh when a long press is
detected on a button.
Anything more complicated than this is probably worth creating a separate
function.
     
    long_press(button, lambda data: db.refresh() if data.began else None)

## Pythonista app-closing gesture

When you use the `hide_title_bar=True` attribute with `present`, you close
the app with the 2-finger-swipe-down gesture. This gesture can be
disabled with:
  
    gestures.disable_swipe_to_close(view)
    
where the `view` must be the one you `present`.

You can also replace the close gesture with another, by providing the
"magic" `close` string as the gesture handler. For example,
if you feel that tapping with two thumbs is more convenient in two-handed
phone use:
  
    gestures.tap(view, 'close', number_of_touches_required=2)

## Other details
 
* Adding a gesture or a drag & drop handler to a view automatically sets 
  `touch_enabled=True` for that
  view, to avoid counter-intuitive situations where adding a gesture
  recognizer to e.g. ui.Label produces no results.
* It can be hard to add gestures to ui.ScrollView, ui.TextView and the like,
  because they have complex multi-view structures and gestures already in
  place.  
"""

__version__ = '1.3'

import ctypes
import functools
import inspect
import os
import os.path
import types
import ui
import dialogs

from sys import exit
from external.menu import Menu, Action
from shutil import rmtree
from objc_util import *
from math import pi

# Recognizer classes (Mickael)
try:
    UITapGestureRecognizer = ObjCClass('UITapGestureRecognizer')
    UILongPressGestureRecognizer = ObjCClass('UILongPressGestureRecognizer')
    UIPanGestureRecognizer = ObjCClass('UIPanGestureRecognizer')
    UIScreenEdgePanGestureRecognizer = ObjCClass('UIScreenEdgePanGestureRecognizer')
    UIPinchGestureRecognizer = ObjCClass('UIPinchGestureRecognizer')
    UIRotationGestureRecognizer = ObjCClass('UIRotationGestureRecognizer')
    UISwipeGestureRecognizer = ObjCClass('UISwipeGestureRecognizer')
    
    # PointerIntergration (Austin)
    UIPointerInteraction = ObjCClass('UIPointerInteraction')
    
    # For Image Picker (Austin)
    SUIViewController = ObjCClass('SUIViewController')
    UIImagePickerController = ObjCClass('UIImagePickerController')    
    
    # For File Picker (Austin)
    UIDocumentPickerViewController = ObjCClass('UIDocumentPickerViewController')
    UTType = ObjCClass('UTType')
    
    # For EditMenus (Legacy & Modern) (Austin)
    UIEditMenuInteraction = ObjCClass('UIEditMenuInteraction')
    UIEditMenuConfiguration = ObjCClass('UIEditMenuConfiguration')
    UIMenuController = ObjCClass('UIMenuController')
    
    #  Drag and drop classes (Mickael)
    NSItemProvider = ObjCClass('NSItemProvider')
    UIDragItem = ObjCClass('UIDragItem')
    UIDragInteraction = ObjCClass('UIDragInteraction')
    UIDropInteraction = ObjCClass('UIDropInteraction')
    UIDropProposal = ObjCClass('UIDropProposal')
    NSItemProvider = ObjCClass('NSItemProvider')
    UIImagePNGRepresentation = c.UIImagePNGRepresentation
    UIImagePNGRepresentation.restype = c_void_p
    UIImagePNGRepresentation.argtypes = [c_void_p]
except:
    console.alert("iOS / iPadOS 16 / macOS Ventura (macOS 13) or newer is needed to run SiP. \n(NOTE: SiP is not programmed for iPhones nor mac, but do work, pretty well on macOS as well.)"); exit(1)

# Constants

# Recognizer states

POSSIBLE = 0
BEGAN = 1
RECOGNIZED = 1
CHANGED = 2
ENDED = 3
CANCELLED = 4
FAILED = 5

# Swipe directions

RIGHT = 1
LEFT = 2
UP = 4
DOWN = 8

# Edge pan, starting edge

EDGE_NONE = 0
EDGE_TOP = 1
EDGE_LEFT = 2
EDGE_BOTTOM = 4
EDGE_RIGHT = 8
EDGE_ALL = 15


class Data():
    """
    Simple class that contains all the data about the gesture. See the Usage
    section and individual gestures for information on the data included. 
    Also provides convenience state-specific properties (`began` etc.).
    (docgen-ignore)
    """
    
    def __init__(self):
        self.recognizer = self.view = self.location = self.state = \
            self.number_of_touches = self.scale = self.rotation = \
            self.velocity = None

    def __str__(self):
        str_states = (
            'possible',
            'began',
            'changed',
            'ended',
            'cancelled',
            'failed'
        )
        result = 'Gesture data object:'
        for key in dir(self):
            if key.startswith('__'): continue
            result += '\n'
            if key == 'state':
                value = f'{str_states[self.state]} ({self.state})'
            elif key == 'recognizer':
                value = self.recognizer.stringValue()
            elif key == 'view':
                value = self.view.name or self.view
            else:
                value = getattr(self, key)
            result += f'  {key}: {value}'
  
        
        return result

    def __repr__(self):
        return f'{type(self)}: {self.__dict__}'

    @property
    def began(self):
        return self.state == BEGAN

    @property
    def changed(self):
        return self.state == CHANGED

    @property
    def ended(self):
        return self.state == ENDED
        
    @property
    def failed(self):
        return self.state == FAILED
            
            
class ObjCPlus:
    """ docgen-ignore """
    
    def __new__(cls, *args, **kwargs):
        objc_class = getattr(cls, '_objc_class', None)
        if objc_class is None:
            objc_class_name = cls.__name__ + '_ObjC'
            objc_superclass = getattr(
                cls, '_objc_superclass', NSObject)
            objc_debug = getattr(cls, '_objc_debug', True)
            
            #'TempClass_'+str(uuid.uuid4())[-12:]
            
            objc_methods = []
            objc_classmethods = []
            for key in cls.__dict__:
                value = getattr(cls, key)
                if (inspect.isfunction(value) and 
                    '_self' in inspect.signature(value).parameters
                ):
                    if getattr(value, '__self__', None) == cls:
                        objc_classmethods.append(value)
                    else:
                        objc_methods.append(value)
            if ObjCDelegate in cls.__mro__:
                objc_protocols = cls.__name__
            else:
                objc_protocols = getattr(cls, '_objc_protocols', [])
            if not type(objc_protocols) is list:
                objc_protocols = [objc_protocols]
            cls._objc_class = objc_class = create_objc_class(
                objc_class_name,
                superclass=objc_superclass,
                methods=objc_methods,
                classmethods=objc_classmethods,
                protocols=objc_protocols,
                debug=objc_debug
            )
        
        instance = objc_class.alloc().init()

        for key in dir(cls):
            value = getattr(cls, key)
            if inspect.isfunction(value):
                if (not key.startswith('__') and 
                not '_self' in inspect.signature(value).parameters):
                    setattr(instance, key, types.MethodType(value, instance))
                if key == '__init__':
                    value(instance, *args, **kwargs)

        return instance

        
class ObjCDelegate(ObjCPlus):
    """ If you inherit from this class, the class name must match the delegate 
    protocol name. (docgen-ignore) """
            
            
def _is_objc_type(objc_instance, objc_class):
    return objc_instance.isKindOfClass_(objc_class.ptr)

class UIGestureRecognizerDelegate(ObjCDelegate):
    """ docgen-ignore """
    
    def __init__(self, recognizer_class, view, handler_func):
        self.view = view
        self.handler_func = handler_func
        self.other_recognizers = []
        
        view.touch_enabled = True

        if handler_func == 'close':
            self.recognizer = replace_close_gesture(view, recognizer_class)
        else:
            self.recognizer = recognizer_class.alloc().initWithTarget_action_(
                self, 'gestureAction').autorelease()
            view.objc_instance.addGestureRecognizer_(self.recognizer)

        retain_global(self)
    
    def gestureAction(_self, _cmd):
        self = ObjCInstance(_self)
        view = self.view
        recognizer = self.recognizer
        handler_func = self.handler_func
        data = Data()
        data.recognizer = recognizer
        data.view = view
        location = recognizer.locationInView_(view.objc_instance)
        data.location = ui.Point(location.x, location.y)
        data.state = recognizer.state()
        data.number_of_touches = recognizer.numberOfTouches()
        
        if (_is_objc_type(recognizer, UIPanGestureRecognizer) or 
        _is_objc_type(recognizer, UIScreenEdgePanGestureRecognizer)):
            trans = recognizer.translationInView_(ObjCInstance(view))
            vel = recognizer.velocityInView_(ObjCInstance(view))
            data.translation = ui.Point(trans.x, trans.y)
            data.velocity = ui.Point(vel.x, vel.y)
        elif _is_objc_type(recognizer, UIPinchGestureRecognizer):
            data.scale = recognizer.scale()
            data.velocity = recognizer.velocity()
        elif _is_objc_type(recognizer, UIRotationGestureRecognizer):
            data.rotation = recognizer.rotation()
            data.velocity = recognizer.velocity()
    
        handler_func(data)
        
    def gestureRecognizer_shouldRecognizeSimultaneouslyWithGestureRecognizer_(
            _self, _sel, _gr, _other_gr):
        self = ObjCInstance(_self)
        other_gr = ObjCInstance(_other_gr)
        return other_gr in self.other_recognizers
        
    @on_main_thread
    def first(self):
        self.recognizer.delaysTouchesBegan = True
        
    @on_main_thread
    def before(self, other):
        other_recognizer = (other.recognizer 
        if isinstance(other, type(self))
        else other)
        other_recognizer.requireGestureRecognizerToFail_(
            self.recognizer)

    @on_main_thread
    def after(self, other):
        other_recognizer = (other.recognizer 
        if isinstance(other, type(self))
        else other)
        self.recognizer.requireGestureRecognizerToFail_(
            other_recognizer)
            
    @on_main_thread
    def together_with(self, other):
        other_recognizer = (other.recognizer 
        if isinstance(other, type(self))
        else other)
        self.other_recognizers.append(other_recognizer)
        self.recognizer.delegate = self

        
#docgen: Gestures

@on_main_thread
def tap(view, action, 
        number_of_taps_required=None, number_of_touches_required=None):
    """ Call `action` when a tap gesture is recognized for the `view`.

    Additional parameters:

    * `number_of_taps_required` - Set if more than one tap is required for
      the gesture to be recognized.
    * `number_of_touches_required` - Set if more than one finger is
      required for the gesture to be recognized.
    """
    handler = UIGestureRecognizerDelegate(UITapGestureRecognizer, view, action)

    recognizer = handler.recognizer
    if number_of_taps_required:
        recognizer.numberOfTapsRequired = number_of_taps_required
    if number_of_touches_required:
        recognizer.numberOfTouchesRequired = number_of_touches_required

    return handler


@on_main_thread
def doubletap(view, action, number_of_touches_required=None):
    """ Convenience method that calls `tap` with a 2-tap requirement.
    """
    return tap(view, action, number_of_taps_required=2, number_of_touches_required=number_of_touches_required)

@on_main_thread
def long_press(view, action,
        number_of_taps_required=None,
        number_of_touches_required=None,
        minimum_press_duration=None,
        allowable_movement=None):
    """ Call `action` when a long press gesture is recognized for the
    `view`. Note that this is a continuous gesture; you might want to
    check for `data.changed` or `data.ended` to get the desired results.

    Additional parameters:

    * `number_of_taps_required` - Set if more than one tap is required for
      the gesture to be recognized.
    * `number_of_touches_required` - Set if more than one finger is
      required for the gesture to be recognized.
    * `minimum_press_duration` - Set to change the default 0.5-second
      recognition treshold.
    * `allowable_movement` - Set to change the default 10 point maximum
    distance allowed for the gesture to be recognized.
    """
    handler = UIGestureRecognizerDelegate(UILongPressGestureRecognizer, view, action)

    recognizer = handler.recognizer
    if number_of_taps_required:
        recognizer.numberOfTapsRequired = number_of_taps_required
    if number_of_touches_required:
        recognizer.numberOfTouchesRequired = number_of_touches_required
    if minimum_press_duration:
        recognizer.minimumPressDuration = minimum_press_duration
    if allowable_movement:
        recognizer.allowableMovement = allowable_movement

    return handler

@on_main_thread
def pan(view, action,
        minimum_number_of_touches=None,
        maximum_number_of_touches=None):
    """ Call `action` when a pan gesture is recognized for the `view`.
    This is a continuous gesture.

    Additional parameters:

    * `minimum_number_of_touches` - Set to control the gesture recognition.
    * `maximum_number_of_touches` - Set to control the gesture recognition.

    Handler `action` receives the following gesture-specific attributes
    in the `data` argument:

    * `translation` - Translation from the starting point of the gesture
      as a `ui.Point` with `x` and `y` attributes.
    * `velocity` - Current velocity of the pan gesture as points per
      second (a `ui.Point` with `x` and `y` attributes).
    """
    handler = UIGestureRecognizerDelegate(UIPanGestureRecognizer, view, action)

    recognizer = handler.recognizer
    if minimum_number_of_touches:
        recognizer.minimumNumberOfTouches = minimum_number_of_touches
    if maximum_number_of_touches:
        recognizer.maximumNumberOfTouches = maximum_number_of_touches

    return handler

@on_main_thread
def edge_pan(view, action, edges):
    """ Call `action` when a pan gesture starting from the edge is
    recognized for the `view`. This is a continuous gesture.

    `edges` must be set to one of
    `gestures.EDGE_NONE/EDGE_TOP/EDGE_LEFT/EDGE_BOTTOM/EDGE_RIGHT
    /EDGE_ALL`. If you want to recognize pans from different edges,
    you have to set up separate recognizers with separate calls to this
    method.

    Handler `action` receives the same gesture-specific attributes in
    the `data` argument as pan gestures, see `pan`.
    """
    handler = UIGestureRecognizerDelegate(UIScreenEdgePanGestureRecognizer, view, action)

    handler.recognizer.edges = edges

    return handler

@on_main_thread
def pinch(view, action):
    """ Call `action` when a pinch gesture is recognized for the `view`.
    This is a continuous gesture.

    Handler `action` receives the following gesture-specific attributes
    in the `data` argument:

    * `scale` - Relative to the distance of the fingers as opposed to when
      the touch first started.
    * `velocity` - Current velocity of the pinch gesture as scale
      per second.
    """
    handler = UIGestureRecognizerDelegate(UIPinchGestureRecognizer, view, action)

    return handler

@on_main_thread
def rotation(view, action):
    """ Call `action` when a rotation gesture is recognized for the `view`.
    This is a continuous gesture.

    Handler `action` receives the following gesture-specific attributes
    in the `data` argument:

    * `rotation` - Rotation in radians, relative to the position of the
      fingers when the touch first started.
    * `velocity` - Current velocity of the rotation gesture as radians
      per second.
    """
    handler = UIGestureRecognizerDelegate(UIRotationGestureRecognizer, view, action)

    return handler

@on_main_thread
def swipe(view, action,
        direction=None,
        number_of_touches_required=None,
        min_distance=None,
        max_distance=None):
    """ Call `action` when a swipe gesture is recognized for the `view`.

    Additional parameters:

    * `direction` - Direction of the swipe to be recognized. Either one of
      `gestures.RIGHT/LEFT/UP/DOWN`, or a list of multiple directions.
    * `number_of_touches_required` - Set if you need to change the minimum
      number of touches required.
    * `min_distance` - Minimum distance the swipe gesture must travel in
      order to be recognized. Default is 50.
      This uses an undocumented recognizer attribute.
    * `max_distance` - Maximum distance the swipe gesture can travel in
      order to still be recognized. Default is a very large number.
      This uses an undocumented recognizer attribute.

    If set to recognize swipes to multiple directions, the handler
    does not receive any indication of the direction of the swipe. Add
    multiple recognizers if you need to differentiate between the
    directions.
    """
    handler = UIGestureRecognizerDelegate(UISwipeGestureRecognizer, view, action)

    recognizer = handler.recognizer
    if direction:
        combined_dir = direction
        if isinstance(direction, list):
            combined_dir = 0
            for one_direction in direction:
                combined_dir |= one_direction
        recognizer.direction = combined_dir
    if number_of_touches_required:
        recognizer.numberOfTouchesRequired = number_of_touches_required
    if min_distance:
        recognizer.minimumPrimaryMovement = min_distance
    if max_distance:
        recognizer.maximumPrimaryMovement = max_distance

    return handler


#docgen: Gesture management

@on_main_thread
def disable(handler):
    """ Disable a recognizer temporarily. """
    handler.recognizer.enabled = False

@on_main_thread
def enable(handler):
    """ Enable a disabled gesture recognizer. There is no error if the
    recognizer is already enabled. """
    handler.recognizer.enabled = True

@on_main_thread
def remove(view, handler):
    ''' Remove the recognizer from the view permanently. '''
    view.objc_instance.removeGestureRecognizer_(handler.recognizer)

@on_main_thread
def remove_all_gestures(view):
    ''' Remove all gesture recognizers from a view. '''
    gestures = view.objc_instance.gestureRecognizers()
    for recognizer in gestures:
        remove(view, recognizer)

@on_main_thread
def disable_swipe_to_close(view):
    """ Utility class method that will disable the two-finger-swipe-down
    gesture used in Pythonista to end the program when in full screen
    view (`hide_title_bar` set to `True`).

    Returns a tuple of the actual ObjC view and dismiss target.
    """
    UILayoutContainerView = ObjCClass('UILayoutContainerView')
    v = view.objc_instance
    while not v.isKindOfClass_(UILayoutContainerView.ptr):
        v = v.superview()
    for gr in v.gestureRecognizers():
        if gr.isKindOfClass_(UISwipeGestureRecognizer.ptr):
            gr.setEnabled(False)
            return v, gr.valueForKey_('targets')[0].target()

@on_main_thread
def replace_close_gesture(view, recognizer_class):
    view, target = disable_swipe_to_close(view)
    recognizer = recognizer_class.alloc().initWithTarget_action_(
        target, sel('dismiss:')).autorelease()
    view.addGestureRecognizer_(recognizer)
    return recognizer


# Drag and drop delegates and helpers

class File:
    """ docgen-ignore """
    
    UTI = 'kUTTypeData'
    
    def __init__(self, path, mode='r', data=None):
        self.path = path
        self.filename = os.path.basename(path)
        self.mode = mode
        self._data = data
    
    @property    
    def data(self):
        if self._data is None:
            with open(self.filename, self.mode) as fp:
                self._data = fp.read()
        return self._data
        
drag_and_drop_prefix = 'py_object_'

def _to_pyobject(item):
    item = ObjCInstance(item)
    try:
        data = item.localObject()
        if data is None: return None
        if not str(data).startswith(drag_and_drop_prefix):
            return None
        address_str = str(data)[len(drag_and_drop_prefix):]
        address = int(address_str)
        result = ctypes.cast(address, ctypes.py_object).value
        return result
    except Exception as e:
        return None


class UIDragInteractionDelegate(ObjCDelegate):
    """ docgen-ignore """
    
    def __init__(self, view, data, allow_others):
        if not callable(data):
            data = functools.partial(lambda d, sender: d, data)
        self.data = { 'payload_func': data }
        self.view = view
        view.touch_enabled = True
        draginteraction = UIDragInteraction.alloc().initWithDelegate_(self)
        draginteraction.setEnabled(True)
        draginteraction.setAllowsSimultaneousRecognitionDuringLift_(allow_others)
        view.objc_instance.addInteraction(draginteraction)
            
        retain_global(self)
    
        
    def dragInteraction_itemsForBeginningSession_(_self, _cmd,
    _interaction, _session):
        self = ObjCInstance(_self)
        session = ObjCInstance(_session)
        payload = self.data['payload_func'](self.view)        
        self.content_actual = {
            'payload': payload,
            'sender': self.view
        }
        
        external_payload = ''
        suggested_name = None
        
        if type(payload) is str:
            external_payload = payload
        elif type(payload) is ui.Image:
            external_payload = ObjCInstance(payload)
            try:
                suggested_name = os.path.basename(payload.name)
            except: pass
        elif type(payload) is File:
            suggested_name = payload.filename
            
        provider = NSItemProvider.alloc().initWithObject(external_payload)
        if suggested_name:
            provider.setSuggestedName_(suggested_name)
        item = UIDragItem.alloc().initWithItemProvider(provider)
        item.setLocalObject_(
            str(drag_and_drop_prefix) +  
            str(id(self.content_actual)))
        object_array = NSArray.arrayWithObject(item)
        return object_array.ptr
    
    def dragInteraction_sessionDidMove_(_self, _cmd, _interaction, _session):
        session = ObjCInstance(_session)
        self = ObjCInstance(_self)
        CGPoint_loc = session.locationInView_(self.view)
    
        
        

class UIDropInteractionDelegate(ObjCDelegate):
    """ docgen-ignore """
    
    def __init__(self, view, handler_func, accept, animation_func, onBegin_func):
        
        if type(accept) is type:
            if accept is str:
                self.accept_type = NSString
            elif accept is ui.Image:
                self.accept_type = UIImage
            elif accept is bytearray:
                self.accept_type = NSData
            accept = functools.partial(lambda dtype, d, s, r: type(d) is dtype, accept)
            
        self.functions = {
            'handler': handler_func,
            'accept': accept,
            'animation_func': animation_func,
            'onbegin_func': onBegin_func
        }
        self.view = view
        view.touch_enabled = True
        
        dropinteraction = UIDropInteraction.alloc().initWithDelegate_(self)
        view.objc_instance.addInteraction(dropinteraction)
        retain_global(self)
        
    def dropInteraction_canHandleSession_(_self, _cmd, _interaction, _session):
        return True
    
    
    def dropInteraction_concludeDrop_(_self, _cmd, _interaction, _session): # Called when the animation for the item drop is finished
        self = ObjCInstance(_self)
        func = self.functions['animation_func']
        
        if callable(func):
            return func() 
    
    def dropInteraction_sessionDidEnter_(_self, _cmd, _interaction, _session): # Called when you first start dragging an item
        self = ObjCInstance(_self)
        func = self.functions['onbegin_func']   
        
        if callable(func):
            return func()
            
    def dropInteraction_sessionDidUpdate_(_self, _cmd, _interaction, _session):
        self = ObjCInstance(_self)
        session = ObjCInstance(_session)
        proposal = 2 # UIDropOperationCopy
        accept_func = self.functions['accept']

        if session.localDragSession():
            if accept_func is not None:
                for item in session.items():
                    data = _to_pyobject(item)
                    payload = data['payload']
                    sender = data['sender']
                    if not accept_func(payload, sender, self.view):
                        proposal = 1 # UIDropOperationForbidden
        else:
            pass
            '''
            if self.accept_type is None:
                proposal = 1
            elif not session.canLoadObjectsOfClass(self.accept_type):
                    proposal = 1 # UIDropOperationForbidden
            '''

        return UIDropProposal.alloc().initWithDropOperation(proposal).ptr
        
    def dropInteraction_performDrop_(_self, _cmd, _interaction, _session):
        self = ObjCInstance(_self)
        session = ObjCInstance(_session)
        handler = self.functions['handler']
        
        if session.localDragSession():
            for item in session.items():
                data = _to_pyobject(item)
                payload = data['payload']
                sender = data['sender']
                handler(payload, sender, self.view)
        else:
            if self.accept_type is not None:
                
                def completion_handler(_cmd, _object, _error):
                    obj = ObjCInstance(_object)
                    payload = None
                    if _is_objc_type(obj, NSString):
                        payload = str(obj)
                    elif _is_objc_type(obj, UIImage):
                        payload = ui.Image.from_data(uiimage_to_png(obj))
                    elif _is_objc_type(obj, NSURL):
                        file_url = str(obj)
                    handler(file_url, None, self.view)
                handler_block = ObjCBlock(
                    completion_handler, restype=None,
                    argtypes=[c_void_p, c_void_p, c_void_p])
                retain_global(handler_block)
                
                for item in session.items():

                    provider = item.itemProvider()
                    if provider.canLoadObjectOfClass(self.accept_type):
                        provider.loadObjectOfClass_completionHandler_(
                        self.accept_type, handler_block)
                    elif self.accept_type is NSData:
                        
                        type_identifier = None
                        suggested_name = None
                        try:
                            type_identifier = provider.registeredTypeIdentifiers()[0]
                            suggested_name = provider.suggestedName()
                        except: pass
                        if type_identifier and suggested_name:
                            provider.loadFileRepresentationForTypeIdentifier_completionHandler_(
                                type_identifier, handler_block)
  
class UIPointerInteractionDelegate(ObjCDelegate):
    def __init__(self, view, delegate_methods, *args, **kwargs):
        
        self.delegate_methods = delegate_methods
        self.view = view
        UIPointerInteractionDelegate = UIPointerInteraction.alloc().initWithDelegate(self)
        view.objc_instance.addInteraction(UIPointerInteractionDelegate) 
        
        retain_global(self)
 
    
    def pointerInteraction_willEnterRegion_animator_(_self, _cmd, _interaction, _region, _animator):
        self = ObjCInstance(_self)
        bnt = self.delegate_methods['pointerInteraction_willEnterRegion_animator_']
        
        def bnt_change():
            bnt.transform = ui.Transform.scale(1.07, 1.07)#.concat(ui.Transform.rotation(pi/50))
        
        ui.animate(bnt_change, 0.3)
    
    def pointerInteraction_willExitRegion_animator_(_self, _cmd, _interaction, _region, _animator):
        self = ObjCInstance(_self)
        bnt = self.delegate_methods['pointerInteraction_willExitRegion_animator_']
        
        def bnt_change():
            bnt.transform = ui.Transform.scale(1.0, 1.0)#.concat(ui.Transform.rotation(0))
        
        ui.animate(bnt_change, 0.3)

class SiPImagePicker(ObjCDelegate):
    def __init__(self, sip):
        viewController_objc = ObjCInstance(sip)
        
        ImgPicker = UIImagePickerController.alloc().init()
        ImgPicker.allowsEditing = True
        ImgPicker.sourceType = 0
        ImgPicker.allowsMultipleSelection = True
            
        ImgPicker.setDelegate_(self)
        
        viewController = SUIViewController.viewControllerForView_(viewController_objc)
        viewController.presentModalViewController_animated_(ImgPicker, True)
        
        self.sip = sip
        retain_global(self)
        
        
    def imagePickerController_didFinishPickingMediaWithInfo_(_self, _cmd, _picker, _info):
        
        self = ObjCInstance(_self)
        picker = ObjCInstance(_picker)
        info = ObjCInstance(_info)
        
        img = info['UIImagePickerControllerEditedImage']
            
        func = c.UIImageJPEGRepresentation
        func.argtypes = [ctypes.c_void_p, ctypes.c_float]
        func.restype = ctypes.c_void_p
        
        x = ObjCInstance(func(img.ptr, 1.0))
        x.writeToFile_atomically_(f'{img.ptr}.png', True)
        
        picker.setDelegate_(None)
        self.release()
        picker.dismissViewControllerAnimated_completion_(True, None)
        
        self.sip.nas.upload_file(self.sip.name, f'{img.ptr}.png')
        
        os.remove(f'{img.ptr}.png')   

class SiPDocumentPicker(ObjCDelegate):
    def __init__(self, view):
        
        file_ext = UTType.typeWithIdentifier_('public.item')
        items = NSArray.arrayWithObject(file_ext)
        
        viewController_objc = ObjCInstance(view)
        document_picker = UIDocumentPickerViewController.alloc().initForOpeningContentTypes_(items)
        document_picker.shouldShowFileExtensions = True
        
        
        viewController = SUIViewController.viewControllerForView_(viewController_objc)
        viewController.presentModalViewController_animated_(document_picker, True)
        
        retain_global(self)
        
    def documentPicker_didPickDocumentsAtURLs_(_self, _cmd, _controller, _urls):
        urls = ObjCInstance(_urls)
 
"""
This class should be able to display the edit context menu (UIMenuEditInteraction)
This is a beta feature for iOS 16+ and currently does not work for me. I do not know
if it does not work in general or if it my programming or the bridge between Python and Obj-C
"""
class UIMenuEditInt(ObjCDelegate):
    def __init__(self, view):
        EditInteraction = UIEditMenuInteraction.alloc().initWithDelegate(self)
        view.objc_instance.addInteraction(EditInteraction)
        
        self.edit_interaction = EditInteraction
        retain_global(self)
        
    def editMenuInteraction_menuForConfiguration_suggestedActions_(_self, _cmd, _interactions, _config, _actions):  
        button = ObjCInstance(_interactions)
        
        return Menu(button, [Action(title='Test', handler=None)], long_press=True)             
        
#docgen: Drag and drop                                
        
@on_main_thread
def drag(view, payload, allow_others=False):
    UIDragInteractionDelegate(view, payload, allow_others)
    
@on_main_thread
def drop(view, action, accept=None, animation_func=None, onBegin_func=None):
    UIDropInteractionDelegate(view, action, accept, animation_func, onBegin_func)

@on_main_thread
def UIPointer(view, delegate_methods):
    UIPointerInteractionDelegate(view, delegate_methods)

@on_main_thread
def import_file_fix(view):
    SiPDocumentPicker(view)

@on_main_thread
def ui_edit_menu(view):
    return UIMenuEditInt(view)
      
@on_main_thread
def ImagePickerDialogue(nas):
    SiPImagePicker(nas)


if __name__ == '__main__':
    
    import math, random, console
    
  
    
    bg = ui.View(background_color='green')
    bg.present('fullscreen', hide_title_bar=True)

    tap(bg, 'close', number_of_touches_required=2)

        
    v = ui.ScrollView(frame=(0, 100, bg.width, bg.height - 100))
    bg.add_subview(v)

    label_count = -1

    def create_label(title, instance=None):
        global label_count
        
        label_count += 1
        label_w = 175
        label_h = 75
        gap = 5
        label_w_with_gap = label_w + gap
        label_h_with_gap = label_h + gap
        labels_per_line = math.floor((v.width - 2 * gap) / (label_w + gap))
        left_margin = (v.width - labels_per_line * label_w_with_gap + gap) / 2
        line = math.floor(label_count / labels_per_line)
        column = label_count - line * labels_per_line

        if instance is None:
            instance = ui.Button(
                text=title,
                text_color='white',
                alignment=ui.ALIGN_CENTER,
                number_of_lines=0
            )
            
        instance.background_color = 'grey'
        instance.tint_color = 'white'
        
        instance.frame = (
            left_margin + column * label_w_with_gap,
            gap + line * label_h_with_gap,
            label_w, label_h
        )
        v.add_subview(instance)
        return instance
    
    interaction = create_label('Hover over')
    c_menu = create_label('Context Menu')
        
    
    edit_menu = ui_edit_menu(c_menu)
    
    def long_press_menu(*args):
        location = args[0][-1].location
        
        loc = CGPoint(location.x, location.y)
        config = UIEditMenuConfiguration.configurationWithIdentifier_sourcePoint_(None, loc)
        edit_menu.edit_interaction.presentEditMenuWithConfiguration_(config)
        
    long_press(c_menu, lambda *args: long_press_menu(args), minimum_press_duration=.5)
    
    
#import_file_fix()
    
    

    
    

