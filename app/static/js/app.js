(function () {
  const isLocalhost = ['localhost', '127.0.0.1', '0.0.0.0'].includes(window.location.hostname);

  if (window.matchMedia('(display-mode: standalone)').matches) {
    console.log('Running in standalone mode');
  }

  if ('serviceWorker' in navigator) {
    if (isLocalhost) {
      window.addEventListener('load', function () {
        navigator.serviceWorker.getRegistrations().then(function (registrations) {
          registrations.forEach(function (registration) {
            registration.unregister();
          });
        });
        if ('caches' in window) {
          window.caches.keys().then(function (keys) {
            keys.forEach(function (key) {
              window.caches.delete(key);
            });
          });
        }
      });
    } else {
      window.addEventListener('load', function () {
        navigator.serviceWorker.register('/service-worker.js').catch(function (error) {
          console.warn('service worker registration failed', error);
        });
      });
    }
  }

  function initEventSections() {
    const form = document.querySelector('form[data-event-form]');
    if (!form) {
      return;
    }
    const eventTypeField = form.querySelector('#id_event_type');
    const sections = form.querySelectorAll('[data-event-section]');
    if (!eventTypeField || !sections.length) {
      return;
    }

    const renderSections = function () {
      const activeType = eventTypeField.value;
      sections.forEach(function (section) {
        section.hidden = section.getAttribute('data-event-section') !== activeType;
      });
    };

    eventTypeField.addEventListener('change', renderSections);
    renderSections();
  }

  window.addEventListener('DOMContentLoaded', function () {
    const timezoneInput = document.getElementById('id_timezone');
    if (timezoneInput && (!timezoneInput.value || timezoneInput.value === 'UTC')) {
      timezoneInput.value = Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC';
    }
    initEventSections();
  });
})();
