(() => {
  const measurementId = window.DOLPHIN_GA4_ID || '';
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
      link_url: link.href,
      language_variant: document.documentElement.lang || 'unknown'
    });
  });
})();
