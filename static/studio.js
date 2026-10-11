const $ = id => document.getElementById(id);
const formats = {wav:{extension:'wav',label:'WAV 24 bit'},wav32:{extension:'wav',label:'WAV 32 bit float'},flac:{extension:'flac',label:'FLAC 24 bit'},mp3:{extension:'mp3',label:'MP3 320 kbps'}};
const profileNames = {focus:'Vokal / merkez odak',wide:'Enstrümantal / geniş stereo'};
let selected, originalUrl, busy=false, renderedSpeed=1, side='A', switchVersion=0, ready=false;
let variants={}, winner='focus', renderedFormat='wav', renderedFilename='';
const original=$('original'), processed=$('processed'), wide=$('processed-wide');
const players={A:original,B:processed,C:wide};
const active=()=>players[side];
function clock(time) { const s=Math.max(0, Math.floor(time || 0)); return `${Math.floor(s/60)}:${String(s%60).padStart(2,'0')}`; }
function update() {
  const v=Number($('speed').value); $('value').textContent=v.toFixed(2)+'×';
  document.querySelectorAll('[data-speed]').forEach(b=>b.classList.toggle('active',Number(b.dataset.speed)===v));
}
$('speed').addEventListener('input',update);
document.querySelectorAll('[data-speed]').forEach(b=>b.onclick=()=>{$('speed').value=b.dataset.speed;update();});
$('profile').onchange=()=>{
  $('profile-note').textContent=$('profile').value==='auto' ? 'Tüm kaydın merkez / yan enerji dağılımından öneri seçilir. Tür veya kalite garantisi değildir. Her işlemde iki profil de oluşturulur; bu tercih ilk dinlenecek sonucu belirler.' : $('profile').value==='focus' ? 'Merkezdeki vokal ve ortak enstrümanların stereo odağını, mono uyumluluğunu önceliklendirir.' : 'Kanalların bağımsız işlenmesiyle geniş stereo ayrıntıları önceliklendirir. Merkezdeki sesler için merkez odak profilini de deneyin.';
};
function releaseResults() {
  ready=false; switchVersion++;
  Object.values(players).forEach(audio=>audio.pause());
  for(const audio of [processed,wide]){audio.removeAttribute('src');audio.load();}
  for(const variant of Object.values(variants)){URL.revokeObjectURL(variant.url);if(variant.listenUrl)URL.revokeObjectURL(variant.listenUrl);}
  variants={}; $('result').classList.add('hidden');
}
function updateDownload() {
  const variant=variants[winner]; if(!variant)return;
  $('winner-label').textContent='Seçilen sonuç: '+profileNames[winner];
  $('download').href=variant.url;
  $('download').download=renderedFilename.replace(/\.[^.]+$/,'')+`-${renderedSpeed.toFixed(2)}x-${winner}.${formats[renderedFormat].extension}`;
  $('download').textContent='Seçilen profili indir ↓';
}
function choose(file) {
  if(busy||!file)return;
  if(!/\.(mp3|wav)$/i.test(file.name)||file.size>150*1024*1024){$('status').textContent='En fazla 150 MB büyüklüğünde MP3 veya WAV seçin.';return;}
  releaseResults(); selected=file; $('filename').textContent=file.name;
  if(originalUrl)URL.revokeObjectURL(originalUrl);
  originalUrl=URL.createObjectURL(file); original.src=originalUrl; original.classList.remove('hidden');
  $('process').disabled=false; $('status').textContent='';
}
$('file').onchange=e=>choose(e.target.files[0]);
for(const event of ['dragenter','dragover'])$('drop').addEventListener(event,e=>{e.preventDefault();$('drop').classList.add('over');});
for(const event of ['dragleave','drop'])$('drop').addEventListener(event,e=>{e.preventDefault();$('drop').classList.remove('over');});
$('drop').addEventListener('drop',e=>choose(e.dataTransfer.files[0]));
async function audioRequest(url, form) {
  const response=await fetch(url,{method:'POST',body:form});
  if(!response.ok){let message='Ses işlenemedi.';try{const error=await response.json();if(typeof error.detail==='string')message=error.detail;}catch{}throw Error(message);}
  return response;
}
function metadata(audio) {
  if(audio.readyState>=1)return Promise.resolve();
  return new Promise((resolve,reject)=>{
    const timer=setTimeout(()=>finish(Error('Ses önizlemesi yüklenemedi.')),20000);
    function finish(error){clearTimeout(timer);audio.removeEventListener('loadedmetadata',ok);audio.removeEventListener('error',bad);error?reject(error):resolve();}
    const ok=()=>finish(), bad=()=>finish(Error('Tarayıcı bu ses kaydını oynatamıyor.'));
    audio.addEventListener('loadedmetadata',ok);audio.addEventListener('error',bad);
  });
}
async function renderVariant(file,speed,format,profile,index) {
  $('status').textContent=`${index}/2 · ${profile==='auto'?'Şarkı analiz ediliyor':profileNames[profile]} · Tam kaliteli R3 işleme…`;
  const form=new FormData();form.append('file',file);form.append('speed',speed);form.append('output_format',format);form.append('profile',profile);
  const response=await audioRequest('/api/process',form),blob=await response.blob();
  const chosen=response.headers.get('X-Tempo-Profile');
  if(!profileNames[chosen])throw Error('Profil sonucu okunamadı.');
  const variant={url:URL.createObjectURL(blob),listenUrl:null,reason:decodeURIComponent(response.headers.get('X-Tempo-Reason')||'')};
  variants[chosen]=variant;
  if(format==='wav32'||format==='flac'){
    $('status').textContent=`${index}/2 · ${profileNames[chosen]} dinleme kopyası hazırlanıyor…`;
    const form=new FormData();form.append('file',blob,'rendered.'+formats[format].extension);
    const listen=await audioRequest('/api/listen',form);variant.listenUrl=URL.createObjectURL(await listen.blob());
  }
  const audio=chosen==='focus'?processed:wide; audio.preload='auto';audio.src=variant.listenUrl||variant.url;
  await metadata(audio);
  if(!Number.isFinite(audio.duration))throw Error('Karşılaştırma süresi okunamadı.');
  return chosen;
}
$('process').onclick=async()=>{
  if(!selected||busy)return;
  busy=true; releaseResults();
  const speed=Number($('speed').value),format=$('format').value,file=selected,profile=$('profile').value;
  const controls=document.querySelectorAll('button,input,select');controls.forEach(c=>c.disabled=true);
  try{
    const first=await renderVariant(file,speed,format,profile,1);
    await renderVariant(file,speed,format,first==='focus'?'wide':'focus',2);
    await metadata(original);
    if(!Number.isFinite(original.duration))throw Error('Orijinal kayıt süresi okunamadı.');
    renderedSpeed=speed;renderedFormat=format;renderedFilename=file.name;winner=first;
    ready=true;side=first==='focus'?'B':'C';
    $('position').max=Math.min(original.duration,processed.duration*speed,wide.duration*speed);
    $('position').value=0;$('loop-start').value=0;$('loop-end').value=Math.min(10,Number($('position').max)).toFixed(2);
    Object.values(players).forEach(audio=>audio.currentTime=0);
    $('summary').textContent=`${speed.toFixed(2)}× · ${formats[format].label} · İki profil hazır · R3`;
    $('analysis-result').textContent=profile==='auto'?variants[first].reason:'Başlangıçta tercih ettiğiniz profil seçildi. Diğer profil de karşılaştırmaya hazır.';
    $('result').classList.remove('hidden');updateDownload();setSideUI();
    $('status').textContent='İki profil hazır. B / C arasında aynı noktada geçiş yapın; beğendiğiniz profili seçip indirin.';
  }catch(error){
    releaseResults();$('status').textContent=error.message==='Failed to fetch'?'Sunucuya ulaşılamadı. Uygulamanın çalıştığından emin olun.':error.message;
  }finally{
    busy=false;controls.forEach(c=>c.disabled=false);$('compare-controls').querySelectorAll('button,input').forEach(c=>c.disabled=!ready);setSideUI();
  }
};
function setSideUI() {
  for(const [id,key] of [['side-a','A'],['side-b','B'],['side-c','C']]){
    $(id).classList.toggle('active',side===key);$(id).setAttribute('aria-pressed',String(side===key));
  }
  $('listening').textContent=side==='A'?'A · Orijinal / 1.00×':`${side} · ${profileNames[side==='B'?'focus':'wide']} / ${renderedSpeed.toFixed(2)}×`;
  $('select-best').disabled=!ready||busy||side==='A';
  $('select-best').textContent=side!=='A'&&winner===(side==='B'?'focus':'wide')?'✓ Bu profil seçili':'Dinlediğim profili seç ✓';
}
$('select-best').onclick=()=>{if(!ready||side==='A')return;winner=side==='B'?'focus':'wide';updateDownload();setSideUI();};
async function switchSide(target) {
  if(!ready||busy||side===target)return;
  const token=++switchVersion,old=active(),wasPlaying=!old.paused;
  const sourceTime=TempoTimeline.toSource(old.currentTime,side,renderedSpeed);
  old.pause(); side=target; setSideUI();
  const next=active(); next.currentTime=TempoTimeline.clamp(TempoTimeline.fromSource(sourceTime,side,renderedSpeed),next.duration);
  if(wasPlaying&&token===switchVersion){try{await next.play();}catch{$('status').textContent='Dinlemek için Oynat düğmesine basın.';}if(token!==switchVersion&&active()!==next)next.pause();}
}
$('side-a').onclick=()=>switchSide('A');$('side-b').onclick=()=>switchSide('B');$('side-c').onclick=()=>switchSide('C');
$('play-compare').onclick=async()=>{
  if(!ready)return;
  if(active().paused){try{await active().play();}catch{$('status').textContent='Ses oynatılamadı.';}}else active().pause();
};
$('position').oninput=()=>{if(ready)active().currentTime=TempoTimeline.clamp(TempoTimeline.fromSource(Number($('position').value),side,renderedSpeed),active().duration);};
$('volume').oninput=()=>{Object.values(players).forEach(audio=>audio.volume=Number($('volume').value));};
function loopBounds() {return [Number($('loop-start').value),Number($('loop-end').value)];}
function validateLoop() {
  const [start,end]=loopBounds();
  const valid=TempoTimeline.validLoop(start,end,Number($('position').max));
  $('loop-note').textContent=valid?'Döngü konumları orijinal kaydın zamanına göre ölçülür.':'Başlangıç/bitiş kaydın içinde olmalı; aralık en az 0.25 saniye olmalı.';
  if(!valid)$('loop-enabled').checked=false;
  return valid;
}
$('loop-start').onchange=validateLoop;$('loop-end').onchange=validateLoop;
$('loop-enabled').onchange=()=>{if($('loop-enabled').checked&&validateLoop()){const [start,end]=loopBounds();const t=TempoTimeline.toSource(active().currentTime,side,renderedSpeed);if(t<start||t>=end)active().currentTime=TempoTimeline.fromSource(start,side,renderedSpeed);}};
for(const [key,audio] of Object.entries(players)) {
  audio.addEventListener('play',()=>{Object.values(players).filter(other=>other!==audio).forEach(other=>other.pause());side=key;setSideUI();});
  audio.addEventListener('volumechange',()=>{
    for(const other of Object.values(players)){if(other.volume!==audio.volume)other.volume=audio.volume;if(other.muted!==audio.muted)other.muted=audio.muted;}
    $('volume').value=audio.volume;
  });
  audio.addEventListener('ended',async()=>{
    if(!ready||busy||audio!==active()||!$('loop-enabled').checked)return;
    const [start,end]=loopBounds();
    if(TempoTimeline.validLoop(start,end,Number($('position').max))){audio.currentTime=TempoTimeline.fromSource(start,side,renderedSpeed);try{await audio.play();}catch{}}
  });
}
setInterval(()=>{
  if(!ready||busy)return;
  const audio=active(),sourceTime=TempoTimeline.toSource(audio.currentTime,side,renderedSpeed);
  if($('loop-enabled').checked&&!audio.paused){const [start,end]=loopBounds();if(TempoTimeline.validLoop(start,end,Number($('position').max))&&(sourceTime>=end||sourceTime<start-0.05))audio.currentTime=TempoTimeline.fromSource(start,side,renderedSpeed);}
  $('position').value=sourceTime; $('position-label').textContent=clock(sourceTime)+' / '+clock(Number($('position').max));
  $('play-compare').textContent=audio.paused?'▶ Oynat':'Ⅱ Duraklat';
},40);
