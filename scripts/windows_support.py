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

def verify_loaded(helper_pid,processor):
    """Confirm the actual llama process loads the shipped CRT, rather than the CI system copy."""
    import ctypes
    from ctypes import wintypes
    kernel=ctypes.WinDLL('kernel32',use_last_error=True);psapi=ctypes.WinDLL('psapi',use_last_error=True)
    class Entry(ctypes.Structure):
        _fields_=[('dwSize',wintypes.DWORD),('cntUsage',wintypes.DWORD),('pid',wintypes.DWORD),('heap',ctypes.c_size_t),('module',wintypes.DWORD),('threads',wintypes.DWORD),('parent',wintypes.DWORD),('priority',wintypes.LONG),('flags',wintypes.DWORD),('name',wintypes.WCHAR*260)]
    kernel.CreateToolhelp32Snapshot.argtypes=[wintypes.DWORD,wintypes.DWORD];kernel.CreateToolhelp32Snapshot.restype=wintypes.HANDLE
    kernel.Process32FirstW.argtypes=kernel.Process32NextW.argtypes=[wintypes.HANDLE,ctypes.POINTER(Entry)]
    kernel.CloseHandle.argtypes=[wintypes.HANDLE]
    snapshot=kernel.CreateToolhelp32Snapshot(2,0)
    if snapshot==ctypes.c_void_p(-1).value:raise ctypes.WinError(ctypes.get_last_error())
    pid=None
    try:
        entry=Entry();entry.dwSize=ctypes.sizeof(entry);more=kernel.Process32FirstW(snapshot,ctypes.byref(entry))
        while more:
            if entry.parent==helper_pid and entry.name.lower()=='llama-server.exe':pid=entry.pid;break
            more=kernel.Process32NextW(snapshot,ctypes.byref(entry))
    finally:kernel.CloseHandle(snapshot)
    if not pid:raise AssertionError('The helper-owned native model process was not found.')
    kernel.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD];kernel.OpenProcess.restype=wintypes.HANDLE
    handle=kernel.OpenProcess(0x410,False,pid)
    if not handle:raise ctypes.WinError(ctypes.get_last_error())
    psapi.EnumProcessModulesEx.argtypes=[wintypes.HANDLE,ctypes.POINTER(wintypes.HMODULE),wintypes.DWORD,ctypes.POINTER(wintypes.DWORD),wintypes.DWORD]
    psapi.GetModuleFileNameExW.argtypes=[wintypes.HANDLE,wintypes.HMODULE,wintypes.LPWSTR,wintypes.DWORD]
    required={'msvcp140.dll','vcruntime140.dll','vcruntime140_1.dll'};found=set()
    try:
        modules=(wintypes.HMODULE*1024)();needed=wintypes.DWORD()
        if not psapi.EnumProcessModulesEx(handle,modules,ctypes.sizeof(modules),ctypes.byref(needed),3):raise ctypes.WinError(ctypes.get_last_error())
        assert needed.value<=ctypes.sizeof(modules)
        for module in modules[:needed.value//ctypes.sizeof(wintypes.HMODULE)]:
            name=ctypes.create_unicode_buffer(32768)
            if not psapi.GetModuleFileNameExW(handle,module,name,len(name)):raise ctypes.WinError(ctypes.get_last_error())
            path=Path(name.value)
            if path.name.lower() in required:
                assert path.parent.resolve()==(processor/'llama/cpu').resolve(),path.name+' was loaded from outside the app.'
                found.add(path.name.lower())
        assert found==required,required-found
    finally:kernel.CloseHandle(handle)
    print('The native Windows model loaded all required C++ runtime DLLs from the app folder.',flush=True)
