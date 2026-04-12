@echo off
rem ------------------------------------------
rem this file exposes 4 commands
rem     clean - deletes the plugin bundle
rem     build - build the plugin and create the bundle in the repo
rem     install - copy the plugin bundle to the Alias plugin install directory
rem ------------------------------------------

call "env.cmd"

set "PLUGIN_NAME=com.sg.basic.alias"
set "BUNDLE_CACHE_FOLDER=%APPDATA%\Shotgun\bundle_cache\app_store\tk-core"
set "ALIAS_PLUGIN_FOLDER=%APPDATA%\Autodesk\Alias\ShotGrid\plugin\"
set "PLUGIN_BUNDLE_OUTPUT=%~dp1\..\dist\Toolkit\plugin"
set "TKCORE_FOLDER_DEFAULT=%BUNDLE_CACHE_FOLDER%\v%TKCORE_VERSION%"

if "%TKCORE_FOLDER%"=="" (set "TKCORE_FOLDER=%TKCORE_FOLDER_DEFAULT%") else (echo using tk-core-folder: %TKCORE_FOLDER%)

rem check the tk-core version
if not exist "%TKCORE_FOLDER%" (goto :missing_tk_core)

set "JUMP_TO="


rem check the incoming command
if "%1"=="clean" (goto :clean) else (
if "%1"=="build" (goto :build) else (
if "%1"=="install" (goto :install) else (
echo "The target %1 is not valid. Please chose one of: clean, build, install"
goto :eof
)))

goto :end

rem -------------TARGETS------------------

:clean
echo clean
rmdir /q /s "%PLUGIN_BUNDLE_OUTPUT%"
goto :jumpto

:build
echo build
"%PYTHON_EXE%" "%~dp1\build_plugin.py" -c "%TKCORE_FOLDER%" -p basic -e "%PLUGIN_NAME%" -v v"%TARGET_VERSION%" -o "%PLUGIN_BUNDLE_OUTPUT%"
goto :jumpto

:install
echo install
if not exist "%ALIAS_PLUGIN_FOLDER%" (
    mkdir "%ALIAS_PLUGIN_FOLDER%"
)
xcopy "%PLUGIN_BUNDLE_OUTPUT%" "%ALIAS_PLUGIN_FOLDER%" /E /Y
goto :jumpto

rem -------------HELPER JUMPMARKS------------------

:jumpto
if "%JUMP_TO%"=="" (goto :eof)
set "TMP_JMP=%JUMP_TO%"
set "JUMP_TO="
goto %TMP_JMP%

:missing_tk_core
echo "The tk-core version given '%TKCORE_VERSION%' does not exist in disk. Please choose a version existing in the folder: '%BUNDLE_CACHE_FOLDER%'"
goto :eof
