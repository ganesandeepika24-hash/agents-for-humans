// Service worker for AgentNick push notifications.
// Runs in the background, independent of whether the tab is open,
// and displays a real OS-level notification when a push arrives.

self.addEventListener('push', function (event) {
  const data = event.data ? event.data.json() : {};
  const title = data.title || 'AgentNick';
  const options = {
    body: data.body || 'You have an update.',
    icon: '/static/icon.png',
    data: { url: data.url || '/' },
  };
  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener('notificationclick', function (event) {
  event.notification.close();
  const url = event.notification.data && event.notification.data.url;
  if (url) {
    event.waitUntil(clients.openWindow(url));
  }
});
