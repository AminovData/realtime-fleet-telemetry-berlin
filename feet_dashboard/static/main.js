function get_query_param(name) {
  const params = new URLSearchParams(window.location.search);
  return params.get(name);
}

function parse_failures(sens_fails) {
  if (Array.isArray(sens_fails)) return sens_fails;
  
  if (typeof sens_fails === "string") {
    const s = sens_fails.trim();
    if (s === "[]" || s === "") return [];
    
    try {
      const parsed = JSON.parse(s);
      if (Array.isArray(parsed)) return parsed;
    } catch (e) {
      return s.replace(/^\[|\]$/g, "")
              .replace(/\\/g, "")
              .replace(/"/g, "")
              .split(",")
              .map(x => x.trim())
              .filter(x => x.length > 0);
    }
  }
  
  return [];
}

function get_marker_col(fails) {
  if (fails.length > 0) {
    return "red";
  } else {
    return "green";
  }
}

function set_txt(elem_id, val) {
  const el = document.getElementById(elem_id);
  if(el) el.textContent = val;
}

function fmt(val, dec = 2) {
  if (val != null) {
    return val.toFixed(dec);
  } else {
    return "N/A";
  }
}

const map_el = document.getElementById("map");
if (map_el) {
  const map = L.map('map').setView([52.5200, 13.4050], 11);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 18,
    attribution: '&copy; OpenStreetMap contributors'
  }).addTo(map);

  const socket = io.connect("http://localhost:8081");
  
  const markers = {};
  const anim_state = {};

  function smooth_move(marker, start, end, dur = 900) {
    const t0 = performance.now();
    function anim(t) {
      const prog = Math.min((t - t0) / dur, 1);
      const lat = start.lat + (end.lat - start.lat) * prog;
      const lng = start.lng + (end.lng - start.lng) * prog;
      marker.setLatLng([lat, lng]);
      if (prog < 1) requestAnimationFrame(anim);
    }
    requestAnimationFrame(anim);
  }

  function make_icon(col) {
    return L.divIcon({
      className: "custom-marker",
      html: `<div style="background-color:${col};width:14px;height:14px;border-radius:50%;border:2px solid white;"></div>`,
      iconSize: [14, 14],
      iconAnchor: [7, 7]
    });
  }

  if (window.last_known && window.last_known.lat && window.last_known.lon) {
    const v = window.last_known;
    const lat = parseFloat(v.lat || v.latitude);
    const lon = parseFloat(v.lon || v.longitude);
    const fails = parse_failures(v.sensor_failures);
    const col = get_marker_col(fails);

    const m = L.marker([lat, lon], { icon: make_icon(col) }).addTo(map);
    
    let label_class = "car-label car-ok";
    if (fails.length > 0) {
      label_class = "car-label car-failed";
    }
    
    m.bindTooltip(v.vehicle_id, { 
      permanent: true, 
      direction: "top", 
      offset: [0, -10], 
      className: label_class
    }).openTooltip();
    markers[v.vehicle_id] = m;
    anim_state[v.vehicle_id] = { target: L.latLng(lat, lon), animating: false };
  }

  const car_id = get_query_param("vehicle_id");

  socket.on("vehicle_batch_update", (vehicles) => {
    if (!Array.isArray(vehicles)) return;
    
    let cars = vehicles;
    if (car_id) {
      cars = vehicles.filter(v => (v.vehicle_id || v.id) === car_id);
    }

    for (let i = 0; i < cars.length; i++) {
      const v = cars[i];
      const id = v.vehicle_id || v.id || "unknown";
      const lat = parseFloat(v.latitude || v.lat);
      const lon = parseFloat(v.longitude || v.lon);
      
      if (isNaN(lat) || isNaN(lon)) {
        continue;
      }

      const spd = v.speed || "N/A";
      let ts = new Date().toLocaleTimeString();
      if (v.timestamp) {
        ts = new Date(v.timestamp).toLocaleTimeString();
      }
      
      const fails = parse_failures(v.sensor_failures);
      const col = get_marker_col(fails);

      if (!markers[id]) {
        const m = L.marker([lat, lon], { icon: make_icon(col) }).addTo(map);
        
        let tooltip_class = "car-label car-ok";
        if (fails.length > 0) {
          tooltip_class = "car-label car-failed";
        }
        
        m.bindTooltip(id, { 
          permanent: true, 
          direction: "top", 
          offset: [0, -10], 
          className: tooltip_class
        }).openTooltip();
        
        let fail_text = "None";
        if (fails.length > 0) {
          fail_text = fails.join(", ");
        }
        
        m.bindPopup(
          `<div class="vehicle-popup">
            <b>ID:</b> ${id}<br>
            <b>Speed:</b> ${spd}<br>
            <b>Time:</b> ${ts}<br>
            <b>Failures:</b> ${fail_text}
          </div>`
        );
        markers[id] = m;
        anim_state[id] = { target: L.latLng(lat, lon), animating: false };
      } else {
        const m = markers[id];
        const prv = m.getLatLng();
        const new_pos = L.latLng(lat, lon);
        
        m.setIcon(make_icon(col));
        const tooltip = m.getTooltip();
        if (tooltip) {
          let tooltip_class = "car-label car-ok";
          if (fails.length > 0) {
            tooltip_class = "car-label car-failed";
          }
          tooltip.setContent(id);
          tooltip.options.className = tooltip_class;
        }
        
        const dist = prv.distanceTo(new_pos);
        if (dist >= 3 && !anim_state[id].animating)  {
          anim_state[id].animating = true;
          smooth_move(m, prv, new_pos, 1000);
          setTimeout(() => (anim_state[id].animating = false), 1000);
        }
        
        const popup = m.getPopup();
        if (popup) {
          let fail_text = "None";
          if (fails.length > 0) {
            fail_text = fails.join(", ");
          }
          
          popup.setContent(
            `<div class="vehicle-popup">
              <b>ID:</b> ${id}<br>
              <b>Speed:</b> ${spd}<br>
              <b>Time:</b> ${ts}<br>
              <b>Failures:</b> ${fail_text}
            </div>`
          );
        }
      }

      if (car_id) {
        set_txt("vehicle-id", id);
        set_txt("speed", spd);
        set_txt("timestamp", ts);
        set_txt("acceleration", fmt(v.acceleration));
        
        let move_status = "Stopped";
        if (v.speed > 0) {
          move_status = "Moving";
        }
        set_txt("motion-status", move_status);
        
        let brake = "Released";
        if (v.brake_status === 1) {
          brake = "Engaged";
        }
        set_txt("brake-status", brake);
        
        if (v.engine_temp != null) {
          set_txt("engine-temp", v.engine_temp.toFixed(2)+"°C");
        } else {
          set_txt("engine-temp", "N/A");
        }
        
        set_txt("coolant-temp", fmt(v.coolant_temp)+"°C");
        
        let oil_val = "N/A";
        if (v.oil_pressure != null) {
          oil_val = v.oil_pressure.toFixed(2)+" PSI";
        }
        set_txt("oil-pressure", oil_val);
        
        if (v.battery_level != null) {
          set_txt("battery-level", v.battery_level.toFixed(0));
        } else {
          set_txt("battery-level", "N/A");
        }

        let tires = {fl: null, fr: null, rl: null, rr: null};
        if (v.tire_pressure) {
          try { 
            tires = JSON.parse(v.tire_pressure); 
          } catch (e) {
            console.log("tire pressure parse error");
          }
        }
        
        if (tires.fl != null) {
          set_txt("tire-fl", tires.fl.toFixed(2));
        } else {
          set_txt("tire-fl", "N/A");
        }
        
        if (tires.fr != null) {
          set_txt("tire-fr", tires.fr.toFixed(2));
        } else {
          set_txt("tire-fr", "N/A");
        }
        
        set_txt("tire-rl", fmt(tires.rl));
        set_txt("tire-rr", fmt(tires.rr));

        set_txt("failure-count", fails.length);
        const sf_el = document.getElementById("sensor-failures");
        if (sf_el) {
          if (fails.length > 0) {
            const items = [];
            for (let j = 0; j < fails.length; j++) {
              items.push(`<div class="metric-list-item">${fails[j]}</div>`);
            }
            sf_el.innerHTML = items.join("");
          } else {
            sf_el.innerHTML = "<div class='metric-list-item'>None</div>";
          }
        }
      }
    }

    if (!car_id) {
      const uniq = {};
      for (let i = 0; i < vehicles.length; i++) {
        const v = vehicles[i];
        const key = v.vehicle_id || v.id || "unknown";
        uniq[key] = v;
      }
      const all_cars = Object.values(uniq);
      
      const fail_cars = [];
      for (let i = 0; i < all_cars.length; i++) {
        const v = all_cars[i];
        const f = parse_failures(v.sensor_failures);
        if (f.length > 0) {
          fail_cars.push(v.vehicle_id || v.id || "unknown");
        }
      }

      const fail_summary = {};
      for (let i = 0; i < all_cars.length; i++) {
        const v = all_cars[i];
        const f = parse_failures(v.sensor_failures);
        const unique = [...new Set(f)];
        for (let j = 0; j < unique.length; j++) {
          const x = unique[j];
          if (x) {
            if (!fail_summary[x]) {
              fail_summary[x] = 0;
            }
            fail_summary[x] = fail_summary[x] + 1;
          }
        }
      }

      const total = Object.keys(markers).length;
      let rate = 0;
      if (total > 0) {
        rate = ((fail_cars.length/total)*100).toFixed(1);
      }

      const act_elem = document.getElementById("active-failures");
      const rate_elem = document.getElementById("failure-rate");
      const comm_elem = document.getElementById("common-failures");
      const list_elem = document.getElementById("failed-vehicles");

      if (act_elem) {
        act_elem.textContent = fail_cars.length;
      }
      
      if (rate_elem) {
        rate_elem.textContent = `${rate}%`;
      }
      
      if (comm_elem) {
        const entries = Object.entries(fail_summary);
        entries.sort((a,b) => b[1] - a[1]);
        
        if (entries.length > 0) {
          const items = [];
          for (let i = 0; i < entries.length; i++) {
            const f = entries[i][0];
            const c = entries[i][1];
            items.push(`<div class="metric-list-item">${f} (${c})</div>`);
          }
          comm_elem.innerHTML = items.join("");
        } else {
          comm_elem.innerHTML = "<div class='metric-list-item'>None</div>";
        }
      }
      
      if (list_elem) {
        if (fail_cars.length > 0) {
          const car_items = [];
          for (let i = 0; i < fail_cars.length; i++) {
            car_items.push(`<div class="metric-list-item">${fail_cars[i]}</div>`);
          }
          list_elem.innerHTML = car_items.join("");
        } else {
          list_elem.innerHTML = "<div class='metric-list-item'>None</div>";
        }
      }
    }
  });

  setInterval(() => {
    const marker_vals = Object.values(markers);
    for (let i = 0; i < marker_vals.length; i++) {
      const m = marker_vals[i];
      if (m.isPopupOpen()) {
        m.update();
      }
    }
  }, 5000);
}

const car_search = document.getElementById("vehicle-search");
if (car_search) {
  car_search.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      const car = car_search.value.trim();
      if (car !== "") {
        window.open(`/vehicle_test?vehicle_id=${encodeURIComponent(car)}`, "_blank");
        car_search.value = "";
      }
    }
  });
}
