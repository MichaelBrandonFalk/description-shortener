export const count = text => Array.from(text).length;
export function validateLimit(value) {
  if (!Number.isSafeInteger(value) || value < 110) throw new Error('Enter a whole number of at least 110. Spaces and punctuation count.');
  return value;
}
export function numericTokens(text) {
  const words = ['zero','one','two','three','four','five','six','seven','eight','nine','ten','eleven','twelve','thirteen','fourteen','fifteen','sixteen','seventeen','eighteen','nineteen','twenty'];
  const protectedWords=[];
  text=text.replace(new RegExp('\\b(?:'+words.join('|')+')(?:[ -]+(?:hundred|thousand|million|billion|(?:'+words.slice(1).join('|')+')))\\b','gi'),m=>{protectedWords.push(m.toLowerCase());return 'QUANTITYPLACEHOLDER';});
  words.forEach((word,i)=>{text=text.replace(new RegExp('\\b'+word+'\\b','gi'),String(i));});
  return [...(text.match(/(?<!\w)\d+(?:[.,:/-]\d+)*(?:\s?[%°])?/g)||[]),...protectedWords].sort();
}
export function hardErrors(original, candidate, limit) {
  validateLimit(limit);
  const errors=[];
  if (!candidate.trim()) errors.push('No meaning-preserving result was found.');
  if (count(candidate)>limit) errors.push(`${count(candidate)} characters exceeds ${limit}.`);
  if (candidate.includes('—')) errors.push('Contains an em dash.');
  if (!/[.!?]["”’']?$/.test(candidate) || /(\.{2,}|…)["”’']?$/.test(candidate)) errors.push('Must be a complete sentence without an ellipsis.');
  if (numericTokens(candidate).some((token,i,list)=>list.slice(0,i+1).filter(t=>t===token).length>numericTokens(original).filter(t=>t===token).length)) errors.push('A number, quantity or numeric specification changed.');
  return errors;
}
export function compactDraft(text) {
  return text.split(/("[^"]*"|“[^”]*”)/).map((part,i)=>i%2 ? part : part.replace(/\ban outdoor living space\b/g,'outdoor living space').replace(/~(\d+(?:\.\d+)?)\s+yrs?\b/g,'~$1yr')).join('');
}
export function fallbackDescription(original,limit) {
  const clean=original.replaceAll('—',',').replaceAll('…','.').replace(/\s+/g,' ').trim();
  for(const part of clean.split(/(?<=[.!?])\s+|,?\s+(?:but|and then|so)\s+/i)) {
    const text=part.replace(/^[ ,;:.!?]+|[ ,;:.!?]+$/g,'')+'.';
    if(text!=='.'&&count(text)<=limit&&!hardErrors(original,text,limit).length)return text;
  }
  let excerpt='';
  for(const word of clean.split(/\s+/)) {
    const trial=(excerpt+' '+word).trim().replace(/[ ,;:.!?]+$/,'')+'.';
    if(count(trial)>limit)break;
    excerpt=trial.slice(0,-1);
  }
  if(!excerpt)throw new Error('No usable prose was found. Please review this input.');
  return excerpt.replace(/[ ,;:.!?]+$/,'')+'.';
}
export class BrowserShortener {
  constructor(runtime,rules,onActivity=()=>{}) {this.runtime=runtime;this.rules=rules;this.cache=new Map();this.reviews=new Map();this.onActivity=onActivity;this.engineFailed=false;}
  reviewFor(original,limit){return this.reviews.get(JSON.stringify([limit,original]))||'';}
  async ask(payload) {
    this.onActivity('Drafting a shorter description…');
    const limit=payload.limit_including_spaces;
    const system=this.rules.system.replace('110 characters',`${limit} characters`)+` Aim for ${payload.word_budget_guidance} words.`;
    const result=await this.runtime.createChatCompletion({messages:[{role:'system',content:system},{role:'user',content:JSON.stringify(payload)}],temperature:0.1,seed:42,max_tokens:Math.min(512,Math.max(96,limit)),cache_prompt:false,chat_template_kwargs:{enable_thinking:false},response_format:{type:'json_schema',json_schema:{name:'result',strict:true,schema:this.rules.textSchema}}});
    return JSON.parse(result.choices[0].message.content);
  }
  async shorten(original,limit) {
    validateLimit(limit);const key=JSON.stringify([limit,original]);
    if(this.cache.has(key))return this.cache.get(key);
    const source=original.trim();
    if(!hardErrors(original,source,limit).length){this.cache.set(key,source);return source;}
    let previous='',reason='',budget=Math.max(10,Math.floor(limit/6));
    for(let attempt=0;attempt<2&&!this.engineFailed;attempt++) {
      try {
        const data=await this.ask({description:Array.from(source).slice(0,6000).join(''),limit_including_spaces:limit,previous_candidate:previous,previous_issue:reason,word_budget_guidance:budget,attempt});
        const candidate=typeof data.text==='string'?data.text.trim():'';
        const errors=hardErrors(original,candidate,limit);
        if(!errors.length){this.cache.set(key,candidate);this.reviews.set(key,'May need review: supporting details may have been omitted.');return candidate;}
        previous=candidate;reason=errors.join(' ');
        if(candidate)budget=Math.max(8,Math.floor(candidate.split(/\s+/).length*(limit-1)/count(candidate)));
      }catch(e){
        if(/ABORT|device lost|out of memory|resource|memory access/i.test(e.message)){this.engineFailed=true;await this.runtime.exit().catch(()=>{});}
        break;
      }
    }
    const candidate=fallbackDescription(original,limit);
    this.cache.set(key,candidate);this.reviews.set(key,'May need review: a best-effort source excerpt was used because the model could not produce a valid result.');return candidate;
  }
}
