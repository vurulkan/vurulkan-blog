/* Small accessibility enhancements for the upstream Chirpy controls. */
document.querySelectorAll('i[class*="fa-"]').forEach((icon) => {
  icon.setAttribute('aria-hidden', 'true');
});
document.querySelectorAll('button.toc-trigger').forEach((button) => {
  if (!button.getAttribute('aria-label')) button.setAttribute('aria-label', 'Open table of contents');
});
document.querySelectorAll('#sidebar .nav-item.active > a').forEach((link) => {
  link.setAttribute('aria-current', 'page');
});
