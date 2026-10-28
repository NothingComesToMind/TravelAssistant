<script setup>
import { computed, ref } from 'vue'
import TripMap from './TripMap.vue'

const destination = ref('南京')
const days = ref(3)
const preferences = ref('博物馆、历史文化、步行游览')
const startDate = ref(new Date().toISOString().slice(0, 10))
const loading = ref(false)
const error = ref('')
const plan = ref(null)
const activeDay = ref(0)
const selectedDay = computed(() => plan.value?.days?.[activeDay.value] || null)

async function generate() {
  loading.value = true
  error.value = ''
  plan.value = null
  try {
    const response = await fetch('/api/plan', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        destination: destination.value.trim(),
        days: Number(days.value),
        preferences: preferences.value.trim(),
        start_date: startDate.value || null,
      }),
    })
    const body = await response.json()
    if (!response.ok) throw new Error(typeof body.detail === 'string' ? body.detail : '规划请求未通过校验')
    plan.value = body
    activeDay.value = 0
  } catch (cause) {
    error.value = cause.message || '服务暂时不可用，请稍后重试'
  } finally {
    loading.value = false
  }
}

function routeText(route) {
  if (route.status !== 'available') return '路线暂不可用'
  if (route.distance_m == null) return '演示路线（非真实道路）'
  const km = (route.distance_m / 1000).toFixed(1)
  const mins = Math.max(1, Math.round((route.duration_s || 0) / 60))
  return `步行约 ${km} km · ${mins} 分钟`
}
</script>

<template>
  <div class="page-shell">
    <header class="topbar">
      <div class="brand"><span class="brand-mark">T</span><span>TravelAssistant</span></div>
      <span class="topbar-note">把旅行想法，整理成可查看的路线</span>
    </header>

    <main>
      <section class="hero">
        <div class="hero-copy">
          <p class="eyebrow">SMART TRIP PLANNER</p>
          <h1>下一段旅程，<br /><em>从这里开始。</em></h1>
          <p class="hero-description">输入目的地与旅行偏好，获取按天整理的景点、天气、住宿建议和地图路线。</p>
        </div>
        <form class="plan-form" @submit.prevent="generate">
          <div class="form-heading"><span>规划你的旅行</span><small>01 / 规划信息</small></div>
          <label>目的地<input v-model="destination" required minlength="2" maxlength="40" placeholder="例如：南京" /></label>
          <div class="form-row">
            <label>出行天数<select v-model.number="days"><option v-for="value in 7" :key="value" :value="value">{{ value }} 天</option></select></label>
            <label>出发日期<input v-model="startDate" type="date" /></label>
          </div>
          <label>旅行偏好<textarea v-model="preferences" maxlength="200" rows="3" placeholder="例如：历史文化、博物馆、轻松步行"></textarea></label>
          <button type="submit" :disabled="loading">{{ loading ? '正在规划，请稍候…' : '生成旅行计划' }}<span aria-hidden="true">↗</span></button>
          <p class="form-hint">未配置密钥时使用标记明确的演示数据，仅支持“南京”。</p>
        </form>
      </section>

      <section v-if="error" class="error-panel" role="alert"><strong>无法生成行程</strong><p>{{ error }}</p></section>

      <section v-if="plan" class="results" aria-live="polite">
        <div class="section-intro">
          <div><p class="eyebrow">YOUR ITINERARY</p><h2>{{ plan.destination }} · {{ plan.days.length }} 日行程</h2></div>
          <span :class="['mode-badge', plan.data_mode]">{{ plan.data_mode === 'demo' ? '演示数据 · 非真实行程' : '实时地点数据' }}</span>
        </div>
        <div v-if="plan.warnings.length" class="notice"><strong>数据提示</strong><ul><li v-for="warning in plan.warnings" :key="warning">{{ warning }}</li></ul></div>
        <div class="day-tabs" role="tablist" aria-label="选择行程日期">
          <button v-for="(day, index) in plan.days" :key="day.day" type="button" role="tab" :aria-selected="activeDay === index" :class="{ active: activeDay === index }" @click="activeDay = index">
            <span>DAY {{ String(day.day).padStart(2, '0') }}</span><small>{{ day.date }}</small>
          </button>
        </div>
        <div v-if="selectedDay" class="day-layout">
          <article class="day-details">
            <div class="day-title"><div><p class="eyebrow">DAY {{ String(selectedDay.day).padStart(2, '0') }}</p><h3>今日安排</h3></div><span>{{ selectedDay.attractions.length }} 个景点</span></div>
            <div class="weather-row"><span class="weather-icon">☀</span><div><strong>{{ selectedDay.weather?.day_weather || '天气暂无数据' }}</strong><small>{{ selectedDay.weather ? `${selectedDay.weather.day_temp}° / ${selectedDay.weather.night_temp}°` : '不展示未经核实的预报' }}</small></div></div>
            <ol class="stops"><li v-for="(place, index) in selectedDay.attractions" :key="place.id"><span class="stop-number">{{ index + 1 }}</span><div><strong>{{ place.name }}</strong><small>{{ place.address || '地址暂无数据' }}</small><span v-if="selectedDay.routes[index]" class="route-note">{{ routeText(selectedDay.routes[index]) }}</span></div></li></ol>
            <div class="hotel-row"><span>住宿建议</span><strong>{{ selectedDay.hotel?.name || '暂无经核实的住宿地点' }}</strong><small v-if="selectedDay.hotel">{{ selectedDay.hotel.address }}</small></div>
          </article>
          <div class="map-card"><div class="map-heading"><span>当日路线地图</span><small>{{ plan.data_mode === 'demo' ? '虚线仅作演示' : '路线来自地图服务' }}</small></div><TripMap :day="selectedDay" :data-mode="plan.data_mode" /></div>
        </div>
      </section>
      <section v-else class="empty-state"><p class="eyebrow">TRAVEL MADE CLEAR</p><h2>景点、天气和路线，<br />放在同一张行程里。</h2><p>填好上面的信息，开始生成你的第一份旅行计划。</p></section>
    </main>
    <footer>TravelAssistant · 每一处地点都经过候选 POI ID 校验</footer>
  </div>
</template>

