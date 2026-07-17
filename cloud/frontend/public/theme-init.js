(function () {
  var pref = localStorage.getItem('theme_preference') || 'system';
  var dark =
    pref === 'dark' ||
    (pref === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches);
  document.documentElement.classList.toggle('v-theme--dark', dark);
  document.documentElement.classList.toggle('v-theme--light', !dark);
  var meta = document.querySelector('meta[name="theme-color"]');
  if (meta) meta.setAttribute('content', dark ? '#121212' : '#FFFFFF');
})();
