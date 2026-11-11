const API = "https://evrent-api.onrender.com/api",
  GOOGLE_CLIENT_ID =
    "743477235332-qj697802pu1hp49ic181m11hshf91mou.apps.googleusercontent.com", // paste your Google OAuth Client ID here to show "Continue with Google"
  $ = (s) => document.querySelector(s),
  dlg = $("#dlg"),
  EM = { scooter: "🛵", bike: "🏍️", car: "🚗" };
const esc = (s) =>
  String(s ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
const hv = (a, b, c, d) => {
  const r = Math.PI / 180,
    x =
      Math.sin(((c - a) * r) / 2) ** 2 +
      Math.cos(a * r) * Math.cos(c * r) * Math.sin(((d - b) * r) / 2) ** 2;
  return 12742 * Math.asin(Math.sqrt(x));
};
// Fares, road factor and CO2 factors live only on the server (backend/rentals/geo.py)
// and are fetched from /api/config/, so the website can never drift from the real fares.
let CFG = null;
const DAYS_PER_YEAR = 300, // riding days used by the savings calculator
  SAVE_RS_PER_KM = 1.8; // petrol vs EV running cost per km (see note under the calculator)
let token = localStorage.token || null,
  P = null,
  D = null,
  kind = "2w",
  ride = null,
  timer = null,
  vs = { "2w": [], "4w": [] },
  mode = "ride",
  pm,
  dm,
  line,
  carM;
const toast = (m) => {
  const t = $("#toast");
  t.textContent = String(m).replace("Error: ", "");
  t.style.display = "block";
  clearTimeout(toast.t);
  toast.t = setTimeout(() => (t.style.display = "none"), 4500);
};
async function api(p, o = {}) {
  const r = await fetch(API + p, {
    method: o.method || "GET",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: "Token " + token } : {}),
    },
    body: o.body ? JSON.stringify(o.body) : undefined,
  });
  const d = await r.json().catch(() => ({}));
  if (!r.ok) {
    const e = new Error(d.detail || Object.values(d)[0] || "Error " + r.status);
    e.code = d.code;
    throw e;
  }
  return d;
}
async function apiForm(p, fd) {
  const r = await fetch(API + p, {
    method: "POST",
    headers: token ? { Authorization: "Token " + token } : {},
    body: fd,
  });
  const d = await r.json().catch(() => ({}));
  if (!r.ok)
    throw new Error(d.detail || Object.values(d)[0] || "Error " + r.status);
  return d;
}
const show = (h) => {
    $("#dlgBody").innerHTML =
      '<button class="x" onclick="dlg.close()" aria-label="Close">✕</button>' +
      h;
    dlg.showModal();
  },
  panel = (h) => {
    $("#panel").innerHTML = h;
  };
const map = L.map("map").setView([28.57, 77.32], 11);
L.tileLayer("https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png", {
  attribution: "© OpenStreetMap © CARTO",
  maxZoom: 19,
}).addTo(map);
const ic = (e, c) =>
    L.divIcon({
      html: e,
      className: "pin",
      iconSize: [32, 32],
      iconAnchor: [16, 16],
    }),
  vl = L.layerGroup().addTo(map);

async function loadNear() {
  const c = P || { lat: 28.57, lng: 77.3219 };
  try {
    if (!CFG) {
      CFG = await api("/config/");
      calc();
    }
    for (const k of ["2w", "4w"])
      vs[k] = await api(`/vehicles/?kind=${k}&lat=${c.lat}&lng=${c.lng}`);
  } catch (e) {
    toast("Server is waking up (free hosting). Retrying…");
    return setTimeout(loadNear, 6000);
  }
  vl.clearLayers();
  [...vs["2w"], ...vs["4w"]].forEach(
    (v) =>
      v.lat != null &&
      L.marker([v.lat, v.lng], { icon: ic(EM[v.vtype] || "🛵") })
        .addTo(vl)
        .bindPopup(
          `<b>${esc(v.name)}</b><br>₹${Math.round(v.daily_price)}/day<br><button onclick="openRent(${v.id})">Rent</button>`,
        ),
  );
  if (!ride && !(P && D && mode === "ride")) rentList();
}
function rentList() {
  const all = [...vs["2w"], ...vs["4w"]].sort(
    (a, b) => (a.distance_km ?? 99) - (b.distance_km ?? 99),
  );
  panel(
    `<h3 style="margin:0">EVs near you</h3><small>Rent by the day · nearest first · one-time KYC needed to rent</small>` +
      (all
        .map(
          (v) =>
            `<div class="opt" onclick="openRent(${v.id})"><span class="e">${EM[v.vtype] || "🛵"}</span><div><b>${esc(v.name)}</b><small>${esc(v.hub)} · ${v.distance_km ?? "-"} km away</small></div><span class="p">₹${Math.round(v.daily_price)}<small>/day</small></span></div>`,
        )
        .join("") || "<p>No EVs available right now.</p>"),
  );
}
function suggest(inp, box, pick) {
  let t;
  inp.oninput = () => {
    clearTimeout(t);
    const q = inp.value.trim();
    if (q.length < 3) {
      box.hidden = true;
      return;
    }
    t = setTimeout(async () => {
      try {
        const r = await (
          await fetch(
            "https://nominatim.openstreetmap.org/search?format=json&limit=5&countrycodes=in&viewbox=76.9,28.9,77.7,28.2&bounded=1&q=" +
              encodeURIComponent(q),
          )
        ).json();
        box.innerHTML = r.length
          ? r
              .map(
                (x, i) =>
                  `<div data-i="${i}">${esc(x.display_name.split(",").slice(0, 3).join(", "))}</div>`,
              )
              .join("")
          : "<div>No match in Noida / Greater Noida</div>";
        box.hidden = false;
        box.onclick = (e) => {
          const i = e.target.dataset.i;
          if (i == null) return;
          const x = r[i];
          pick({
            lat: +x.lat,
            lng: +x.lon,
            text: x.display_name.split(",").slice(0, 2).join(", "),
          });
          inp.value = x.display_name.split(",").slice(0, 2).join(", ");
          box.hidden = true;
        };
      } catch (e) {}
    }, 500);
  };
}
function setP(p) {
  P = p;
  $("#pu").value = p.text;
  pm ? pm.setLatLng(p) : (pm = L.marker(p, { icon: ic("🟢") }).addTo(map));
  map.setView([p.lat, p.lng], 13);
  route();
  loadNear();
}
function setD(d) {
  D = d;
  $("#dr").value = d.text;
  dm ? dm.setLatLng(d) : (dm = L.marker(d, { icon: ic("🔴") }).addTo(map));
  route();
}
function route() {
  if (!(P && D)) return;
  line && map.removeLayer(line);
  line = L.polyline([P, D], {
    color: "#0b0f0d",
    weight: 4,
    dashArray: "8 8",
  }).addTo(map);
  map.fitBounds(line.getBounds(), { padding: [60, 60] });
}
suggest($("#pu"), $("#sgp"), setP);
suggest($("#dr"), $("#sgd"), setD);
const R = [
  [
    { lat: 28.57, lng: 77.3219, text: "Sector 18 Metro, Noida" },
    { lat: 28.627, lng: 77.365, text: "Sector 62, Noida" },
  ],
  [
    { lat: 28.4744, lng: 77.504, text: "Knowledge Park, Greater Noida" },
    { lat: 28.47, lng: 77.51, text: "Alpha 1, Greater Noida" },
  ],
];
document.querySelectorAll(".chip").forEach(
  (c) =>
    (c.onclick = async () => {
      const r = R[c.dataset.r];
      D = r[1];
      setP(r[0]);
      setD(r[1]);
      await loadNear();
      options();
    }),
);
$("#loc").onclick = () =>
  navigator.geolocation
    ? navigator.geolocation.getCurrentPosition(
        (p) =>
          setP({
            lat: p.coords.latitude,
            lng: p.coords.longitude,
            text: "My location",
          }),
        () => toast("Location blocked. Type your pickup instead."),
      )
    : toast("Location is not supported");
$("#see").onclick = async () => {
  if (!(P && D))
    return toast("Enter a pickup and a drop-off in Noida or Greater Noida");
  await loadNear();
  options();
  $("#live").scrollIntoView();
};

function options() {
  if (!(P && D && CFG)) return;
  const dist = hv(P.lat, P.lng, D.lat, D.lng) * CFG.road_factor,
    N = {
      "2w": ["EV Bike / Scooter", "🛵", "1 rider"],
      "4w": ["EV Cab", "🚗", "up to 4 riders"],
    };
  if (!vs[kind][0]) kind = kind === "2w" ? "4w" : "2w";
  panel(
    `<h3 style="margin:0">Choose your EV</h3><small>${dist.toFixed(1)} km · estimated fares</small>` +
      ["2w", "4w"]
        .map((k) => {
          const n = vs[k][0];
          return n
            ? `<div class="opt ${k === kind ? "on" : ""}" data-k="${k}"><span class="e">${N[k][1]}</span><div><b>${N[k][0]}</b><small>${N[k][2]} · ${Math.max(2, Math.round(((n.distance_km * CFG.road_factor) / 30) * 60))} min away</small></div><span class="p">₹${Math.round(CFG.rates[k].base + CFG.rates[k].per_km * dist)}</span></div>`
            : `<div class="opt off"><span class="e">${N[k][1]}</span><div><b>${N[k][0]}</b><small>No EV nearby right now</small></div></div>`;
        })
        .join("") +
      `<button class="btn" id="bk" style="width:100%">Book ${N[kind][0]}</button><p><small>Pay after the ride · 100% electric ⚡</small></p>`,
  );
  document.querySelectorAll(".opt[data-k]").forEach(
    (o) =>
      (o.onclick = () => {
        kind = o.dataset.k;
        options();
      }),
  );
  $("#bk").onclick = book;
}
async function book() {
  if (!token) return openAuth("Log in to book your EV");
  try {
    ride = await api("/rides/", {
      method: "POST",
      body: {
        kind,
        pickup_lat: P.lat,
        pickup_lng: P.lng,
        drop_lat: D.lat,
        drop_lng: D.lng,
      },
    });
    track();
  } catch (e) {
    e.code === "PHONE_NOT_VERIFIED" ? openVerify(book) : toast(e.message);
  }
}
function track() {
  clearInterval(timer);
  carM && map.removeLayer(carM);
  carM = null;
  const T = {
    arriving: "Your EV is on its way",
    on_trip: "Enjoy your ride",
    completed: "You have arrived 🎉",
    cancelled: "Ride cancelled",
  };
  const tick = async () => {
    try {
      const t = await api(`/rides/${ride.id}/track/`),
        pt = [t.lat, t.lng],
        pin = 1000 + ((ride.id * 7919) % 9000);
      carM
        ? carM.setLatLng(pt)
        : (carM = L.marker(pt, {
            icon: ic(EM[t.vehicle.vtype] || "🚗"),
            zIndexOffset: 900,
          }).addTo(map));
      map.panTo(pt);
      panel(
        `<div style="display:flex;gap:12px;align-items:center"><span style="font-size:40px">${EM[t.vehicle.vtype] || "🚗"}</span><div><b>${esc(t.vehicle.name)}</b><small>${esc(t.vehicle.reg_number)}</small></div><b style="margin-left:auto;background:var(--ink);color:#fff;border-radius:10px;padding:6px 10px">PIN ${pin}</b></div><h3>${T[t.phase] || t.phase}</h3><div class="bar"><i style="width:${t.progress}%"></i></div>` +
          (t.phase === "completed"
            ? `<p>Fare <b>₹${t.fare}</b> · ${t.distance_km} km</p><p>🌱 You saved about <b>${t.co2_saved_kg} kg</b> of CO₂ on this ride.</p><button class="btn" onclick="resetRide()">Book another</button>`
            : `<p>ETA about <b>${Math.max(1, Math.ceil(t.eta_seconds / 60))} min</b> · fare ₹${t.fare}</p>` +
              (t.phase === "arriving"
                ? `<button class="btn o s" onclick="cancelRide()">Cancel ride</button> `
                : "") +
              `<small>Live GPS is simulated in this demo at a faster speed.</small>`),
      );
      if (t.phase === "completed" || t.phase === "cancelled") {
        clearInterval(timer);
        loadNear();
      }
    } catch (e) {
      toast(e.message);
    }
  };
  tick();
  timer = setInterval(tick, 2500);
}
async function cancelRide() {
  try {
    await api(`/rides/${ride.id}/cancel/`, { method: "POST" });
    toast("Ride cancelled");
  } catch (e) {
    toast(e.message);
  }
}
function resetRide() {
  ride = null;
  D = null;
  $("#dr").value = "";
  dm && map.removeLayer(dm);
  dm = null;
  line && map.removeLayer(line);
  carM && map.removeLayer(carM);
  carM = null;
  rentList();
}

async function openRent(id) {
  const v = [...vs["2w"], ...vs["4w"]].find((x) => x.id === id);
  if (!v) return;
  if (!token) return openAuth("Log in to rent");
  let ks;
  try {
    ks = (await api("/kyc/")).status;
  } catch (e) {
    return toast(e.message);
  }
  if (ks !== "approved") return kycDialog(ks, () => openRent(id));
  show(
    `<h3>Rent ${esc(v.name)}</h3><p>${esc(v.hub)}</p><label>Number of days</label><input id="days" type="number" min="1" max="30" value="1"><p id="tot"></p><button class="btn" id="go">Confirm booking</button> <button class="btn o" onclick="dlg.close()">Cancel</button>`,
  );
  const u = () =>
    ($("#tot").textContent =
      `₹${Math.round(v.daily_price * (+$("#days").value || 1))} rent + ₹${Math.round(v.deposit)} refundable deposit`);
  u();
  $("#days").oninput = u;
  $("#go").onclick = async () => {
    try {
      const b = await api("/bookings/", {
        method: "POST",
        body: { vehicle: id, days: +$("#days").value || 1 },
      });
      show(
        `<h3>✅ Booked</h3><p>Booking #${b.id}: ${esc(v.name)} for ${b.days} day(s), ₹${esc(b.amount)}.</p><p>Collect it at ${esc(v.hub)}.</p><button class="btn" onclick="dlg.close()">Done</button>`,
      );
      loadNear();
    } catch (e) {
      toast(e.message);
    }
  };
}
let authMsg = "",
  gInit = false,
  cd = 0,
  kycNext = null;
function openAuth(msg) {
  authMsg = msg || "";
  authStep1();
}
function authStep1() {
  show(
    `<h3>${esc(authMsg || "Log in or sign up")}</h3><p style="color:var(--m);margin-top:0">Enter your mobile number. We will send a code to confirm it.</p><div class="pn"><span>+91</span><input id="ph" placeholder="Mobile number" inputmode="numeric" maxlength="10" autocomplete="tel-national"></div><div class="err" id="err"></div><button class="btn" id="go" style="width:100%">Get OTP</button>` +
      (GOOGLE_CLIENT_ID
        ? `<div class="or">or</div><div id="gbtn" style="display:flex;justify-content:center"></div>`
        : "") +
      `<p style="text-align:center;font-size:12px;color:var(--m);margin-bottom:0">By continuing you agree to the terms of service.</p>`,
  );
  const go = async () => {
    const ph = $("#ph").value.trim();
    if (!/^[6-9]\d{9}$/.test(ph))
      return ($("#err").textContent = "Enter a valid 10-digit mobile number");
    $("#go").disabled = true;
    try {
      authStep2(
        ph,
        await api("/auth/otp/request/", {
          method: "POST",
          body: { phone: ph },
        }),
      );
    } catch (e) {
      $("#err").textContent = e.message;
      $("#go").disabled = false;
    }
  };
  $("#go").onclick = go;
  $("#ph").onkeydown = (e) => {
    if (e.key === "Enter") go();
  };
  $("#ph").focus();
  initGoogle(0);
}
function authStep2(ph, d) {
  show(
    `<h3>Enter the code</h3><p style="color:var(--m);margin-top:0">Sent to +91 ${esc(ph)} <a href="#" id="chg" style="font-weight:700">Change</a></p><input id="otp" class="otp" placeholder="······" inputmode="numeric" maxlength="6" autocomplete="one-time-code"><div class="demo" id="demo" hidden></div><div class="err" id="err"></div><button class="btn" id="vf" style="width:100%">Verify and continue</button><p style="text-align:center;font-size:14px"><a href="#" id="rs" style="font-weight:700"></a></p>`,
  );
  const demo = (x) => {
      if (x && x.demo_otp) {
        $("#demo").hidden = false;
        $("#demo").textContent = "Demo mode: your code is " + x.demo_otp;
      }
    },
    tick = () => {
      clearInterval(cd);
      let n = 30;
      const f = () => {
        const a = $("#rs");
        if (!a) return clearInterval(cd);
        a.textContent = n > 0 ? `Resend code in ${n}s` : "Resend code";
        a.style.pointerEvents = n > 0 ? "none" : "auto";
        a.style.opacity = n > 0 ? 0.5 : 1;
        n--;
      };
      f();
      cd = setInterval(f, 1000);
    };
  demo(d);
  tick();
  $("#chg").onclick = (e) => {
    e.preventDefault();
    clearInterval(cd);
    authStep1();
  };
  $("#rs").onclick = async (e) => {
    e.preventDefault();
    try {
      demo(
        await api("/auth/otp/request/", {
          method: "POST",
          body: { phone: ph },
        }),
      );
      tick();
    } catch (x) {
      $("#err").textContent = x.message;
    }
  };
  const vf = async () => {
    $("#err").textContent = "";
    $("#vf").disabled = true;
    try {
      const r = await api("/auth/otp/login/", {
        method: "POST",
        body: { phone: ph, code: $("#otp").value.trim() },
      });
      token = r.token;
      localStorage.token = token;
      clearInterval(cd);
      auth();
      r.new ? askName() : (dlg.close(), toast("Welcome back!"));
    } catch (x) {
      $("#err").textContent = x.message;
      $("#vf").disabled = false;
    }
  };
  $("#vf").onclick = vf;
  $("#otp").oninput = (e) => {
    e.target.value = e.target.value.replace(/\D/g, "");
    if (e.target.value.length === 6) vf();
  };
  $("#otp").focus();
}
function askName() {
  show(
    `<h3>Welcome to EV Mobility 🎉</h3><p style="color:var(--m);margin-top:0">What should we call you?</p><input id="nm" placeholder="Your name" maxlength="60" autocomplete="name"><button class="btn" id="sv" style="width:100%">Continue</button><p style="text-align:center"><a href="#" id="sk" style="font-weight:700">Skip for now</a></p>`,
  );
  $("#sv").onclick = async () => {
    const n = $("#nm").value.trim();
    if (n)
      try {
        await api("/auth/me/", { method: "POST", body: { name: n } });
      } catch (e) {}
    dlg.close();
    toast("You are all set!");
  };
  $("#sk").onclick = (e) => {
    e.preventDefault();
    dlg.close();
  };
  $("#nm").focus();
}
function kycDialog(st, retry) {
  kycNext = retry;
  if (st === "pending")
    return show(
      `<h3>KYC under review</h3><p>We have your documents. You can rent as soon as our team approves them.</p><button class="btn" onclick="dlg.close()">OK</button>`,
    );
  show(
    `<h3>Verify your identity</h3><p style="color:var(--m)">${st === "rejected" ? "Your last submission was not approved. Please upload clearer photos." : "One-time KYC, needed to rent an EV or become a partner. Your documents are private and only our verification team can see them."}</p><label>Driving licence photo</label><input id="kd" type="file" accept="image/*"><label>Selfie</label><input id="kf" type="file" accept="image/*" capture="user"><div class="err" id="err"></div><button class="btn" id="kgo" style="width:100%">Submit for verification</button>`,
  );
  $("#kgo").onclick = async () => {
    const d = $("#kd").files[0],
      f = $("#kf").files[0];
    if (!d || !f) return ($("#err").textContent = "Please add both photos");
    const fd = new FormData();
    fd.append("doc_type", "licence");
    fd.append("document", d);
    fd.append("selfie", f);
    $("#kgo").disabled = true;
    try {
      await apiForm("/kyc/", fd);
      show(
        `<h3>✅ Submitted</h3><p>Our team will review your documents.</p><button class="btn" onclick="dlg.close();kycNext&&kycNext()">Continue</button>`,
      );
    } catch (e) {
      $("#err").textContent = e.message;
      $("#kgo").disabled = false;
    }
  };
}
async function openVerify(done) {
  let m;
  try {
    m = await api("/auth/me/");
  } catch (e) {
    return toast(e.message);
  }
  if (m.phone_verified) return done && done();
  const has = !!m.phone;
  show(
    `<h3>Verify your mobile number</h3><p style="color:var(--m)">We confirm your number before your first ride so drivers and support can reach you.</p>` +
      (has
        ? `<p><b>+91 ${esc(m.phone)}</b></p>`
        : `<input id="vp" placeholder="Mobile number (10 digits)" inputmode="numeric" maxlength="10">`) +
      `<div id="s1"><button class="btn" id="snd" style="width:100%">Send OTP</button></div><div id="s2" hidden><input id="otp" placeholder="Enter 6-digit code" inputmode="numeric" maxlength="6"><div class="demo" id="demo" hidden></div><button class="btn" id="vf" style="width:100%">Verify and continue</button><p style="text-align:center;font-size:14px"><a href="#" id="rs" style="font-weight:700">Resend code</a></p></div><div class="err" id="err"></div>`,
  );
  const err = (t) => ($("#err").textContent = t),
    send = async () => {
      err("");
      try {
        const d = await api("/auth/otp/send/", {
          method: "POST",
          body: has ? {} : { phone: $("#vp").value.trim() },
        });
        $("#s1").hidden = true;
        $("#s2").hidden = false;
        $("#otp").focus();
        if (d.demo_otp) {
          $("#demo").hidden = false;
          $("#demo").textContent = "Demo mode: your code is " + d.demo_otp;
        }
      } catch (e) {
        err(e.message);
      }
    };
  $("#snd").onclick = send;
  $("#rs").onclick = (e) => {
    e.preventDefault();
    send();
  };
  $("#vf").onclick = async () => {
    err("");
    try {
      await api("/auth/otp/verify/", {
        method: "POST",
        body: { code: $("#otp").value.trim() },
      });
      dlg.close();
      toast("Mobile number verified");
      done && done();
    } catch (e) {
      err(e.message);
    }
  };
}
function initGoogle(n) {
  if (!GOOGLE_CLIENT_ID || !$("#gbtn")) return;
  if (!window.google) {
    return n < 10 ? setTimeout(() => initGoogle(n + 1), 400) : 0;
  }
  if (!gInit) {
    google.accounts.id.initialize({
      client_id: GOOGLE_CLIENT_ID,
      callback: async (r) => {
        try {
          const d = await api("/auth/google/", {
            method: "POST",
            body: { credential: r.credential },
          });
          token = d.token;
          localStorage.token = token;
          dlg.close();
          auth();
          toast("Signed in with Google");
        } catch (e) {
          $("#err") && ($("#err").textContent = e.message);
        }
      },
    });
    gInit = true;
  }
  google.accounts.id.renderButton($("#gbtn"), {
    theme: "outline",
    size: "large",
    width: 330,
    text: "continue_with",
    shape: "pill",
  });
}
const auth = () => {
  $("#bAuth").textContent = token ? "Log out" : "Log in / Sign up";
};
$("#bAuth").onclick = () => {
  if (token) {
    token = null;
    localStorage.clear();
    auth();
    toast("Logged out");
  } else openAuth();
};
$("#bPart").onclick = async () => {
  if (!token) return openAuth("Log in to become a partner");
  let ks;
  try {
    ks = (await api("/kyc/")).status;
  } catch (e) {
    return toast(e.message);
  }
  if (ks === "none" || ks === "rejected")
    return kycDialog(ks, () => $("#bPart").onclick());
  try {
    const p = await api("/partner/me/");
    if (p.status === "none") {
      show(
        `<h3>Become a fleet partner</h3><input id="co" placeholder="Company / owner name"><input id="ci" value="Noida"><input id="fs" type="number" placeholder="Number of vehicles"><label><input type="checkbox" id="ag" style="width:auto;margin-right:6px">I accept the revenue-share agreement</label><p><button class="btn" id="ap">Apply</button></p>`,
      );
      return ($("#ap").onclick = async () => {
        try {
          await api("/partner/me/", {
            method: "POST",
            body: {
              company_name: $("#co").value,
              city: $("#ci").value,
              fleet_size: +$("#fs").value || 0,
              agreement_accepted: $("#ag").checked,
            },
          });
          show(
            "<h3>✅ Application received</h3><p>We will review it shortly.</p>",
          );
        } catch (e) {
          toast(e.message);
        }
      });
    }
    if (p.status !== "approved")
      return show(
        `<h3>${esc(p.company_name)}</h3><p>Status: <b>${esc(p.status)}</b>. Waiting for approval.</p>`,
      );
    const e = await api("/partner/earnings/");
    show(
      `<h3>${esc(p.company_name)}</h3><p>${e.vehicles} vehicles · ${e.completed_bookings} completed · your share ₹${Math.round(e.partner_share)}</p><b>Add a vehicle</b><small>Placed at your pickup point (or central Noida).</small><input id="vn" placeholder="Model name"><select id="vt"><option value="scooter">Scooter</option><option value="bike">Bike</option><option value="car">Car (4W)</option></select><input id="vr" placeholder="Registration number"><input id="vp" type="number" placeholder="Price per day ₹"><input id="vh" placeholder="Hub / area"><p><button class="btn" id="av">Add vehicle</button></p>`,
    );
    $("#av").onclick = async () => {
      try {
        const c = P || { lat: 28.57, lng: 77.3219 };
        await api("/partner/vehicles/", {
          method: "POST",
          body: {
            name: $("#vn").value,
            vtype: $("#vt").value,
            reg_number: $("#vr").value,
            daily_price: $("#vp").value,
            hub: $("#vh").value,
            lat: c.lat,
            lng: c.lng,
          },
        });
        show(
          "<h3>✅ Vehicle added</h3><p>It appears on the map once an admin approves it.</p>",
        );
      } catch (x) {
        toast(x.message);
      }
    };
  } catch (x) {
    toast(x.message);
  }
};
function setMode(m) {
  mode = m;
  $("#mRide").classList.toggle("on", m === "ride");
  $("#mRent").classList.toggle("on", m === "rent");
  $("#rideF").hidden = m !== "ride";
  $("#rentF").hidden = m !== "rent";
  if (m === "rent" && !ride) rentList();
}
$("#mRide").onclick = () => setMode("ride");
$("#mRent").onclick = () => setMode("rent");
$("#nRent").onclick = () => setMode("rent");
$("#browse").onclick = () => {
  rentList();
  $("#live").scrollIntoView();
};
const calc = () => {
  const k = +$("#km").value;
  $("#kmv").textContent = k;
  $("#sv").textContent =
    "₹" +
    Math.round(k * DAYS_PER_YEAR * SAVE_RS_PER_KM).toLocaleString("en-IN");
  $("#co").textContent = CFG
    ? Math.round(k * DAYS_PER_YEAR * CFG.co2_kg_per_km["2w"]) + " kg"
    : "…";
};
$("#km").oninput = calc;
dlg.addEventListener("click", (e) => {
  if (e.target === dlg) dlg.close();
});
calc();
auth();
loadNear();
