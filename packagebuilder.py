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
import time

# This script is designed to walk a directory tree to find *.package-definition files and associated *.package-components.
# These files contain package definitions to be prepared and deployed to a website, in order to make the packages available to 
# eWamLauncher package puller. 
# 
# Example:
# > python packagebuilder.py D:\wyde\ --package-index-policy overwrite --deploy C:\inetpub\wwwroot\eWamUpdate --wipe-destination

script_version = '2019-01-10'

parser = argparse.ArgumentParser(description="Index and deploy products referenced by *.package-definition and *.package-components")
parser.add_argument('root_pathes', metavar='PATH', nargs='+', help='root path for indexing')
parser.add_argument('--package-index', help='package index file', default='package-index.xml')
parser.add_argument('--package-index-policy', choices=['overwrite', 'append', 'update', 'update-keep-old-packages'], help='Decide what to do if package-index already exists: overwrite=overwrite existing, append=append to existing, update=update existing package-index including removing package, components and files that ate not found anymore, update-keep-old-packages=update but keep old packages that where not found anymore, only update packages', required=True)
parser.add_argument('--deploy', help='If provided, should specify where packages files should be deployed. No deployment is done if this argument is not provided.')
parser.add_argument('--deploy-policy', choices=['wipe', 'update'], help='Decide what to do with existing deployed files: wipe=wipe existing in destination folder, update=update existing files in destination folder includeing remove files, pacakges, components that dont exist anymore. Use update-keep-old-packages for package-index-policy in order to prevent deletion of old packages that you removed from source.')
parser.add_argument('--version', action='version', version=script_version)

args = parser.parse_args()

script_name = sys.argv[0] 
root_pathes = args.root_pathes
package_index_file = args.package_index
package_index_policy = args.package_index_policy
destination = os.path.abspath(args.deploy)
deploy_policy = args.deploy_policy


class PackageIndex:
    """Represents a package index."""

    def __init__(self, packages = []):
        self.packages = packages

    def import_from_xml(self, wideIndexXML):
        """Re-import PackageIndex from XML"""
        for child in wideIndexXML:
            if child.tag == "Package":
                package = Package('', '', '', '', '', '')
                package.import_from_xml(child)
                self.packages.append(package)

    def __getitem__(self, item):
        """Implementation of operator [] with a Package object as parmeter: returns the Package with same id, if exists."""
        return next((x for x in self.packages if item.id == x.id), None)

    def __contains__(self, item):
        """Implementation of operator 'in' : "if package in packageIndex..." : returns true if the Package with same id is found in the PackageIndex."""
        return any((x for x in self.packages if item.id == x.id))

    def append(self, package):
        """Append a package to PackageIndex"""
        self.packages.append(package)
        
    def sort(self):
        """Sort the list of packages by their name"""
        self.packages.sort(key=lambda package:package.id)
        for package in self.packages:
            package.sort()
    
    def to_element_tree(self):
        """Converts to an XML node."""
        wideIndexXML = ET.Element('WideIndex')
        for package in self.packages:
            if len(package.components) != 0 and (package.state != "removed" or package_index_policy == "update-keep-old-packages"):
                wideIndexXML.append(package.to_element_tree())
        return wideIndexXML

class Package:
    """Represents a package. A package is composed of components, each containing files."""

    def __init__(self, source_path, name, description, product, version, package_id):
        self.source_path = source_path
        self.type = str.lower(product)
        self.name = name
        self.description = description
        self.id = package_id
        self.version = version
        self.components = []
        self.state = 'added'

    def import_from_xml(self, packageXML):
        """Re-import Package from XML"""
        self.source_path = ''
        self.type = packageXML.attrib['Type']
        self.name = packageXML.attrib['Name']
        self.description = packageXML.attrib['Description']
        self.id = packageXML.attrib['Id']
        self.version = packageXML.attrib['Version']
        self.components = []
        self.state = 'unchanged'
        for child in packageXML:
            if child.tag == "Component":
                component = Component('', '')
                component.import_from_xml(child)
                self.components.append(component)

    def __getitem__(self, item):
        """Implementation of operator [] with a Component object as parmeter: returns the Component with same name, if exists."""
        return next((x for x in self.components if item.name == x.name), None)

    def __contains__(self, item):
        """Implementation of operator 'in' : "if component in package..." : returns true if the Component with same name is found in the Package."""
        return any((x for x in self.components if item.name == x.name))

    def sort(self):
        """Sort the list of components by their name"""
        self.components.sort(key=lambda component:component.name)
        for component in self.components:
            component.sort()

    def append(self, component):
        """Append a Component to Package"""
        self.components.append(component)

    def to_element_tree(self):
        """Converts to an XML node."""

        packageXML = ET.Element('Package')
        packageXML.set("Type", self.type)
        packageXML.set("Id", self.id)
        packageXML.set("Name", self.name)
        packageXML.set("Version", self.version)
        packageXML.set("Description", self.description)
        # packageXML.set("State", self.state)

        for component in self.components:
            if len(component.files) != 0 and component.state != 'removed':
                packageXML.append(component.to_element_tree())

        return packageXML

class Component:
    """Component contained in a package. A component can be set to have its files compressed in a zip file, if 'compression' is set to deflate, zip lzma, bzip2, or store. 'store' means the files are stored in the zip file without compression. If compression is empty string, component files will be stored raw, not in an archive. The archive container format is always '.zip'. Compression specifies the compression algorithm used."""

    def __init__(self, name, compression="7z"):
        self.name = name
        self.compression = compression
        self.files = []
        self.state = 'added'

    def import_from_xml(self, componentXML):
        """Re-import Component from XML"""
        self.name = componentXML.attrib['Name']
        self.compression = componentXML.attrib['Compression']
        self.files = []
        self.state = 'unchanged'
        for child in componentXML:
            if child.tag == "File":
                componentfile = File('')
                componentfile.import_from_xml(child)
                self.files.append(componentfile)

    def __getitem__(self, item):
        """Implementation of operator [] with a File object as parmeter: returns the File with same path, if exists."""
        return next((x for x in self.files if item.path == x.path), None)

    def __contains__(self, item):
        """Implementation of operator 'in' : "if file in component..." : returns true if the File with same path is found in the Component."""
        return any((x for x in self.files if item.path == x.path))

    def sort(self):
        """Sort the list of files by their path"""
        self.files.sort(key=lambda file:file.path)

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
        found_files = glob.glob(wildcards, recursive=True)
        for found_file in found_files:
            found_file = os.path.normpath(found_file)
            if os.path.isfile(found_file):
                self.append_filepath(found_file)

    def create_zip(self, archive_filename):
        """Create a zip file from Component 'files' list"""
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
        
        if os.path.isfile(archive_filename):
            os.remove(archive_filename)

        with zipfile.ZipFile(archive_filename, mode='w', compression=archive_format) as zip_file:
            for file in self.files:
                zip_file.write(file.path)

    def to_element_tree(self):
        """Converts to an XML node."""
        componentXML = ET.Element("Component")
        componentXML.set("Name", self.name)
        componentXML.set("Compression", self.compression)
        # componentXML.set("State", self.state)

        for componentFile in self.files:
            if componentFile.state != 'removed':
                componentXML.append(componentFile.to_element_tree())

        return componentXML

class File:
    def __init__(self, path):
        self.path = os.path.normpath(path)
        self.hash = ''
        self.calculateHash()
        self.state = 'added'
        
    def import_from_xml(self, fileXML):
        """Re-import File from XML"""
        self.path = fileXML.attrib['Path']
        self.hash = fileXML.attrib['Hash']
        self.state = 'unchanged'

    def calculateHash(self):
        """Calculate MD5 hash if the file"""
        if not os.path.isfile(self.path):
            self.hash = ""
            return

        BLOCKSIZE = 65536
        hasher = hashlib.md5()
        with open(self.path, 'rb') as dataFile:
            buf = dataFile.read(BLOCKSIZE)
            while len(buf) > 0:
                hasher.update(buf)
                buf = dataFile.read(BLOCKSIZE)
        self.hash = hasher.hexdigest()

    def to_element_tree(self):
        """Converts to an XML node."""
        fileXML = ET.Element("File")
        fileXML.set("Path", self.path)
        fileXML.set("Hash", self.hash)
        # fileXML.set("State", self.state)
        return fileXML


def parse_package_definition(filename):
    """Parse the content of a file '[...].package-definition' and return the corresponding Package object."""
    package_id = ""
    product = ""
    version = ""
    description = ""
    # For each line in the file, get the information provided
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

    source_path = os.path.dirname(os.path.abspath(filename))
    return Package(source_path, name, description, product, version, package_id)

def parse_components_definition(filename, package_id, components=None):
    """Parse the content of a file '[...].package-components' and append files and to the passed 'components' dictionary. The dictionary will be created if empty."""
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
    """Deploy files provided in the list of 'filenames' to the provided 'destination' folder. filenames may contain a leading folder, which will be created as sub tree of the destination. Move the file instead of copying if 'move' is True. Creates the path if it doesn't exist. Overwrites destination if exists."""
    for filename in filenames:

        if not os.path.isabs(filename):
            real_destination = destination + '\\' + os.path.dirname(filename)
        else:
            real_destination = destination

        if not os.path.exists(real_destination):
            os.makedirs(real_destination)

        print("   copying " + filename + " to " + real_destination)

        if os.path.isfile(real_destination + '\\' + os.path.basename(filename)):
            print("      Warning: " + real_destination + '\\' + os.path.basename(filename) + " already exists. Overwriting.")
            os.remove(real_destination + '\\' + os.path.basename(filename))

        deploy_success = False
        while not deploy_success:
            try:
                if move == True:
                    shutil.move(filename, real_destination)
                    deploy_success = True
                else:
                    shutil.copy2(filename, real_destination)
                    deploy_success = True
            except:
                print("   Deploy failed... retrying in 10 seconds")
                time.sleep(10)
                pass

def build_pacakge_list(root_dir):
    """Traverses root_dir in search for *.package-definition files, parses them and there corresponding *.package-components files, to build a package list."""
    # Backup cwd
    previous_cwd = os.getcwd()

    # Search for any .package-definition
    os.chdir(root_dir)
    package_def_list = []
    package_def_list.extend(glob.glob('**/.package-definition', recursive=True))
    package_def_list.extend(glob.glob('**/*.package-definition', recursive=True))
    if (len(package_def_list) == 0):
        print("Error: no *.package-definition found in '" + root_dir)
        exit(1)
        
    # for each package-definition, create a package and find its components
    print("*.package-definition files found:")
    packages = []
    for package_definition in package_def_list:
        print("   - " + package_definition, end="... ")
        # Parse .package-definition file
        os.chdir(root_dir)
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

    # Remove empty components
    for package in packages:
        componentsToRemove = []
        for component in package.components:
            if  component.files == None or len(component.files) == 0:
                componentsToRemove.append(component)
        for component in componentsToRemove:
            package.components.remove(component)

    # Restore cwd
    os.chdir(previous_cwd)
    return packages

def make_package_index(packages, package_index_file, old_package_index_file, package_index_policy):
    """Build new PackageIndex object based on new package list and old package list and package index policy (should we update the new index based on old index?)"""
    new_package_index = PackageIndex(packages)
    old_package_index = None
    
    # Create or update package-index.xml

    # if policy is to overwrite : simply overwrite any existing package-index.xml file
    if package_index_policy == 'overwrite':
        if os.path.isfile(package_index_file):
            os.remove(package_index_file)

    # if policy is to append, just append new content found to old existing package-index.xml file
    elif package_index_policy == 'append' and os.path.isfile(old_package_index_file):
        xmlTree = ET.parse(old_package_index_file)
        wideIndexXML = xmlTree.getroot()
        old_package_index = PackageIndex()
        old_package_index.import_from_xml(wideIndexXML)
        for package in new_package_index.packages:
            old_package_index.append(package)
        new_package_index = old_package_index

    # if policy is to update, compare newly created index with old index, and set up accordingly the "state" attribute of each package/component/file. This will be used in deployment phase (deploy_packages).
    elif package_index_policy == 'update' or package_index_policy == 'update-keep-old-packages' and os.path.isfile(old_package_index_file):
        xmlTree = ET.parse(old_package_index_file)
        wideIndexXML = xmlTree.getroot()
        old_package_index = PackageIndex()
        old_package_index.import_from_xml(wideIndexXML)
        
        # look for modified/added packages/components/files
        for package in new_package_index.packages:
            if package in old_package_index:
                package.state = 'unchanged'
            else:
                package.state = 'added'
                continue

            old_package = old_package_index[package]

            for component in package.components:
                if component in old_package:
                    component.state = 'unchanged'
                else:
                    component.state = 'added'
                    package.state = 'modified'
                    continue

                old_component = old_package[component]

                if component.compression != old_component.compression:
                    component.state = 'modifiedcompression'
                    package.state = 'modified'

                for componentFile in component.files:
                    if componentFile in old_component:
                        componentFile.state = 'unchanged'
                    else:
                        componentFile.state = 'added'
                        component.state = 'modified'
                        package.state = 'modified'
                        continue

                    old_file = old_component[componentFile]

                    if componentFile.hash != old_file.hash:
                        componentFile.state = 'modified'
                        component.state = 'modified'
                        package.state = 'modified'

        # look for removed packages/components/files
        for package in old_package_index.packages:
            if not package in new_package_index:
                if package_index_policy != 'update-keep-old-packages':
                    package.state = 'removed'
                else:
                    package.state = 'unchanged'
                new_package_index.append(package)
                continue

            for component in package.components:
                if not component in new_package_index[package]:
                    new_package_index[package].state = 'modified'
                    component.state = 'removed'
                    new_package_index[package].append(component)
                    continue

                for componentFile in component.files:
                    if not componentFile in new_package_index[package][component]:
                        componentFile.state = 'removed'
                        new_package_index[package][component].state = 'modified'
                        new_package_index[package].state = 'modified'
                        new_package_index[package][component].append_file(componentFile)
                        continue

    new_package_index.sort()

    # Write package index
    wideIndexXML = new_package_index.to_element_tree()
    indentXML(wideIndexXML)
    wideTree = ET.ElementTree(wideIndexXML)
    wideTree.write(package_index_file)

    return new_package_index

def indentXML(elem, level=0):
    """Indent XML when generating it"""
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

def deploy_packages(package_index_file, new_package_index, destination, deploy_policy):
    """Deploy files from package index. Use 'state' attribute to know if the package/component/file has been modified, added, removed or is unchanged, thus deciding what to do about it, depending on the deploy_policy"""
    print("Deploying...")

    # backup cwd
    tmp_dir = os.getcwd()

    if deploy_policy == 'wipe' and os.path.exists(destination):
        print("Wiping destination folder " + destination + "...")
        shutil.rmtree(destination, ignore_errors=False)

    # Zip everything (if needed) and copy to target destination
    for package in new_package_index.packages:
        
        # if the package is marked as unchanged, just skip it
        if deploy_policy == 'update' and package.state == "unchanged":
            print("unchanged package '" + package.id)
            continue
        
        # if package is marked as removed, delete its destination
        if deploy_policy == 'update' and package.state == "removed":
            print("removed package '" + package.id)
            shutil.rmtree(destination + "\\" + package.id, ignore_errors=False)
            continue

        # for each component of the package
        print("deploying package " + package.id)
        os.chdir(package.source_path)
        for component in package.components:

            # if component is marked as unchanged, skip it
            if deploy_policy == 'update' and component.state == "unchanged":
                continue

            # If component compression has changed, just remove any existing file, the component will be re-generated (zip or raw files of the component)
            if deploy_policy == 'update' and component.state == "modifiedcompression":
                
                print("   changed compression of '" + component.name + "' to " + component.compression)

                zip_filename = component.name + ".zip"
                if os.path.isfile(destination + "\\" + package.id + '\\' + zip_filename):
                    os.remove(destination + "\\" + package.id + '\\' + zip_filename)

                for file in component.files:
                    if os.path.isfile(destination + "\\" + package.id + '\\' + file.path):
                        os.remove(destination + "\\" + package.id + '\\' + file.path)

            # if the component is marked for compression, put all its files in a zip file named after the component
            if component.compression != None and component.compression != "None" and component.compression != "":

                zip_filename = component.name + ".zip"
                
                # if the component has been marked as removed, remove its corresponding archive if it exists
                if deploy_policy == 'update' and component.state == "removed":
                    if os.path.isfile(destination + "\\" + package.id + '\\' + zip_filename):
                        print("   component '" + component.name + "' : removed")
                        os.remove(destination + "\\" + package.id + '\\' + zip_filename)
                    continue

                # Create component zip
                print("   Compressing " + component.name + " to .zip archive, using method '" + component.compression + "'...")
                component.create_zip(tmp_dir + "\\" + zip_filename)
                deploy([ tmp_dir + "\\" + zip_filename ], destination + "\\" + package.id, move=True)

            # if the component is not marked for compression, simply deploy the files of the component
            else:

                # if the component is marked as removed, delete each of his existing already deployed files
                if deploy_policy == 'update' and component.state == "removed":
                    print("   component '" + component.name + "' : removed, removing files:")
                    for file in component.files:
                        if os.path.isfile(destination + "\\" + package.id + '\\' + file.path):
                            print("      file '" + file.path + "' : removed")
                            os.remove(destination + "\\" + package.id + '\\' + file.path)
                    continue

                # for each file of the component...
                filenames_to_deploy = []
                for file in component.files:

                    # if the file is marked as removed, remove its pre-existing instance
                    if deploy_policy == 'update' and file.state == "removed":
                        if os.path.isfile(destination + "\\" + package.id + '\\' + file.path):
                            print("      file '" + file.path + "' : removed")
                            os.remove(destination + "\\" + package.id + '\\' + file.path)
                            
                    # otherwise just add the file to the list of files to deploy
                    else:
                        filenames_to_deploy.append(file.path)
                
                deploy(filenames_to_deploy, destination + "\\" + package.id)


    os.chdir(tmp_dir)

    # Deploy newly created package-index
    print("Deploying " + package_index_file + "...")
    deploy([ package_index_file ], destination, move=False)

def main():
    # Gather packages/components/files list from **/.package-definition and **/.package-components files
    packages = []
    for root_path in root_pathes:
        root_path = os.path.abspath(root_path)
        packages.extend(build_pacakge_list(root_path))

    #Build new package index, and generate package-index XML file
    old_package_index_file = package_index_file
    if destination != None and destination != "":
        old_package_index_file = destination + "\\" + package_index_file
    new_package_index = make_package_index(packages, package_index_file, old_package_index_file, package_index_policy)

    # Deploy
    if destination != None and destination != "":
        deploy_packages(package_index_file, new_package_index, destination, deploy_policy)

main()