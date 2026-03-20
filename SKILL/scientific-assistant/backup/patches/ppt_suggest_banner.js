/* ── PPT 제안 배너 ── */
let _pptBannerShownCount = 0;
const _pptSuggestItems = [
  {icon:'📊', title:'차트/그래프를 포함할까요?', hint:'"매출 데이터를 막대 차트로 넣어줘"', example:'차트/그래프도 포함해서 PPT 만들어줘'},
  {icon:'📋', title:'표(Table)를 넣어볼까요?', hint:'"비교 데이터를 표로 정리해서 넣어줘"', example:'데이터를 표로 정리해서 PPT에 넣어줘'},
  {icon:'🖼️', title:'이미지/다이어그램도 가능해요!', hint:'"구조도를 슬라이드에 추가해줘"', example:'다이어그램도 포함해서 PPT 만들어줘'},
  {icon:'📈', title:'데이터 시각화를 추가할까요?', hint:'"트렌드를 꺾은선 그래프로 보여줘"', example:'데이터를 시각화해서 PPT에 넣어줘'},
  {icon:'🍩', title:'원형/도넛 차트는 어때요?', hint:'"비율을 도넛 차트로 만들어줘"', example:'비율 데이터를 원형 차트로 PPT에 넣어줘'},
  {icon:'📉', title:'비교 차트를 넣어볼까요?', hint:'"전년 대비 성장률을 비교 차트로"', example:'비교 차트를 포함해서 PPT 만들어줘'},
];

function _showPptSuggestBanner(){
  if(_pptBannerShownCount >= 3) return;
  _pptBannerShownCount++;
  const area = document.getElementById('pptSuggestArea');
  if(!area) return;
  const item = _pptSuggestItems[Math.floor(Math.random()*_pptSuggestItems.length)];
  const banner = document.createElement('div');
  banner.className = 'ppt-suggest-banner';
  banner.innerHTML = `<span class="ppt-banner-icon">${item.icon}</span>`
    + `<div class="ppt-banner-title">${item.title}</div>`
    + `<div class="ppt-banner-hint"><em onclick="_usePptSuggestion(this,'${item.example.replace(/'/g,"\\'")}')">${item.hint}</em> 처럼 말해보세요!</div>`
    + `<button class="ppt-banner-close" onclick="_closePptBanner(this)" title="닫기">✕</button>`;
  area.innerHTML = '';
  area.appendChild(banner);
  setTimeout(()=>{
    if(banner.parentNode){
      banner.classList.add('hiding');
      setTimeout(()=>{ if(banner.parentNode) banner.remove(); }, 400);
    }
  }, 8000);
}

function _closePptBanner(btn){
  const banner = btn.closest('.ppt-suggest-banner');
  if(banner){ banner.classList.add('hiding'); setTimeout(()=>banner.remove(), 400); }
}

function _usePptSuggestion(el, text){
  const input = document.getElementById('input');
  if(input){ input.value = text; input.focus(); input.style.height='auto'; input.style.height=input.scrollHeight+'px'; }
  const banner = el.closest('.ppt-suggest-banner');
  if(banner){ banner.classList.add('hiding'); setTimeout(()=>banner.remove(), 400); }
}

const _pptKeywords = /PPT|ppt|파워포인트|프레젠테이션|발표자료|슬라이드\s*만들|피피티/i;

/*
 * === 적용 방법 ===
 *
 * 1. HTML: <div class="messages"> 바로 위에 추가
 *    <div id="pptSuggestArea"></div>
 *
 * 2. send() 함수 시작 부분에 추가 (const text= 다음):
 *    if(text && _pptKeywords.test(text) && !/차트|그래프|표|table|chart|graph|시각화|도넛|원형/i.test(text)){
 *      _showPptSuggestBanner();
 *    }
 */
