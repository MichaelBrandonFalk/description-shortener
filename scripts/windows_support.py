"""App-local Microsoft CRT files from the CI host's licensed Visual Studio redist directory."""
import hashlib,json,os,shutil,subprocess
from pathlib import Path

def bundle(processor):
    if os.name!='nt':raise RuntimeError('Windows runtime preparation requires a Windows build host.')
    tools=Path(os.environ['ProgramFiles(x86)'])/'Microsoft Visual Studio/Installer/vswhere.exe'
    installation=Path(subprocess.check_output([str(tools),'-latest','-products','*','-property','installationPath'],text=True).strip())
    root=installation/'VC/Redist/MSVC'
    folders=[p for p in root.glob('*/x64/Microsoft.VC143.CRT') if p.is_dir()]
    if not folders:raise RuntimeError('The Visual Studio x64 redistributable CRT directory is missing.')
    folder=max(folders,key=lambda p:tuple(int(x) for x in p.relative_to(root).parts[0].split('.')))
    libraries=list(folder.glob('*.dll'))
    required={'msvcp140.dll','vcruntime140.dll','vcruntime140_1.dll'}
    if not required<={p.name.lower() for p in libraries}:raise RuntimeError('Required x64 Microsoft runtime files are missing.')
    metadata={}
    for path in libraries:
        for backend in ['cpu','vulkan']:shutil.copy2(path,processor/'llama'/backend/path.name)
        with path.open('rb') as source:metadata[path.name]=hashlib.file_digest(source,'sha256').hexdigest()
    licenses=processor/'licenses';licenses.mkdir(exist_ok=True)
    (licenses/'Microsoft-Visual-C++-runtime.json').write_text(json.dumps({'source':'Visual Studio x64 Microsoft.VC143.CRT redist directory','version':folder.relative_to(root).parts[0],'sha256':metadata},indent=2)+'\n')
    (licenses/'Microsoft-Visual-C++-runtime-NOTICE.txt').write_text('Microsoft Visual C++ Runtime\nCopyright Microsoft Corporation.\n\nThese Windows DLLs are Microsoft redistributable components, not open-source components and not covered by Description Shortener\'s MIT license. Original binaries are copied from the build host\'s Visual Studio x64 redist directory. Their source version and SHA-256 values are in Microsoft-Visual-C++-runtime.json.\n\nMicrosoft redistribution and local deployment guidance:\nhttps://learn.microsoft.com/en-us/cpp/windows/redistributing-visual-cpp-files\nhttps://learn.microsoft.com/en-us/cpp/windows/choosing-a-deployment-method\n')
    for path in installation.glob('Common7/IDE/*/License.rtf'):
        shutil.copy2(path,licenses/('Microsoft-Visual-Studio-'+path.parent.name+'-License.rtf'))
    return required
