/* Love Match AI — front-end behavior (vanilla JS, fully offline). */
(function () {
  "use strict";

  /* ---------- floating hearts background ---------- */
  var heartsBg = document.getElementById("hearts-bg");
  if (heartsBg) {
    var HEARTS = ["💗", "💖", "💘", "💕", "❤️", "💜"];
    function spawnHeart() {
      var el = document.createElement("span");
      el.className = "floating-heart";
      el.textContent = HEARTS[Math.floor(Math.random() * HEARTS.length)];
      el.style.left = Math.random() * 100 + "vw";
      el.style.fontSize = 14 + Math.random() * 26 + "px";
      var dur = 9 + Math.random() * 10;
      el.style.animationDuration = dur + "s";
      heartsBg.appendChild(el);
      setTimeout(function () { el.remove(); }, dur * 1000);
    }
    for (var i = 0; i < 6; i++) setTimeout(spawnHeart, i * 900);
    setInterval(spawnHeart, 2600);
  }

  /* ---------- drop zones: click, preview, drag & drop ---------- */
  document.querySelectorAll(".drop-zone").forEach(function (zone) {
    var input = zone.querySelector("input[type=file]");
    var preview = zone.querySelector(".dz-preview");
    if (!input) return;

    function showPreview(file) {
      if (!file || !file.type || file.type.indexOf("image") !== 0) return;
      var reader = new FileReader();
      reader.onload = function (e) {
        preview.src = e.target.result;
        preview.hidden = false;
        zone.classList.add("has-photo");
      };
      reader.readAsDataURL(file);
    }

    input.addEventListener("change", function () {
      if (input.files && input.files[0]) showPreview(input.files[0]);
    });

    ["dragenter", "dragover"].forEach(function (ev) {
      zone.addEventListener(ev, function (e) {
        e.preventDefault();
        zone.classList.add("drag-over");
      });
    });
    ["dragleave", "drop"].forEach(function (ev) {
      zone.addEventListener(ev, function (e) {
        e.preventDefault();
        zone.classList.remove("drag-over");
      });
    });
    zone.addEventListener("drop", function (e) {
      if (e.dataTransfer && e.dataTransfer.files.length) {
        input.files = e.dataTransfer.files;
        showPreview(e.dataTransfer.files[0]);
      }
    });
  });

  /* ---------- candidate slots: add / remove ---------- */
  var addBtn = document.getElementById("add-candidate");
  if (addBtn) {
    addBtn.addEventListener("click", function () {
      var hidden = document.querySelector(".cand-slot.slot-hidden");
      if (hidden) hidden.classList.remove("slot-hidden");
      if (!document.querySelector(".cand-slot.slot-hidden")) addBtn.style.display = "none";
    });
    document.querySelectorAll(".slot-remove").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var slot = btn.closest(".cand-slot");
        var input = slot.querySelector("input[type=file]");
        var name = slot.querySelector("input[type=text]");
        var preview = slot.querySelector(".dz-preview");
        input.value = "";
        name.value = "";
        preview.hidden = true;
        preview.removeAttribute("src");
        slot.querySelector(".drop-zone").classList.remove("has-photo");
        slot.classList.add("slot-hidden");
        addBtn.style.display = "";
      });
    });
  }

  /* ---------- analyzing overlay ---------- */
  var overlay = document.getElementById("love-overlay");
  var overlayMsg = document.getElementById("overlay-msg");
  var overlayFill = document.getElementById("overlay-progress-fill");
  var msgTimer = null;

  function getAnalyzingMessages() {
    var el = document.getElementById("analyzing-data");
    try { return JSON.parse(el.textContent); } catch (e) { return ["💘"]; }
  }

  function startOverlay() {
    if (!overlay) return;
    overlay.hidden = false;
    var msgs = getAnalyzingMessages();
    var idx = 0;
    overlayMsg.textContent = msgs[0];
    msgTimer = setInterval(function () {
      overlayMsg.classList.add("fading");
      setTimeout(function () {
        idx = (idx + 1) % msgs.length;
        overlayMsg.textContent = msgs[idx];
        overlayMsg.classList.remove("fading");
      }, 300);
    }, 1400);
  }

  function setOverlayProgress(pct) {
    if (overlayFill) overlayFill.style.width = pct + "%";
  }

  function stopOverlay() {
    if (!overlay) return;
    clearInterval(msgTimer);
    overlay.classList.add("closing");
    setTimeout(function () { overlay.hidden = true; }, 520);
  }

  /* show overlay while the form uploads + the server analyzes */
  var matchForm = document.getElementById("match-form");
  if (matchForm) {
    matchForm.addEventListener("submit", function () {
      startOverlay();
      var p = 8;
      setOverlayProgress(p);
      var t = setInterval(function () {
        p = Math.min(p + Math.random() * 9, 88); // real finish happens on redirect
        setOverlayProgress(p);
      }, 450);
      window.addEventListener("pagehide", function () { clearInterval(t); });
    });
  }

  /* ---------- result page: dramatic reveal sequence ---------- */
  var resultRoot = document.getElementById("result-root");
  if (resultRoot) {
    var isNew = resultRoot.getAttribute("data-new") === "1";
    var items = resultRoot.querySelectorAll(".result-item");

    function fillBars() {
      resultRoot.querySelectorAll(".score-bar-fill").forEach(function (bar) {
        var score = parseInt(bar.getAttribute("data-score"), 10) || 0;
        requestAnimationFrame(function () { bar.style.width = score + "%"; });
      });
    }

    function countUps() {
      resultRoot.querySelectorAll(".count-up").forEach(function (el) {
        var target = parseInt(el.getAttribute("data-target"), 10) || 0;
        var start = null;
        var dur = 1500;
        function tick(ts) {
          if (!start) start = ts;
          var t = Math.min((ts - start) / dur, 1);
          var eased = 1 - Math.pow(1 - t, 3);
          el.textContent = Math.round(target * eased);
          if (t < 1) requestAnimationFrame(tick);
        }
        requestAnimationFrame(tick);
      });
    }

    function celebrate() {
      if (typeof confetti !== "function") return;
      var photo = document.getElementById("winner-photo");
      var origin = { x: 0.5, y: 0.35 };
      if (photo) {
        var r = photo.getBoundingClientRect();
        origin = {
          x: (r.left + r.width / 2) / window.innerWidth,
          y: (r.top + r.height / 2) / window.innerHeight,
        };
      }
      confetti({ particleCount: 130, spread: 85, origin: origin });
      setTimeout(function () {
        confetti({ particleCount: 70, angle: 60, spread: 60, origin: { x: 0, y: 0.7 } });
        confetti({ particleCount: 70, angle: 120, spread: 60, origin: { x: 1, y: 0.7 } });
      }, 550);
      setTimeout(function () {
        confetti({
          particleCount: 45,
          spread: 100,
          origin: origin,
          scalar: 1.6,
          shapes: ["circle"],
          colors: ["#ff5d8f", "#ff8fb3", "#c99bff", "#ffffff"],
        });
      }, 1100);
    }

    function revealAll() {
      items.forEach(function (el, i) {
        el.style.animationDelay = i * 0.16 + "s";
        el.classList.add("shown");
      });
      setTimeout(fillBars, 500);
      setTimeout(countUps, 500);
      setTimeout(celebrate, 1300);
    }

    if (isNew) {
      /* dramatic pause: overlay plays ~4.2s, then the big reveal */
      startOverlay();
      var prog = 0;
      var pt = setInterval(function () {
        prog = Math.min(prog + 5, 100);
        setOverlayProgress(prog);
      }, 190);
      setTimeout(function () {
        clearInterval(pt);
        setOverlayProgress(100);
        setTimeout(function () {
          stopOverlay();
          revealAll();
        }, 350);
      }, 4200);
    } else {
      /* viewing an old match: no overlay, quick reveal */
      revealAll();
    }
  }

  /* ---------- history: rename toggle ---------- */
  document.querySelectorAll(".rename-toggle").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var card = btn.closest(".history-body");
      var form = card.querySelector(".rename-form");
      form.hidden = !form.hidden;
      if (!form.hidden) form.querySelector("input[type=text]").focus();
    });
  });

  /* ---------- delete confirmation ---------- */
  document.querySelectorAll("form.js-confirm").forEach(function (form) {
    form.addEventListener("submit", function (e) {
      var msg = form.getAttribute("data-confirm") || "Are you sure?";
      if (!window.confirm(msg)) e.preventDefault();
    });
  });
})();
