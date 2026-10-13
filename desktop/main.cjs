const {app,BrowserWindow,ipcMain,dialog,shell,clipboard}=require('electron');
const {spawn}=require('node:child_process');const path=require('node:path');const fs=require('node:fs');
const uiSmoke=process.argv.includes('--ui-smoke-test');
let window,worker,buffer='',requestId=0,active=null,closing=false;
const resources=()=>app.isPackaged?path.join(process.resourcesPath,'processor'):path.join(__dirname,'../build/desktop-processor');
function send(event){if(window&&!window.isDestroyed())window.webContents.send('processor-event',event);}
function startWorker(){
  if(worker)return;
  const root=resources();const binary=path.join(root,'helper',process.platform==='win32'?'shortener-helper.exe':'shortener-helper');
  worker=spawn(binary,[root,'--serve'],{stdio:['pipe','pipe','ignore'],windowsHide:true,env:{...process.env,PYTHONUTF8:'1'}});
  const current=worker;buffer='';
  current.stdout.setEncoding('utf8');current.stdout.on('data',chunk=>{buffer+=chunk;let newline;while((newline=buffer.indexOf('\n'))>=0){const line=buffer.slice(0,newline);buffer=buffer.slice(newline+1);try{const event=JSON.parse(line);if(event.request_id===active||event.request_id==='warm'){if(event.event==='result')active=null;send(event);}}catch{}}});
  current.on('error',()=>{if(worker===current){worker=null;active=null;send({event:'result',ok:false,error:'The bundled processor could not start. Reinstall the complete archive.'});}});
  current.on('exit',()=>{if(worker===current){worker=null;if(active){active=null;send({event:'result',ok:false,error:'The local processor stopped. No result was exported.'});}}});
}
function request(value){startWorker();worker.stdin.write(JSON.stringify(value)+'\n','utf8');}
async function stopWorker(){
  const stopped=worker;worker=null;active=null;if(!stopped||stopped.exitCode!==null||stopped.signalCode!==null)return;
  if(process.platform==='win32')await new Promise(resolve=>{const killer=spawn('taskkill.exe',['/PID',String(stopped.pid),'/T','/F'],{windowsHide:true,stdio:'ignore'});killer.on('exit',resolve);killer.on('error',resolve);});
  else stopped.kill('SIGTERM');
}
function ownSender(event){return window&&event.sender===window.webContents;}
ipcMain.handle('warm',event=>{if(!ownSender(event)||active||uiSmoke)return;request({mode:'warm',request_id:'warm'});});
ipcMain.handle('choose-file',async event=>{if(!ownSender(event)||active)return null;const result=await dialog.showOpenDialog(window,{properties:['openFile'],filters:[{name:'Descriptions',extensions:['xlsx','csv','docx','txt']}]});return result.canceled?null:result.filePaths[0];});
ipcMain.handle('shorten',async(event,value)=>{
  if(!ownSender(event)||active)throw new Error('A description is already being processed.');
  if(!Number.isSafeInteger(value.limit)||value.limit<110)throw new Error('Choose a whole-number character limit of at least 110.');
  let destination;
  if(value.mode==='file'){
    if(typeof value.source!=='string'||!['.xlsx','.csv','.docx','.txt'].includes(path.extname(value.source).toLowerCase()))throw new Error('Choose XLSX, CSV, DOCX or TXT.');
    const ext=path.extname(value.source);const result=await dialog.showSaveDialog(window,{defaultPath:path.join(path.dirname(value.source),path.basename(value.source,ext)+'_shortened'+ext),filters:[{name:ext.slice(1).toUpperCase(),extensions:[ext.slice(1)]}]});
    if(result.canceled)return {canceled:true};destination=result.filePath;
    if(fs.existsSync(destination))throw new Error('Choose a new filename. Existing files and originals are never overwritten.');
  }else if(typeof value.text!=='string'||!value.text.trim())throw new Error('Paste a description first.');
  active=String(++requestId);
  request({mode:value.mode,text:value.text,source:value.source,destination,character_limit:value.limit,request_id:active});return {started:true};
});
ipcMain.handle('cancel',async event=>{if(ownSender(event))await stopWorker();});
ipcMain.handle('copy',(event,text)=>{if(ownSender(event)&&typeof text==='string')clipboard.writeText(text);});
ipcMain.handle('show-file',(event,file)=>{if(ownSender(event)&&typeof file==='string'&&fs.existsSync(file))shell.showItemInFolder(file);});
app.whenReady().then(()=>{
  window=new BrowserWindow({width:1040,height:820,minWidth:880,minHeight:650,title:'Description Shortener V'+app.getVersion().replace(/\.0$/, ''),icon:path.join(__dirname,'icon.png'),webPreferences:{preload:path.join(__dirname,'preload.cjs'),contextIsolation:true,nodeIntegration:false,sandbox:true}});
  window.webContents.setWindowOpenHandler(({url})=>{if(/^https:\/\/(github\.com|michaelbrandonfalk\.github\.io|huggingface\.co|lxml\.de|www\.python\.org|pyinstaller\.org)\//.test(url))shell.openExternal(url);return {action:'deny'};});
  window.webContents.on('will-navigate',(event,url)=>{if(!url.startsWith('file:'))event.preventDefault();});
  window.webContents.on('did-finish-load',async()=>{
    if(!uiSmoke)return;
    try{
      const result=await window.webContents.executeJavaScript(`(()=>{document.getElementById('settings-button').click();document.getElementById('limit').value='109';document.getElementById('save-settings').click();if(!document.getElementById('settings-error').textContent)throw new Error('Minimum limit not enforced');document.getElementById('limit').value='150';document.getElementById('save-settings').click();if(!document.getElementById('limit-label').textContent.includes('150'))throw new Error('Setting not applied');document.getElementById('file-mode').click();if(document.getElementById('file-panel').hidden)throw new Error('File controls not visible');return true;})()`);
      if(result)console.log('Packaged Electron UI settings and file controls passed.');app.exit(result?0:1);
    }catch(error){console.error(error.message);app.exit(1);}
  });
  window.loadFile(path.join(__dirname,'index.html'));
});
app.on('window-all-closed',()=>app.quit());
app.on('before-quit',event=>{if(!closing&&worker){event.preventDefault();closing=true;stopWorker().finally(()=>app.quit());}});
