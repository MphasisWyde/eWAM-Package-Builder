using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Xml;
using System.IO;
using System.Diagnostics;
using System.Reflection;

namespace eWAM_PackageMaker
{
   class Program
   {
      static void Main(string[] args)
      {
         string rootFolder = "";
         string outputIndexFile = "";
         string product = "";
         string version = "";
         string description = "";
         string uniqueId = "";
         string deployDestination = "";

         if (args.Length != 6 && args.Length != 7)
         {
            Console.WriteLine("Usage: " + Assembly.GetEntryAssembly().GetName().Name + " <root folder> <output index file> <product> <version> <description> <unique id> [deploy destination]");
            return;
         }
         else
         {
            rootFolder = Path.GetFullPath(args[0]);
            outputIndexFile = args[1];
            product = args[2];
            version = args[3];
            description = args[4];
            uniqueId = args[5].ToLower().Replace(' ', '-');
            if (args.Length == 7)
            {
               deployDestination = args[6];
            }
         }

         //Create the XmlDocument.
         XmlDocument doc = new XmlDocument();
         XmlElement rootNode;

         if (File.Exists(outputIndexFile))
         {
            doc.Load(outputIndexFile);
            rootNode = (XmlElement)doc.FirstChild;
            if (rootNode.Name != "WideIndex")
            {
               throw new Exception("Couldn't find root node \"WideIndex\".");
            }
         }
         else
         {
            rootNode = doc.CreateElement("WideIndex");
            doc.AppendChild(rootNode);
         }

         List<string> bins = new List<string>();
         List<string> pdbs = new List<string>();
         List<string> dcls = new List<string>();
         List<string> src = new List<string>();
         List<string> maps = new List<string>();
         List<string> wwconf = new List<string>();
         List<string> admin = new List<string>();
         List<string> envdefs = new List<string>();
         List<string> binsets= new List<string>();
         List<string> tgvs = new List<string>();
         //+ BMPs
         //+ Documentation
         //+ Compress stuffs

         List<KeyValuePair<string, string>> filesToCopy = new List<KeyValuePair<string, string>>();

         //Binaries
         try
         {
            bins.Clear();
            bins.AddRange(StripPrefix(rootFolder, Directory.GetFiles(rootFolder, "*.exe", SearchOption.AllDirectories)));
            bins.AddRange(StripPrefix(rootFolder, Directory.GetFiles(rootFolder, "*.dll", SearchOption.AllDirectories)));
         }
         catch (Exception e)
         {
            System.Console.Out.WriteLine("Exception ! " + e.Message);
         }

         //Debug symbols
         try
         {
            pdbs.Clear();
            pdbs.AddRange(StripPrefix(rootFolder, Directory.GetFiles(rootFolder, "*.pdb", SearchOption.AllDirectories)));
         }
         catch (Exception e)
         {
            System.Console.Out.WriteLine("Exception ! " + e.Message);
         }

         //DCLs
         try
         {
            dcls.Clear();
            dcls.AddRange(StripPrefix(rootFolder, Directory.GetFiles(rootFolder, "*.dcl", SearchOption.AllDirectories)));
         }
         catch (Exception e)
         {
            System.Console.Out.WriteLine("Exception ! " + e.Message);
         }

         //Sources
         try
         {
            src.Clear();
            src.AddRange(StripPrefix(rootFolder, Directory.GetFiles(rootFolder, "*.h", SearchOption.AllDirectories)));
            src.AddRange(StripPrefix(rootFolder, Directory.GetFiles(rootFolder, "*.hpp", SearchOption.AllDirectories)));
            src.AddRange(StripPrefix(rootFolder, Directory.GetFiles(rootFolder, "*.cpp", SearchOption.AllDirectories)));
            src.AddRange(StripPrefix(rootFolder, Directory.GetFiles(rootFolder, "*.req", SearchOption.AllDirectories)));
         }
         catch (Exception e)
         {
            System.Console.Out.WriteLine("Exception ! " + e.Message);
         }

         //.map files
         try
         {
            maps.Clear();
            maps.AddRange(StripPrefix(rootFolder, Directory.GetFiles(rootFolder, "*.map", SearchOption.TopDirectoryOnly)));
         }
         catch (Exception e)
         {
            System.Console.Out.WriteLine("Exception ! " + e.Message);
         }

         //wnetconf.ini
         try
         {
            wwconf.Clear();
            wwconf.AddRange(StripPrefix(rootFolder, Directory.GetFiles(rootFolder, "wnetconf.ini", SearchOption.TopDirectoryOnly)));
         }
         catch (Exception e)
         {
            System.Console.Out.WriteLine("Exception ! " + e.Message);
         }

         //Admin
         try
         {
            admin.Clear();
            admin.AddRange(StripPrefix(rootFolder, Directory.GetFiles(rootFolder + "\\admin", "*", SearchOption.AllDirectories)));
         }
         catch (Exception e)
         {
            System.Console.Out.WriteLine("Exception ! " + e.Message);
         }

         //Environments / launchers definitions
         try
         {
            envdefs.Clear();
            envdefs.AddRange(StripPrefix(rootFolder, Directory.GetFiles(rootFolder, "*.jsenv", SearchOption.AllDirectories)));
            envdefs.AddRange(StripPrefix(rootFolder, Directory.GetFiles(rootFolder, "*.xenv", SearchOption.AllDirectories)));
         }
         catch (Exception e)
         {
            System.Console.Out.WriteLine("Exception ! " + e.Message);
         }

         //Binaries sets definitions
         try
         {
            binsets.Clear();
            binsets.AddRange(StripPrefix(rootFolder, Directory.GetFiles(rootFolder, "*.jswam", SearchOption.AllDirectories)));
            binsets.AddRange(StripPrefix(rootFolder, Directory.GetFiles(rootFolder, "*.xwam", SearchOption.AllDirectories)));
         }
         catch (Exception e)
         {
            System.Console.Out.WriteLine("Exception ! " + e.Message);
         }

         //TGVs
         try
         {
            tgvs.Clear();
            tgvs.AddRange(StripPrefix(rootFolder, Directory.GetFiles(rootFolder, "#####AntiSharedFile.tmp", SearchOption.AllDirectories)));
            tgvs.AddRange(StripPrefix(rootFolder, Directory.GetFiles(rootFolder, "W001001.TGV", SearchOption.AllDirectories)));
            tgvs.AddRange(StripPrefix(rootFolder, Directory.GetFiles(rootFolder, "W003001.TGV", SearchOption.AllDirectories)));
            tgvs.AddRange(StripPrefix(rootFolder, Directory.GetFiles(rootFolder, "W007001.TGV", SearchOption.AllDirectories)));
         }
         catch (Exception e)
         {
            System.Console.Out.WriteLine("Exception ! " + e.Message);
         }



         XmlAttribute attribute;

         XmlElement packageElement = doc.CreateElement("Package");
         attribute = doc.CreateAttribute("Type");
         attribute.Value = "ewam"; //by opposition to "environment"
         packageElement.Attributes.Append(attribute);
         attribute = doc.CreateAttribute("Id");
         attribute.Value = uniqueId;
         packageElement.Attributes.Append(attribute);
         attribute = doc.CreateAttribute("Name");
         attribute.Value = product;
         packageElement.Attributes.Append(attribute);
         attribute = doc.CreateAttribute("Version");
         attribute.Value = version;
         packageElement.Attributes.Append(attribute);
         attribute = doc.CreateAttribute("Description");
         attribute.Value = description;
         packageElement.Attributes.Append(attribute);

         XmlElement fileElement;

         //Binaries
         if (bins.Count > 0)
         {
            XmlElement binariesElement = doc.CreateElement("Component");
            attribute = doc.CreateAttribute("Name");
            attribute.Value = "Binaries";
            binariesElement.Attributes.Append(attribute);
            foreach (string file in bins)
            {
               fileElement = doc.CreateElement("File");
               attribute = doc.CreateAttribute("Path");
               attribute.Value = file;
               fileElement.Attributes.Append(attribute);

               if (GetDllMachineType(rootFolder + "\\" + file) == MachineType.IMAGE_FILE_MACHINE_I386)
               {
                  attribute = doc.CreateAttribute("Plateform");
                  attribute.Value = "win32";
                  fileElement.Attributes.Append(attribute);
               }
               else if (GetDllMachineType(rootFolder + "\\" + file) == MachineType.IMAGE_FILE_MACHINE_AMD64)
               {
                  attribute = doc.CreateAttribute("Plateform");
                  attribute.Value = "x64";
                  fileElement.Attributes.Append(attribute);
               }

               attribute = doc.CreateAttribute("Version");
               FileVersionInfo assemblyInfoVersion = FileVersionInfo.GetVersionInfo(rootFolder + "\\" + file);
               attribute.Value = assemblyInfoVersion.FileVersion;
               fileElement.Attributes.Append(attribute);

               binariesElement.AppendChild(fileElement);

               if (deployDestination != "")
               {
                  filesToCopy.Add(new KeyValuePair<string, string>(
                     Path.GetFullPath(rootFolder + "\\" + file),
                     Path.GetFullPath(deployDestination + "\\" + uniqueId + "\\" + file)));
               }
            }
            foreach (string file in dcls)
            {
               fileElement = doc.CreateElement("File");
               attribute = doc.CreateAttribute("Path");
               attribute.Value = file;
               fileElement.Attributes.Append(attribute);

               binariesElement.AppendChild(fileElement);

               if (deployDestination != "")
               {
                  filesToCopy.Add(new KeyValuePair<string, string>(
                     Path.GetFullPath(rootFolder + "\\" + file),
                     Path.GetFullPath(deployDestination + "\\" + uniqueId + "\\" + file)));
               }
            }
            packageElement.AppendChild(binariesElement);
         }

         //Symbols
         if (pdbs.Count > 0)
         {
            XmlElement symbolsElement = doc.CreateElement("Component");
            attribute = doc.CreateAttribute("Name");
            attribute.Value = "Symbols";
            symbolsElement.Attributes.Append(attribute);
            foreach (string file in pdbs)
            {
               fileElement = doc.CreateElement("File");
               attribute = doc.CreateAttribute("Path");
               attribute.Value = file;
               fileElement.Attributes.Append(attribute);

               symbolsElement.AppendChild(fileElement);

               if (deployDestination != "")
               {
                  filesToCopy.Add(new KeyValuePair<string, string>(
                     Path.GetFullPath(rootFolder + "\\" + file),
                     Path.GetFullPath(deployDestination + "\\" + uniqueId + "\\" + file)));
               }
            }
            packageElement.AppendChild(symbolsElement);
         }

         //Source
         if (src.Count > 0)
         {
            XmlElement sourceElement = doc.CreateElement("Component");
            attribute = doc.CreateAttribute("Name");
            attribute.Value = "Source";
            sourceElement.Attributes.Append(attribute);
            foreach (string file in src)
            {
               fileElement = doc.CreateElement("File");
               attribute = doc.CreateAttribute("Path");
               attribute.Value = file;
               fileElement.Attributes.Append(attribute);

               sourceElement.AppendChild(fileElement);

               if (deployDestination != "")
               {
                  filesToCopy.Add(new KeyValuePair<string, string>(
                     Path.GetFullPath(rootFolder + "\\" + file),
                     Path.GetFullPath(deployDestination + "\\" + uniqueId + "\\" + file)));
               }
            }
            packageElement.AppendChild(sourceElement);
         }

         //.map files
         if (maps.Count > 0)
         {
            XmlElement mapsElement = doc.CreateElement("Component");
            attribute = doc.CreateAttribute("Name");
            attribute.Value = "Maps";
            mapsElement.Attributes.Append(attribute);
            foreach (string file in maps)
            {
               fileElement = doc.CreateElement("File");
               attribute = doc.CreateAttribute("Path");
               attribute.Value = file;
               fileElement.Attributes.Append(attribute);

               mapsElement.AppendChild(fileElement);

               if (deployDestination != "")
               {
                  filesToCopy.Add(new KeyValuePair<string, string>(
                     Path.GetFullPath(rootFolder + "\\" + file),
                     Path.GetFullPath(deployDestination + "\\" + uniqueId + "\\" + file)));
               }
            }
            packageElement.AppendChild(mapsElement);
         }

         //wnetconf.ini
         if (wwconf.Count > 0)
         {
            XmlElement wnetconfElement = doc.CreateElement("Component");
            attribute = doc.CreateAttribute("Name");
            attribute.Value = "wNetConf";
            wnetconfElement.Attributes.Append(attribute);
            foreach (string file in wwconf)
            {
               fileElement = doc.CreateElement("File");
               attribute = doc.CreateAttribute("Path");
               attribute.Value = file;
               fileElement.Attributes.Append(attribute);

               wnetconfElement.AppendChild(fileElement);

               if (deployDestination != "")
               {
                  filesToCopy.Add(new KeyValuePair<string, string>(
                     Path.GetFullPath(rootFolder + "\\" + file),
                     Path.GetFullPath(deployDestination + "\\" + uniqueId + "\\" + file)));
               }
            }
            packageElement.AppendChild(wnetconfElement);
         }

         //Admin
         if (admin.Count > 0)
         {
            XmlElement adminElement = doc.CreateElement("Component");
            attribute = doc.CreateAttribute("Name");
            attribute.Value = "Admin";
            adminElement.Attributes.Append(attribute);
            foreach (string file in admin)
            {
               fileElement = doc.CreateElement("File");
               attribute = doc.CreateAttribute("Path");
               attribute.Value = file;
               fileElement.Attributes.Append(attribute);

               adminElement.AppendChild(fileElement);

               if (deployDestination != "")
               {
                  filesToCopy.Add(new KeyValuePair<string, string>(
                     Path.GetFullPath(rootFolder + "\\" + file),
                     Path.GetFullPath(deployDestination + "\\" + uniqueId + "\\" + file)));
               }
            }
            packageElement.AppendChild(adminElement);
         }

         //Environments
         if (envdefs.Count > 0)
         {
            XmlElement envdefElement = doc.CreateElement("Component");
            attribute = doc.CreateAttribute("Name");
            attribute.Value = "Launchers";
            envdefElement.Attributes.Append(attribute);
            foreach (string file in envdefs)
            {
               fileElement = doc.CreateElement("File");
               attribute = doc.CreateAttribute("Path");
               attribute.Value = file;
               fileElement.Attributes.Append(attribute);

               envdefElement.AppendChild(fileElement);

               if (deployDestination != "")
               {
                  filesToCopy.Add(new KeyValuePair<string, string>(
                     Path.GetFullPath(rootFolder + "\\" + file),
                     Path.GetFullPath(deployDestination + "\\" + uniqueId + "\\" + file)));
               }
            }
            packageElement.AppendChild(envdefElement);
         }


         //Binaries sets definitions
         if (binsets.Count > 0)
         {
            XmlElement binsetsElement = doc.CreateElement("Component");
            attribute = doc.CreateAttribute("Name");
            attribute.Value = "BinariesSets";
            binsetsElement.Attributes.Append(attribute);
            foreach (string file in binsets)
            {
               fileElement = doc.CreateElement("File");
               attribute = doc.CreateAttribute("Path");
               attribute.Value = file;
               fileElement.Attributes.Append(attribute);

               binsetsElement.AppendChild(fileElement);

               if (deployDestination != "")
               {
                  filesToCopy.Add(new KeyValuePair<string, string>(
                     Path.GetFullPath(rootFolder + "\\" + file),
                     Path.GetFullPath(deployDestination + "\\" + uniqueId + "\\" + file)));
               }
            }
            packageElement.AppendChild(binsetsElement);
         }

         //TGVs
         if (tgvs.Count > 0)
         {
            XmlElement tgvsElement = doc.CreateElement("Component");
            attribute = doc.CreateAttribute("Name");
            attribute.Value = "TGVs";
            tgvsElement.Attributes.Append(attribute);
            foreach (string file in tgvs)
            {
               fileElement = doc.CreateElement("File");
               attribute = doc.CreateAttribute("Path");
               attribute.Value = file;
               fileElement.Attributes.Append(attribute);

               tgvsElement.AppendChild(fileElement);

               if (deployDestination != "")
               {
                  filesToCopy.Add(new KeyValuePair<string, string>(
                     Path.GetFullPath(rootFolder + "\\" + file),
                     Path.GetFullPath(deployDestination + "\\" + uniqueId + "\\" + file)));
               }
            }
            packageElement.AppendChild(tgvsElement);
         }


         rootNode.AppendChild(packageElement);

         doc.Save(outputIndexFile);

         if (deployDestination != "")
         {
            foreach (KeyValuePair<string, string> deployment in filesToCopy)
            {
               string targetPath = Path.GetDirectoryName(deployment.Value);
               if (!Directory.Exists(targetPath))
               {
                  Directory.CreateDirectory(targetPath);
               }

               File.Copy(deployment.Key, deployment.Value, true);
            }
         }
      }

      static List<string> StripPrefix(string prefix, string[] files)
      {
         List<string> result = new List<string>();

         string normalizePrefix = Path.GetFullPath(new Uri(prefix).LocalPath)
            .TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);

         foreach (string file in files)
         {
            string normalizedFile = Path.GetFullPath(new Uri(file).LocalPath)
               .TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);

            if (file.StartsWith(normalizePrefix))
            {
               result.Add( normalizedFile.Substring(normalizePrefix.Length + 1) );
            }
         }

         return result;
      }

      public static MachineType GetDllMachineType(string dllPath)
      {
         // See http://www.microsoft.com/whdc/system/platform/firmware/PECOFF.mspx
         // Offset to PE header is always at 0x3C.
         // The PE header starts with "PE\0\0" =  0x50 0x45 0x00 0x00,
         // followed by a 2-byte machine type field (see the document above for the enum).
         //
         FileStream fs = new FileStream(dllPath, FileMode.Open, FileAccess.Read);
         BinaryReader br = new BinaryReader(fs);
         fs.Seek(0x3c, SeekOrigin.Begin);
         Int32 peOffset = br.ReadInt32();
         fs.Seek(peOffset, SeekOrigin.Begin);
         UInt32 peHead = br.ReadUInt32();

         if (peHead != 0x00004550) // "PE\0\0", little-endian
            throw new Exception("Can't find PE header");

         MachineType machineType = (MachineType)br.ReadUInt16();
         br.Close();
         fs.Close();
         return machineType;
      }

      public enum MachineType : ushort
      {
         IMAGE_FILE_MACHINE_UNKNOWN = 0x0,
         IMAGE_FILE_MACHINE_AM33 = 0x1d3,
         IMAGE_FILE_MACHINE_AMD64 = 0x8664,
         IMAGE_FILE_MACHINE_ARM = 0x1c0,
         IMAGE_FILE_MACHINE_EBC = 0xebc,
         IMAGE_FILE_MACHINE_I386 = 0x14c,
         IMAGE_FILE_MACHINE_IA64 = 0x200,
         IMAGE_FILE_MACHINE_M32R = 0x9041,
         IMAGE_FILE_MACHINE_MIPS16 = 0x266,
         IMAGE_FILE_MACHINE_MIPSFPU = 0x366,
         IMAGE_FILE_MACHINE_MIPSFPU16 = 0x466,
         IMAGE_FILE_MACHINE_POWERPC = 0x1f0,
         IMAGE_FILE_MACHINE_POWERPCFP = 0x1f1,
         IMAGE_FILE_MACHINE_R4000 = 0x166,
         IMAGE_FILE_MACHINE_SH3 = 0x1a2,
         IMAGE_FILE_MACHINE_SH3DSP = 0x1a3,
         IMAGE_FILE_MACHINE_SH4 = 0x1a6,
         IMAGE_FILE_MACHINE_SH5 = 0x1a8,
         IMAGE_FILE_MACHINE_THUMB = 0x1c2,
         IMAGE_FILE_MACHINE_WCEMIPSV2 = 0x169,
      }


   }
}
