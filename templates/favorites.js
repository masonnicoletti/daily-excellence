/* Daily Excellence favorites.
   Saved only in this browser (localStorage "de-favorites"), newest favorite first:
   [{"slug": "2026-11-04", "at": 1762300000000}, ...]. Nothing is sent anywhere. */
(function () {
  "use strict";
  var KEY = "de-favorites";

  function load() {
    try {
      var list = JSON.parse(localStorage.getItem(KEY) || "[]");
      return Array.isArray(list) ? list.filter(function (f) { return f && typeof f.slug === "string"; }) : [];
    } catch (e) { return []; }
  }
  function save(list) {
    try { localStorage.setItem(KEY, JSON.stringify(list)); } catch (e) {}
  }
  function has(list, slug) {
    return list.some(function (f) { return f.slug === slug; });
  }

  /* Star button at the top of an essay. */
  function initButton() {
    var btn = document.querySelector(".fav-button");
    if (!btn) return;
    var slug = btn.getAttribute("data-slug"), label = btn.querySelector(".fav-label");
    function sync() {
      var on = has(load(), slug);
      btn.setAttribute("aria-pressed", String(on));
      label.textContent = on ? "Favorited" : "Favorite";
      btn.title = on ? "Remove from favorites" : "Add to favorites";
    }
    btn.addEventListener("click", function () {
      var list = load();
      if (has(list, slug)) list = list.filter(function (f) { return f.slug !== slug; });
      else list.unshift({ slug: slug, at: Date.now() });
      save(list);
      sync();
    });
    sync();
  }

  /* Filled stars on list rows (Recent, Archive, Favorites). */
  function markRows() {
    var list = load();
    document.querySelectorAll(".fav-indicator").forEach(function (el) {
      var on = has(list, el.getAttribute("data-slug"));
      el.classList.toggle("is-fav", on);
      el.title = on ? "Favorite" : "";
    });
  }

  /* Favorites section on the home page, built from the embedded essay list. */
  function renderFavorites() {
    var ul = document.getElementById("favorites-list"), data = document.getElementById("posts-data");
    if (!ul || !data) return;
    var cards = {};
    try { JSON.parse(data.textContent).forEach(function (c) { cards[c.slug] = c; }); } catch (e) { return; }
    var star = document.querySelector(".fav-indicator .star");
    ul.textContent = "";
    load().forEach(function (f) {
      var c = cards[f.slug];
      if (!c) return;                         /* an essay that no longer exists */
      var li = document.createElement("li"), a = document.createElement("a");
      a.href = "posts/" + c.slug + ".html";
      var time = document.createElement("time");
      time.dateTime = c.date; time.textContent = c.date_short;
      var title = document.createElement("span");
      title.className = "archive-title"; title.textContent = c.title;
      var idea = document.createElement("span");
      idea.className = "archive-idea"; idea.textContent = c.idea;
      var ind = document.createElement("span");
      ind.className = "fav-indicator is-fav"; ind.title = "Favorite";
      ind.setAttribute("data-slug", c.slug);  /* so markRows() keeps it filled */
      if (star) ind.appendChild(star.cloneNode(true));
      a.append(time, title, idea, ind);
      li.appendChild(a);
      ul.appendChild(li);
    });
    var empty = document.getElementById("favorites-empty");
    if (empty) empty.hidden = ul.children.length > 0;
  }

  function init() {
    initButton();
    renderFavorites();
    markRows();
  }
  document.addEventListener("DOMContentLoaded", init);
  /* Returning with the Back button can show a cached page; refresh the stars. */
  window.addEventListener("pageshow", function (e) { if (e.persisted) init(); });
})();
