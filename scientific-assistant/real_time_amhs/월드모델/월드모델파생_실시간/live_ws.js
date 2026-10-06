/* 월드모델파생_실시간 — 웹소켓(/ws) 대신 1초마다 HTTP 로 묻는다.
   ★화면(월드모델파생 dashboard.html)은 손대지 않는다. 서버가 이 조각을 <head> 바로 뒤에 끼운다.
     실시간 서버는 표준 파이썬이라 웹소켓이 없다. 화면은 ws.onmessage 로 받기만 하므로,
     같은 모양으로 /api/live/snapshot 을 불러 onmessage 에 넘겨 주면 그대로 그린다.
   ★재생 명령(send: 재생·정지·속도·점프)은 버린다 — 실시간에는 없다.
   ★실패해도 끊지 않고 계속 묻는다 (서버를 다시 켜면 저절로 이어진다). */
(function () {
  var RealWS = window.WebSocket;
  var EVERY_MS = 1000;
  function LiveSocket(url) {
    var me = this;
    me.url = url;
    me.readyState = 0;
    me.onopen = me.onmessage = me.onclose = me.onerror = null;
    setTimeout(function () {
      me.readyState = 1;
      if (me.onopen) me.onopen({});
      me._tick();
    }, 0);
  }
  LiveSocket.prototype._tick = function () {
    var me = this;
    if (me.readyState !== 1) return;
    fetch('/api/live/snapshot', { cache: 'no-store', credentials: 'same-origin' })
      .then(function (r) { return r.text(); })
      .then(function (t) {
        window.__liveOk = Date.now();
        window.__liveErr = '';
        if (me.onmessage) me.onmessage({ data: t });
      })
      .catch(function (e) { window.__liveErr = String((e && e.message) || e); })
      .then(function () { me._timer = setTimeout(function () { me._tick(); }, EVERY_MS); });
  };
  LiveSocket.prototype.send = function () {};
  LiveSocket.prototype.close = function () { this.readyState = 3; clearTimeout(this._timer); };
  window.WebSocket = function (url, protocols) {
    if (/\/ws(\?|$)/.test(String(url))) return new LiveSocket(url);
    return protocols === undefined ? new RealWS(url) : new RealWS(url, protocols);
  };
  window.WebSocket.CONNECTING = 0; window.WebSocket.OPEN = 1;
  window.WebSocket.CLOSING = 2; window.WebSocket.CLOSED = 3;
})();
