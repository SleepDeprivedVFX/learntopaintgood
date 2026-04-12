# Development

### Support

- Windows

The framework has pre-release steps:

1. Include a pre-built [Toolkit Plugin](#build_toolkit_plugin)
2. Include any necessary [embeddable Python packages](#embed_py_package)
3. Include any [required Python packages](#required-python-packages)

## <a name="build_toolkit_plugin"></a> Build the Toolkit Plugin

The framework provides the functionality to bootstrap a Toolkit engine (e.g. [tk-alias](https://github.com/shotgunsoftware/tk-alias)) using the the [ToolkitManager](https://github.com/shotgunsoftware/tk-core/blob/develop/python/tank/bootstrap/manager.py). A Toolkit Plugin must be created in order to intialize the manager to bootstrap an engine. The framework provides build scripts to generate the plugin bundle; after running the build, it will create the `com.sg.basic.alias` plugin bundle in the `dist/Toolkit/plugin` folder. At runtime, the framework start up utils will install the plugin bundle to the user's `%APPDATA%` folder, where it can be accessed during the [bootstrap process](https://github.com/shotgunsoftware/tk-framework-alias/blob/develop/python/tk_framework_alias_utils/plugin_bootstrap.py).

The following files are provided to build the plugin:

- env.cmd
- make.bat
- build_plugin.py

The actual plugin is built from the file `plugin/Toolkit/basic/info.yml`. The `info.yml` defines the Toolkit Plugin.

Before exeuting the build scripts, set all necessary variables in `dev\env.cmd`. These environment variables will be set by calling `env.cmd` from the `make.bat` file. This is what the env file should look like:

```
TARGET_VERSION=1.1.3 # Make sure this matches the tk-framework-alias version you will be releasing

TKCORE_VERSION=0.19.19  # This core version is expected to exist in your bundle cache

PYTHON_EXE=/path/to/python.exe
```

Follow [this link](https://developer.shotgridsoftware.com/7c9867c0/#bundle-cache) to find out where your bundle cache is located.

### Build

Run the build to create the plugin bunlde in the `dist/Toolkit/plugin` folder. This is all that is needed to prep the plugin for release with the framework.

```
cd path/to/tk-framework-alias
cd dev
make build
```

### Install

Optionally, you can install the plugin immediately to your `%APPDATA%` folder. This install step will be done at run time in the start up utils, if it does not exist.

```
cd path/to/tk-framework-alias
cd dev
make build
make install
```

### Remove plugin build

```
cd path/to/tk-framework-alias
cd dev
make clean
```

## <a name="embed_py_package"></a>Embeddable Python Package

The `get-pip.py` script is not included to set up the embeddable Python packages in `dist` (see [pip installation](https://pip.pypa.io/en/stable/installation/)). Download from [here](https://bootstrap.pypa.io/get-pip.py). The base embeddable Python packages do not come with pip, so this script can be used to make pip available to the embeddable Python, which can then be used to install any additional required Python packages. See [dist](https://github.com/shotgunsoftware/tk-framework-alias/blob/develop/dist/README.md) for more details on how to set up the embeddable Python package.

## Required Python Packages

The framework requires additional Python packages to the standard package that Flow Production Tracking Toolkit ships with. To make these packages available to the framework, they must be included in the distribution directory `dist/Python/Python<MAJOR_VERSION><MINOR_VERSION>/packages`.

### What's included?

The packages that are included are defined by the `requirements.txt` in each of the `dist/Python/Python<MAJOR_VERSION><MINOR_VERSION>` directory. The packages can be obtained by running the [update_python_packages.py](https://github.com/shotgunsoftware/tk-framework-alias/blob/develop/dev/update_python_packages.py) script that uses pip to intall them. The script will then zip of the packages and copy them to the distribution directory. Standard Python packages will be found in `pkgs.zip`, and C extension packages will be found in `c_extensions.zip`. The reason for separating these packages is because C extension packages need to be unzipped in order to allow them to be imported by the framework (while standard packages do not).

### Update the packages

Follow these steps to update the packages when needed, these steps will update the packages for Python 3.7:

1. Change the packages (add, remove, update version) by modifying the [requirements.txt](https://github.com/shotgunsoftware/tk-framework-alias/blob/develop/dist/Python/Python37/requirements.txt).
2. Using Python 3.7, run the [update_python_packages.py](https://github.com/shotgunsoftware/tk-framework-alias/blob/develop/dev/update_python_packages.py) script. This script must be run from inside the `dev` directory.
3. Check that the packages have been updated correctly [here](https://github.com/shotgunsoftware/tk-framework-alias/blob/develop/dist/Python/Python37/packages). There is a `frozen_requirements.txt` file that records the package versions that were installed.
4. Add the changes to the packages to git using `git add dist -f`.
5. Commit and push the change to git as for any change.

#### Key details about the update script

- The version of Python used to run the scripts, is the version of Python that the packages will be installed for
- The script must be run from inside the `dev` folder
- The update script will use the requirements file and pip to install the packages to a local temp directory, which are eventually copied to the `dist` folder
- C extension packages are put in their own separate zip file, to easily unzip them at run time.
- To limit the size of the packages (to not bloat the repository size), special handling is made to the PySide2 package. PySide2 functionality is limited to using a single method from the QtCore module, and it is not intended that any further PySide2 functionality is to be needed. For this reason, the minimum files are included to use only the QtCore module.
