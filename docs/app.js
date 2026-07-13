/*
 * Cowork Team Report — Team installer helper (client-side only).
 *
 * The two download buttons hand over the exact, ready-to-use skill zips under ./downloads/.
 * Each skill asks for the team's Teams channel link the first time it runs, so nothing is baked
 * in here. The optional "Parse & verify" tool just sanity-checks a pasted channel link in the
 * browser (the link never leaves the page) so the manager knows it looks right before first run.
 */
(function () {
  "use strict";

  var GUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
  var CHANNEL_RE = /(19:[^/?#]+?@thread\.[a-z0-9]+)/i;

  // ---- Resolver (ported from the skill's proven first-run link parser) --------------------------
  function parseTeamsChannelLink(raw) {
    var input = (raw || "").trim();
    if (!input) return { ok: false, error: "Paste your team's Teams channel link first." };

    // URL-decode the link (%3A -> :, %40 -> @, ...). Fall back to targeted replacements if the
    // whole-string decode throws on a stray percent sequence.
    var decoded;
    try {
      decoded = decodeURIComponent(input);
    } catch (e) {
      decoded = input
        .replace(/%3A/gi, ":")
        .replace(/%40/gi, "@")
        .replace(/%2F/gi, "/")
        .replace(/%20/gi, " ");
    }

    // channel_id = first 19:…@thread.<suffix> match in the decoded (or raw) string.
    var chMatch = CHANNEL_RE.exec(decoded) || CHANNEL_RE.exec(input);
    var channelId = chMatch ? chMatch[1] : "";

    // team_id = the groupId query param (case-insensitive), from decoded or raw.
    var gidMatch = /[?&]groupId=([^&#]+)/i.exec(decoded) || /[?&]groupId=([^&#]+)/i.exec(input);
    var teamId = gidMatch ? gidMatch[1] : "";
    try { teamId = decodeURIComponent(teamId); } catch (e) { /* keep raw */ }
    teamId = teamId.trim();

    // Reject with a clear message if the pieces don't look right.
    if (!channelId || !/@thread\./i.test(channelId)) {
      return { ok: false, error: "Couldn't find a channel id (expected 19:…@thread.…). Use the channel's ⋯ → Copy link." };
    }
    if (!GUID_RE.test(teamId)) {
      return { ok: false, error: "Couldn't find a valid team id (a groupId GUID) in the link. Copy the full channel link and try again." };
    }

    // channel_name = the path segment right after the thread id, unless it's all digits (message id).
    var channelName = "";
    var pathPart = decoded.split(/[?#]/)[0];
    var segs = pathPart.split("/").filter(Boolean);
    var idx = -1;
    for (var i = 0; i < segs.length; i++) {
      if (/@thread\./i.test(segs[i])) { idx = i; break; }
    }
    if (idx >= 0 && idx + 1 < segs.length) {
      var cand = segs[idx + 1];
      try { cand = decodeURIComponent(cand); } catch (e) { /* keep raw */ }
      if (!/^\d+$/.test(cand)) channelName = cand.trim();
    }

    return { ok: true, channel_id: channelId, team_id: teamId, channel_name: channelName };
  }

  // ---- DOM wiring ------------------------------------------------------------------------------
  var $ = function (id) { return document.getElementById(id); };
  var resolved = null; // last successful parse

  function setStatus(el, msg, cls) {
    el.textContent = msg || "";
    el.className = "status" + (cls ? " " + cls : "");
  }

  function onParse() {
    var res = parseTeamsChannelLink($("link").value);
    var status = $("status");
    var panel = $("resolved");
    if (!res.ok) {
      resolved = null;
      panel.classList.remove("show");
      refreshDownloadNotes();
      setStatus(status, "✕ " + res.error, "err");
      return;
    }
    resolved = res;
    $("rName").textContent = res.channel_name || "(none in link)";
    $("rTeam").textContent = res.team_id;
    $("rChannel").textContent = res.channel_id;
    panel.classList.add("show");
    refreshDownloadNotes();
    setStatus(status, "");
    setStatus($("dlStatus"), "");
    setStatus($("dlMgrStatus"), "");
  }

  // Toggle a note by id.
  function toggleNote(id, show) {
    var el = $(id);
    if (el) { if (show) { el.classList.remove("hidden"); } else { el.classList.add("hidden"); } }
  }

  // Under each download button: reassure that the ready-to-use skill asks for the channel on
  // first run. Nothing is baked in, so we simply keep the first-run notes visible.
  function refreshDownloadNotes() {
    toggleNote("genNote", true);
    toggleNote("genNoteMgr", true);
    toggleNote("bakeNote", false);
    toggleNote("bakeNoteMgr", false);
  }

  // Editing the link invalidates any prior verification — fall back to generic until re-verified.
  function onLinkChanged() {
    resolved = null;
    var panel = $("resolved");
    if (panel) panel.classList.remove("show");
    refreshDownloadNotes();
    setStatus($("status"), "");
    setStatus($("dlStatus"), "");
    setStatus($("dlMgrStatus"), "");
  }

  function triggerDownload(blob, fname) {
    var url = URL.createObjectURL(blob);
    var a = document.createElement("a");
    a.href = url;
    a.download = fname;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(function () { URL.revokeObjectURL(url); }, 4000);
  }

  // Hands over the exact, ready-to-use skill zip under ./downloads/ — no in-browser assembly.
  async function downloadStatic(opts) {
    var st = $(opts.statusId);
    var btn = $(opts.btnId);
    btn.disabled = true;
    setStatus(st, "Preparing your download…");
    try {
      var resp = await fetch(opts.file, { cache: "no-store" });
      if (!resp.ok) throw new Error("could not fetch " + opts.file + " (" + resp.status + ")");
      var blob = await resp.blob();
      triggerDownload(blob, opts.fname);
      setStatus(st, "✓ Downloaded " + opts.fname + " — " + opts.successMsg, "ok");
    } catch (err) {
      setStatus(st, "✕ Could not start the download: " + (err && err.message ? err.message : err), "err");
    } finally {
      btn.disabled = false;
    }
  }

  function onDownloadMember() {
    return downloadStatic({
      btnId: "downloadBtn", statusId: "dlStatus",
      file: "downloads/cowork-roi-member.zip",
      fname: "cowork-roi-member.zip",
      successMsg: "post this one into your dedicated channel and @tag your team."
    });
  }

  function onDownloadManager() {
    return downloadStatic({
      btnId: "downloadMgrBtn", statusId: "dlMgrStatus",
      file: "downloads/cowork-roi-team-dashboard.zip",
      fname: "cowork-roi-team-dashboard.zip",
      successMsg: "install this one yourself."
    });
  }

  function makeCopyHandler(taId, btnId) {
    return function () {
      var ta = $(taId);
      if (!ta) return;
      ta.select();
      var done = function () {
        var btn = $(btnId);
        if (!btn) return;
        var old = btn.textContent;
        btn.textContent = "Copied";
        setTimeout(function () { btn.textContent = old; }, 1500);
      };
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(ta.value).then(done, function () { try { document.execCommand("copy"); done(); } catch (e) {} });
      } else {
        try { document.execCommand("copy"); done(); } catch (e) {}
      }
    };
  }

  if (typeof document !== "undefined") {
    document.addEventListener("DOMContentLoaded", function () {
      $("parseBtn").addEventListener("click", onParse);
      $("link").addEventListener("keydown", function (e) { if (e.key === "Enter") { e.preventDefault(); onParse(); } });
      $("link").addEventListener("input", onLinkChanged);
      $("downloadBtn").addEventListener("click", onDownloadMember);
      var mgrBtn = $("downloadMgrBtn"); if (mgrBtn) mgrBtn.addEventListener("click", onDownloadManager);
      $("copyBtn").addEventListener("click", makeCopyHandler("installText", "copyBtn"));
      var copyMgr = $("copyMgrBtn"); if (copyMgr) copyMgr.addEventListener("click", makeCopyHandler("installMgrText", "copyMgrBtn"));
      var copyRunMember = $("copyRunMemberBtn"); if (copyRunMember) copyRunMember.addEventListener("click", makeCopyHandler("runMemberText", "copyRunMemberBtn"));
    });
  }

  // Exposed for the offline resolver self-test (docs/skill-template not required).
  if (typeof module !== "undefined" && module.exports) {
    module.exports = { parseTeamsChannelLink: parseTeamsChannelLink };
  }
})();
