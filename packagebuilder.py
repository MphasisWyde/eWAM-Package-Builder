import xml.etree.ElementTree as ET
import sys
import glob
import os
import pathlib
import zipfile
import shutil
import time
import argparse
import fnmatch
import hashlib

# This script is designed to walk a directory tree to find *.package-definition files and associated *.package-components.
# These files contain package definitions to be prepared and deployed to a website, in order to make the packages available to 
# eWamLauncher package puller. 
# 
# Example:
# > python packagebuilder.py D:\wyde\ --package-index-policy overwrite --deploy C:\inetpub\wwwroot\eWamUpdate --wipe-destination

class Package:
    def __init__(self, source_path, name, description, product, version, package_id):
        self.source_path = source_path
        self.type = str.lower(product)
        self.name = name
        self.description = description
        self.id = package_id
        self.version = version
        self.components = []

    def append_component(self, component):
        self.components.append(component)

    def to_element_tree(self):
        packageXML = ET.Element('Package')
        packageXML.set("Type", self.type)
        packageXML.set("Id", self.id)
        packageXML.set("Name", self.name)
        packageXML.set("Version", self.version)
        packageXML.set("Description", self.description)

        for component in self.components:
            componentXML = component.to_element_tree()
            packageXML.append(componentXML)

        return packageXML

class Component:
    def __init__(self, name, compression="7z"):
        self.name = name
        self.compression = compression
        self.files = []

    def append_file(self, componentFile):
        """Append given 'File' object."""
        if os.path.isfile(componentFile.path):
            self.files.append(componentFile)

    def append_filepath(self, filename):
        """Create and append 'File' object for given file name."""
        if os.path.isfile(filename):
            componentFile = File(filename)
            self.files.append(componentFile)

    def append_files(self, componentFiles):
        """Append given 'File' objects."""
        for componentFile in componentFiles:
            if os.path.isfile(componentFile.path):
                self.files.append(componentFile)

    def append_filepathes(self, filenames):
        """Create and append 'File' object for each file name in the list."""
        for filename in filenames:
            if os.path.isfile(filename):
                self.append_filepath(filename)

    def append_wildcards_files(self, wildcards):
        """Search and append wildcards path files, from current directory."""
        self.append_filepathes(glob.glob(wildcards, recursive=True))

    def create_zip(self, archive_filename):

        archive_format = None
        if self.compression == "deflate" or self.compression == "zip":
            archive_format = zipfile.ZIP_DEFLATED
        elif self.compression == "lzma":
            archive_format = zipfile.ZIP_LZMA
        elif self.compression == "bzip2":
            archive_format = zipfile.ZIP_BZIP2
        elif self.compression == "store":
            archive_format = zipfile.ZIP_STORED
        else:
            print("Warning: unknown compression method for " + self.name + ": '" + self.compression + "'")
            exit(1)
        
        if os.path.exists(archive_filename):
            os.remove(archive_filename)

        with zipfile.ZipFile(archive_filename, mode='w', compression=archive_format) as zip_file:
            for file in self.files:
                zip_file.write(file.path)

    def to_element_tree(self):
        componentXML = ET.Element("Component")
        componentXML.set("Name", self.name)
        componentXML.set("Compression", self.compression)

        for componentFile in self.files:
            fileXML = componentFile.to_element_tree()
            componentXML.append(fileXML)

        return componentXML

class File:
    def __init__(self, path):
        self.path = os.path.normpath(path)
        self.calculateHash()
        
    def calculateHash(self):
        BLOCKSIZE = 65536
        hasher = hashlib.md5()
        with open(self.path, 'rb') as dataFile:
            buf = dataFile.read(BLOCKSIZE)
            while len(buf) > 0:
                hasher.update(buf)
                buf = dataFile.read(BLOCKSIZE)
        self.hash = hasher.hexdigest()

    def to_element_tree(self):
        fileXML = ET.Element("File")
        fileXML.set("Path", self.path)
        fileXML.set("Hash", self.hash)
        return fileXML


def parse_package_definition(filename):
    package_id = ""
    product = ""
    version = ""
    description = ""
    with open(filename) as pkginfofile:
        for count, line in enumerate(pkginfofile):
            if (line.startswith("unique-id:")):
                package_id = line.split(":")[1].strip("\n\r\b")
            elif (line.startswith("product:")):
                product = line.split(":")[1].strip("\n\r\b")
            elif (line.startswith("version:")):
                version = line.split(":")[1].strip("\n\r\b")
            elif (line.startswith("description:")):
                description = line.split(":")[1].strip("\n\r\b")
            elif (line.startswith("name:")):
                name = line.split(":")[1].strip("\n\r\b")
            else:
                print("Error in " + filename + " line " + str(count) + " : Unknown keyword.")
                exit(1)
    pkginfofile.close()

    if package_id == "" or product == "" or version == "" or description == "":
        print("Warning in " + filename + " : incomplete package definition.")

    source_path = str(pathlib.PurePath(filename).parent)
    return Package(source_path, name, description, product, version, package_id)

def parse_components_definition(filename, package_id, components=None):
    if components == None:
        components = dict()

    with open(filename) as pkgcompfile:
        # parse each line in the components definition file...
        for count, line in enumerate(pkgcompfile):

            # Split the fields
            fields = line.split(";")
            if len(fields) != 3 and len(fields) != 4:
                print("Warning in " + filename + " line " + str(count) + " : Expected 3 or 4 fields, found " + str(len(fields)))
                continue

            # parse first field (name)
            name = fields[0].strip("\n\r\b")

            # parse second field (wildcard list of packages in which the component can be included in)
            packageIds = fields[1].strip("\n\r\b").split(",")
            includeThisComponent = False
            for packageId in packageIds:
                # fnmatch says if the string corresponds to the passed wildcard
                # see https://docs.python.org/3/library/fnmatch.html
                if fnmatch.fnmatch(package_id, packageId):
                    includeThisComponent = True
                    break
            # if this component doesn't refer to the current package_id, don't include it, continue to the next one.
            if includeThisComponent == False:
                continue

            # parse third field (list of files)
            wildcards_paths = fields[2].strip("\n\r\b").split(",")

            # parse fourth field (compression algorithm)
            compression = "lzma" # lzma compression by default
            if len(fields) == 4:
                compression = fields[3].strip("\n\r\b")

            # Find or create the appropriate component
            if not name in components.keys():
                components[name] = Component(name, compression)
            
            # search and append the files for this component
            prefix = str(pathlib.PurePath(filename).parent)
            for wildcards_path in wildcards_paths:
                components[name].append_wildcards_files(prefix + "\\" + wildcards_path)

    pkgcompfile.close()

def deploy(filenames, destination, move=False):
    for filename in filenames:
        real_destination = destination

        if not os.path.isabs(filename):
            sub_path = str(pathlib.PurePath(filename).parent)
            real_destination = destination + "\\" + sub_path

        if not os.path.exists(real_destination + "\\"):
            os.makedirs(real_destination + "\\")

        print("   copying " + filename + " to " + real_destination + "\\")

        if os.path.exists(real_destination + "\\" + filename):
            print("      Warning: " + real_destination + "\\" + filename + " already exists. Overwriting.")
            os.remove(real_destination + "\\" + filename)

        if move == True:
            shutil.move(filename, real_destination + "\\")
        else:
            shutil.copy2(filename, real_destination + "\\")

def remove_and_clean_existing_packages(wideIndex, packages, destination):
    for package in packages:
        for oldPackage in wideIndex.findall("./Package[@Id='" + package.id + "']"):
            print("Package " + package.id + " already exists. Updating index with newly built package.")
            wideIndex.remove(oldPackage)
            if destination != None and destination != "" and os.path.exists(destination + "\\" + package.id):
                shutil.rmtree(destination + "\\" + package.id)

def indentXML(elem, level=0):
    i = "\n" + level*"  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for elem in elem:
            indentXML(elem, level+1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i

def main():
    # param1 input path:                    "D:\wyde\Wynsure"
    # param2 package-index:                 package-index.xml
    # param3 destination:                   C:\inetpub\wwwroot\eWamUpdate
    # optional param4 wipde_destination:    yes

    parser = argparse.ArgumentParser(description="Index and deploy products referenced by *.package-definition and *.package-components")
    parser.add_argument('root_path', help='root path for indexing')
    parser.add_argument('--package-index', help='package index file', default='package-index.xml')
    parser.add_argument('--package-index-policy', choices=['overwrite', 'append', 'update'], help='Decide what to do if package-index already exists: overwrite=overwrite existing, append=append to existing, update=update existing', required=True)
    parser.add_argument('--deploy', help='If provided, should specify where packages files should be deployed. No deployment is done if this argument is not provided.')
    parser.add_argument('--wipe-destination', action='store_true', help='Wipe destination before deploying.')
    parser.add_argument('--version', action='version', version='2018-11-03')

    args = parser.parse_args()

    script_name = sys.argv[0] 
    input_path = args.root_path
    package_index = args.package_index
    destination = args.deploy
    wipe_destination = args.wipe_destination

    if destination != None and wipe_destination and os.path.exists(destination):
        print("Wiping destination folder in 10 seconds...")
        time.sleep(10)
        shutil.rmtree(destination, ignore_errors=False)

    if os.path.exists(package_index) and args.package_index_policy == 'overwrite':
        os.remove(package_index)

    start_dir = os.getcwd()

    # Search for any .package-definition
    os.chdir(input_path)
    package_def_list = []
    package_def_list.extend(glob.glob('**/.package-definition', recursive=True))
    package_def_list.extend(glob.glob('**/*.package-definition', recursive=True))
    if (len(package_def_list) == 0):
        print("Error: no *.package-definition found in '" + input_path)
        exit(1)
        
    # for each package-definition, create a package and find its components
    print("*.package-definition files found:")
    packages = []
    for package_definition in package_def_list:
        print("   - " + package_definition, end="... ")
        # Parse .package-definition file
        os.chdir(input_path)
        package = parse_package_definition(package_definition)
        print(package.id)
        
        # Find all the .package-components files in the sub-tree as .package-definition
        os.chdir(package.source_path)
        components_def_list = []
        components_def_list.extend(glob.glob('**/.package-components', recursive=True))
        components_def_list.extend(glob.glob('**/*.package-components', recursive=True))
        if (len(components_def_list) == 0):
            print("Error: no *.package-components found in '" + package.source_path)
            exit(1)
        
        # Parse all *.package-components found
        components = dict()
        for components_def in components_def_list:
            print("      - " + package.source_path + "\\" + components_def)
            parse_components_definition(components_def, package.id, components)

        package.components.extend(components.values())
        packages.append(package)

    # remove empty components
    for package in packages:
        componentsToRemove = []
        for component in package.components:
            if  component.files == None or len(component.files) == 0:
                componentsToRemove.append(component)
        for component in componentsToRemove:
            package.components.remove(component)
        
    os.chdir(start_dir)
    wideIndex = None
    if (pathlib.Path(package_index).exists()):
        xmlTree = ET.parse(package_index)
        wideIndex = xmlTree.getroot()
        if args.package_index_policy == "update":
            remove_and_clean_existing_packages(wideIndex, packages, destination)
    else:
        wideIndex = ET.Element('WideIndex')

    for package in packages:
        if len(package.components) != 0:
            wideIndex.append(package.to_element_tree())

    indentXML(wideIndex)
    # ET.dump(wideIndex) 
    wideTree = ET.ElementTree(wideIndex)
    wideTree.write(package_index)

    # Zip everything and copy to target destination
    if destination != None and destination != "":
        for package in packages:
            print("Deploying package " + package.id)
            os.chdir(input_path + "\\" + package.source_path)
            for component in package.components:
                if component.compression != None and component.compression != "None" and component.compression != "":
                    # Create component zip
                    print("   Compressing " + component.name + " to .zip archive, using method '" + component.compression + "'...")
                    zip_filename = start_dir + "\\" +  component.name + ".zip"
                    component.create_zip(zip_filename)
                    deploy([ zip_filename ], destination + "\\" + package.id, move=True)
                else:
                    filenames_to_deploy = []
                    for file in component.files:
                        filenames_to_deploy.append(file.path)
                    deploy(filenames_to_deploy, destination + "\\" + package.id)

        # Deploy the package index
        os.chdir(start_dir)
        deploy([package_index], destination)

main()
