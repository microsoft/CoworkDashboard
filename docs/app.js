/*
 * Cowork ROI — Team installer generator (client-side only).
 *
 * Parses a Teams channel link, shows the resolved ids for confirmation, then assembles a
 * ready-to-distribute copy of the cowork-roi-member skill with config/team_channel.json pre-filled.
 * Everything runs in the browser: the pasted link never leaves the page, and the only network
 * calls are same-origin fetches of the skill template under ./skill-template/.
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

  function slugForName(res) {
    var base = (res.channel_name || res.team_id || "team").toLowerCase();
    base = base.replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");
    return base || "team";
  }

  function onParse() {
    var res = parseTeamsChannelLink($("link").value);
    var status = $("status");
    var panel = $("resolved");
    var buttons = [$("downloadBtn"), $("downloadMgrBtn")];
    if (!res.ok) {
      resolved = null;
      panel.classList.remove("show");
      buttons.forEach(function (b) { if (b) b.disabled = true; });
      setStatus(status, "✕ " + res.error, "err");
      return;
    }
    resolved = res;
    $("rName").textContent = res.channel_name || "(none in link)";
    $("rTeam").textContent = res.team_id;
    $("rChannel").textContent = res.channel_id;
    panel.classList.add("show");
    buttons.forEach(function (b) { if (b) b.disabled = false; });
    setStatus(status, "✓ Link parsed. Confirm the values below, then download both skills.", "ok");
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

  // Generic builder: fetch a skill template by manifest, bake its channel config, download the zip.
  async function buildAndDownload(opts) {
    if (!resolved) return;
    var st = $(opts.statusId);
    var btn = $(opts.btnId);
    btn.disabled = true;
    setStatus(st, "Assembling zip in your browser…");

    try {
      var manifest = await (await fetch("skill-template/" + opts.manifestPath, { cache: "no-store" })).json();
      if (!Array.isArray(manifest) || !manifest.length) {
        throw new Error("template manifest is empty");
      }

      var zip = new JSZip();
      var configText = null;

      for (var i = 0; i < manifest.length; i++) {
        var relPath = manifest[i];
        var resp = await fetch("skill-template/" + relPath, { cache: "no-store" });
        if (!resp.ok) throw new Error("could not fetch " + relPath + " (" + resp.status + ")");
        if (relPath === opts.configPath) {
          configText = await resp.text();
          zip.file(relPath, configText); // placeholder — overwritten with the baked version below
        } else {
          zip.file(relPath, await resp.arrayBuffer());
        }
      }

      // Bake the resolved channel into this skill's config, preserving any other settings.
      zip.file(opts.configPath, opts.fillConfig(configText));

      var blob = await zip.generateAsync({ type: "blob", compression: "DEFLATE" });
      var fname = opts.zipPrefix + slugForName(resolved) + ".zip";
      triggerDownload(blob, fname);
      setStatus(st, "✓ Downloaded " + fname + " — " + opts.successMsg, "ok");
    } catch (err) {
      setStatus(st, "✕ Could not build the zip: " + (err && err.message ? err.message : err), "err");
    } finally {
      btn.disabled = false;
    }
  }

  // Member skill config — a small file with just the channel fields.
  function memberConfig() {
    return JSON.stringify({
      _note: "Per-team channel config baked by the installer generator. The skill uses these ids on first run instead of asking for a link.",
      channel_link: $("link").value.trim(),
      team_id: resolved.team_id,
      channel_id: resolved.channel_id,
      channel_name: resolved.channel_name
    }, null, 2) + "\n";
  }

  // Manager (dashboard) skill config — keep every operational default; only fill the channel fields.
  function dashboardConfig(templateText) {
    var cfg;
    try { cfg = JSON.parse(templateText); } catch (e) { cfg = {}; }
    cfg.team_id = resolved.team_id;
    cfg.channel_id = resolved.channel_id;
    cfg.channel_name = resolved.channel_name;
    cfg.channel_link = $("link").value.trim();
    return JSON.stringify(cfg, null, 2) + "\n";
  }

  function onDownloadMember() {
    return buildAndDownload({
      btnId: "downloadBtn", statusId: "dlStatus",
      manifestPath: "manifest.json",
      configPath: "cowork-roi-member/config/team_channel.json",
      zipPrefix: "cowork-roi-member-",
      successMsg: "send this one to your team.",
      fillConfig: memberConfig
    });
  }

  function onDownloadManager() {
    return buildAndDownload({
      btnId: "downloadMgrBtn", statusId: "dlMgrStatus",
      manifestPath: "manifest-dashboard.json",
      configPath: "cowork-roi-team-dashboard/config/team_config.json",
      zipPrefix: "cowork-roi-team-dashboard-",
      successMsg: "install this one yourself.",
      fillConfig: dashboardConfig
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
      $("downloadBtn").addEventListener("click", onDownloadMember);
      var mgrBtn = $("downloadMgrBtn"); if (mgrBtn) mgrBtn.addEventListener("click", onDownloadManager);
      $("copyBtn").addEventListener("click", makeCopyHandler("installText", "copyBtn"));
      var copyMgr = $("copyMgrBtn"); if (copyMgr) copyMgr.addEventListener("click", makeCopyHandler("installMgrText", "copyMgrBtn"));
    });
  }

  // Exposed for the offline resolver self-test (docs/skill-template not required).
  if (typeof module !== "undefined" && module.exports) {
    module.exports = { parseTeamsChannelLink: parseTeamsChannelLink };
  }
})();
