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
const labelScrollableContent = () => {
  document.querySelectorAll('.highlight, .table-wrapper').forEach((region) => {
    if (region.scrollWidth > region.clientWidth) {
      region.tabIndex = 0;
      region.setAttribute('role', 'region');
      region.setAttribute('aria-label', region.classList.contains('highlight') ? 'Scrollable code example' : 'Scrollable table');
    }
  });
};
document.fonts.ready.then(labelScrollableContent);
window.addEventListener('resize', labelScrollableContent);
const labelHeadingLinks = () => {
  document.querySelectorAll('.content a.anchor').forEach((link) => {
    const heading = link.closest('h2, h3, h4, h5, h6');
    if (heading) link.setAttribute('aria-label', `Link to ${heading.textContent.trim()}`);
  });
};
document.addEventListener('DOMContentLoaded', labelHeadingLinks);
window.addEventListener('load', labelHeadingLinks);
labelHeadingLinks();
