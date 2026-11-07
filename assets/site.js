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
