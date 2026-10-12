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
  if (JSON.stringify(numericTokens(original))!==JSON.stringify(numericTokens(candidate))) errors.push('A number, quantity or numeric specification changed.');
  return errors;
}
export function compactDraft(text) {
  return text.split(/("[^"]*"|“[^”]*”)/).map((part,i)=>i%2 ? part : part.replace(/\ban outdoor living space\b/g,'outdoor living space').replace(/~(\d+(?:\.\d+)?)\s+yrs?\b/g,'~$1yr')).join('');
}
export class BrowserShortener {
  constructor(runtime,rules,onActivity=()=>{}) { this.runtime=runtime;this.rules=rules;this.cache=new Map();this.onActivity=onActivity; }
  async ask(review,payload) {
    this.onActivity(review ? "Checking the sentence and material facts…" : "Drafting a shorter description…");
    const limit=payload.limit_including_spaces;
    const system=review?this.rules.review:this.rules.system.replace('110 characters',`${limit} characters`)+`\nFor this draft, aim for at most ${payload.word_budget_guidance} words. The hard character limit is ${limit}. Omit optional enjoyment; retain every material fact.`;
    let messages=[{role:'system',content:system},{role:'user',content:JSON.stringify(payload)}];
    if (!review && payload.previous_candidate) messages=[{role:'system',content:system},{role:'user',content:JSON.stringify({description:payload.description,limit_including_spaces:limit,word_budget_guidance:payload.word_budget_guidance})},{role:'assistant',content:JSON.stringify({text:payload.previous_candidate})},{role:'user',content:`Revise that draft. It has ${count(payload.previous_candidate)} characters. Maximum: ${limit}. ${payload.previous_issue} Aim for about ${payload.word_budget_guidance} words without omitting material facts. ${payload.revision_instruction} Remove redundant infinitive wording where equivalent (wanted to have more room -> wanted more room). Return a complete sentence in JSON.`}];
    const result=await this.runtime.createChatCompletion({messages,temperature:payload.previous_candidate?0.2:0.1,seed:42+17*(payload.attempt||0)+count(payload.previous_candidate||''),max_tokens:review?384:Math.min(4096,Math.max(256,limit*2)),cache_prompt:true,chat_template_kwargs:{enable_thinking:false},response_format:{type:'json_schema',json_schema:{name:'result',strict:true,schema:review?this.rules.reviewSchema:this.rules.textSchema}}});
    try { return JSON.parse(result.choices[0].message.content); } catch { throw new Error('The local model returned an incomplete response. This description needs review.'); }
  }
  async shorten(original,limit) {
    validateLimit(limit);
    const key=JSON.stringify([limit,original]);
    if (this.cache.has(key)) return this.cache.get(key);
    if (count(original)>12000) throw new Error('This section is too long to verify as one description. Split it into individual descriptions.');
    let previous='', reason='', budget=Math.min(Math.max(21,Math.floor(limit/5)),Math.max(12,original.trim().split(/\s+/).length));
    let compact=original.trim();
    for (const [phrase,replacement] of [['in order to','to'],['due to the fact that','because'],['does not contain','contains no'],['is manufactured in','is made in'],['carries a','has a'],['at a rate of','at'],['a total of ',''],['in the event that','if']]) compact=compact.replace(new RegExp('\\b'+phrase+'\\b','gi'),replacement);
    for (let attempt=0;attempt<3;attempt++) {
      let candidate=attempt===0&&!hardErrors(original,compact,limit).length?compact:null;
      if (candidate===null) {
        const response=await this.ask(false,{description:original,limit_including_spaces:limit,previous_candidate:previous,previous_characters:count(previous),previous_issue:reason,word_budget_guidance:budget,attempt,revision_instruction:previous?`Write a distinctly different, more compact complete sentence. Use compound verbs; after a purchase verb, an indefinite article can replace a redundant possessive. Use the full ${limit}-character budget.`:'Keep every key detail using compact grammar.'});
        candidate=typeof response.text==='string'?response.text.trim():'';
        if (count(candidate)>limit) candidate=compactDraft(candidate);
      }
      if (!candidate) break;
      previous=candidate;
      const errors=hardErrors(original,candidate,limit);
      if (errors.length) {
        if (count(candidate)>limit) budget=Math.max(12,Math.floor(candidate.split(/\s+/).length*(limit-1)/count(candidate)));
        reason=errors.join(' ')+' Use shorter equivalent vocabulary and compact grammar. Preserve all material facts and the source tense.';
        continue;
      }
      const verdict=await this.ask(true,{original,candidate,limit_including_spaces:limit});
      if (['equivalent','complete_sentences','close_wording'].every(k=>verdict[k]===true)) { this.cache.set(key,candidate);return candidate; }
      reason=verdict.issue||'The draft changed meaning, omitted material details or was not a complete sentence.';
    }
    throw new Error(`The local model couldn't fit the material facts into a complete sentence within ${limit} characters. This description needs review.`);
  }
}
