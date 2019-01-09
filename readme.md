

# Package Builder

This script is meant to be used to generate package-index.xml and deploy the corresponding packages to the location of your choice (e.g. IIS wwwroot). This is meant to be used in conjunction with eWAM Launcher, which is able to pull packages from an online repository indexed with a package-index.xml file.

### How it works
This tools allows you to builf packages (e.g. wynsure 5.8.0.65, ewam 6.1.5.33, ewam 6.0.0.19). A package is composed of components (Binaries, Dlls, CppDlls, Documentation, etc.). A component is composed ot files. A component may be compressed (i.e. all its files are put in an archive .zip file), or not compressed (all its files are deployed "as is").

The script looks for package definition files (\*.package-definition files) in all the provided root pathes. Then it looks for the component definitions for each package (\*.package-components files under the same folder as its corresponding .package-definition file). You can see some [samples](Samples).

### .package-definition format
It must contain these sections :

```
unique-id:ewam-6.1.5.15-x64
product:eWAM
version:6.1.5.15
description:eWAM 6.1.5.15 x64
```

### .package-components format
This file is composed ot several lines. Each line is a semi-colon list of parameters :
- Component name
- The list of packages this component will be included in. It can be a wildcard string. '*' means to be included in every package.
- A comma-seperated list of patterns of files that will be included in this component, relative to the folder where the .package-component file is. '\*\*' means recursively every file, '\*\*/' means to recursively traverse all sub folders.
- An optional last parameter can specify whether or not to compress the component. You may use "None" for no compression. If nothing is specified, the component will be compressed by default.

Example:

```
Core Binaries;*;Bin/**/*.exe,Bin/**/*.dll,Dll/**/*.dll,Dll/**/*.exe
Core Symbols;*;Bin/**/*.pdb,Dll/**/*.pdb
CppDll;*;CppDll/*.exe,CppDll/*.dll,CppDll/*.dcl
CppDll Symbols;*;CppDll/**/*.pdb
Debug Binaries;*;CppDll.Debug/**,Dll.debug/**
Batches;*;**/*.bat
Libs;*;Lib/**/*.lib
Source;*;**/*.h,**/*.hpp,**/*.cpp,**/*.req,**/*.cs
Maps;*;**/*.map
WNetConf;*;wnetconf.ini
WydeWeb;*;WydeServer/**
Admin;*;Admin/**
Launchers;*;**/*.jsenv,**/*.xenv
Binaries Sets;*;**/*.jswam,**/*.xwam
TGVs;*;Tgv/**,EmptyTeam/**
Images;*;Bmp/**
Documentation;*;Documentation/**,Help/**,Examples/**
Bundles;*;Bundle/**,Config/**
```


### Deployment
When deploying the files to IIS folder, you might want to use the [web.config](Documentation/web.config), to configure IIS to allow .xml file to be downloaded, and any other file type that you need to deploy.

## Command line

```
packagebuilder.py --help
usage: packagebuilder.py [-h] [--package-index PACKAGE_INDEX]
                         --package-index-policy {overwrite,append,update}
                         [--deploy DEPLOY] [--deploy-policy {wipe,update}]
                         [--version]
                         PATH [PATH ...]

Index and deploy products referenced by *.package-definition and *.package-
components

positional arguments:
  PATH                  root path for indexing

optional arguments:
  -h, --help            show this help message and exit
  --package-index PACKAGE_INDEX
                        package index file
  --package-index-policy {overwrite,append,update}
                        Decide what to do if package-index already exists:
                        overwrite=overwrite existing, append=append to
                        existing, update=update existing
  --deploy DEPLOY       If provided, should specify where packages files
                        should be deployed. No deployment is done if this
                        argument is not provided.
  --deploy-policy {wipe,update}
                        Decide what to do with existing deployed files:
                        wipe=wipe existing in destination folder,
                        update=update existing files in destination folder
  --version             show program's version number and exit
```

## Examples

> `python packagebuilder.py Path\To\Source1 "C:\Path\To\Source 2" --package-index-policy update --deploy C:\inetpub\wwwroot\eWamUpdate --deploy-policy update`


## Improvments
- [ ] Hierarchise the package-index.xml into sub indexes, to make it lighter (currently, the index stores all the files of all the components of all the pacakges, which makes it bigger : ~25MB for ~50 packages)


## Changelog

### 2019-01-01
- [x] Allow defining several packages in same folder
- [x] Optimize : build/rebuild component only if needed
- [x] Optimize : deploy/redeply files only if needed, + cleanup files that got removed