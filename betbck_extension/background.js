// background.js
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  console.log('[BetBCK Helper][Background] Received message:', message);
  if (message.type === 'FOCUS_BETBCK_TAB') {
    chrome.tabs.query({ url: '*://betbck.com/*' }, (tabs) => {
      console.log('[BetBCK Helper][Background] Found BetBCK tabs:', tabs);
      if (tabs.length > 0) {
        chrome.tabs.update(tabs[0].id, { active: true }, () => {
          console.log('[BetBCK Helper][Background] Activated BetBCK tab:', tabs[0].id);
          chrome.tabs.sendMessage(tabs[0].id, {
            type: 'SEARCH_BETBCK',
            keyword: message.keyword,
            betInfo: message.betInfo || {}
          }, () => {
            console.log('[BetBCK Helper][Background] Sent SEARCH_BETBCK to content script.');
          });
        });
      } else {
        // Optionally open a new tab if not found
        chrome.tabs.create({ url: 'https://betbck.com' }, (tab) => {
          console.log('[BetBCK Helper][Background] Created new BetBCK tab:', tab.id);
          // Wait for tab to load, then send message
          chrome.tabs.onUpdated.addListener(function listener(tabId, info) {
            if (tabId === tab.id && info.status === 'complete') {
              chrome.tabs.onUpdated.removeListener(listener);
              chrome.tabs.sendMessage(tabId, {
                type: 'SEARCH_BETBCK',
                keyword: message.keyword,
                betInfo: message.betInfo || {}
              }, () => {
                console.log('[BetBCK Helper][Background] Sent SEARCH_BETBCK to new content script.');
              });
            }
          });
        });
      }
    });
    sendResponse({ status: 'ok' });
    return true;
  }
}); 