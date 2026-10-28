<script setup>
import { onBeforeUnmount, onMounted, watch } from 'vue'
import L from 'leaflet'
import { toLeaflet } from './coordinate'

const props = defineProps({
  day: { type: Object, default: null },
  dataMode: { type: String, default: 'demo' },
})

let map
let layer

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  })[char])
}

function draw() {
  if (!map || !layer) return
  layer.clearLayers()
  const points = []
  for (const [index, place] of (props.day?.attractions || []).entries()) {
    const coordinate = toLeaflet(place.longitude, place.latitude)
    points.push(coordinate)
    L.marker(coordinate, {
      icon: L.divIcon({
        className: 'number-marker',
        html: `<span>${index + 1}</span>`,
        iconSize: [31, 31],
        iconAnchor: [15, 31],
      }),
    }).bindPopup(`<strong>${escapeHtml(place.name)}</strong>`).addTo(layer)
  }
  for (const route of props.day?.routes || []) {
    if (route.status !== 'available' || !route.polyline?.length) continue
    const line = route.polyline.map(([lon, lat]) => toLeaflet(lon, lat))
    L.polyline(line, {
      color: props.dataMode === 'demo' ? '#7895a1' : '#207c86',
      weight: 5,
      opacity: 0.85,
      dashArray: props.dataMode === 'demo' ? '8 8' : undefined,
    }).addTo(layer)
    points.push(...line)
  }
  if (props.day?.hotel) {
    const hotel = props.day.hotel
    const coordinate = toLeaflet(hotel.longitude, hotel.latitude)
    L.circleMarker(coordinate, { radius: 8, color: '#ba6c36', fillColor: '#e69a53', fillOpacity: 1 })
      .bindPopup(`住宿：${escapeHtml(hotel.name)}`)
      .addTo(layer)
    points.push(coordinate)
  }
  if (points.length) map.fitBounds(L.latLngBounds(points).pad(0.24), { maxZoom: 13 })
  else map.setView([32.06, 118.79], 11)
  setTimeout(() => map?.invalidateSize(), 50)
}

onMounted(() => {
  map = L.map('trip-map', { zoomControl: true }).setView([32.06, 118.79], 11)
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors',
    maxZoom: 19,
  }).addTo(map)
  layer = L.layerGroup().addTo(map)
  draw()
})

watch(() => props.day, draw)
onBeforeUnmount(() => map?.remove())
</script>

<template>
  <div id="trip-map" class="trip-map" role="img" aria-label="当日景点和路线地图"></div>
</template>

