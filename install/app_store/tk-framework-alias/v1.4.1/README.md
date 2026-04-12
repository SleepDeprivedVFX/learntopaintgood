[![VFX Platform](https://img.shields.io/badge/vfxplatform-2023%20%7C%202022%20%7C%202021-blue.svg)](http://www.vfxplatform.com/)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.9%20%7C%203.7-blue.svg)](https://www.python.org/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Build Status](https://dev.azure.com/shotgun-ecosystem/Toolkit/_apis/build/status%2Ftk-framework-alias?repoName=shotgunsoftware%2Ftk-framework-alias&branchName=main)](https://dev.azure.com/shotgun-ecosystem/Toolkit/_build/latest?definitionId=120&repoName=shotgunsoftware%2Ftk-framework-alias&branchName=main)

# tk-framework-alias

Toolkit framework for integration with Autodesk Alias.

The main use of this framework is by the [Alias Engine](https://github.com/shotgunsoftware/tk-alias). The framework allows the engine to run alongside Alias, providing access to the Flow Production Tracking Toolkit Apps that can interact with the data in Alias.

### <a name="support"></a>Support

- 2022.2 <= Alias <= 2024
- Windows only

<br/>

## What's in the Framework

### <a name="alias_plugin"></a>Alias Plugin ###

This plugin is loaded by Alias and is the main entry point to integrating a Python client (e.g. Flow Production Tracking) with Alias. This is maintained by the Flow Production Tracking Automotive Team.

File location:  `dist/Alias/{python_version/{alias_version}/{plugin_name}.plugin`

### Alias Python API ###

The Python module that provides bindings to the C++ Alias API. This allows the Python client (e.g. Flow Production Tracking) to interact with the Alias data. This is maintained by the Flow Production Tracking Automotive Team.

File location:  `dist/Alias/{python_version/{alias_version}/alias_api.pyd`

### <a name="toolkit_plugin"></a>Toolkit Plugin for Alias ###

The Toolkit Plugin is used by [plugin_bootstrap.py](https://github.com/shotgunsoftware/tk-framework-alias/blob/develop/python/tk_framework_alias_utils/plugin_bootstrap.py) to bootstrap the Flow Production Tracking Alias Engine, which can be initiated by the Alias Plugin. This allows Flow Production Tracking to be started up by Alias. See [dev](https://github.com/shotgunsoftware/tk-framework-alias/tree/main/dev#readme) for more details on how the Toolkit Plugin is built.

File location:  `dist/Toolkit/plugin/com.sg.basic.alias`

### Embeddable Python Package ###

To ensure the framework can run with any Alias version, a specific Python version may be required. In this case, the framework provides a minimal embeddable Python package that can be installed to the user's `%APPDATA%` folder at runtime. Embeddable Python packages can be downloaded from [here](https://www.python.org/ftp/python/). See [dist](https://github.com/shotgunsoftware/tk-framework-alias/tree/main/dist#readme) for more details about the Python distribution.

File location:  `dist/Python{major}{minor}/python-{major}.{minor}-embed-amd64.zip`

### Development Tools

The `dev` folder provides scripts to build the necessary components for the framework. See [dev](https://github.com/shotgunsoftware/tk-framework-alias/tree/main/dev#readme) for more details.

<br/>

## <a name="how_it_works"></a>How it Works

_The framework has potential to be used more generally, but for the purpose of demonstrating how the farmework works, the provided example will use the Alias Engine._

The framework can be used for any version of Alias (within the [support](#support) cycle). The high-level steps include:

1. First, run the framework's start up utils.
2. The start up utils will generate a plugin lst file that can be used when launching Alias to auto-load the [Alias Plugin](#alias_plugin). For example, using a Windows command lint:
```
"C:\Program Files\Autodesk\AliasAutoStudio2024.0\bin\Alias.exe" -a as -P "C:\path\to\alias_plugins.lst"
```
3. Alias loads the plugin which will embed Python to access the Python modules to initialize Flow Production Tracking and establish communication with Alias.

The [startup utils](https://github.com/shotgunsoftware/tk-framework-alias/blob/develop/python/tk_framework_alias_utils/startup.py) do all the necessary set up to ensure that Alias can load the plugin to initialize Flow Production Tracking. See the main start up function [ensure_plugin_ready](https://github.com/shotgunsoftware/tk-framework-alias/blob/develop/python/tk_framework_alias_utils/startup.py#L536) for more details.

Due to major changes to Alias starting in 2024.0, the framework essentially operates in two different modes. For Alias versions prior to 2024.0:

- Only the framework's start up utils are used to generate the plugin list file
- The Alias Engine will use the plugin list file to launch Alias and auto-load the plugin
- The plugin will start the Alias Engine in the same process as Alias
- The Alias Engine will import the Alias Python API module directly to interact with the data in Alias
- The Alias Engine will create a Qt Application and share the Alias event loop to display Toolkit UI alongside Alias.
- No other framework functionality is used

For Alias 2024.0 and later:

- The framework's start up utils are used to ensure the [Toolkit Plugin](#toolkit_plugin) is installed and a suitable version of Python is avilable, in addition to generating the plugin list file
- The Alias Engine will use the plugin list file to launch Alias and auto-load the plugin
- The plugin will start the Alias Python API server
- The plugin will then use the Toolkit Plugin to bootstrap the Alias Engine in a new process (separate from Alias)
- The Alias Engine will establish a connection to the Alias Python API server to interact with the data in Alias
- the Alias Engine will create a Qt Application and start its own event loop to display Toolkit UI alongside Alias

The plugin will use the [AliasBridge](https://github.com/shotgunsoftware/tk-framework-alias/blob/develop/python/tk_framework_alias/server/alias_bridge.py#L33) object to manage the Alias Python API server. The [plugin_bootstrap.py](https://github.com/shotgunsoftware/tk-framework-alias/blob/develop/python/tk_framework_alias_utils/plugin_bootstrap.py) script will called to bootsrap the Alias Engine. The Alias Engine will create a [client](https://github.com/shotgunsoftware/tk-framework-alias/blob/develop/python/tk_framework_alias/client/socketio/client.py) to connect to the Alias Python API server.

<br/>

## Prep for Release

1. Build and install the [Toolkit Plugin](#toolkit_plugin) to `dist/Toolkit/plugin`. See [dev](https://github.com/shotgunsoftware/tk-framework-alias/tree/main/dev#readme) on how to build.
2. Add the necessary embeddable Python packages to `dist/Python{major}{minor}`. See [dist](https://github.com/shotgunsoftware/tk-framework-alias/tree/main/dist#readme) on how to create an embeddable Python package.
