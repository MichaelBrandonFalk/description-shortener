/* Incremental verification in a worker keeps the page responsive. */
importScripts('./vendor/sha256.js');
onmessage=async({data:{file,expected}})=>{
  try{
    const hash=await hashwasm.createSHA256();hash.init();
    const reader=file.stream().getReader();
    while(true){const {done,value}=await reader.read();if(done)break;hash.update(value);}
    postMessage({ok:hash.digest()===expected});
  }catch{postMessage({error:'Model verification failed. Try loading it again.'});}
};
