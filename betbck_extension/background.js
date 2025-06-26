// background.js
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'FOCUS_BETBCK_TAB') {
    chrome.tabs.query({ url: '*://betbck.com/*' }, (tabs) => {
      if (tabs.length > 0) {
        chrome.tabs.update(tabs[0].id, { active: true });
        // Send the search term to the content script
        chrome.tabs.sendMessage(tabs[0].id, {
          type: 'SEARCH_BETBCK',
          keyword: message.keyword,
          betInfo: message.betInfo || {}
        });
      } else {
        // Optionally open a new tab if not found
        chrome.tabs.create({ url: 'https://betbck.com' }, (tab) => {
          // Wait for tab to load, then send message
          chrome.tabs.onUpdated.addListener(function listener(tabId, info) {
            if (tabId === tab.id && info.status === 'complete') {
              chrome.tabs.onUpdated.removeListener(listener);
              chrome.tabs.sendMessage(tabId, {
                type: 'SEARCH_BETBCK',
                keyword: message.keyword,
                betInfo: message.betInfo || {}
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