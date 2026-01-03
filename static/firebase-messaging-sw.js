// Firebase Cloud Messaging Service Worker
// This file is required by browsers for web push notifications
// Since we're using React Native for mobile notifications, this is a minimal implementation

self.addEventListener('install', function(event) {
    // Service worker installed
    self.skipWaiting();
});

self.addEventListener('activate', function(event) {
    // Service worker activated
    event.waitUntil(self.clients.claim());
});

// Minimal Firebase messaging handler (for web push if needed in future)
self.addEventListener('message', function(event) {
    // Handle messages if needed
});

