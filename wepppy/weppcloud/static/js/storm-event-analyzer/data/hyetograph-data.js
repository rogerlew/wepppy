const DEFAULT_NINTEN = 11;
const MIN_STEP_SECONDS = 300;
const EPS = 1e-9;

function toNumberOrNull(value) {
  if (value === null || value === undefined || value === '') {
    return null;
  }
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : null;
}

function weppEqroot(a) {
  if (!(a > 0 && a <= 1)) {
    throw new Error('eqroot expects 0 < a <= 1');
  }
  if (a <= 0.06) {
    return 1 / a;
  }
  if (a < 0.999) {
    let u;
    if (a <= 0.2) {
      u = 1 / a;
    } else if (a <= 0.5) {
      u = 0.968732 / a - 1.55098 * a + 0.431653;
    } else if (a <= 0.94) {
      u = 1.13243 / a - 0.92824 * a - 0.207111;
    } else {
      u = 1.5 - Math.sqrt(6 * a - 3.75);
    }

    while (true) {
      const e = Math.exp(-u);
      const f = (1 - e) / u;
      const d = a - f;
      const tmp = (u + 1) * f - 1;
      const r = a / tmp;
      const s = r <= 1 ? Math.abs(d / a) : Math.abs(d / tmp);
      if (s < 0.59e-6) {
        break;
      }
      u = u * (1 + d / (e - f));
    }
    return u;
  }
  if (a < 1) {
    return 1.5 - Math.sqrt(6 * a - 3.75);
  }
  return 0;
}

function computeDimensionless(tp, ip, ninten, useConst) {
  const timedl = Array(ninten).fill(0);
  const intdl = Array(ninten).fill(0);
  const deltfq = 1 / (ninten - 1);

  if (useConst) {
    let fqx = 0;
    for (let i = 0; i < ninten - 1; i += 1) {
      fqx += deltfq;
      timedl[i + 1] = fqx;
      intdl[i] = 1;
    }
    intdl[ninten - 1] = 0;
    return { timedl, intdl, deltfq };
  }

  const cappedIp = Math.min(ip, 60);
  const cappedTp = Math.min(tp, 0.99);
  const u = weppEqroot(1 / cappedIp);
  const b = u / cappedTp;
  const a = cappedIp * Math.exp(-u);
  const d = u / (1 - cappedTp);

  timedl[ninten - 1] = 1;
  let fqx = 0;
  for (let i = 0; i < ninten - 1; i += 1) {
    if (i < ninten - 2) {
      fqx += deltfq;
      if (fqx <= cappedTp) {
        timedl[i + 1] = (1 / b) * Math.log(1 + (b / a) * fqx);
      } else {
        timedl[i + 1] = cappedTp - (1 / d) * Math.log(1 - (d / cappedIp) * (fqx - cappedTp));
      }
    }
    const diff = timedl[i + 1] - timedl[i];
    if (diff > 0) {
      intdl[i] = deltfq / diff;
    } else {
      intdl[i] = deltfq / 0.00001;
    }
  }
  intdl[ninten - 1] = 0;
  return { timedl, intdl, deltfq };
}

function minStepSeconds(timedl, durationHours) {
  let minStep = Infinity;
  for (let i = 0; i < timedl.length - 1; i += 1) {
    const diff = timedl[i + 1] - timedl[i];
    const step = diff * durationHours * 3600;
    if (step < minStep) {
      minStep = step;
    }
  }
  return minStep;
}

export function computeHyetographPoints({ depth_mm, duration_hours, tp, ip }, options = {}) {
  const depth = toNumberOrNull(depth_mm);
  const duration = toNumberOrNull(duration_hours);
  const timepRaw = toNumberOrNull(tp);
  const ipRaw = toNumberOrNull(ip);

  if (!Number.isFinite(depth) || !Number.isFinite(duration)) {
    return null;
  }
  if (!Number.isFinite(timepRaw) || !Number.isFinite(ipRaw)) {
    return null;
  }
  if (depth <= 0 || duration <= 0) {
    return null;
  }

  let localIp = ipRaw < 1 ? 1 : ipRaw;
  let timep = timepRaw;
  if (timep > 1 || localIp === 1) {
    timep = 1;
  } else if (timep <= 0) {
    timep = 0.01;
  }

  let ninten = Number.isFinite(options.ninten) ? Math.floor(options.ninten) : DEFAULT_NINTEN;
  if (ninten < 2) {
    ninten = 2;
  }

  const minSeconds = Number.isFinite(options.minStepSeconds) ? options.minStepSeconds : MIN_STEP_SECONDS;
  let timedl;
  let deltfq;
  while (true) {
    const useConst = timep >= 1 && localIp <= 1;
    const result = computeDimensionless(timep, localIp, ninten, useConst);
    timedl = result.timedl;
    deltfq = result.deltfq;
    const minStep = minStepSeconds(timedl, duration);
    if (minStep >= minSeconds - EPS || ninten <= 2) {
      break;
    }
    ninten -= 1;
    if (ninten <= 2) {
      ninten = 2;
    }
  }

  const points = [];
  let fq = 0;
  for (let i = 0; i < timedl.length; i += 1) {
    if (i > 0) {
      fq += deltfq;
    }
    points.push({
      elapsed_hours: timedl[i] * duration,
      cumulative_depth_mm: depth * fq,
    });
  }
  return points;
}

export function buildHyetographSeries(rows, options = {}) {
  const series = [];
  (rows || []).forEach((row) => {
    const simDayIndex = toNumberOrNull(row.sim_day_index);
    if (!Number.isFinite(simDayIndex)) {
      return;
    }
    const points = computeHyetographPoints(row, options);
    if (!points) {
      return;
    }
    series.push({
      sim_day_index: simDayIndex,
      date: row.date || null,
      points,
      depth_mm: row.depth_mm,
      duration_hours: row.duration_hours,
    });
  });
  return series;
}
