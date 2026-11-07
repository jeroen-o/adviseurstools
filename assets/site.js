// Menu op mobiel
(function(){
  var b=document.querySelector('.menu-btn'),n=document.getElementById('nav');
  if(b&&n)b.addEventListener('click',function(){n.classList.toggle('open');b.setAttribute('aria-expanded',n.classList.contains('open'))});
})();
// Tool-iframes automatisch op inhoudshoogte zetten (zelfde origin)
(function(){
  document.querySelectorAll('iframe.autofit').forEach(function(f){
    var n=0;
    function fit(){
      try{
        var d=f.contentDocument;if(!d||!d.body)return;
        var h=Math.max(d.body.scrollHeight,d.documentElement.scrollHeight);
        if(h>100&&Math.abs(h-f.offsetHeight)>4&&n<400){n++;f.style.height=(h+4)+'px';}
      }catch(e){}
    }
    f.addEventListener('load',function(){
      fit();
      try{new ResizeObserver(fit).observe(f.contentDocument.body);}catch(e){}
      setInterval(fit,1500);
    });
  });
})();
// Zoeker in de header: "Wat zoek je, wat wil je berekenen?"
(function(){
  var bar=document.querySelector('header.top .bar'); if(!bar) return;
  var me=document.currentScript||document.querySelector('script[src$="assets/site.js"]');
  var root=me?me.src.replace(/assets\/site\.js.*$/,''):'/';
  var MAIL='jeroen@oversteegen.nl';
  var form=document.createElement('form');
  form.className='zoeker'; form.setAttribute('role','search'); form.setAttribute('autocomplete','off');
  form.innerHTML='<label for="zoekveld" class="sr">Zoek een tool of pagina</label>'+
    '<input id="zoekveld" type="search" placeholder="Wat zoek je, wat wil je berekenen?" aria-autocomplete="list" aria-controls="zoekres" aria-expanded="false">'+
    '<div id="zoekres" class="zoekres" role="listbox" hidden></div>';
  var plek=document.getElementById('zoekplek');
  if(plek){ plek.appendChild(form); }
  else { var menu=bar.querySelector('.menu-btn'); bar.insertBefore(form, menu||bar.querySelector('nav')); }
  var inp=form.querySelector('input'), box=form.querySelector('.zoekres'), idx=null, sel=-1, hits=[];
  var SYN={lenen:'maximale hypotheek leencapaciteit',hypotheek:'maximale hypotheek',maandlast:'netto maandlasten',maandlasten:'netto maandlasten',
    scheiding:'echtscheiding na scheiding oha',pensioen:'aow pensioenklif pensioencijfer',boete:'boeterente',
    oversluiten:'oversluit boeterente rentemiddeling',starter:'starterslening overdrachtsbelasting kosten koper',
    belasting:'box 3 overdrachtsbelasting schenking renteaftrek',krediet:'lening vfn bkr',verzekering:'assurantie orv aov polischeck opstal',
    overlijden:'orv anw life events',arbeidsongeschikt:'aov wia life events',werkloos:'ww life events',duurzaam:'energielabel verduurzamen klimaatcijfer',
    schenken:'schenkingsvrijstelling',inkomen:'toetsinkomen besteedbaar'};
  function norm(s){return (s||'').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g,'').replace(/[^a-z0-9%& ]+/g,' ');}
  function esc(s){return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}
  function laad(cb){
    if(idx) return cb();
    if(window.ZOEKINDEX){idx=prep(window.ZOEKINDEX);return cb();}
    var s=document.createElement('script'); s.src=root+'assets/zoekindex.js';
    s.onload=function(){idx=prep(window.ZOEKINDEX||[]);cb();}; document.head.appendChild(s);
  }
  function uitbreid(t){return t.replace(/\bmax\b/g,'maximale').replace(/\bhyp\b/g,'hypotheek').replace(/\bovb\b/g,'overdrachtsbelasting');}
  function prep(a){return a.map(function(x){var nt=norm(x.t);return {t:x.t,c:x.c,u:x.u,nt:nt+' '+uitbreid(nt),nc:norm(x.c),nk:norm(x.k)};});}
  function zoek(q){
    var toks=norm(q).split(' ').filter(function(w){return w.length>1;}); if(!toks.length) return [];
    return idx.map(function(x){
      var sc=0, alle=true;
      toks.forEach(function(w){
        var extra=SYN[w]?norm(SYN[w]).split(' '):[]; var s=0;
        if(x.nt.indexOf(w)>=0) s+= (x.nt.indexOf(w)===0||x.nt.indexOf(' '+w)>=0)?12:8;
        else if(x.nc.indexOf(w)>=0) s+=4;
        else if(x.nk.indexOf(w)>=0) s+=3;
        var syn=0; extra.forEach(function(e){ if(e.length>2&&x.nt.indexOf(e)>=0) syn+=4; else if(e.length>2&&x.nk.indexOf(e)>=0) syn+=1; }); s=Math.max(s,syn);
        if(!s) alle=false; sc+=s;
      });
      if(!alle) sc*=0.35;
      return {x:x,sc:sc};
    }).filter(function(r){return r.sc>=3;}).sort(function(a,b){return b.sc-a.sc;}).slice(0,8).map(function(r){return r.x;});
  }
  function mailLink(q){
    var sub='Verzoek nieuwe rekentool: '+q;
    var body='Hallo Jeroen,\n\nOp adviseurstools.nl kon ik niet vinden wat ik zocht:\n"'+q+'"\n\nWat ik graag zou willen berekenen of zien:\n- \n\nVoor wie is de tool bedoeld (adviseur/klant/website):\n- \n\nNaam:\nKantoor:\nTelefoon:\n\nMet vriendelijke groet,\n';
    return 'mailto:'+MAIL+'?subject='+encodeURIComponent(sub)+'&body='+encodeURIComponent(body);
  }
  function toon(){
    var q=inp.value.trim(); if(q.length<2){box.hidden=true;inp.setAttribute('aria-expanded','false');return;}
    hits=zoek(q); sel=-1;
    var h=hits.map(function(x,i){return '<a role="option" id="zr'+i+'" class="zr" href="'+esc(/^https?:/.test(x.u)?x.u:root+x.u)+'"'+(/^https?:/.test(x.u)?' target="_blank" rel="noopener"':'')+'><span class="zt">'+esc(x.t)+(x.c==='Beveiligd'?' 🔒':'')+'</span><span class="zc">'+esc(x.c)+'</span></a>';}).join('');
    var m='<a class="zmail" href="'+esc(mailLink(q))+'">'+(hits.length?'Staat het er niet tussen? <b>Vraag een tool aan →</b>':'<b>Niets gevonden voor “'+esc(q)+'”.</b><br>Wil je dat we dit voor je maken? <b>Stuur ons een mail →</b>')+'</a>';
    box.innerHTML=(hits.length?h:'')+m; box.hidden=false; inp.setAttribute('aria-expanded','true');
  }
  function kies(i){var a=box.querySelectorAll('.zr');a.forEach(function(e,j){e.classList.toggle('act',j===i);});sel=i;if(a[i])inp.setAttribute('aria-activedescendant','zr'+i);}
  inp.addEventListener('focus',function(){laad(function(){});});
  inp.addEventListener('input',function(){laad(toon);});
  inp.addEventListener('keydown',function(e){
    var n=box.querySelectorAll('.zr').length;
    if(e.key==='ArrowDown'&&n){e.preventDefault();kies((sel+1)%n);}
    else if(e.key==='ArrowUp'&&n){e.preventDefault();kies((sel-1+n)%n);}
    else if(e.key==='Escape'){box.hidden=true;inp.blur();}
  });
  form.addEventListener('submit',function(e){e.preventDefault();laad(function(){
    toon(); var a=box.querySelectorAll('.zr'); var t=a[sel>=0?sel:0];
    if(t) location.href=t.href; else { var m=box.querySelector('.zmail'); if(m) m.focus(); }
  });});
  document.addEventListener('click',function(e){if(!form.contains(e.target)){box.hidden=true;inp.setAttribute('aria-expanded','false');}});
  try{var qp=new URLSearchParams(location.search).get('q'); if(qp){inp.value=qp; laad(toon);}}catch(e){}
  document.querySelectorAll('.chip[data-q]').forEach(function(c){c.addEventListener('click',function(){
    inp.value=c.getAttribute('data-q'); inp.focus(); laad(toon);});});
  document.addEventListener('keydown',function(e){if(e.key==='/'&&document.activeElement.tagName!=='INPUT'&&document.activeElement.tagName!=='TEXTAREA'){e.preventDefault();inp.focus();}});
})();
// Filter in het tooloverzicht
(function(){
  var ov=document.getElementById('tooloverzicht'); if(!ov) return;
  var inp=ov.querySelector('.tfilter input'), leeg=ov.querySelector('.tleeg');
  function n(s){return (s||'').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g,'');}
  inp.addEventListener('input',function(){
    var w=n(inp.value).split(/\s+/).filter(Boolean), tot=0;
    ov.querySelectorAll('.tgroep').forEach(function(g){
      var z=0; g.querySelectorAll('.tcard').forEach(function(c){
        var t=n(c.getAttribute('data-zoek')), ok=w.every(function(x){return t.indexOf(x)>=0;});
        c.hidden=!ok; if(ok) z++;
      });
      g.hidden=!z; tot+=z;
    });
    leeg.hidden=tot>0;
  });
})();
