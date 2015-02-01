@echo off
setlocal

rem -----------------------------------------------------
rem Credit to Mitch Schwartz for the source of this file
rem Original code from http://stackoverflow.com/a/4405155
rem -----------------------------------------------------

rem This batch file points to an executable that is
rem located in another directory. Specify the path here:

set actualfile=<DIRECTORY>

rem Call the executable, preserving arguments.

set args=%1

:beginloop
if "%1" == "" goto endloop
shift
set args=%args% %1
goto beginloop
:endloop

<INTERPRETER> %actualfile% %args%

endlocal

