# Synology-Interactive-Panel
Made for Pythonista on iPad Pro 11” 

I do not expect this to be used by anyone, and am saving this here purely for my own purposes.

A small rundown for anyone who stumbles across this:

Made for Pythonista, programmed on an iPad Pro 11" and NOT tested on another model.

Can view files, folders, and images.

To connect to your own NAS, in the file arguments (Run Options) in pythonista, use this format:

<NAS URL> <Port> <Username> <Password> <root> 
  Example for NAS URL: nasname.synology.me
  Port: Is always 5001, unless configured in NAS settings
  Username: Whatever user you want to use
  Password: Whatever the password is for the user you want to use (NOTE: IF THE PASSWORD HAS BACKSLASHES (\) PUT TWO)
  root: Name of the root of the NAS, mine is /Volume, yours maybe different. 



PS: Because I am too lazy to program a back button, tilt your device to the left to go back to the last directory. Or use arrow keys if using a magic keyboard / hardware keyboard
  
  Made by Austin Ares (Austin Ares#2263 on Discord)
  "nas" module made by https://github.com/N4S4/ on GitHub, but edited by me to fit my needs, go check them out.
