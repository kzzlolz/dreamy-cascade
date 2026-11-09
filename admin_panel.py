import json
import os
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import requests
from flask import (
    Blueprint, jsonify, redirect, render_template_string,
    request, session
)

OWNER_IDS = {
    "1209411379178635345",
    "1295215372886347859",
}

DISCORD_AUTHORIZE_URL = "https://discord.com/oauth2/authorize"
DISCORD_TOKEN_URL = "https://discord.com/api/oauth2/token"
DISCORD_USER_URL = "https://discord.com/api/users/@me"

ADMIN_HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Dreamy Cascade · Admin</title>
<style>
:root{color-scheme:dark;--bg:#100910;--panel:#21131f;--panel2:#2b1928;--line:#69475d;--rose:#e6b6ca;--muted:#b99eaf;--gold:#d7bd91;--white:#fff7fb;--danger:#e27b91}
*{box-sizing:border-box}body{margin:0;min-height:100vh;background:radial-gradient(ellipse at top,#48263f 0,#1b101b 45%,#0b070d 100%);color:var(--white);font:15px Inter,system-ui,sans-serif}
button,input,textarea,select{font:inherit}button{cursor:pointer}
.shell{max-width:1120px;margin:auto;padding:32px 20px 60px}.top{display:flex;justify-content:space-between;align-items:center;gap:16px;margin-bottom:26px}
.brand{display:flex;align-items:center;gap:14px}.brand img{width:54px;height:54px;border-radius:14px;border:1px solid var(--gold);object-fit:cover}.brand h1{font:600 27px Georgia,serif;margin:0}.brand p{margin:4px 0 0;color:var(--muted);font-size:12px;letter-spacing:.12em;text-transform:uppercase}
button,.button{border:1px solid var(--line);background:#43243a;color:var(--white);padding:11px 16px;border-radius:10px;text-decoration:none;display:inline-flex;align-items:center;justify-content:center;gap:8px}
button:hover,.button:hover{border-color:var(--gold);background:#593149}.secondary{background:transparent}.danger{background:#51212f;border-color:#8a4058}.layout{display:grid;grid-template-columns:320px minmax(0,1fr);gap:18px}
.panel{background:linear-gradient(145deg,rgba(48,28,44,.96),rgba(24,14,25,.96));border:1px solid var(--line);border-radius:16px;padding:20px;box-shadow:0 16px 50px #0005}
h2{font:600 21px Georgia,serif;margin:0 0 8px}.sub{color:var(--muted);font-size:13px;line-height:1.55;margin:0 0 18px}
label{display:block;color:var(--rose);font-size:12px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;margin:15px 0 7px}
input,textarea,select{width:100%;background:#140d16;color:var(--white);border:1px solid #62445a;border-radius:9px;padding:11px 12px;outline:none}
input:focus,textarea:focus,select:focus{border-color:var(--gold);box-shadow:0 0 0 3px #d7bd9122}textarea{min-height:110px;resize:vertical;line-height:1.5}
.small{font-size:12px;color:var(--muted);line-height:1.5}.actions{display:flex;gap:9px;flex-wrap:wrap;margin-top:18px}.status{min-height:22px;color:var(--gold);font-size:13px;margin-top:12px}.member-row{display:flex;align-items:center;gap:10px;padding:9px;border:1px solid #62445a;border-radius:10px;margin-top:8px;background:#160e18}.member-row img{width:35px;height:35px;border-radius:50%;object-fit:cover}.member-row span{min-width:0;overflow-wrap:anywhere}.profile-list{margin-top:15px;display:grid;gap:7px}.profile-chip{text-align:left;justify-content:flex-start;background:#1a111c}.hidden{display:none!important}.login{max-width:500px;margin:10vh auto;text-align:center}.login img{width:78px;height:78px;border-radius:20px;border:1px solid var(--gold)}.login h1{font:600 32px Georgia,serif}.login .button{margin-top:12px}.preview{border:1px dashed #8b667d;border-radius:12px;padding:14px;margin-top:18px;background:#170f19}.preview-head{display:flex;align-items:center;gap:12px}.preview-head img{width:52px;height:52px;border-radius:50%;object-fit:cover}.preview h3{margin:0;font:600 20px Georgia,serif}.preview p{color:#d6c3cf;white-space:pre-wrap;line-height:1.55}.pill{display:inline-block;background:#482b40;color:#f1d6e3;padding:5px 9px;border-radius:30px;margin:4px 4px 0 0;font-size:12px}
@media(max-width:760px){.layout{grid-template-columns:1fr}.top{align-items:flex-start}.brand h1{font-size:22px}.shell{padding:22px 13px 40px}}
/* Dreamy Cascade admin refresh */
:root{color-scheme:light;--bg:#f7f2f8;--panel:#fffafd;--panel2:#f5edf6;--line:#ead8e8;--rose:#a87598;--muted:#927f91;--gold:#b78bb0;--white:#554457;--danger:#b85e78}
body{background:radial-gradient(ellipse at 12% 0%,#f3e2f0 0,transparent 38%),radial-gradient(ellipse at 90% 10%,#e8e8fa 0,transparent 34%),#f8f5fa;color:#554457}
.shell{max-width:1240px;padding-top:38px}
.brand img{border:1px solid #ead8e8;box-shadow:0 8px 24px #b78bb022}.brand h1{color:#6f5870}.brand p{color:#a18ba0}
button,.button{border:1px solid #dfc5dc;background:linear-gradient(135deg,#bd91b4,#a987b7);color:white;box-shadow:0 6px 16px #b78bb022}
button:hover,.button:hover{border-color:#b78bb0;background:linear-gradient(135deg,#ad7fa5,#9472a8)}
.secondary{background:#fffafd;color:#806680;box-shadow:none}.secondary:hover{background:#f7edf6;color:#765a78}
.danger{background:#fff1f4;color:#a64e69;border-color:#f0cbd6;box-shadow:none}
.layout{grid-template-columns:minmax(260px,310px) minmax(0,1fr);gap:20px}
.panel{background:rgba(255,253,255,.94);border:1px solid #eadde9;border-radius:22px;padding:24px;box-shadow:0 14px 38px #94728d12}
h2{color:#795f7b;font-size:23px}.sub{color:#9b899b}
label{color:#a27698}
input,textarea,select{background:#fff;color:#5f4c61;border:1px solid #e8d8e7;border-radius:12px}
input:focus,textarea:focus,select:focus{border-color:#bd91b4;box-shadow:0 0 0 3px #bd91b422}
.status{color:#8e7191}.member-row{background:#fff;border:1px solid #eee1ed;color:#5e4c61}
.profile-chip{background:#fff;color:#765f79;border-color:#eaddea}.profile-chip:hover{background:#f8eff7}
.preview{background:#fcf7fc;border:1px dashed #d8bdd5}.preview p{color:#806c82}
.pill{background:#f3e7f1;color:#8b6988}.login{padding:42px 28px}.login h1{color:#765e79}
.announcement-panel{margin-top:20px}
.announcement-layout{display:grid;grid-template-columns:minmax(0,1fr) minmax(260px,.8fr);gap:22px}
.announcement-list{display:grid;gap:10px;align-content:start}
.announcement-item{padding:13px 14px;border:1px solid #eee0ed;border-radius:14px;background:#fff}
.announcement-item strong{display:block;color:#795f7b;margin-bottom:5px}
.announcement-item p{margin:0;color:#8d7b8f;white-space:pre-wrap;overflow-wrap:anywhere;font-size:13px;line-height:1.6}
.announcement-item .small{margin-top:7px}
@media(max-width:760px){.announcement-layout{grid-template-columns:1fr}.panel{padding:18px}}


.analytics-stats{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin:14px 0}
.analytics-stat{padding:13px;border:1px solid #eadbea;border-radius:13px;background:#faf5fb}
.analytics-stat strong{display:block;font-size:1.35rem;color:#8f668d}.analytics-stat span{font-size:.72rem;color:#947f91}
.analytics-chart-wrap{padding:14px;border:1px solid #eadbea;border-radius:13px;background:#fffafd}
.analytics-chart{height:150px;margin-top:12px}.analytics-bars{height:115px;display:flex;align-items:end;gap:3px;border-bottom:1px solid #eadbea}
.analytics-bar{flex:1;min-width:2px;border-radius:4px 4px 0 0;background:linear-gradient(180deg,#c7a3d5,#9d7cac);opacity:.85}
.analytics-chart-labels{display:flex;justify-content:space-between;gap:8px;margin-top:7px;font-size:.65rem;color:#98859a}
@media(max-width:600px){.analytics-stats{grid-template-columns:1fr}}
</style>
</head>
<body>
<div id="login" class="shell login hidden">
<img src="https://raw.githubusercontent.com/kzzlolz/dreamy-cascade/main/DC.png" alt="Dreamy Cascade clouds">
<h1>Dreamy Cascade</h1><p class="sub">Private owner dashboard · Member profiles</p>
<a class="button" href="/auth/discord">Continue with Discord</a>
<p class="small" id="login-note">Sign in with an authorised server owner account.</p>
</div>
<div id="dashboard" class="shell hidden">
<header class="top">
<div class="brand"><img src="https://raw.githubusercontent.com/kzzlolz/dreamy-cascade/main/DC.png" alt=""><div><h1>Dreamy Cascade</h1><p>Owner dashboard · Profile studio</p></div></div>
<div><span class="small" id="whoami"></span> <button class="secondary" id="logout">Log out</button></div>
</header>
<div class="layout">
<aside class="panel">
<h2>Members</h2><p class="sub">Choose a member to create or edit their public profile.</p>
<input id="member-search" placeholder="Search members…">
<select id="member-select" size="9" style="margin-top:10px;height:270px"></select>
<div class="small" style="margin-top:12px">Existing profiles</div><div id="profile-list" class="profile-list"></div>
</aside>
<main class="panel">
<h2>Profile editor</h2><p class="sub">Changes are saved to the profile database. Discord names and avatars remain live unless you add an override.</p>
<form id="profile-form">
<label for="display-name">Display name override</label><input id="display-name" maxlength="80" placeholder="Leave blank to use their Discord name">
<label for="tagline">Short introduction</label><input id="tagline" maxlength="140" placeholder="A little line beneath their name">
<label for="bio">About me</label><textarea id="bio" maxlength="5000" placeholder="Write their introduction or longer biography…"></textarea>
<label for="interests">Interests</label><textarea id="interests" maxlength="1200" placeholder="One interest per line"></textarea>
<label for="avatar-url">Profile picture URL (optional)</label><input id="avatar-url" type="url" maxlength="500" placeholder="Leave blank to use their Discord avatar">
<label for="social-links">Social links (one per line: label | https://…)</label><textarea id="social-links" maxlength="1800" placeholder="Instagram | https://instagram.com/…"></textarea>
<div class="actions"><button type="submit" id="save">Save profile</button><button type="button" class="secondary" id="preview-button">Preview</button><button type="button" class="danger" id="delete">Delete profile</button></div>
<div id="status" class="status" role="status"></div>
</form>
<section id="preview" class="preview hidden"><div class="small">LIVE PREVIEW</div><div class="preview-head"><img id="preview-avatar" alt=""><div><h3 id="preview-name"></h3><div class="small" id="preview-tagline"></div></div></div><p id="preview-bio"></p><div id="preview-interests"></div><div id="preview-links" class="small"></div></section>
</main>
</div>
<section class="panel announcement-panel" id="analytics-panel">
<h2>Community analytics</h2>
<p class="sub">A small overview of member growth and recent community activity. Snapshots are collected every 15 minutes while the bot is online.</p>
<div class="analytics-stats">
<div class="analytics-stat"><strong id="analytics-members">—</strong><span>Latest members</span></div>
<div class="analytics-stat"><strong id="analytics-online">—</strong><span>Online now (at snapshot)</span></div>
<div class="analytics-stat"><strong id="analytics-samples">—</strong><span>Snapshots saved</span></div>
</div>
<div class="analytics-chart-wrap"><div class="small">MEMBER COUNT HISTORY</div><div id="analytics-chart" class="analytics-chart"><p class="small">Loading analytics…</p></div></div>
<div class="small" style="margin:16px 0 8px">RECENT COMMUNITY ACTIVITY</div>
<div id="analytics-activity" class="announcement-list"><p class="small">Loading activity…</p></div>
<div id="analytics-status" class="status" role="status"></div>
</section>
<section class="panel announcement-panel">
<h2>Community announcements</h2>
<p class="sub">Publish a message here and it will appear on the public Dreamy Cascade homepage.</p>
<div class="announcement-layout">
<form id="announcement-form">
<label for="announcement-title">Announcement title</label>
<input id="announcement-title" maxlength="100" required placeholder="A little update for everyone…">
<label for="announcement-body">Message</label>
<textarea id="announcement-body" maxlength="2000" required placeholder="Share the news, event details, or reminder…"></textarea>
<div class="actions"><button type="submit">Publish announcement</button></div>
<div id="announcement-status" class="status" role="status"></div>
</form>
<div><div class="small" style="margin-bottom:9px">RECENT ANNOUNCEMENTS</div>
<div id="announcement-list" class="announcement-list"><p class="small">Loading announcements…</p></div></div>
</div>
</section>
</div>
<script>
(function(){
const $=id=>document.getElementById(id);
let csrf="",members=[],profiles={};
function say(message){$("status").textContent=message;}
async function api(url,options){
  options=options||{};options.credentials="same-origin";
  options.headers=Object.assign({"Content-Type":"application/json"},options.headers||{});
  if(options.method&&options.method!=="GET"&&csrf)options.headers["X-CSRF-Token"]=csrf;
  const response=await fetch(url,options);
  const data=await response.json().catch(()=>({error:"Unexpected server response"}));
  if(!response.ok)throw new Error(data.error||"Request failed ("+response.status+")");
  return data;
}
function selected(){return $("member-select").value;}
function memberById(id){return members.find(m=>String(m.id)===String(id));}
function fillForm(profile){
  $("display-name").value=profile?profile.display_name||"":"";
  $("tagline").value=profile?profile.tagline||"":"";
  $("bio").value=profile?profile.bio||"":"";
  $("interests").value=profile?profile.interests||"":"";
  $("avatar-url").value=profile?profile.avatar_url||"":"";
  $("social-links").value=profile?(profile.social_links||[]).map(x=>x.label+" | "+x.url).join("\n"):"";
  $("preview").classList.add("hidden");say(profile?"Profile loaded.":"No saved profile yet.");
}
function renderMembers(){
  const query=$("member-search").value.toLowerCase();
  const select=$("member-select");select.replaceChildren();
  members.filter(m=>(m.display_name||m.username||"").toLowerCase().includes(query)).forEach(m=>{
    const option=document.createElement("option");option.value=m.id;option.textContent=(m.display_name||m.username)+" · "+m.id;select.appendChild(option);
  });
  if(select.options.length){select.selectedIndex=0;loadSelected();}
}
function renderProfileList(){
  const root=$("profile-list");root.replaceChildren();
  Object.keys(profiles).forEach(id=>{
    const m=memberById(id);const b=document.createElement("button");b.type="button";b.className="profile-chip";
    b.textContent=(m?(m.display_name||m.username):"Unknown member")+" · "+id;
    b.addEventListener("click",()=>{$("member-search").value="";renderMembers();$("member-select").value=id;loadSelected();});
    root.appendChild(b);
  });
  if(!root.children.length){const p=document.createElement("div");p.className="small";p.textContent="No profiles saved yet.";root.appendChild(p);}
}
function parseLinks(){
  return $("social-links").value.split("\n").map(line=>line.trim()).filter(Boolean).map(line=>{
    const parts=line.split("|");if(parts.length<2)throw new Error("Use the format: label | https://…");
    return {label:parts[0].trim().slice(0,40),url:parts.slice(1).join("|").trim()};
  });
}
function preview(){
  const m=memberById(selected());if(!m)return say("Choose a member first.");
  $("preview-name").textContent=$("display-name").value.trim()||(m.display_name||m.username);
  $("preview-tagline").textContent=$("tagline").value;
  $("preview-bio").textContent=$("bio").value;
  $("preview-avatar").src=$("avatar-url").value.trim()||m.avatar_url||"";
  const tags=$("preview-interests");tags.replaceChildren();
  $("interests").value.split("\n").map(x=>x.trim()).filter(Boolean).forEach(x=>{const span=document.createElement("span");span.className="pill";span.textContent=x;tags.appendChild(span);});
  const links=$("preview-links");links.textContent=parseLinks().map(x=>x.label+": "+x.url).join(" · ");
  $("preview").classList.remove("hidden");
}
async function loadSelectedProfileData(){
  profiles=await api("/api/admin/profiles");renderProfileList();loadSelected();
}
async function loadSelected(){
  const id=selected();fillForm(profiles[id]||null);
}
async function loadAnalytics(){
 const chart=$("analytics-chart"),activity=$("analytics-activity");
 try{
  const data=await api("/api/admin/analytics");
  const snapshots=data.snapshots||[],events=data.recent_activity||[];
  $("analytics-samples").textContent=snapshots.length;
  if(snapshots.length){
   const latest=snapshots[snapshots.length-1];
   $("analytics-members").textContent=Number(latest.total_members||0).toLocaleString();
   $("analytics-online").textContent=Number(latest.online_members||0).toLocaleString();
   const values=snapshots.map(x=>Number(x.total_members)||0),min=Math.min(...values),max=Math.max(...values),range=Math.max(1,max-min);
   chart.replaceChildren();
   const bars=document.createElement("div");bars.className="analytics-bars";
   snapshots.forEach((item,index)=>{
    const bar=document.createElement("div");bar.className="analytics-bar";
    bar.style.height=(18+((Number(item.total_members)-min)/range)*82)+"%";
    bar.title=new Date(item.recorded_at).toLocaleString()+": "+item.total_members+" members";
    bars.appendChild(bar);
   });
   chart.appendChild(bars);
   const labels=document.createElement("div");labels.className="analytics-chart-labels";
   const first=document.createElement("span");first.textContent=new Date(snapshots[0].recorded_at).toLocaleString();
   const last=document.createElement("span");last.textContent=new Date(latest.recorded_at).toLocaleString();
   labels.append(first,last);chart.appendChild(labels);
  }else{
   $("analytics-members").textContent="—";$("analytics-online").textContent="—";
   chart.textContent="Your first snapshot will appear after the bot's next 15-minute analytics check.";
  }
  activity.replaceChildren();
  if(!events.length){activity.textContent="No community activity recorded yet.";return;}
  events.forEach(item=>{
   const row=document.createElement("article");row.className="announcement-item";
   const title=document.createElement("strong");
   title.textContent=item.event_type==="join"?"Member joined":item.event_type==="leave"?"Member left":item.event_type==="milestone"?"Milestone reached":"Community activity";
   const detail=document.createElement("p");detail.textContent=[item.display_name,item.details].filter(Boolean).join(" — ");
   const date=document.createElement("div");date.className="small";date.textContent=new Date(item.created_at).toLocaleString();
   row.append(title,detail,date);activity.appendChild(row);
  });
 }catch(error){$("analytics-status").textContent="Analytics unavailable: "+error.message;}
}
async function loadAnnouncements(){
 const root=$("announcement-list");
 try{
  const items=await api("/api/admin/announcements");root.replaceChildren();
  if(!items.length){const p=document.createElement("p");p.className="small";p.textContent="No announcements published yet.";root.appendChild(p);return;}
  items.forEach(item=>{
   const card=document.createElement("article");card.className="announcement-item";
   const title=document.createElement("strong");title.textContent=item.title;
   const body=document.createElement("p");body.textContent=item.body;
   const meta=document.createElement("div");meta.className="small";const date=new Date(item.created_at);meta.textContent=Number.isNaN(date.getTime())?"":date.toLocaleString();
   const remove=document.createElement("button");remove.type="button";remove.className="danger";remove.textContent="Delete";remove.style.marginTop="9px";
   remove.addEventListener("click",async()=>{if(!confirm("Delete this announcement from the website?"))return;try{await api("/api/admin/announcements/"+item.id,{method:"DELETE"});await loadAnnouncements();$("announcement-status").textContent="Announcement deleted.";}catch(error){$("announcement-status").textContent=error.message;}});
   card.append(title,body,meta,remove);root.appendChild(card);
  });
 }catch(error){root.textContent=error.message;}
}
$("announcement-form").addEventListener("submit",async event=>{
 event.preventDefault();const title=$("announcement-title").value.trim(),body=$("announcement-body").value.trim();
 try{await api("/api/admin/announcements",{method:"POST",body:JSON.stringify({title,body})});$("announcement-form").reset();$("announcement-status").textContent="Published! It will appear on the homepage shortly.";await loadAnnouncements();}
 catch(error){$("announcement-status").textContent=error.message;}
});
$("member-search").addEventListener("input",renderMembers);
$("member-select").addEventListener("change",loadSelected);
$("preview-button").addEventListener("click",()=>{try{preview();}catch(e){say(e.message);}});
["display-name","tagline","bio","interests","avatar-url","social-links"].forEach(id=>{
 $(id).addEventListener("input",()=>{if(!$("preview").classList.contains("hidden")){try{preview();}catch(e){$("status").textContent=e.message;}}});
});
$("profile-form").addEventListener("submit",async e=>{
  e.preventDefault();const id=selected();if(!id)return say("Choose a member first.");
  try{
    const payload={display_name:$("display-name").value.trim(),tagline:$("tagline").value.trim(),bio:$("bio").value,interests:$("interests").value,avatar_url:$("avatar-url").value.trim(),social_links:parseLinks()};
    const result=await api("/api/admin/profiles/"+encodeURIComponent(id),{method:"PUT",body:JSON.stringify(payload)});
    profiles[id]=result.profile;renderProfileList();say("Profile saved successfully.");preview();
  }catch(error){say(error.message);}
});
$("delete").addEventListener("click",async()=>{
  const id=selected();if(!id||!profiles[id])return say("There is no saved profile to delete.");
  if(!confirm("Delete this member profile?"))return;
  try{await api("/api/admin/profiles/"+encodeURIComponent(id),{method:"DELETE"});delete profiles[id];renderProfileList();fillForm(null);say("Profile deleted.");}catch(error){say(error.message);}
});
$("logout").addEventListener("click",async()=>{
  try{await api("/api/admin/logout",{method:"POST",body:"{}"});}catch(e){}
  location.reload();
});
async function start(){
  try{
    const auth=await api("/api/admin/session");
    if(!auth.authenticated){$("login").classList.remove("hidden");return;}
    csrf=auth.csrf_token;$("whoami").textContent="Signed in as "+auth.username;
    $("dashboard").classList.remove("hidden");
    const guild=await api("/api/guild-data");
    members=(guild.members||[]).filter(m=>!m.bot).sort((a,b)=>(a.display_name||a.username).localeCompare(b.display_name||b.username));
    renderMembers();await loadSelectedProfileData();await loadAnnouncements();await loadAnalytics();
  }catch(error){$("login").classList.remove("hidden");$("login-note").textContent=error.message;}
}
start();
})();
</script>
</body>
</html>"""


def register_admin_routes(app):
    app.secret_key = os.environ.get("FLASK_SESSION_SECRET") or secrets.token_urlsafe(48)
    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SECURE=True,
        SESSION_COOKIE_SAMESITE="Lax",
        PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
    )

    blueprint = Blueprint("dreamy_cascade_admin", __name__)

    def database():
        path = os.environ.get("PROFILE_DB_PATH") or os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "dreamy-cascade-profiles.sqlite3",
        )
        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        connection = sqlite3.connect(path, timeout=15)
        connection.row_factory = sqlite3.Row
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS profiles (
                member_id TEXT PRIMARY KEY,
                display_name TEXT NOT NULL DEFAULT '',
                tagline TEXT NOT NULL DEFAULT '',
                bio TEXT NOT NULL DEFAULT '',
                interests TEXT NOT NULL DEFAULT '',
                avatar_url TEXT NOT NULL DEFAULT '',
                social_links TEXT NOT NULL DEFAULT '[]',
                updated_by TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS announcements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                body TEXT NOT NULL,
                created_by TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS activity_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                member_id TEXT NOT NULL DEFAULT '',
                display_name TEXT NOT NULL DEFAULT '',
                details TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS guild_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                total_members INTEGER NOT NULL,
                online_members INTEGER NOT NULL,
                bot_count INTEGER NOT NULL,
                recorded_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS announced_milestones (
                milestone INTEGER PRIMARY KEY,
                announced_at TEXT NOT NULL
            )
            """
        )
        connection.commit()
        return connection

    def is_admin():
        return str(session.get("admin_id", "")) in OWNER_IDS

    def require_admin():
        if not is_admin():
            return jsonify({"error": "Please sign in with an authorised owner account."}), 401
        return None

    def require_csrf():
        supplied = request.headers.get("X-CSRF-Token", "")
        expected = session.get("csrf_token", "")
        if not supplied or not expected or not secrets.compare_digest(supplied, expected):
            return jsonify({"error": "Your session expired. Refresh the page and sign in again."}), 403
        return None

    def config_ready():
        return all(
            os.environ.get(key)
            for key in ("DISCORD_CLIENT_ID", "DISCORD_CLIENT_SECRET", "FLASK_SESSION_SECRET")
        )

    @blueprint.get("/admin")
    def admin_page():
        return render_template_string(ADMIN_HTML)

    @blueprint.get("/auth/discord")
    def discord_login():
        if not config_ready():
            return (
                "Admin login is not configured yet. Add DISCORD_CLIENT_ID, "
                "DISCORD_CLIENT_SECRET and FLASK_SESSION_SECRET to the server environment.",
                503,
            )
        state = secrets.token_urlsafe(32)
        session["oauth_state"] = state
        redirect_uri = os.environ.get(
            "DISCORD_REDIRECT_URI",
            "https://serverwidget.onrender.com/auth/discord/callback",
        )
        params = {
            "client_id": os.environ["DISCORD_CLIENT_ID"],
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "scope": "identify",
            "state": state,
        }
        return redirect(DISCORD_AUTHORIZE_URL + "?" + urlencode(params))

    @blueprint.get("/auth/discord/callback")
    def discord_callback():
        if request.args.get("error"):
            return "Discord sign-in was cancelled or denied.", 400
        state = request.args.get("state", "")
        if not state or not secrets.compare_digest(state, session.get("oauth_state", "")):
            session.clear()
            return "Invalid sign-in state. Please return to the admin page and try again.", 400

        code = request.args.get("code")
        if not code or not config_ready():
            return "Discord sign-in is not configured correctly.", 400

        redirect_uri = os.environ.get(
            "DISCORD_REDIRECT_URI",
            "https://serverwidget.onrender.com/auth/discord/callback",
        )

        try:
            token_response = requests.post(
                DISCORD_TOKEN_URL,
                data={
                    "client_id": os.environ["DISCORD_CLIENT_ID"],
                    "client_secret": os.environ["DISCORD_CLIENT_SECRET"],
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect_uri,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=15,
            )

            if not token_response.ok:
                print(
                    "[OAuth] Token exchange failed:",
                    token_response.status_code,
                    token_response.text[:1000],
                    flush=True,
                )
                return "Discord token exchange failed. Check server logs.", 502

            access_token = token_response.json()["access_token"]

            user_response = requests.get(
                DISCORD_USER_URL,
                headers={"Authorization": "Bearer " + access_token},
                timeout=15,
            )

            if not user_response.ok:
                print(
                    "[OAuth] User lookup failed:",
                    user_response.status_code,
                    user_response.text[:1000],
                    flush=True,
                )
                return "Discord account lookup failed. Check server logs.", 502

            user = user_response.json()

        except (requests.RequestException, KeyError, ValueError) as error:
            print(
                "[OAuth] Unexpected error:",
                type(error).__name__,
                str(error)[:1000],
                flush=True,
            )
            return "Discord could not verify your account. Please try again.", 502


        user_id = str(user.get("id", ""))
        if user_id not in OWNER_IDS:
            session.clear()
            return "This Discord account is not authorised to access the Dreamy Cascade admin panel.", 403

        session.clear()
        session["admin_id"] = user_id
        session["admin_name"] = user.get("global_name") or user.get("username") or "Owner"
        session["csrf_token"] = secrets.token_urlsafe(32)
        session.permanent = True
        return redirect("/admin")

    @blueprint.get("/api/admin/session")
    def admin_session():
        if not is_admin():
            return jsonify({"authenticated": False})
        return jsonify({
            "authenticated": True,
            "username": session.get("admin_name", "Owner"),
            "csrf_token": session.get("csrf_token", ""),
        })

    @blueprint.post("/api/admin/logout")
    def admin_logout():
        denied = require_admin()
        if denied:
            return denied
        denied = require_csrf()
        if denied:
            return denied
        session.clear()
        return jsonify({"ok": True})


    @blueprint.get("/api/public-profiles")
    def get_public_profiles():
        """Return only fields intentionally published on member profile cards."""
        connection = database()
        try:
            rows = connection.execute(
                "SELECT member_id, display_name, tagline, bio, interests, "
                "avatar_url, social_links FROM profiles ORDER BY display_name COLLATE NOCASE"
            ).fetchall()
            result = {}
            for row in rows:
                item = dict(row)
                try:
                    item["social_links"] = json.loads(item.get("social_links") or "[]")
                except (TypeError, ValueError):
                    item["social_links"] = []
                result[item["member_id"]] = item
            response = jsonify(result)
            response.headers["Cache-Control"] = "no-store"
            return response
        finally:
            connection.close()

    @blueprint.get("/api/announcements")
    def get_public_announcements():
        connection = database()
        try:
            rows = connection.execute(
                "SELECT id, title, body, created_at FROM announcements "
                "ORDER BY id DESC LIMIT 4"
            ).fetchall()
            response = jsonify([dict(row) for row in rows])
            response.headers["Cache-Control"] = "no-store"
            return response
        finally:
            connection.close()

    @blueprint.get("/api/activity")
    def get_public_activity():
        connection = database()
        try:
            rows = connection.execute(
                "SELECT id, event_type, display_name, details, created_at "
                "FROM activity_events ORDER BY id DESC LIMIT 20"
            ).fetchall()
            response = jsonify([dict(row) for row in rows])
            response.headers["Cache-Control"] = "no-store"
            return response
        finally:
            connection.close()

    @blueprint.get("/api/admin/analytics")
    def get_admin_analytics():
        denied = require_admin()
        if denied:
            return denied
        connection = database()
        try:
            snapshots = connection.execute(
                "SELECT total_members, online_members, bot_count, recorded_at "
                "FROM guild_snapshots ORDER BY id DESC LIMIT 96"
            ).fetchall()
            activity = connection.execute(
                "SELECT event_type, display_name, details, created_at "
                "FROM activity_events ORDER BY id DESC LIMIT 12"
            ).fetchall()
            return jsonify({
                "snapshots": [dict(row) for row in reversed(snapshots)],
                "recent_activity": [dict(row) for row in activity],
            })
        finally:
            connection.close()

    @blueprint.get("/api/admin/announcements")
    def get_admin_announcements():
        denied = require_admin()
        if denied:
            return denied
        connection = database()
        try:
            rows = connection.execute(
                "SELECT id, title, body, created_at FROM announcements "
                "ORDER BY id DESC LIMIT 30"
            ).fetchall()
            return jsonify([dict(row) for row in rows])
        finally:
            connection.close()

    @blueprint.post("/api/admin/announcements")
    def create_announcement():
        denied = require_admin()
        if denied:
            return denied
        denied = require_csrf()
        if denied:
            return denied
        payload = request.get_json(silent=True) or {}
        title, body = payload.get("title", ""), payload.get("body", "")
        if not isinstance(title, str) or not isinstance(body, str):
            return jsonify({"error": "Enter a valid title and message."}), 400
        title, body = title.strip(), body.strip()
        if not title or len(title) > 100:
            return jsonify({"error": "Title must be between 1 and 100 characters."}), 400
        if not body or len(body) > 2000:
            return jsonify({"error": "Message must be between 1 and 2000 characters."}), 400
        created_at = datetime.now(timezone.utc).isoformat()
        connection = database()
        try:
            cursor = connection.execute(
                "INSERT INTO announcements (title, body, created_by, created_at) "
                "VALUES (?, ?, ?, ?)",
                (title, body, session["admin_id"], created_at),
            )
            connection.commit()
            return jsonify({"ok": True, "announcement": {
                "id": cursor.lastrowid, "title": title,
                "body": body, "created_at": created_at
            }})
        finally:
            connection.close()

    @blueprint.delete("/api/admin/announcements/<int:announcement_id>")
    def delete_announcement(announcement_id):
        denied = require_admin()
        if denied:
            return denied
        denied = require_csrf()
        if denied:
            return denied
        connection = database()
        try:
            connection.execute("DELETE FROM announcements WHERE id = ?", (announcement_id,))
            connection.commit()
            return jsonify({"ok": True})
        finally:
            connection.close()

    @blueprint.get("/api/admin/profiles")
    def get_profiles():
        denied = require_admin()
        if denied:
            return denied
        connection = database()
        try:
            rows = connection.execute(
                "SELECT * FROM profiles ORDER BY updated_at DESC"
            ).fetchall()
            result = {}
            for row in rows:
                item = dict(row)
                try:
                    item["social_links"] = json.loads(item["social_links"])
                except (TypeError, ValueError):
                    item["social_links"] = []
                result[item["member_id"]] = item
            return jsonify(result)
        finally:
            connection.close()

    @blueprint.put("/api/admin/profiles/<member_id>")
    def save_profile(member_id):
        denied = require_admin()
        if denied:
            return denied
        denied = require_csrf()
        if denied:
            return denied
        if not member_id.isdigit() or len(member_id) > 25:
            return jsonify({"error": "Invalid Discord member ID."}), 400

        payload = request.get_json(silent=True) or {}
        fields = {
            "display_name": 80,
            "tagline": 140,
            "bio": 5000,
            "interests": 1200,
            "avatar_url": 500,
        }
        clean = {}
        for field, limit in fields.items():
            value = payload.get(field, "")
            if not isinstance(value, str):
                return jsonify({"error": "Invalid value for " + field + "."}), 400
            value = value.strip() if field != "bio" else value.strip()
            if len(value) > limit:
                return jsonify({"error": field + " is too long."}), 400
            clean[field] = value

        avatar_url = clean["avatar_url"]
        if avatar_url and not avatar_url.startswith(("https://", "http://")):
            return jsonify({"error": "Profile picture URL must start with https:// or http://."}), 400

        links = payload.get("social_links", [])
        if not isinstance(links, list) or len(links) > 8:
            return jsonify({"error": "Add no more than 8 social links."}), 400
        clean_links = []
        for link in links:
            if not isinstance(link, dict):
                return jsonify({"error": "Invalid social link."}), 400
            label = str(link.get("label", "")).strip()[:40]
            url = str(link.get("url", "")).strip()
            if not label or len(url) > 500 or not url.startswith(("https://", "http://")):
                return jsonify({"error": "Each social link needs a label and a valid http(s) URL."}), 400
            clean_links.append({"label": label, "url": url})

        updated_at = datetime.now(timezone.utc).isoformat()
        connection = database()
        try:
            connection.execute(
                """
                INSERT INTO profiles (
                    member_id, display_name, tagline, bio, interests,
                    avatar_url, social_links, updated_by, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(member_id) DO UPDATE SET
                    display_name=excluded.display_name,
                    tagline=excluded.tagline,
                    bio=excluded.bio,
                    interests=excluded.interests,
                    avatar_url=excluded.avatar_url,
                    social_links=excluded.social_links,
                    updated_by=excluded.updated_by,
                    updated_at=excluded.updated_at
                """,
                (
                    member_id, clean["display_name"], clean["tagline"],
                    clean["bio"], clean["interests"], clean["avatar_url"],
                    json.dumps(clean_links), session["admin_id"], updated_at,
                ),
            )
            connection.commit()
        finally:
            connection.close()

        clean.update({
            "member_id": member_id,
            "social_links": clean_links,
            "updated_by": session["admin_id"],
            "updated_at": updated_at,
        })
        return jsonify({"ok": True, "profile": clean})

    @blueprint.delete("/api/admin/profiles/<member_id>")
    def delete_profile(member_id):
        denied = require_admin()
        if denied:
            return denied
        denied = require_csrf()
        if denied:
            return denied
        if not member_id.isdigit() or len(member_id) > 25:
            return jsonify({"error": "Invalid Discord member ID."}), 400
        connection = database()
        try:
            connection.execute("DELETE FROM profiles WHERE member_id = ?", (member_id,))
            connection.commit()
        finally:
            connection.close()
        return jsonify({"ok": True})

    app.register_blueprint(blueprint)
