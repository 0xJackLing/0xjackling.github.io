(function () {
  var sections = ["papers", "dashboard", "opportunities", "benchmark"];
  var parts = location.pathname.split("/").filter(Boolean);
  var section = "";
  for (var i = 0; i < parts.length; i++) {
    if (sections.indexOf(parts[i]) !== -1) section = parts[i];
  }
  var root = section ? "../" : "./";
  var page = section || "home";
  if (!section && (parts[parts.length - 1] || "").indexOf("related") === 0) page = "links";

  var items = [
    ["home", "Homepage", root + "index.html"],
    ["links", "Related Links", root + "related.html"],
    ["papers", "Paper Tracker", root + "papers/"],
    ["dashboard", "Dashboard", root + "dashboard/"],
    ["opportunities", "Opportunities", root + "opportunities/"],
    ["benchmark", "Benchmark", root + "benchmark/ranking.html"]
  ];

  var links = items.map(function (item) {
    var current = item[0] === page ? ' aria-current="page"' : "";
    return '<a href="' + item[2] + '"' + current + ">" + item[1] + "</a>";
  }).join("");

  document.documentElement.classList.add("site-has-nav");
  document.write(
    '<header class="site-nav">' +
      '<a class="site-brand" href="' + root + 'index.html">Shengchen Ling</a>' +
      '<button class="site-toggle" type="button" aria-expanded="false" aria-controls="site-links" aria-label="Open menu">' +
        "<span></span><span></span><span></span>" +
      "</button>" +
      '<nav class="site-links" id="site-links">' + links + "</nav>" +
    "</header>"
  );

  var toggle = document.querySelector(".site-toggle");
  if (toggle) {
    toggle.addEventListener("click", function () {
      var nav = document.querySelector(".site-nav");
      var open = nav.classList.toggle("is-open");
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
    });
  }
})();
