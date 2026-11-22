// Both layouts use the native disclosure, including when scripts are unavailable.
const landingMenu = document.querySelector('.wc-landing__menu');
const narrowHeader = window.matchMedia('(max-width: 44rem)');
function setMenuLayout() {
  landingMenu.open = !narrowHeader.matches;
}
setMenuLayout();
narrowHeader.addEventListener('change', setMenuLayout);
