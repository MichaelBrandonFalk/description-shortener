import {loadLocalModel} from './model-loader.mjs';
import {BrowserShortener,count,validateLimit} from './shortening.mjs';
import {processFile} from './files.mjs';
const $=id=>document.getElementById(id);
let limit=110,mode='text',busy=false,shortener=null,abort=null,generation=0;
try { limit=validateLimit(Number(localStorage.getItem('description-shortener-limit')||110)); } catch { limit=110; }
const label=()=>{$('limit-label').textContent=`${limit} characters maximum`;$('limit').value=limit;};label();
function ready(){ $('shorten').disabled=busy||!shortener||(mode==='text'?!$('original').value.trim():!$('file').files.length); }
function lock(value) {busy=value;for(const id of ['text-mode','file-mode','settings-button','original','file','load'])$(id).disabled=value;ready();}
function status(message,error=false){$('status').textContent=message;$('status').classList.toggle('error',error);}
$('original').oninput=ready;$('file').onchange=ready;
for(const current of ['text','file'])$(current+'-mode').onclick=()=>{mode=current;for(const kind of ['text','file']){$(kind+'-panel').hidden=kind!==current;$(kind+'-mode').classList.toggle('selected',kind===current);$(kind+'-mode').setAttribute('aria-pressed',kind===current);} $('shorten').textContent=mode==='text'?'Shorten description':'Shorten & save copy';status('');ready();};
$('settings-button').onclick=()=>{$('settings').hidden=!$('settings').hidden;$('settings-button').setAttribute('aria-expanded',!$('settings').hidden);label();$('settings-error').textContent='';};
$('reset').onclick=()=>{$('limit').value=110;};
$('save-settings').onclick=()=>{try{limit=validateLimit(Number($('limit').value));try{localStorage.setItem('description-shortener-limit',String(limit));}catch{}label();$('output').value='';$('copy').disabled=true;$('settings').hidden=true;$('settings-button').setAttribute('aria-expanded','false');status('');}catch(e){$('settings-error').textContent=e.message;}};
$('load').onclick=async()=>{lock(true);abort=new AbortController();$('cancel-load').hidden=false;try{const rules=await (await fetch('./rules.json')).json();const runtime=await loadLocalModel(message=>{$('load-status').textContent=message;},abort.signal);shortener=new BrowserShortener(runtime,rules,message=>status(message));$('load-status').textContent='Local model ready. Your descriptions stay on this device.';$('load').hidden=true;}catch(e){$('load-status').textContent=abort.signal.aborted?'Download canceled. Choose Load local model to resume.':e.message;}finally{$('cancel-load').hidden=true;lock(false);}};
$('cancel-load').onclick=()=>{abort?.abort();};
$('copy').onclick=async()=>{try{await navigator.clipboard.writeText($('output').value);status('Copied shortened text.');}catch{status('Select the shortened text and copy it.',true);}};
$('cancel-run').onclick=async()=>{if(!busy||!shortener)return;generation++;const stopped=shortener;shortener=null;await stopped.runtime.exit().catch(()=>{});$('load').hidden=false;$('cancel-run').hidden=true;status('Canceled. No result was exported. Reload the local model to continue.');lock(false);};
$('shorten').onclick=async()=>{
  const currentRun=++generation,model=shortener;
  const checkCanceled=()=>{if(currentRun!==generation)throw new Error('CANCELED');};
  lock(true);$('cancel-run').hidden=false;$('output').value='';$('copy').disabled=true;status('Shortening and checking…');
  try{
    if(mode==='text'){
      const lines=$('original').value.split(/\r\n|\n|\r/).filter(line=>line.trim());const results=[];
      for(let i=0;i<lines.length;i++){status(`Checking description ${i+1} of ${lines.length}…`);results.push(await model.shorten(lines[i],limit));}
      checkCanceled();$('output').value=results.join('\n');$('copy').disabled=false;status(results.length===1?`${count(results[0])} / ${limit} characters`:`${results.length} descriptions checked. Each is ${limit} characters or fewer.`);
    }else{
      const result=await processFile($('file').files[0],model,limit,message=>status(message));
      checkCanceled();const url=URL.createObjectURL(new Blob([result.bytes],{type:'application/octet-stream'}));const a=document.createElement('a');a.href=url;a.download=result.name;a.click();setTimeout(()=>URL.revokeObjectURL(url),60000);status(`Saved ${result.name}. ${result.checked} descriptions checked.`);
    }
  }catch(e){
    if(currentRun!==generation)return;
    const engineFailed=/ABORT|device lost|out of memory/i.test(e.message);
    if(engineFailed){await shortener.runtime.exit().catch(()=>{});shortener=null;$('load').hidden=false;$('load-status').textContent='The browser model stopped. Close other demanding apps and reload the model, or use the Mac app.';}
    status(engineFailed?'The browser ran out of resources. No result was exported.':e.message,true);
  }finally{if(currentRun===generation){$('cancel-run').hidden=true;lock(false);}}
};
ready();
