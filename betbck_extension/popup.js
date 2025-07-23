// popup.js
document.getElementById('test-btn').onclick = () => {
  chrome.runtime.sendMessage({
    type: 'FOCUS_BETBCK_TAB',
    keyword: 'Test Search',
    betInfo: {
      line: 'Test Line',
      ev: '+5.00%',
      betbck_odds: '-110',
      nvp: '-108',
      eventId: 'test_event_id'
    }
  }, (response) => {
    document.getElementById('status').textContent = response && response.status === 'ok' ? 'Triggered' : 'Failed';
  });
}; 