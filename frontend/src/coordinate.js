// 高德地点坐标为 GCJ-02；OpenStreetMap 底图采用 WGS84。
// 只用于前端展示，后端路线查询始终使用原始高德坐标。
const PI = Math.PI
const A = 6378245.0
const EE = 0.006693421622965943

function transformLat(x, y) {
  let ret = -100 + 2 * x + 3 * y + 0.2 * y * y + 0.1 * x * y + 0.2 * Math.sqrt(Math.abs(x))
  ret += (20 * Math.sin(6 * x * PI) + 20 * Math.sin(2 * x * PI)) * 2 / 3
  ret += (20 * Math.sin(y * PI) + 40 * Math.sin(y / 3 * PI)) * 2 / 3
  ret += (160 * Math.sin(y / 12 * PI) + 320 * Math.sin(y * PI / 30)) * 2 / 3
  return ret
}

function transformLon(x, y) {
  let ret = 300 + x + 2 * y + 0.1 * x * x + 0.1 * x * y + 0.1 * Math.sqrt(Math.abs(x))
  ret += (20 * Math.sin(6 * x * PI) + 20 * Math.sin(2 * x * PI)) * 2 / 3
  ret += (20 * Math.sin(x * PI) + 40 * Math.sin(x / 3 * PI)) * 2 / 3
  ret += (150 * Math.sin(x / 12 * PI) + 300 * Math.sin(x / 30 * PI)) * 2 / 3
  return ret
}

export function toLeaflet(longitude, latitude) {
  if (longitude < 72 || longitude > 138 || latitude < 0 || latitude > 56) return [latitude, longitude]
  const dLat = transformLat(longitude - 105, latitude - 35)
  const dLon = transformLon(longitude - 105, latitude - 35)
  const radLat = latitude / 180 * PI
  let magic = Math.sin(radLat)
  magic = 1 - EE * magic * magic
  const sqrtMagic = Math.sqrt(magic)
  const offsetLat = (dLat * 180) / ((A * (1 - EE)) / (magic * sqrtMagic) * PI)
  const offsetLon = (dLon * 180) / (A / sqrtMagic * Math.cos(radLat) * PI)
  return [latitude - offsetLat, longitude - offsetLon]
}

