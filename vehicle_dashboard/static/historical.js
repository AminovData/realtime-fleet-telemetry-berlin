document.addEventListener("DOMContentLoaded", () => {
  const vehicle_search = document.getElementById("vehicle-search");
  const start_date = document.getElementById("startDate");
  const end_date = document.getElementById("endDate");
  const apply_btn = document.getElementById("applyFilter");

  const ind_start = document.getElementById("independentStart");
  const ind_end = document.getElementById("independentEnd");
  const apply_ind_btn = document.getElementById("applyIndependentFilter");

  const dist_el = document.getElementById("distance");
  const dur_el = document.getElementById("duration");
  const fails_el = document.getElementById("failures");
  const avg_spd_el = document.getElementById("avgSpeed");
  const max_spd_el = document.getElementById("maxSpeed");
  const eng_temp_el = document.getElementById("engineTemp");
  const fail_table = document.getElementById("failureTable");

  let map;
  let polylines = [];
  window.segmentMarkers = [];

  let spd_temp_chart, bat_oil_chart;

  const destroy_charts = () => {
    if (spd_temp_chart) {
      try { 
        spd_temp_chart.destroy(); 
      } catch (e) {
        console.log("chart destroy error");
      }
      spd_temp_chart = null;
    }
    if (bat_oil_chart) {
      try { 
        bat_oil_chart.destroy(); 
      } catch (e) {}
      bat_oil_chart = null;
    }
  };

  const build_url = (endpoint, vid, start, end) => {
    let url = `/${endpoint}?vehicle_id=${encodeURIComponent(vid)}`;
    if (start) {
      url += `&start=${start}`;
    }
    if (end) {
      url += `&end=${end}`;
    }
    return url;
  };

  const update_fail_table = (timeline) => {
    fail_table.innerHTML = "";
    
    if (timeline && timeline.length > 0) {
      for (let i = 0; i < timeline.length; i++) {
        const f = timeline[i];
        const row = document.createElement("tr");
        row.innerHTML = `<td>${f.time}</td><td>${f.event}</td>`;
        fail_table.appendChild(row);
      }
    } else {
      const row = document.createElement("tr");
      row.innerHTML = `<td colspan="2">No failures in the selected range.</td>`;
      fail_table.appendChild(row);
    }
  };

  const create_speed_temp_chart = (labels, speed_data, temp_data) => {
    const ctx = document.getElementById("speedTempChart").getContext("2d");
    
    let label_arr = [];
    if (labels) {
      label_arr = labels;
    }
    
    let spd_arr = [];
    if (speed_data) {
      spd_arr = speed_data;
    }
    
    let temp_arr = [];
    if (temp_data) {
      temp_arr = temp_data;
    }
    
    const chart = new Chart(ctx, {
      type: "line",
      data: {
        labels: label_arr,
        datasets: [
          { 
            label: "Speed (km/h)", 
            data: spd_arr, 
            borderColor: "blue", 
            yAxisID: "ySpeed", 
            fill: false 
          },
          { 
            label: "Engine Temp (°C)", 
            data: temp_arr, 
            borderColor: "red", 
            yAxisID: "yTemp", 
            fill: false 
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          ySpeed: { 
            type: "linear", 
            position: "left", 
            title: { display: true, text: "Speed (km/h)" } 
          },
          yTemp: { 
            type: "linear", 
            position: "right", 
            title: { display: true, text: "Engine Temp (°C)" }, 
            grid: { drawOnChartArea: false } 
          }
        }
      }
    });
    
    return chart;
  };

  const create_battery_oil_chart = (labels, bat_data, oil_data) => {
    const ctx = document.getElementById("batteryOilChart").getContext("2d");
    
    let label_arr = [];
    if (labels) {
      label_arr = labels;
    }
    
    let bat_arr = [];
    if (bat_data) {
      bat_arr = bat_data;
    }
    
    let oil_arr = [];
    if (oil_data) {
      oil_arr = oil_data;
    }
    
    const chart = new Chart(ctx, {
      type: "line",
      data: {
        labels: label_arr,
        datasets: [
          { 
            label: "Battery Level (%)", 
            data: bat_arr, 
            borderColor: "green", 
            fill: false, 
            yAxisID: "yBattery" 
          },
          { 
            label: "Oil Pressure", 
            data: oil_arr, 
            borderColor: "orange", 
            fill: false, 
            yAxisID: "yOil" 
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          yBattery: { 
            type: "linear", 
            position: "left", 
            title: { display: true, text: "Battery Level (%)" } 
          },
          yOil: { 
            type: "linear", 
            position: "right", 
            title: { display: true, text: "Oil Pressure" }, 
            grid: { drawOnChartArea: false } 
          }
        }
      }
    });
    
    return chart;
  };

  const draw_segments = (overview_data) => {
    for (let i = 0; i < polylines.length; i++) {
      const p = polylines[i];
      try { 
        map.removeLayer(p); 
      } catch (e) {}
    }
    polylines = [];
    
    for (let i = 0; i < window.segmentMarkers.length; i++) {
      const m = window.segmentMarkers[i];
      try { 
        map.removeLayer(m); 
      } catch (e) {}
    }
    window.segmentMarkers = [];

    if (overview_data.sorted_segment_ids && overview_data.sorted_segment_ids.length > 0) {
      const seg_ids = overview_data.sorted_segment_ids;
      
      for (let i = 0; i < seg_ids.length; i++) {
        const seg_id = seg_ids[i];
        let pts = [];
        
        if (overview_data.segments[seg_id]) {
          pts = overview_data.segments[seg_id];
        }
        
        if (!pts || pts.length === 0) {
          continue;
        }

        let col = "blue";
        if (overview_data.segment_colors && overview_data.segment_colors[seg_id]) {
          col = overview_data.segment_colors[seg_id];
        }
        
        const latlngs = [];
        for (let j = 0; j < pts.length; j++) {
          const p = pts[j];
          latlngs.push([p.lat, p.lon]);
        }
        
        const poly = L.polyline(latlngs, { color: col, weight: 4 }).addTo(map);
        polylines.push(poly);

        let markers = [];
        if (overview_data.segment_markers && overview_data.segment_markers[seg_id]) {
          markers = overview_data.segment_markers[seg_id];
        }
        
        for (let j = 0; j < markers.length; j++) {
          const marker = markers[j];
          
          if (marker.type === "start") {
            let order_txt = "?";
            if (marker.order) {
              order_txt = marker.order;
            }
            
            const start_icon = L.divIcon({
              html: `<div style="background-color: green; color: white; border-radius: 50%; width: 22px; height: 22px; display: flex; justify-content: center; align-items: center; font-size: 12px; font-weight: bold; border: 2px solid white;">${order_txt}</div>`,
              className: "",
              iconSize: [22, 22]
            });
            const m = L.marker([marker.lat, marker.lon], { icon: start_icon }).addTo(map);
            window.segmentMarkers.push(m);
          } else if (marker.type === "end") {
            const m = L.circleMarker([marker.lat, marker.lon], { color: "red", radius: 6 }).addTo(map);
            window.segmentMarkers.push(m);
          } else if (marker.type === "failure") {
            const m = L.circleMarker([marker.lat, marker.lon], { color: "orange", radius: 5 }).addTo(map);
            window.segmentMarkers.push(m);
          }
        }
      }
    } else {
      let segs = overview_data.segments;
      if (!segs) {
        segs = {};
      }
      
      const seg_values = Object.values(segs);
      for (let i = 0; i < seg_values.length; i++) {
        const seg = seg_values[i];
        if (!seg || seg.length === 0) {
          continue;
        }
        
        const latlngs = [];
        for (let j = 0; j < seg.length; j++) {
          const p = seg[j];
          latlngs.push([p.lat, p.lon]);
        }
        
        const poly = L.polyline(latlngs, { color: "blue", weight: 4 }).addTo(map);
        polylines.push(poly);
      }
    }

    const all_latlngs = [];
    let segs = overview_data.segments;
    if (!segs) {
      segs = {};
    }
    
    const seg_values = Object.values(segs);
    for (let i = 0; i < seg_values.length; i++) {
      const s = seg_values[i];
      for (let j = 0; j < s.length; j++) {
        const p = s[j];
        all_latlngs.push([p.lat, p.lon]);
      }
    }
    
    if (all_latlngs.length > 0) {
      map.fitBounds(all_latlngs);
    }
  };

  apply_btn.addEventListener("click", async () => {
    const vid = vehicle_search.value.trim();
    const start = start_date.value;
    const end = end_date.value;

    if (!vid) {
      alert("Please enter a vehicle ID");
      return;
    }

    if (start && end) {
      if (start > end) {
        alert("Start date cannot be after end date");
        return;
      }
    }

    try {
      const overview_url = build_url("get_vehicle_overview", vid, start, end);
      const trends_url = build_url("get_vehicle_trends", vid, start, end);

      const overview_promise = fetch(overview_url);
      const trends_promise = fetch(trends_url);
      
      const results = await Promise.all([overview_promise, trends_promise]);
      const overview_res = results[0];
      const trends_res = results[1];

      const overview_data = await overview_res.json();
      const trends_data = await trends_res.json();

      if (overview_data.error) {
        alert(overview_data.error);
        return;
      }
      if (trends_data.error) {
        alert(trends_data.error);
        return;
      }

      const metrics = overview_data.metrics;
      dist_el.textContent = `${metrics.distance} km`;
      dur_el.textContent = `${metrics.duration} h`;
      fails_el.textContent = metrics.failures;
      avg_spd_el.textContent = `${metrics.avg_speed} km/h`;
      max_spd_el.textContent = `${metrics.max_speed} km/h`;
      eng_temp_el.textContent = `${metrics.avg_temp} °C`;

      update_fail_table(trends_data.failure_timeline);

      if (!map) {
        const seg_keys = Object.keys(overview_data.segments);
        if (seg_keys.length > 0) {
          const first_seg = Object.values(overview_data.segments)[0];
          const first_pt = first_seg[0];
          map = L.map("map").setView([first_pt.lat, first_pt.lon], 12);
          L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
            maxZoom: 18,
            attribution: "© OpenStreetMap"
          }).addTo(map);
        }
      }

      draw_segments(overview_data);

      destroy_charts();
      spd_temp_chart = create_speed_temp_chart(
        trends_data.daily_labels, 
        trends_data.daily_speed, 
        trends_data.daily_engine_temp
      );
      bat_oil_chart = create_battery_oil_chart(
        trends_data.daily_labels, 
        trends_data.daily_battery, 
        trends_data.daily_oil
      );

    } catch (err) {
      console.error(err);
      alert("Failed to fetch vehicle data");
    }
  });

  apply_ind_btn.addEventListener("click", async () => {
    const vid = vehicle_search.value.trim();
    const start = ind_start.value;
    const end = ind_end.value;

    if (!vid) {
      alert("Please select a vehicle first");
      return;
    }

    if (start && end) {
      if (start > end) {
        alert("Start date cannot be after end date");
        return;
      }
    }

    try {
      const url = build_url("get_vehicle_trends", vid, start, end);
      const res = await fetch(url);
      const data = await res.json();

      if (data.error) {
        alert(data.error);
        return;
      }

      update_fail_table(data.failure_timeline);

      destroy_charts();
      
      spd_temp_chart = create_speed_temp_chart(
        data.daily_labels, 
        data.daily_speed, 
        data.daily_engine_temp
      );
      
      bat_oil_chart = create_battery_oil_chart(
        data.daily_labels, 
        data.daily_battery, 
        data.daily_oil
      );

    } catch (err) {
      console.error(err);
      alert("Failed to fetch trends data");
    }
  });

});