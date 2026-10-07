(() => {
  const measurementId = '';
  if (!/^G-[A-Z0-9]+$/i.test(measurementId)) return;

  window.dataLayer = window.dataLayer || [];
  window.gtag = window.gtag || function(){ window.dataLayer.push(arguments); };
  window.gtag('js', new Date());
  window.gtag('config', measurementId, {
    send_page_view: true,
    language_variant: document.documentElement.lang || 'unknown'
  });

  const script = document.createElement('script');
  script.async = true;
  script.src = `https://www.googletagmanager.com/gtag/js?id=${encodeURIComponent(measurementId)}`;
  document.head.appendChild(script);

  document.addEventListener('click', (event) => {
    const link = event.target.closest('a[data-track]');
    if (!link) return;
    window.gtag('event', link.dataset.track, {
      link_type: link.protocol === 'tel:' ? 'phone' : link.protocol === 'mailto:' ? 'email' : 'navigation',
      language_variant: document.documentElement.lang || 'unknown'
    });
  });
})();
