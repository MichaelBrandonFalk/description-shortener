const $=id=>document.getElementById(id);
let limit=110,mode='text',busy=false,source=null,saved=null,readyModel=false;
try{const n=Number(localStorage.getItem('description-shortener-limit')||110);if(Number.isSafeInteger(n)&&n>=110)limit=n;}catch{}
const update=()=>{$('limit-label').textContent=limit+' characters maximum';$('limit').value=limit;};update();
function ready(){$('shorten').disabled=busy||!readyModel||(mode==='text'?!$('original').value.trim():!source);}
function lock(value){busy=value;for(const id of ['text-mode','file-mode','settings-button','original','choose-file'])$(id).disabled=value;$('cancel-run').hidden=!value;ready();}
function status(text,error=false){$('status').textContent=text;$('status').classList.toggle('error',error);}
$('original').oninput=ready;
for(const kind of ['text','file'])$(kind+'-mode').onclick=()=>{mode=kind;for(const other of ['text','file']){$(other+'-panel').hidden=other!==kind;$(other+'-mode').classList.toggle('selected',other===kind);$(other+'-mode').setAttribute('aria-pressed',other===kind);}$('shorten').textContent=kind==='text'?'Shorten description':'Shorten & save copy';status('');ready();};
$('settings-button').onclick=()=>{$('settings').hidden=!$('settings').hidden;$('settings-button').setAttribute('aria-expanded',!$('settings').hidden);update();$('settings-error').textContent='';};
$('reset').onclick=()=>{$('limit').value=110;};
$('save-settings').onclick=()=>{const n=Number($('limit').value);if(!Number.isSafeInteger(n)||n<110){$('settings-error').textContent='Enter a whole number of at least 110.';return;}limit=n;try{localStorage.setItem('description-shortener-limit',String(n));}catch{}update();$('output').value='';$('copy').disabled=true;saved=null;$('settings').hidden=true;$('settings-button').setAttribute('aria-expanded','false');status('');};
$('choose-file').onclick=async()=>{source=await desktop.chooseFile()||source;$('filename').textContent=source||'XLSX, CSV, DOCX or TXT';ready();};
$('copy').onclick=()=>desktop.copy($('output').value);
$('cancel-run').onclick=async()=>{await desktop.cancel();readyModel=false;lock(false);status('Canceled. No result was exported. Reloading the local model…');desktop.warm();};
$('shorten').onclick=async()=>{lock(true);$('output').value='';$('copy').disabled=true;status('Shortening and checking…');try{const result=await desktop.shorten({mode,text:$('original').value,source,limit});if(result.canceled)lock(false);}catch(error){status(error.message,true);lock(false);}};
desktop.onEvent(event=>{
  if(event.event==='ready'){readyModel=event.ok===true;$('load-status').textContent=event.ok?'Local model ready ('+event.backend+'). No account or API key is needed.':event.error;ready();return;}
  if(event.event==='progress'){status(`Checking ${event.current} of ${event.total}: ${event.location}`);return;}
  if(event.event==='result'){
    lock(false);if(!event.ok){status(event.error||event.issues?.map(i=>i.location+': '+i.reason).join('\n')||'This description needs review. No file was exported.',true);return;}
    if(typeof event.text==='string'){$('output').value=event.text;$('copy').disabled=false;status(event.counts.length===1?event.counts[0]+' / '+limit+' characters':event.counts.length+' descriptions checked.');}
    else{saved=event.path;status(`Saved ${event.checked} checked descriptions to ${saved}`);desktop.showFile(saved);}
  }
});
desktop.warm();ready();
