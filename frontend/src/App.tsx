import { useMemo, useState } from "react";
import {
  ArrowDownRight, ArrowRight, ArrowUpRight, Bell, Bike, CalendarDays,
  Check, ChevronDown, ChevronRight, CircleHelp, Clock3, Compass, CreditCard,
  Gauge, Leaf, LocateFixed, MapPin, Menu, Search, ShieldCheck, SlidersHorizontal,
  Sparkles, Wallet, X, Zap
} from "lucide-react";

type Service = "ride" | "rent" | "charge";
const stations = [
  { id: 1, name: "ChargeZone – Sector 18", area: "Sector 18, Noida", distance: "1.2 km", type: "Public charging point" },
  { id: 2, name: "Tata Power EZ Charge", area: "Sector 16, Noida", distance: "2.8 km", type: "Public charging point" },
  { id: 3, name: "Statiq Charging Hub", area: "Sector 62, Noida", distance: "4.1 km", type: "Public charging point" },
];
const vehicles = [
  { id: 1, name: "Ather 450X", kind: "Electric scooter", range: "105 km range", rate: "₹299", tag: "Popular", image: "https://images.unsplash.com/photo-1558981806-ec527fa84c39?w=800&q=85" },
  { id: 2, name: "TVS iQube", kind: "Electric scooter", range: "100 km range", rate: "₹249", tag: "Best value", image: "https://images.unsplash.com/photo-1591637333184-19aa84b3e01f?w=800&q=85" },
  { id: 3, name: "Ola S1 Pro", kind: "Electric scooter", range: "120 km range", rate: "₹329", tag: "Long range", image: "https://images.unsplash.com/photo-1558981806-ec527fa84c39?w=800&q=85" },
];

function Logo() {
  return <div className="brand"><span className="brand-mark"><Zap size={19} fill="currentColor" /></span><span>ev<span className="brand-light">mobility</span></span></div>;
}
function App() {
  const [service, setService] = useState<Service>("ride");
  const [location, setLocation] = useState("Sector 18, Noida");
  const [destination, setDestination] = useState("");
  const [query, setQuery] = useState("");
  const [activeNav, setActiveNav] = useState("Overview");
  const [noticeOpen, setNoticeOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const [selectedVehicle, setSelectedVehicle] = useState<number | null>(null);
  const [rentalDays, setRentalDays] = useState(1);
  const [toast, setToast] = useState("");
  const filteredStations = useMemo(() => stations.filter(s => (s.name + s.area).toLowerCase().includes(query.toLowerCase())), [query]);

  const notify = (message: string) => {
    setToast(message);
    window.setTimeout(() => setToast(""), 2800);
  };
  const chooseService = (s: Service) => {
    setService(s);
    setActiveNav(s === "ride" ? "Ride & Earn" : s === "rent" ? "Rent an EV" : "Charging stations");
    setSelectedVehicle(null);
  };
  const handleLocation = () => {
    if (!navigator.geolocation) return notify("Location is not supported by this browser.");
    navigator.geolocation.getCurrentPosition(
      p => { setLocation(`${p.coords.latitude.toFixed(4)}, ${p.coords.longitude.toFixed(4)}`); notify("Your current location is set."); },
      () => notify("Location permission was not granted. Please enter your area manually."),
      { enableHighAccuracy: true, timeout: 10000 }
    );
  };

  return <div className="app-shell">
    <aside className="sidebar">
      <div className="sidebar-top"><Logo /><button className="icon-btn mobile-menu" aria-label="Open menu"><Menu size={19}/></button></div>
      <div className="workspace-label">WORKSPACE</div>
      <nav className="side-nav" aria-label="Main navigation">
        {[{label:"Overview",icon:Gauge},{label:"Ride & Earn",icon:Bike},{label:"Rent an EV",icon:Zap},{label:"Charging stations",icon:MapPin}].map(item => {
          const Icon=item.icon; return <button key={item.label} className={activeNav===item.label?"nav-item active":"nav-item"} onClick={()=>{setActiveNav(item.label); if(item.label==="Ride & Earn")chooseService("ride");if(item.label==="Rent an EV")chooseService("rent");if(item.label==="Charging stations")chooseService("charge");}}>
            <Icon size={18}/><span>{item.label}</span>{item.label==="Charging stations"&&<span className="nav-new">NEW</span>}
          </button>;
        })}
      </nav>
      <div className="workspace-label nav-spaced">YOUR ACCOUNT</div>
      <nav className="side-nav">
        <button className="nav-item" onClick={()=>notify("Your activity will appear here once you start booking.")}><CalendarDays size={18}/><span>My activity</span></button>
        <button className="nav-item" onClick={()=>notify("Wallet and transactions will be available in the next integration phase.")}><Wallet size={18}/><span>Wallet & payments</span></button>
        <button className="nav-item" onClick={()=>notify("Help centre is coming soon.")}><CircleHelp size={18}/><span>Help & support</span></button>
      </nav>
      <div className="sidebar-bottom">
        <div className="green-promo"><div className="promo-icon"><Leaf size={18}/></div><strong>Make every move count.</strong><p>Choose electric. Make a lighter footprint.</p><span className="promo-dots">● ● ●</span></div>
        <button className="profile-mini" onClick={()=>setProfileOpen(!profileOpen)}><div className="avatar">RC</div><span className="profile-copy"><strong>Welcome, Ritik</strong><small>Personal account</small></span><ChevronDown size={16}/></button>
        {profileOpen&&<div className="profile-pop"><strong>Personal account</strong><small>Profile settings and preferences</small><button onClick={()=>notify("Profile settings will be connected soon.")}>Manage profile <ArrowRight size={14}/></button></div>}
      </div>
    </aside>

    <main className="main-area">
      <header className="topbar">
        <div className="breadcrumb"><span>Workspace</span><ChevronRight size={14}/><strong>{activeNav}</strong></div>
        <div className="top-actions">
          <div className="location-pill"><MapPin size={15}/><span>{location}</span><button onClick={handleLocation} aria-label="Use current location"><LocateFixed size={15}/></button></div>
          <div className="notice-wrap"><button className="icon-btn notification-btn" onClick={()=>setNoticeOpen(!noticeOpen)} aria-label="Notifications"><Bell size={19}/><i/></button>
            {noticeOpen&&<div className="notice-pop"><strong>You're all caught up</strong><p>New ride updates and booking notifications will appear here.</p></div>}
          </div>
          <div className="avatar top-avatar">RC</div>
        </div>
      </header>

      <div className="content">
        <section className="welcome-row">
          <div><div className="eyebrow"><Sparkles size={14}/> YOUR ELECTRIC JOURNEY STARTS HERE</div><h1>Good morning, Ritik <span className="wave">✳</span></h1><p className="welcome-sub">Where would you like to go today?</p></div>
          <div className="date-chip"><CalendarDays size={16}/> Thursday, 12 November</div>
        </section>

        <section className="hero-card">
          <div className="hero-copy">
            <div className="hero-kicker"><span className="live-dot"/> THE SMARTER WAY TO MOVE</div>
            <h2>Move better.<br/><span>Move electric.</span></h2>
            <p>One platform for your everyday rides, flexible EV rentals and nearby charging stations.</p>
            <button className="hero-cta" onClick={()=>chooseService("ride")}>Explore mobility <ArrowRight size={17}/></button>
            <div className="hero-proof"><span><ShieldCheck size={15}/> Verified partners</span><span><Zap size={15}/> Electric first</span></div>
          </div>
          <div className="hero-visual" role="img" aria-label="Electric scooter on a clean city street">
            <div className="visual-orbit orbit-one"/><div className="visual-orbit orbit-two"/>
            <div className="visual-label label-top"><span className="label-icon"><Zap size={14}/></span><span><strong>100% electric</strong><small>A cleaner way forward</small></span></div>
            <div className="visual-label label-bottom"><span className="online-dot"/><span><strong>Ready when you are</strong><small>Explore your options</small></span></div>
            <img src="https://images.unsplash.com/photo-1558981806-ec527fa84c39?w=1000&q=90" alt="Modern electric two-wheeler" />
          </div>
          <div className="hero-index">01 <span/> 03</div>
        </section>

        <section className="section-block service-section">
          <div className="section-heading"><div><div className="eyebrow muted">YOUR MOBILITY, YOUR CHOICE</div><h2>What would you like to do?</h2><p>Three simple ways to make the most of electric mobility.</p></div><span className="section-count">01 — 03</span></div>
          <div className="service-grid">
            <button className={service==="ride"?"service-card service-ride selected":"service-card service-ride"} onClick={()=>chooseService("ride")}>
              <div className="service-top"><span className="service-icon"><Bike size={21}/></span><span className="service-arrow"><ArrowUpRight size={18}/></span></div>
              <div className="service-art ride-art"><div className="art-circle"/><img src="https://images.unsplash.com/photo-1558981806-ec527fa84c39?w=700&q=85" alt="Electric scooter for rides"/></div>
              <div className="service-text"><span className="service-label">FOR EVERYDAY TRAVEL</span><h3>Ride & Earn</h3><p>Book an electric ride or register your own EV and earn on the move.</p><span className="text-link">Explore rides <ArrowRight size={15}/></span></div>
            </button>
            <button className={service==="rent"?"service-card service-rent selected":"service-card service-rent"} onClick={()=>chooseService("rent")}>
              <div className="service-top"><span className="service-icon"><Zap size={21}/></span><span className="service-arrow"><ArrowUpRight size={18}/></span></div>
              <div className="service-art rent-art"><div className="art-circle"/><img src="https://images.unsplash.com/photo-1591637333184-19aa84b3e01f?w=700&q=85" alt="Electric scooter available for rent"/></div>
              <div className="service-text"><span className="service-label">FLEXIBLE EV ACCESS</span><h3>Rent an EV</h3><p>Choose a partner-listed electric vehicle and use it to earn.</p><span className="text-link">Browse vehicles <ArrowRight size={15}/></span></div>
            </button>
            <button className={service==="charge"?"service-card service-charge selected":"service-card service-charge"} onClick={()=>chooseService("charge")}>
              <div className="service-top"><span className="service-icon"><MapPin size={21}/></span><span className="service-arrow"><ArrowUpRight size={18}/></span></div>
              <div className="service-art charge-art"><div className="art-circle"/><div className="mini-map"><span className="map-road road-a"/><span className="map-road road-b"/><i className="map-pin pin-a"/><i className="map-pin pin-b"/><i className="map-pin pin-c"/><span className="map-route"/></div></div>
              <div className="service-text"><span className="service-label">STAY CHARGED</span><h3>Find charging</h3><p>Discover nearby EV charging stations and navigate to one.</p><span className="text-link">Find a station <ArrowRight size={15}/></span></div>
            </button>
          </div>
        </section>

        {service==="ride"&&<section className="work-panel">
          <div className="panel-heading"><div><span className="service-label">RIDE & EARN</span><h2>Plan your next ride</h2><p>Enter your pickup and destination to get started.</p></div><span className="panel-badge"><Bike size={15}/> Electric two-wheelers</span></div>
          <div className="ride-form">
            <label><span className="field-dot pickup-dot"/> <span className="field-copy">PICKUP LOCATION</span><input value={location} onChange={e=>setLocation(e.target.value)} placeholder="Enter pickup location"/></label>
            <div className="field-connector"/>
            <label><span className="field-dot drop-dot"/> <span className="field-copy">YOUR DESTINATION</span><input value={destination} onChange={e=>setDestination(e.target.value)} placeholder="Where do you want to go?"/></label>
            <button className="primary-btn" onClick={()=>destination.trim()?notify("Ride search UI is ready. Driver matching will be connected to the backend in the next phase."):notify("Please enter your destination first.")}>Find a ride <ArrowRight size={17}/></button>
          </div>
          <div className="panel-foot"><span><ShieldCheck size={15}/> Verified driver onboarding</span><span><Clock3 size={15}/> Quick booking experience</span></div>
        </section>}

        {service==="rent"&&<section className="work-panel">
          <div className="panel-heading"><div><span className="service-label">RENT AN EV & EARN</span><h2>Find your ride to opportunity.</h2><p>Explore electric two-wheelers listed by our fleet partners.</p></div><span className="panel-badge"><ShieldCheck size={15}/> Partner supplied</span></div>
          {selectedVehicle===null?<div className="vehicle-grid">{vehicles.map(v=><article className="vehicle-card" key={v.id}><div className="vehicle-photo"><img src={v.image} alt={v.name}/><span>{v.tag}</span></div><div className="vehicle-info"><small>{v.kind}</small><h3>{v.name}</h3><div className="vehicle-meta"><span><Zap size={14}/>{v.range}</span><strong>{v.rate}<small>/ day</small></strong></div><button className="outline-btn" onClick={()=>setSelectedVehicle(v.id)}>View details <ArrowRight size={15}/></button></div></article>)}</div>:<div className="rental-detail"><button className="back-link" onClick={()=>setSelectedVehicle(null)}>← Back to vehicles</button><h3>{vehicles.find(v=>v.id===selectedVehicle)?.name}</h3><p>Choose how long you need the vehicle. This is a frontend preview; partner availability and booking will be connected later.</p><label className="days-label">Rental duration <select value={rentalDays} onChange={e=>setRentalDays(Number(e.target.value))}>{[1,2,3,7,14,30].map(d=><option value={d} key={d}>{d} {d===1?"day":"days"}</option>)}</select></label><div className="rental-total"><span>Estimated rental total</span><strong>{(Number(vehicles.find(v=>v.id===selectedVehicle)?.rate.replace("₹",""))*rentalDays).toLocaleString("en-IN",{style:"currency",currency:"INR",maximumFractionDigits:0})}</strong></div><button className="primary-btn" onClick={()=>notify("Rental selection saved in this demo. Real booking will be enabled after API integration.")}>Continue to booking <ArrowRight size={17}/></button></div>}
          <div className="panel-foot"><span><ShieldCheck size={15}/> Verified partner listings</span><span><CalendarDays size={15}/> Flexible rental durations</span></div>
        </section>}

        {service==="charge"&&<section className="work-panel">
          <div className="panel-heading"><div><span className="service-label">CHARGING STATION FINDER</span><h2>Find power around you.</h2><p>Discover nearby charging locations and navigate to your choice.</p></div><span className="panel-badge"><LocateFixed size={15}/> Location based</span></div>
          <div className="station-search"><Search size={18}/><input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Search station or area"/><button onClick={handleLocation}><LocateFixed size={16}/> Use my location</button></div>
          <div className="station-list">{filteredStations.map(s=><div className="station-row" key={s.id}><span className="station-icon"><Zap size={19}/></span><div className="station-copy"><strong>{s.name}</strong><small>{s.area} · {s.type}</small></div><span className="station-distance">{s.distance}</span><button className="icon-btn" aria-label={"Navigate to "+s.name} onClick={()=>notify("Navigation preview selected. Live GPS directions will be connected in the maps integration phase.")}><ArrowUpRight size={18}/></button></div>)}{filteredStations.length===0&&<p className="empty-state">No demo stations match that search. Try another area.</p>}</div>
          <div className="panel-foot"><span><MapPin size={15}/> Station discovery only</span><span><Compass size={15}/> Navigation, no charging booking</span></div>
        </section>}

        <section className="bottom-grid">
          <div className="impact-card"><div className="impact-icon"><Leaf size={19}/></div><div className="eyebrow muted">A SMALLER FOOTPRINT</div><h3>Every electric trip<br/>moves us forward.</h3><p>Make a more thoughtful choice for your everyday commute.</p><button onClick={()=>notify("EV impact information will be expanded in a future release.")}>Discover the EV difference <ArrowRight size={15}/></button><div className="impact-decoration"><Leaf size={90}/></div></div>
          <div className="quick-card"><div className="quick-head"><div><div className="eyebrow muted">GETTING STARTED</div><h3>New to EV Mobility?</h3></div><span className="quick-spark"><Sparkles size={19}/></span></div><div className="quick-step"><span>01</span><div><strong>Choose your service</strong><small>Ride, rent or find a charging station.</small></div><ChevronRight size={17}/></div><div className="quick-step"><span>02</span><div><strong>Complete your details</strong><small>Set up your profile and preferences.</small></div><ChevronRight size={17}/></div><div className="quick-step"><span>03</span><div><strong>You're ready to go</strong><small>Enjoy a simpler electric journey.</small></div><ChevronRight size={17}/></div></div>
        </section>
        <footer className="footer"><Logo/><span>Move better. Move electric.</span><span>© 2026 EV Mobility</span></footer>
      </div>
    </main>
    {toast&&<div className="toast"><Check size={16}/>{toast}</div>}
  </div>;
}
export default App;
