import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
const read=async p=>JSON.parse(await fs.readFile(p,'utf8'));
const norm=x=>String(x??'').normalize('NFKC').toUpperCase().replace(/[\s._-]/g,'');
const allowed=x=>['S21','S21CHAEWON','CHAEWON','KIMCHAEWON','김채원'].includes(norm(x));
const rows=(data,key)=>Array.isArray(data)?data:(data?.[key]||[]);
async function main(){
 const profile=await read('public/data/chaewon.json'); assert.equal(profile.member.id,'S21');
 for(const [p,key,checker] of [
  ['photos.json','photos',x=>allowed(x.memberId)],
  ['films.json','items',x=>Array.isArray(x.memberIds)&&x.memberIds.some(allowed)],
  ['objekt.json','objekts',x=>allowed(x.member)],
  ['chaewon-activities.json','activities',x=>x.s21===true],
 ]){
  const data=await read(`public/data/${p}`); const items=rows(data,key);assert.ok(Array.isArray(items),p);
  const seen=new Set();for(const entry of items){const id=p==='films.json'?entry.youtubeId:entry.id;assert.ok(id&&!seen.has(id),`Duplicate or blank ${p} ID: ${id}`);seen.add(id);assert.ok(checker(entry),`Non-S21 ${p} ID: ${id}`);}
  console.log(`${p}: ${items.length} S21 entries`);
 }
}
main().catch(e=>{console.error(e);process.exitCode=1;});
