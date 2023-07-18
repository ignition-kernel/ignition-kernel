from zipfile import ZipFile
from git_semver_tags import Version
import os, sys, re


def unpack_project_export(zip_filename):
    src_file = os.path.abspath('./dist/%s' % (zip_filename,))

    project_scripts_dir = os.path.abspath('./python')
    webdev_scripts_dir = os.path.abspath('./webdev')

    with ZipFile(src_file, 'r') as projzip:
        
        for filepath in projzip.namelist():
            if filepath.endswith('/resource.json'):
                continue

            if 'ignition/script-python/' in filepath and filepath.endswith('/code.py'):
                sub_path = filepath[len('ignition/script-python/'):-len('/code.py')]                
                dst_path = os.path.abspath(os.path.join(project_scripts_dir, sub_path + '.py'))

            elif 'com.inductiveautomation.webdev' in filepath:
                sub_path = filepath[len('com.inductiveautomation.webdev/resources/'):]
                dst_path = os.path.abspath(os.path.join(webdev_scripts_dir, sub_path))
            else:
                continue

            os.makedirs(os.path.dirname(dst_path),exist_ok=True)

            with open(dst_path, 'wb') as write_file:
                with projzip.open(filepath, 'r') as read_zip:
                    write_file.write(read_zip.read())



def latest_export_version(version_filter=None, search_root='./dist/'):
    EXPORT_FILENAME_PATTERN = re.compile('(?P<project>.+)_(?P<version>v.+).zip', re.I)

    desired_version = Version(version_filter)

    export_bundles = []
    for filename in os.listdir(search_root):
        
        matched = EXPORT_FILENAME_PATTERN.match(filename)
        
        if not matched:
            continue
        
        version = Version(matched.groupdict()['version'])
        
        if not version in desired_version:
            continue

        export_bundles.append((version, filename))
        
    export_bundles.sort(reverse=True)

    return export_bundles[0][1]



if __name__ == '__main__':

    if len(sys.argv) > 1:
        version_filter = sys.argv[1]
    else:
        version_filter = None

    project_export = latest_export_version(version_filter)

    print('Unpacking %s' % (project_export,))
    unpack_project_export(project_export)


