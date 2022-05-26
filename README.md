# Synology-Interactive-Panel
## Made for Pythonista on iPad Pro 11″ 

I do not expect this to be used by anyone, and am saving this here purely for my own purposes.

A small rundown for anyone who stumbles across this:

Made for Pythonista, programmed on an iPad Pro 11″ and NOT tested on another model.

Can view files, folders, and images.

This tool is to be used outside of the Synology NAS's local network.
If you are within the local network of the NAS, I recommend connecting to it directly,
or use FE File Explorer if you are on iOS, very good app.

I made this mostly for myself, as I disliked the DS File UI and how it functioned.
Though use it if you please, but be warned this is not made by a professional.

## NAS Settings

**To connect to your own NAS in the file arguments (Run Options) in pythonista, use this format:**

  <NAS URL> <Port> <Username> <Password> <root>
 
  
  1. NAS URL  >  nasname.synology.me or IP
  
  1. Port  >  Is always 5001, unless configured in NAS settings
  
  1. Username  >  Whatever user you want to use
  
  1. Password  >  Whatever the password is for the user you want to use
  
  1. root  >  Name of the root of the NAS, mine is /Volume, yours maybe different. 

## Prerequisites
  
  You will need three extra modules that are not bundled with Pythonista, these are:
  
  * StaSh (```import requests as r; exec(r.get('https://bit.ly/get-stash').content``` this used for installing the next modules)
  
  * hurry.filesize (```pip install hurry.filesize```)
  * config (```pip install config```)
  * crtifi (You may run into an error with SSL, this may not be crucial for SiP to run, but to fix this, install StaSh, and do this command: ```pip install certifi``` or ```pip install --upgrade certifi```)
  
## Credits
  Made by Austin Ares (Austin Ares#2263 on Discord, or 400089431933059072 on [Discord.id](https://discord.id))
  "nas" module made by [N4S4 On GitHub](https://github.com/N4S4/), but edited by me to fit my needs, go check them out.
  on a small note, any release of this project can be considered unstable, I will say it is stable when I think so.
