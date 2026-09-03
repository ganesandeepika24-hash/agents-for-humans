// Service worker for AgentNick push notifications.
// Handles both plain notifications (open the app) and in-notification
// action buttons that resolve directly (call /approve from the
// background, no app tab needs to be open).

const BACKEND_URL = 'https://f917a6d1-f299-444c-96af-61b8209cfd8c-00-339l9ymu91s2a.archer.replit.dev';
const DB_NAME = 'agentnick-sw';
const STORE_NAME = 'auth';

function openDb() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, 1);
    req.onupgradeneeded = () => {
      req.result.createObjectStore(STORE_NAME);
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

async function getToken() {
  const db = await openDb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readonly');
    const req = tx.objectStore(STORE_NAME).get('token');
    req.onsuccess = () => resolve(req.result || null);
    req.onerror = () => reject(req.error);
  });
}

self.addEventListener('push', function (event) {
  const data = event.data ? event.data.json() : {};
  const title = data.title || 'AgentNick';
  const notifOptions = {
    body: data.body || 'You have an update.',
    data: {
      url: data.url || '/',
      card_id: data.card_id || null,
      signal_id: data.signal_id || null,
    },
    actions: (data.actions || []).map(a => ({ action: a.action, title: a.title })),
  };
  event.waitUntil(self.registration.showNotification(title, notifOptions));
});

self.addEventListener('notificationclick', function (event) {
  event.notification.close();
  const notifData = event.notification.data || {};
  const clickedAction = event.action; // '' if the body was clicked, not a button

  // Body click (no action button) -- just open the app.
  if (!clickedAction) {
    if (notifData.url) {
      event.waitUntil(clients.openWindow(notifData.url));
    }
    return;
  }

  // A specific action button was clicked -- resolve it directly,
  // no need to open the app at all.
  if ((clickedAction === 'dismiss' || clickedAction === 'remind_later') && notifData.signal_id) {
    event.waitUntil(
      getToken().then(token => {
        if (!token) return clients.openWindow(notifData.url || '/');
        return fetch(`${BACKEND_URL}/approve`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`,
          },
          body: JSON.stringify({
            signal_id: notifData.signal_id,
            option_label: clickedAction,
            option_type: clickedAction,
          }),
        });
      })
    );
    return;
  }

  // Anything else (or missing signal_id) -- fall back to opening the app.
  if (notifData.url) {
    event.waitUntil(clients.openWindow(notifData.url));
  }
});
