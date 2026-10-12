const {contextBridge,ipcRenderer}=require('electron');
contextBridge.exposeInMainWorld('desktop',{
  warm:()=>ipcRenderer.invoke('warm'),chooseFile:()=>ipcRenderer.invoke('choose-file'),
  shorten:value=>ipcRenderer.invoke('shorten',value),cancel:()=>ipcRenderer.invoke('cancel'),
  copy:text=>ipcRenderer.invoke('copy',text),showFile:file=>ipcRenderer.invoke('show-file',file),
  onEvent:handler=>ipcRenderer.on('processor-event',(_,event)=>handler(event))
});
