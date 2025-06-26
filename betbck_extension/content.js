// content.js
function sleep(ms) { return new Promise(resolve => setTimeout(resolve, ms)); }

// --- Auto re-login logic ---
function isLoggedOut() {
  // Adjust selectors as needed for BetBCK login form
  return !!document.querySelector('input[type="password"], input[name="password"], form[action*="login"]');
}

function tryAutoLogin() {
  // Try to click the login button if credentials are pre-filled
  const loginBtn = document.querySelector('button[type="submit"], input[type="submit"]');
  if (loginBtn) {
    loginBtn.click();
    return true;
  }
  return false;
}

// --- Enhanced auto re-login logic ---
function clickErrorDialogIfPresent() {
  // Try to find and click a modal/alert button (adjust selector as needed)
  const errorBtn = document.querySelector('button, input[type="button"], input[type="submit"]');
  if (errorBtn && errorBtn.offsetParent !== null) {
    errorBtn.click();
    return true;
  }
  return false;
}

async function handleBetbckAction(message) {
  // Step 1: If error dialog is present, click it and retry after a short delay
  if (clickErrorDialogIfPresent()) {
    setTimeout(() => handleBetbckAction(message), 1000);
    return;
  }
  // Step 2: If logged out, try to auto-login
  if (isLoggedOut()) {
    alert('You are logged out of BetBCK. Please log in to continue.');
    if (tryAutoLogin()) {
      setTimeout(() => handleBetbckAction(message), 2000); // Retry after login
    }
    return;
  }
  if (message.type === 'SEARCH_BETBCK') {
    const keyword = message.keyword;
    const betInfo = message.betInfo || {};
    // Try to find the search bar (adjust selector as needed)
    const searchInput = document.querySelector('input[name="keyword_search"], input#keyword_search');
    if (searchInput) {
      searchInput.focus();
      searchInput.value = '';
      // Simulate typing
      (async () => {
        for (let i = 0; i < keyword.length; i++) {
          searchInput.value += keyword[i];
          await sleep(50 + Math.random() * 50);
        }
        searchInput.dispatchEvent(new Event('input', { bubbles: true }));
        await sleep(200);
        // Try to submit search
        const searchBtn = document.querySelector('button[type="submit"], input[type="submit"]');
        if (searchBtn) searchBtn.click();
        else searchInput.form && searchInput.form.submit();
        // Show the popup with bet info
        showBetPopup(betInfo, keyword);
      })();
    }
  } else if (message.type === 'FOCUS_BETBCK_TAB') {
    chrome.runtime.sendMessage({
      type: 'FOCUS_BETBCK_TAB',
      keyword: message.keyword,
      betInfo: message.betInfo || {}
    });
  }
}

chrome.runtime.onMessage.addListener(async (message, sender, sendResponse) => {
  if (message.type === 'SEARCH_BETBCK' || message.type === 'FOCUS_BETBCK_TAB') {
    handleBetbckAction(message);
  }
});

// Listen for window.postMessage from the web app
window.addEventListener('message', function(event) {
  // Only accept messages from the same window
  if (event.source !== window) return;
  const message = event.data;
  if (message && message.type === 'FOCUS_BETBCK_TAB') {
    chrome.runtime.sendMessage({
      type: 'FOCUS_BETBCK_TAB',
      keyword: message.keyword,
      betInfo: message.betInfo || {}
    });
  }
});

// --- Popup UI ---
let betPopup = null;
function showBetPopup(betInfo, keyword) {
  if (betPopup) betPopup.remove();
  betPopup = document.createElement('div');
  betPopup.style.position = 'fixed';
  betPopup.style.top = '80px';
  betPopup.style.right = '40px';
  betPopup.style.zIndex = 99999;
  betPopup.style.background = '#181c24';
  betPopup.style.color = '#fff';
  betPopup.style.padding = '18px 22px 18px 18px';
  betPopup.style.borderRadius = '12px';
  betPopup.style.boxShadow = '0 4px 24px rgba(0,0,0,0.25)';
  betPopup.style.minWidth = '260px';
  betPopup.style.fontFamily = 'Inter, Roboto, Arial, sans-serif';
  betPopup.style.cursor = 'move';
  betPopup.style.userSelect = 'none';
  betPopup.innerHTML = `
    <div style="font-weight:700;font-size:1.1em;margin-bottom:6px;">BetBCK Helper</div>
    <div><b>Search:</b> <span style="color:#00d4ff">${keyword}</span></div>
    <div><b>Line:</b> ${betInfo.line || ''}</div>
    <div><b>EV:</b> <span id="ev-value">${betInfo.ev || ''}</span></div>
    <div><b>BetBCK Odds:</b> ${betInfo.betbck_odds || ''}</div>
    <div><b>NVP:</b> <span id="nvp-value">${betInfo.nvp || ''}</span></div>
    <button id="close-betbck-popup" style="margin-top:10px;padding:4px 12px;border:none;background:#ff6b35;color:#fff;border-radius:6px;cursor:pointer;">Close</button>
  `;
  document.body.appendChild(betPopup);
  // Drag logic
  let isDragging = false, offsetX = 0, offsetY = 0;
  betPopup.addEventListener('mousedown', (e) => {
    isDragging = true;
    offsetX = e.clientX - betPopup.getBoundingClientRect().left;
    offsetY = e.clientY - betPopup.getBoundingClientRect().top;
    betPopup.style.transition = 'none';
  });
  document.addEventListener('mousemove', (e) => {
    if (isDragging) {
      betPopup.style.left = (e.clientX - offsetX) + 'px';
      betPopup.style.top = (e.clientY - offsetY) + 'px';
      betPopup.style.right = '';
    }
  });
  document.addEventListener('mouseup', () => { isDragging = false; betPopup.style.transition = ''; });
  document.getElementById('close-betbck-popup').onclick = () => betPopup.remove();
  // Poll for real-time NVP/EV
  if (betInfo.eventId) {
    pollEVNVP(betInfo.eventId);
  }
}

function pollEVNVP(eventId) {
  // Replace with your backend endpoint as needed
  const url = `http://localhost:5001/get_active_events_data`;
  let interval = setInterval(async () => {
    try {
      const res = await fetch(url);
      const data = await res.json();
      for (let eid in data) {
        if (eid === eventId) {
          const event = data[eid];
          if (event && event.markets && event.markets.length > 0) {
            // Find the matching market (by line, etc.)
            // For now, just take the first
            document.getElementById('ev-value').textContent = event.markets[0].ev;
            document.getElementById('nvp-value').textContent = event.markets[0].pinnacle_nvp;
          }
        }
      }
    } catch {}
  }, 3000);
  betPopup.addEventListener('remove', () => clearInterval(interval));
} 