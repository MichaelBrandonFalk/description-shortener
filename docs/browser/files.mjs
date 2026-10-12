import {unzipSync,zipSync,strToU8,strFromU8} from './vendor/fflate.mjs';
import {count,hardErrors} from './shortening.mjs';
const S='http://schemas.openxmlformats.org/spreadsheetml/2006/main', W='http://schemas.openxmlformats.org/wordprocessingml/2006/main';
const description=/description|synopsis|overview|summary|blurb|long.?text|short.?text|plot|^details$|^copy$/i;
const identifier=/(^|[ _-])(id|sku|url|uri|code|name|title|isbn|upc|ean|email|link|path)([ _-]|$)/i;
export const relevant=(text,header='')=>typeof text==='string'&&text.trim()&&!identifier.test(header)&&(description.test(header)||(count(text.trim())>110&&text.trim().split(/\s+/).length>=5));
function parseXML(bytes) {
  const source=strFromU8(bytes);
  if(/<!DOCTYPE|<!ENTITY/i.test(source)) throw new Error('This document contains unsupported XML declarations. Use the Mac app.');
  const root=new DOMParser().parseFromString(source,'application/xml');
  if(root.querySelector('parsererror')) throw new Error('The document contains invalid XML.');
  return root;
}
const nodes=(root,ns,name)=>Array.from(root.getElementsByTagNameNS(ns,name));
const serialize=root=>strToU8(new XMLSerializer().serializeToString(root));
function packageFiles(bytes) {
  let expanded=0;
  return unzipSync(bytes,{filter:file=>{expanded+=file.originalSize;if(expanded>512*1024*1024)throw new Error('Expanded document exceeds 512 MB.');return true;}});
}
export function parseCSV(text,delimiter) {
  const rows=[];let row=[],field='',quoted=false;
  for(let i=0;i<text.length;i++) {
    const c=text[i];
    if(quoted) { if(c==='"'&&text[i+1]==='"'){field+='"';i++;}else if(c==='"')quoted=false;else field+=c; }
    else if(c==='"'&&field==='')quoted=true;
    else if(c===delimiter){row.push(field);field='';}
    else if(c==='\r'||c==='\n'){if(c==='\r'&&text[i+1]==='\n')i++;row.push(field);rows.push(row);row=[];field='';}
    else field+=c;
  }
  if(quoted)throw new Error('The CSV contains an unclosed quoted field.');
  if(field||row.length){row.push(field);rows.push(row);}
  return rows;
}
export function encodeCSV(rows,delimiter,newline,trailing) {
  return rows.map(row=>row.map(value=>/["\r\n]/.test(value)||value.includes(delimiter)?'"'+value.replace(/"/g,'""')+'"':value).join(delimiter)).join(newline)+(trailing?newline:'');
}
function textDocument(bytes,ext) {
  let text;
  try {text=new TextDecoder('utf-8',{fatal:true,ignoreBOM:true}).decode(bytes);}catch{throw new Error('Use the Mac app for files with this text encoding, or save a UTF-8 copy.');}
  const bom=text.startsWith('\uFEFF');if(bom)text=text.slice(1);
  const items=[];
  if(ext==='txt') {
    const parts=text.split(/(\r\n|\n|\r)/);
    parts.forEach((line,i)=>{if(i%2===0&&line.trim())items.push({location:`Line ${Math.floor(i/2)+1}`,original:line,apply:value=>{parts[i]=value;}});});
    return {items,write:()=>new TextEncoder().encode((bom?'\uFEFF':'')+parts.join(''))};
  }
  const candidates=[',',';','\t','|'].map(delimiter=>{const rows=parseCSV(text,delimiter);return {delimiter,rows,score:rows.slice(0,20).reduce((a,r)=>a+r.length,0)};}).sort((a,b)=>b.score-a.score);
  const {delimiter,rows}=candidates[0];
  const hasHeader=rows[0]?.every(value=>count(value)<80&&!/[.!?]$/.test(value));
  const headers=hasHeader?rows[0]:[];
  for(let i=hasHeader?1:0;i<rows.length;i++)for(let j=0;j<rows[i].length;j++)if(relevant(rows[i][j],headers[j]||''))items.push({location:`Row ${i+1}, ${headers[j]||'column '+(j+1)}`,original:rows[i][j],apply:value=>{rows[i][j]=value;}});
  const newline=text.includes('\r\n')?'\r\n':text.includes('\r')?'\r':'\n';
  return {items,write:()=>new TextEncoder().encode((bom?'\uFEFF':'')+encodeCSV(rows,delimiter,newline,/[\r\n]$/.test(text)))};
}
function officeDocument(bytes,ext) {
  const files=packageFiles(bytes),items=[],changed=new Map();
  if(ext==='docx') {
    if(!files['word/document.xml'])throw new Error('This is not a valid DOCX file.');
    const root=parseXML(files['word/document.xml']);
    const paragraphs=nodes(root,W,'p');
    for(let i=0;i<paragraphs.length;i++) {
      const p=paragraphs[i];
      const style=nodes(p,W,'pStyle')[0]?.getAttributeNS(W,'val')||'';
      if(/heading|title|subtitle/i.test(style))continue;
      const ts=nodes(p,W,'t');const original=ts.map(t=>t.textContent).join('');
      if(!original.trim()||(count(original)<=110&&!/[.!?—]/.test(original)))continue;
      if(['fldChar','instrText','del','ins'].some(name=>nodes(p,W,name).length))throw new Error(`Paragraph ${i+1} contains fields or tracked changes. Use the Mac app or accept changes first.`);
      items.push({location:`Paragraph ${i+1}`,original,apply:value=>{ts[0].textContent=value;ts[0].setAttributeNS('http://www.w3.org/XML/1998/namespace','xml:space','preserve');ts.slice(1).forEach(t=>{t.textContent='';});changed.set('word/document.xml',root);}});
    }
  } else {
    const shared=files['xl/sharedStrings.xml']?nodes(parseXML(files['xl/sharedStrings.xml']),S,'si').map(si=>nodes(si,S,'t').map(t=>t.textContent).join('')):[];
    const names={};
    if(files['xl/workbook.xml']&&files['xl/_rels/workbook.xml.rels']) {
      const relations={};
      for(const r of Array.from(parseXML(files['xl/_rels/workbook.xml.rels']).documentElement.children)) {
        const path=r.getAttribute('Target');relations[r.getAttribute('Id')]=new URL(path,'https://local/xl/').pathname.slice(1);
      }
      for(const sheet of nodes(parseXML(files['xl/workbook.xml']),S,'sheet'))names[relations[sheet.getAttributeNS('http://schemas.openxmlformats.org/officeDocument/2006/relationships','id')]]=sheet.getAttribute('name');
    }
    for(const name of Object.keys(files).filter(n=>/^xl\/worksheets\/sheet\d+\.xml$/.test(n))) {
      const root=parseXML(files[name]),rows=nodes(root,S,'row');
      const value=c=>{if(nodes(c,S,'f').length)return null;const type=c.getAttribute('t');return type==='s'?shared[Number(nodes(c,S,'v')[0]?.textContent)]:type==='inlineStr'?nodes(c,S,'t').map(t=>t.textContent).join(''):null;};
      const column=c=>(c.getAttribute('r')||'').replace(/\d/g,'');
      let headers={},headerRow=-1;
      for(let i=0;i<Math.min(20,rows.length);i++) {
        const cells=nodes(rows[i],S,'c');
        if(cells.some(c=>{const v=value(c)||'';return count(v)<80&&v.split(/\s+/).length<7&&!/[.!?]$/.test(v)&&description.test(v);})) { headers=Object.fromEntries(cells.map(c=>[column(c),value(c)||'']));headerRow=i;break; }
      }
      if(headerRow<0&&rows[0]) {
        const cells=nodes(rows[0],S,'c');
        if(cells.length&&cells.every(c=>{const v=value(c);return v===null||(count(v)<80&&!/[.!?]$/.test(v));})) {headers=Object.fromEntries(cells.map(c=>[column(c),value(c)||'']));headerRow=0;}
      }
      for(let i=headerRow+1;i<rows.length;i++)for(const cell of nodes(rows[i],S,'c')) {
        const original=value(cell);if(!relevant(original,headers[column(cell)]||''))continue;
        items.push({location:`${names[name]||name}!${cell.getAttribute('r')}`,original,apply:result=>{
          for(const child of Array.from(cell.children))if(child.namespaceURI===S&&['v','is'].includes(child.localName))child.remove();
          cell.setAttribute('t','inlineStr');const inline=root.createElementNS(S,'is'),t=root.createElementNS(S,'t');t.textContent=result;t.setAttributeNS('http://www.w3.org/XML/1998/namespace','xml:space','preserve');inline.append(t);cell.append(inline);changed.set(name,root);
        }});
      }
    }
  }
  return {items,write:()=>{for(const [name,root] of changed)files[name]=serialize(root);return zipSync(files,{level:6});}};
}
export async function processFile(file,shortener,limit,status) {
  if(file.size>128*1024*1024)throw new Error('The file exceeds the 128 MB input limit.');
  const ext=file.name.split('.').pop().toLowerCase();
  if(!['xlsx','csv','docx','txt'].includes(ext))throw new Error('Choose XLSX, CSV, DOCX or TXT. The Mac app also supports other document formats.');
  const bytes=new Uint8Array(await file.arrayBuffer());
  const doc=['xlsx','docx'].includes(ext)?officeDocument(bytes,ext):textDocument(bytes,ext);
  const warnings=[];
  for(let i=0;i<doc.items.length;i++) {
    const item=doc.items[i];status(`Checking ${i+1} of ${doc.items.length}: ${item.location}`);
    let result;
    try {result=await shortener.shorten(item.original,limit);const errors=hardErrors(item.original,result,limit);if(errors.length)throw new Error(errors.join(' '));}
    catch(error){throw new Error(`${item.location}: ${error.message} No file was exported.`);}
    const warning=shortener.reviewFor?.(item.original,limit);if(warning)warnings.push(`${item.location}: ${warning}`);
    if(result!==item.original)item.apply(result);
  }
  return {bytes:doc.write(),name:file.name.slice(0,-ext.length-1)+'_shortened.'+ext,checked:doc.items.length,warnings};
}
