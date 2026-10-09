#!/usr/bin/env python3
"""Build one immutable, self-contained macOS app version."""
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
VERSION = (ROOT/'VERSION').read_text().strip()
APP = ROOT/'dist'/f'Description Shortener V{VERSION}.app'
ZIP = ROOT/'downloads'/f'Description-Shortener-V{VERSION}-Apple-Silicon.zip'
MODEL_SHA = '9c6e0763577125a994a9bea0bbd7a737ac4498b8a6a4e0f788727553af1806c9'
if ZIP.exists(): raise SystemExit('This version is already packaged. Bump VERSION before building another release.')
if hashlib.file_digest(open(ROOT/'vendor/model.gguf','rb'),'sha256').hexdigest() != MODEL_SHA:
    raise SystemExit('Model checksum mismatch.')

def run(args): subprocess.run([str(a) for a in args], check=True)
run([sys.executable,'-m','unittest','discover','-s','tests'])
iconset = ROOT/'build/AppIcon.iconset'
iconset.mkdir(parents=True, exist_ok=True)
run(['xcrun','swift','-module-cache-path',ROOT/'build/swift-cache','scripts/make_icon.swift',ROOT/'build/icon-1024.png'])
for size in [16,32,128,256,512]:
    for multiplier in [1,2]:
        pixels=size*multiplier
        suffix='@2x' if multiplier==2 else ''
        run(['sips','-z',pixels,pixels,ROOT/'build/icon-1024.png','--out',iconset/f'icon_{size}x{size}{suffix}.png'])
run(['iconutil','-c','icns',iconset,'-o',ROOT/'build/AppIcon.icns'])
run([sys.executable,'-m','PyInstaller','--noconfirm','--clean','--onedir','--name','shortener-helper',
     '--distpath','build/helper-dist','--workpath','build/helper-work','--specpath','build','src/engine.py'])
if APP.exists(): shutil.rmtree(APP)
resources = APP/'Contents/Resources'
macos = APP/'Contents/MacOS'
resources.mkdir(parents=True); macos.mkdir(parents=True)
run(['xcrun','swiftc','-parse-as-library','-O','-target','arm64-apple-macos14.0','src/DescriptionShortener.swift',
     '-o',macos/'DescriptionShortener','-module-cache-path',ROOT/'build/swift-cache'])
shutil.copytree(ROOT/'build/helper-dist/shortener-helper',resources/'helper',symlinks=True)
shutil.copyfile(ROOT/'vendor/model.gguf',resources/'model.gguf')
llama = resources/'llama'; llama.mkdir()
for p in (ROOT/'vendor/llama-b11531').iterdir():
    if p.name == 'llama-server' or p.name.endswith(('.dylib','.metallib')):
        if p.is_symlink(): (llama/p.name).symlink_to(os.readlink(p))
        else: shutil.copy2(p,llama/p.name)
licenses = resources/'licenses'
shutil.copytree(ROOT/'licenses',licenses)
# Include exact third-party metadata and notices from installed Python distributions.
for package in ['lxml','pyinstaller','altgraph','macholib','packaging','setuptools','pyinstaller-hooks-contrib']:
    distribution = importlib.metadata.distribution(package)
    target = licenses/package; target.mkdir(exist_ok=True)
    for entry in distribution.files or []:
        if any(x in entry.name.lower() for x in ['license','copying','notice']) and distribution.locate_file(entry).is_file():
            shutil.copy2(distribution.locate_file(entry),target/entry.name)
shutil.copy2(ROOT/'vendor/llama-b11531/LICENSE',licenses/'llama.cpp-LICENSE')
python_license = Path(sys.base_prefix)/'LICENSE.txt'
if python_license.exists(): shutil.copy2(python_license,licenses/'Python-LICENSE.txt')
shutil.copy2(ROOT/'docs/research.md',licenses/'research.md')
shutil.copy2(ROOT/'THIRD_PARTY_NOTICES.md',licenses/'THIRD_PARTY_NOTICES.md')
shutil.copy2(ROOT/'LICENSE',licenses/'Description-Shortener-LICENSE')
plist = {'CFBundleName':f'Description Shortener V{VERSION}','CFBundleDisplayName':f'Description Shortener V{VERSION}',
'CFBundleIdentifier':'com.michaelbrandonfalk.description-shortener','CFBundleExecutable':'DescriptionShortener',
'CFBundlePackageType':'APPL','CFBundleShortVersionString':VERSION,'CFBundleVersion':VERSION,
'LSMinimumSystemVersion':'14.0','NSHighResolutionCapable':True,'NSHumanReadableCopyright':'Copyright © 2026 Michael Brandon Falk',
'CFBundleIconFile':'AppIcon',
'CFBundleDocumentTypes':[{'CFBundleTypeName':'Description documents','CFBundleTypeRole':'Editor','LSHandlerRank':'Alternate',
'CFBundleTypeExtensions':['xlsx','csv','docx','txt','rtf','doc','odt','pdf']}]}
with (APP/'Contents/Info.plist').open('wb') as f: plistlib.dump(plist,f)
if (ROOT/'build/AppIcon.icns').exists(): shutil.copy2(ROOT/'build/AppIcon.icns', resources/'AppIcon.icns')
# Ad-hoc signing is for integrity only. Developer ID signing/notarization is a separate release step.
run(['codesign','--force','--deep','--sign','-',APP])
run(['codesign','--verify','--deep','--strict',APP])
ZIP.parent.mkdir(exist_ok=True)
run(['ditto','-c','-k','--sequesterRsrc','--keepParent',APP,ZIP])
sha = hashlib.file_digest(open(ZIP,'rb'),'sha256').hexdigest()
(ROOT/'downloads'/f'SHA256-V{VERSION}.txt').write_text(f'{sha}  {ZIP.name}\n')
(ROOT/'build/release.json').write_text(json.dumps({'version':VERSION,'archive':ZIP.name,'sha256':sha,'bytes':ZIP.stat().st_size},indent=2)+'\n')
print(json.dumps({'app':str(APP),'zip':str(ZIP),'sha256':sha}))
