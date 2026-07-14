/*
 * Cowork Team Report — Team installer helper (client-side only).
 *
 * The two download buttons hand over ready-to-use skill zips that already have the manager's
 * Teams channel BAKED IN. When you paste your channel link and it verifies, the download builds
 * the zip in your browser (via JSZip) and writes the team_id / channel_id into the skill's channel
 * CONFIG file only (member: config/team_channel.json, manager: config/team_config.json) — the same
 * file each skill already reads on first run. No SKILL.md, script, or other skill logic is touched,
 * so an app-baked zip and a hand-downloaded one run identical skill code; the baked one just skips
 * the first-run "paste the link" prompt. Everything happens locally; the link never leaves the page.
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

    return { ok: true, channel_id: channelId, team_id: teamId, channel_name: channelName, link: input };
  }

  // ---- Baking: inject the resolved channel into each skill's channel CONFIG file ---------------
  //
  // This helper is PURE (JSON text in → JSON text out) so it can be unit-tested offline. It ONLY
  // fills the channel fields that already exist in the config — key order, comments (_note fields),
  // pricing, and every other value are preserved. No skill logic file is ever modified.
  //
  //   member  → config/team_channel.json  (channel_link, team_id, channel_id, channel_name)
  //   manager → config/team_config.json   (same channel fields; pricing/privacy fields untouched)
  //
  // A blank config makes the skill ask for the link on first run; a filled one makes it skip that
  // prompt and read the right channel straight away — so baked and hand-downloaded zips behave the
  // same except for that first-run question.
  function patchChannelConfig(jsonText, ch) {
    var cfg;
    try {
      cfg = JSON.parse(jsonText);
    } catch (e) {
      // If the config can't be parsed for some reason, leave it untouched rather than corrupt it.
      return jsonText;
    }
    if ("channel_link" in cfg) cfg.channel_link = ch.link || "";
    if ("team_id" in cfg) cfg.team_id = ch.team_id || "";
    if ("channel_id" in cfg) cfg.channel_id = ch.channel_id || "";
    if ("channel_name" in cfg && ch.channel_name) cfg.channel_name = ch.channel_name;
    return JSON.stringify(cfg, null, 2) + "\n";
  }

  // Load the static zip, patch the channel config entry in place, and return a fresh Blob.
  async function bakeZip(file, ch, kind) {
    if (typeof JSZip === "undefined") {
      throw new Error("the zip builder (JSZip) didn't load — refresh the page and try again.");
    }
    var resp = await fetch(file, { cache: "no-store" });
    if (!resp.ok) throw new Error("could not fetch " + file + " (" + resp.status + ")");
    var zip = await JSZip.loadAsync(await resp.blob());

    var configRe = kind === "member"
      ? /\/config\/team_channel\.json$/i
      : /\/config\/team_config\.json$/i;

    var targets = [];
    zip.forEach(function (path, entry) {
      if (!entry.dir && configRe.test(path)) targets.push(path);
    });

    for (var i = 0; i < targets.length; i++) {
      var original = await zip.file(targets[i]).async("string");
      zip.file(targets[i], patchChannelConfig(original, ch));
    }

    return zip.generateAsync({ type: "blob", compression: "DEFLATE" });
  }

  // ---- DOM wiring ------------------------------------------------------------------------------
  var $ = function (id) { return document.getElementById(id); };
  var resolved = null; // last successful parse

  // Default (un-baked) copy for the state spans, restored when there's no verified link.
  var DEFAULT_MGR_STATE = "It asks for your Teams channel link the first time you run it.";
  var DEFAULT_MEM_STATE = "Each teammate is asked for the Teams channel link the first time they run it.";

  function setStatus(el, msg, cls) {
    if (!el) return;
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

  function setText(id, txt) {
    var el = $(id);
    if (el) el.textContent = txt;
  }

  // Under each download button: when a channel is verified, tell the manager it will be baked into
  // the zip (nothing to paste on first run). Otherwise, prompt them to verify a link first.
  function refreshDownloadNotes() {
    if (resolved) {
      var name = resolved.channel_name || "your team's channel";
      var baked = "✓ Your channel (" + name + ") will be baked into this zip — teammates just upload it, no first-run link to paste.";
      var bakedMgr = "✓ Your channel (" + name + ") will be baked into this zip — no first-run link to paste.";
      setText("bakeNote", baked);
      setText("bakeNoteMgr", bakedMgr);
      toggleNote("bakeNote", true);
      toggleNote("bakeNoteMgr", true);
      toggleNote("genNote", false);
      toggleNote("genNoteMgr", false);
      setText("mgrBakeState", "The channel is already baked into your download — no first-run link to paste.");
      setText("memBakeState", "The channel is already baked into the zip you share — no first-run link to paste.");
    } else {
      toggleNote("bakeNote", false);
      toggleNote("bakeNoteMgr", false);
      toggleNote("genNote", true);
      toggleNote("genNoteMgr", true);
      setText("mgrBakeState", DEFAULT_MGR_STATE);
      setText("memBakeState", DEFAULT_MEM_STATE);
    }
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

  // Resolve the channel to bake: prefer the verified parse; otherwise try to parse the link field
  // live so a manager who typed a good link but didn't click "verify" still gets a baked zip.
  function requireChannel(statusEl) {
    if (resolved) return resolved;
    var res = parseTeamsChannelLink($("link") ? $("link").value : "");
    if (res.ok) {
      resolved = res;
      onParse(); // reflect it in the UI + readout
      return resolved;
    }
    setStatus(statusEl, "✕ Paste your Teams channel link above and click “Parse & verify” first — it gets baked into the download.", "err");
    var linkEl = $("link");
    if (linkEl) linkEl.focus();
    return null;
  }

  // Build + hand over the channel-baked skill zip.
  async function downloadBaked(opts) {
    var st = $(opts.statusId);
    var btn = $(opts.btnId);
    var ch = requireChannel(st);
    if (!ch) return;
    btn.disabled = true;
    setStatus(st, "Baking your channel into the skill…");
    try {
      var blob = await bakeZip(opts.file, ch, opts.kind);
      triggerDownload(blob, opts.fname);
      var name = ch.channel_name || "your channel";
      setStatus(st, "✓ Downloaded " + opts.fname + " with " + name + " baked in — " + opts.successMsg, "ok");
    } catch (err) {
      setStatus(st, "✕ Could not build the download: " + (err && err.message ? err.message : err), "err");
    } finally {
      btn.disabled = false;
    }
  }

  function onDownloadMember() {
    return downloadBaked({
      btnId: "downloadBtn", statusId: "dlStatus", kind: "member",
      file: "downloads/cowork-dashboard-member.zip",
      fname: "cowork-dashboard-member.zip",
      successMsg: "post this one into your dedicated channel and @tag your team."
    });
  }

  function onDownloadManager() {
    return downloadBaked({
      btnId: "downloadMgrBtn", statusId: "dlMgrStatus", kind: "manager",
      file: "downloads/cowork-dashboard-team-dashboard.zip",
      fname: "cowork-dashboard-team-dashboard.zip",
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
      refreshDownloadNotes();
    });
  }

  // Exposed for the offline resolver + baking self-tests.
  if (typeof module !== "undefined" && module.exports) {
    module.exports = {
      parseTeamsChannelLink: parseTeamsChannelLink,
      patchChannelConfig: patchChannelConfig
    };
  }
})();
