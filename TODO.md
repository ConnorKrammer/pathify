# Todo

1. Implement more nuanced error messages. These should be based upon
   existing defaults, presence of targets, etc.
2. Allow *"unpathifying"* executables with a `-d` flag. Defaults to saved
   destination directory, overridden in the usual way.
3. Allow the target file to be selected without a flag.
4. Create a better help section.
5. Make templates for the different shell scripting languages (bash, ...)
   so that it can produce scripts that work in any shell.
6. Use a smart selection, so that if the user says `pathify gvim` pathify
   will intelligently determine that they must mean `gvim.exe`. By default
   this should trigger a confirmation prompt ("Did you mean *gvim.exe*?")
   which can be disabled in settings. If there is more than one gvim
   (gvim.exe, gvim.bat, gvim.sh), then the program should prompt the user
   to select which they meant. Ex:
   ```
   Which gvim do you want to pathify?
   1 gvim.exe
   2 gvim.bat
   3 gvim.sh
   ```
