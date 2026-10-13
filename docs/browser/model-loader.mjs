import { Wllama } from './vendor/wllama.js';
const MODEL_FILE='gemma4-12b-qat-q4_0.gguf';
export async function loadLocalModel(status,signal) {
  if (!navigator.gpu) throw new Error('This browser does not support WebGPU. Use a current Chrome or Edge browser, or download a desktop app.');
  const adapter=await navigator.gpu.requestAdapter();
  if (!adapter) throw new Error('A compatible GPU is unavailable. Use a desktop download on this computer.');
  if (!navigator.storage?.getDirectory) throw new Error('Local model storage is unavailable. Use a regular browser window or the Mac app.');
  const manifest=await (await fetch('./model/manifest.json')).json();
  // A stable origin and model filename keep weights across application releases.
  const persistent=await navigator.storage.persist?.().catch(()=>false);
  const directory=await (await navigator.storage.getDirectory()).getDirectoryHandle('description-shortener',{create:true});
  const handle=await directory.getFileHandle(MODEL_FILE,{create:true});
  let file=await handle.getFile();
  if (file.size>manifest.bytes) { const writer=await handle.createWritable();await writer.close();file=await handle.getFile(); }
  if (file.size<manifest.bytes) {
    const estimate=await navigator.storage.estimate();
    if ((estimate.quota||0)-(estimate.usage||0)<manifest.bytes-file.size) throw new Error('Not enough browser storage for the 7 GB model. Free space or use a desktop download.');
    status(`Downloading model: ${Math.floor(file.size/manifest.bytes*100)}%. Descriptions stay on this device.`);
    const headers=file.size?{Range:`bytes=${file.size}-`}:{};
    const response=await fetch(manifest.url,{headers,signal});
    if (!(response.status===200||response.status===206)) throw new Error('The model download failed. Try again to resume it.');
    let position=file.size;
    if (position && response.status!==206) position=0;
    if (response.status===206 && !response.headers.get('Content-Range')?.startsWith(`bytes ${position}-`)) throw new Error('The model server returned an invalid download range.');
    const writer=await handle.createWritable({keepExistingData:position>0});
    await writer.seek(position);
    try {
      const reader=response.body.getReader();
      while (true) {
        const {done,value}=await reader.read();if(done) break;
        if(position+value.length>manifest.bytes) throw new Error('The model download was larger than expected.');
        await writer.write(value);position+=value.length;
        status(`Downloading model: ${Math.floor(position/manifest.bytes*100)}%. Descriptions stay on this device.`);
      }
    } finally { await writer.close(); }
    file=await handle.getFile();
    if (file.size!==manifest.bytes) throw new Error('The model download is incomplete. Choose Load model again to resume.');
  }
  status('Verifying the saved model…');
  const verified=await new Promise((resolve,reject)=>{
    const worker=new Worker(new URL('./verify-model.js',import.meta.url));
    const cancel=()=>{worker.terminate();reject(new Error('Model loading canceled.'));};
    signal?.addEventListener('abort',cancel,{once:true});
    worker.onmessage=({data})=>{worker.terminate();signal?.removeEventListener('abort',cancel);data.error?reject(new Error(data.error)):resolve(data.ok);};
    worker.onerror=()=>{worker.terminate();signal?.removeEventListener('abort',cancel);reject(new Error('Model verification failed. Try loading it again.'));};
    worker.postMessage({file,expected:manifest.sha256});
  });
  if(!verified) {
    await directory.removeEntry(MODEL_FILE);
    throw new Error('The model checksum did not match. Choose Load model to download a verified copy.');
  }
  const shards=[];
  for(const shard of manifest.shards) {
    const response=await fetch('./model/'+shard.header,{signal});
    if(!response.ok) throw new Error('Model metadata could not be loaded. Reload the page.');
    shards.push(new File([await response.blob(),file.slice(shard.offset,shard.offset+shard.bytes)],shard.name));
  }
  if(signal?.aborted) throw new Error('Model loading canceled.');
  status(persistent?'Loading the cached model (persistent storage granted)…':'Loading the cached model. Browser storage may be evicted if disk space is low…');
  const runtime=new Wllama({default:new URL('./vendor/wasm/wllama.wasm',import.meta.url).href},{logger:{debug(){},log(){},warn(){},error(){}},parallelDownloads:1});
  try { await runtime.loadModel(shards,{n_ctx:2048,n_batch:64,n_ubatch:32,n_gpu_layers:99,n_threads:1,jinja:true,reasoning:false,reasoning_format:'deepseek'}); }
  catch { await runtime.exit().catch(()=>{});throw new Error('The browser could not load this model. Check available memory, try Chrome or Edge, or use a desktop download.'); }
  if(signal?.aborted) {await runtime.exit();throw new Error('Model loading canceled.');}
  return runtime;
}
