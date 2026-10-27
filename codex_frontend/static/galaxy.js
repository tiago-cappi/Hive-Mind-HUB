// Desenho extraído de Codex Hub.dc.html, aprovado pelo usuário.
// Sem React/DCLogic, respostas simuladas, áudio artificial ou timers de conversa.
export class CodexGalaxy {
  static PH = {
    idle: { spd: 1, bri: 1, blue: 0, amp: .016, react: 0, shim: 1, pulse: 0 },
    listening: { spd: 1.12, bri: 1.06, blue: 0, amp: .006, react: 1, shim: 1.15, pulse: 0 },
    processing: { spd: 2.6, bri: 1.28, blue: 0, amp: .006, react: 0, shim: 2.4, pulse: .06 },
    speaking: { spd: 1.3, bri: 1.14, blue: 1, amp: .006, react: 1.25, shim: 1.3, pulse: 0 }
  };

  constructor(canvas, meter, {getState, getLevel}) {
    this.canvasRef = {current:canvas}; this.meterRef = {current:meter};
    this.getState = getState; this.getLevel = getLevel;
    this.variantName = 'A'; this.rot = 0; this.m = 0; this.lvl = 0; this.prog = 0;
    this.p = {...CodexGalaxy.PH.idle};
    this.t0 = this.last = performance.now();
    this.ro = new ResizeObserver(() => this.resize());
    this.buildBg(); this.buildGalaxy('A', 1);
    this.frame = this.frame.bind(this);
    this.active = false;
  }

  setActive(on) {
    if (on === this.active) return;
    this.active = on;
    if (on) { this.last = performance.now(); this.resize(); this.raf = requestAnimationFrame(this.frame); }
    else cancelAnimationFrame(this.raf);
  }

  setVariant(variant) {
    if (variant === this.variantName) return;
    this.variantName = variant;
    this.buildGalaxy(variant, 1);
  }

  frame(now) {
    if (!this.active) return;
    this.raf = requestAnimationFrame(this.frame);
    const dt = Math.min(.05, (now - this.last) / 1000); this.last = now;
    const t = (now - this.t0) / 1000;
    if (!this.ctx) this.resize();
    if (!this.ctx) return;
    this.m = Math.min(1, this.m + dt / 2.8);
    const ph = ({listen:'listening', think:'processing', speak:'speaking'})[this.getState()] || 'idle';
    const T = CodexGalaxy.PH[ph], k = 1 - Math.exp(-dt * 2.2);
    for (const q in T) this.p[q] += (T[q] - this.p[q]) * k;
    const raw = ph === 'listening' || ph === 'speaking' ? this.getLevel() : 0;
    this.lvl += (raw - this.lvl) * (1 - Math.exp(-dt * 14));
    this.rot -= this.p.spd * .045 * dt;
    this.draw(t); this.drawMeter(t, ph);
  }

  rng(s) { return () => { s |= 0; s = s + 0x6D2B79F5 | 0; let t = Math.imul(s ^ s >>> 15, 1 | s); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
  mix(a, b, k) { return [a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k, a[2] + (b[2] - a[2]) * k]; }
  css(c, a) { return a === undefined ? `rgb(${c[0] | 0},${c[1] | 0},${c[2] | 0})` : `rgba(${c[0] | 0},${c[1] | 0},${c[2] | 0},${a < 0 ? 0 : a})`; }
  buildBg() {
    const R = this.rng(77); this.bgS = [];
    for (let i = 0; i < 320; i++) this.bgS.push({ x: R(), y: R(), b: .05 + R() * R() * .4, s: R() < .08 ? 1.6 : 1, f: .3 + R() * 1.2, p: R() * 6.28 });
  }
  buildGalaxy(variant, dens) {
    const B = variant === 'B', R = this.rng(B ? 11 : 5);
    const g = () => { let u = 0; while (!u) u = R(); return Math.sqrt(-2 * Math.log(u)) * Math.cos(6.283185 * R()); };
    const N = Math.round((B ? 7800 : 10500) * dens), out = [];
    const arms = B ? [[0, .5], [Math.PI, .5]] : [[0, .33], [Math.PI, .33], [Math.PI * .5, .17], [Math.PI * 1.5, .17]];
    const pitch = B ? .42 : .30, r0 = B ? .12 : .2;
    const knots = [];
    if (B) for (let k = 0; k < 40; k++) { const a = k % 2 ? Math.PI : 0, r = .22 + R() * .75; knots.push([r, a + Math.log(r / r0) / pitch + g() * .05]); }
    for (let i = 0; i < N; i++) {
      const u = R(); let r, th, y, b, gi, sz = 1;
      if (u < (B ? .10 : .15)) { r = Math.abs(g()) * (B ? .07 : .10); th = R() * 6.2832; y = g() * r * .6; b = .26 + R() * .3; gi = 0; }
      else if (!B && u < .22) { const x = (R() * 2 - 1) * .24, z = g() * .03; r = Math.hypot(x, z); th = Math.atan2(z, x); y = g() * .02; b = .3 + R() * .3; gi = 0; }
      else if (u < (B ? .86 : .80)) {
        if (B && R() < .14) { const kn = knots[(R() * knots.length) | 0]; r = kn[0] + g() * .012; th = kn[1] + g() * .014 / kn[0]; gi = R() < .3 ? 3 : 2; b = .55 + R() * .4; }
        else {
          let k = R(), ai = 0; for (; ai < arms.length - 1; ai++) { if (k < arms[ai][1]) break; k -= arms[ai][1]; }
          r = r0 + Math.pow(R(), B ? 1.1 : 1.35) * (1.02 - r0);
          const base = arms[ai][0] + Math.log(r / r0) / pitch;
          const spread = ((B ? .03 : .028) + (B ? .07 : .055) * r) * (ai > 1 ? 1.3 : 1);
          th = base + g() * spread / r; r += g() * .012;
          const q = R(); gi = q < .06 ? 3 : (q < .55 ? 2 : 1); b = .3 + R() * .5 + (gi === 3 ? .2 : 0);
        }
        y = g() * .016;
        if (R() < .035) { sz = 1.9; b = Math.min(1, b + .3); }
      } else { r = .1 - Math.log(1 - R() * .97) * .3; if (r > 1.25) r = .1 + R() * 1.1; th = R() * 6.2832; y = g() * .035; gi = R() < .5 ? 1 : 2; b = .1 + R() * .24; }
      out.push([r, th, y, Math.min(1, b), sz, gi, .4 + R() * 1.4, R() * 6.28, R(), g(), g()]);
    }
    out.sort((a, c) => a[5] - c[5]);
    const n = out.length, A = () => new Float32Array(n);
    const G = { n, R: A(), TH: A(), Y: A(), B: A(), SZ: A(), G: new Uint8Array(n), F: A(), PHS: A(), DL: A() };
    out.forEach((s, i) => { G.R[i] = s[0]; G.TH[i] = s[1]; G.Y[i] = s[2]; G.B[i] = s[3]; G.SZ[i] = s[4]; G.G[i] = s[5]; G.F[i] = s[6]; G.PHS[i] = s[7]; G.DL[i] = s[8]; });
    this.gal = G;
    this.V = B
      ? { tilt: 1.0, pa: .28, core: .055, rw: .23, rh: .42, trail: .05, cols: [[255, 236, 212], [220, 228, 255], [150, 182, 255], [255, 196, 172]] }
      : { tilt: .66, pa: -.35, core: .075, rw: .21, rh: .36, trail: 0, cols: [[255, 226, 186], [236, 238, 246], [178, 198, 255], [255, 172, 200]] };
    this.m = 0;
  }

  resize() {
    const c = this.canvasRef.current; if (!c) return;
    if (this.cv !== c) { this.cv = c; this.ctx = c.getContext('2d'); this.ro && this.ro.observe(c); }
    const r = c.getBoundingClientRect(); this.dpr = Math.min(2, window.devicePixelRatio || 1);
    this.W = Math.max(1, r.width); this.H = Math.max(1, r.height);
    c.width = Math.round(this.W * this.dpr); c.height = Math.round(this.H * this.dpr);
  }

  draw(t) {
    const ctx = this.ctx, W = this.W, H = this.H, P = this.p, V = this.V, m = this.m, G = this.gal;
    ctx.setTransform(this.dpr, 0, 0, this.dpr, 0, 0); ctx.clearRect(0, 0, W, H);
    ctx.globalCompositeOperation = 'lighter';
    const cx = W / 2, cy = H * .42, bri = P.bri * (1 + P.pulse * Math.sin(t * 6.5));
    ctx.fillStyle = '#dfe4ee';
    for (const s of this.bgS) { ctx.globalAlpha = s.b * (.55 + .45 * Math.sin(t * s.f + s.p)) * Math.min(1, m * 2); ctx.fillRect(s.x * W, s.y * H, s.s, s.s); }
    const pulse = 1 + P.amp * Math.sin(t * 1.26) + P.react * this.lvl * .075;
    const Rg = Math.min(W * V.rw, H * V.rh) * pulse;
    const ct = Math.cos(V.tilt), st = Math.sin(V.tilt), cp = Math.cos(V.pa), sp = Math.sin(V.pa);
    const BL = [125, 172, 255], cols = V.cols.map((c, i) => this.mix(c, BL, P.blue * (i === 0 ? .62 : .5)));
    const L = 6, paths = []; for (let i = 0; i < 4 * L; i++) paths.push(new Path2D());
    const rot = this.rot, sh = .012 * P.shim, trail = V.trail * (.7 + .3 * P.spd), intro = m < 1;
    for (let i = 0; i < G.n; i++) {
      let th = G.TH[i] + rot + sh * Math.sin(t * G.F[i] + G.PHS[i]), ap = 1, ee = 1;
      if (intro) { let e = (m - G.DL[i] * .45) / .55; e = e < 0 ? 0 : e > 1 ? 1 : e; ee = e * e * (3 - 2 * e); th += (1 - ee) * 1.6; ap = Math.min(1, e * 2); }
      const r = G.R[i] * (intro ? .05 + .95 * ee : 1);
      const x = r * Math.cos(th), z = r * Math.sin(th), y = G.Y[i];
      const yv = z * ct - y * st, d = z * st + y * ct, ps = 4 / (4 + d);
      const gx = cx + (x * cp - yv * sp) * Rg * ps, gy = cy + (x * sp + yv * cp) * Rg * ps;
      const a = G.B[i] * bri * ap * ps * ps * (.72 + .28 * Math.sin(t * G.F[i] * 2.3 + G.PHS[i]));
      if (a < .02) continue;
      let li = (a * L) | 0; if (li >= L) li = L - 1;
      const p = paths[G.G[i] * L + li];
      if (trail) {
        const t2 = th + trail, x2 = r * Math.cos(t2), z2 = r * Math.sin(t2), yv2 = z2 * ct - y * st, ps2 = 4 / (4 + z2 * st + y * ct);
        p.moveTo(gx, gy); p.lineTo(cx + (x2 * cp - yv2 * sp) * Rg * ps2, cy + (x2 * sp + yv2 * cp) * Rg * ps2);
      } else { const s = G.SZ[i]; p.rect(gx - s * .5, gy - s * .5, s, s); }
    }
    if (trail) { ctx.lineWidth = 1.05; ctx.lineCap = 'round'; }
    for (let g = 0; g < 4; g++) { const c = this.css(cols[g]); for (let l = 0; l < L; l++) { ctx.globalAlpha = (l + .5) / L; if (trail) { ctx.strokeStyle = c; ctx.stroke(paths[g * L + l]); } else { ctx.fillStyle = c; ctx.fill(paths[g * L + l]); } } }
    const I = Math.min(1, m * 1.3) * bri;
    ctx.save(); ctx.translate(cx, cy); ctx.rotate(V.pa); ctx.scale(1, ct);
    const hot = this.mix([255, 250, 242], BL, P.blue * .4), cc = cols[0], rc = Rg * V.core * (.3 + .7 * Math.min(1, m * 1.2));
    let gr = ctx.createRadialGradient(0, 0, 0, 0, 0, rc * 5);
    gr.addColorStop(0, this.css(hot, .9 * I)); gr.addColorStop(.1, this.css(cc, .5 * I)); gr.addColorStop(.38, this.css(cc, .12 * I)); gr.addColorStop(1, this.css(cc, 0));
    ctx.globalAlpha = 1; ctx.fillStyle = gr; ctx.fillRect(-rc * 5, -rc * 5, rc * 10, rc * 10);
    const hz = cols[2]; gr = ctx.createRadialGradient(0, 0, 0, 0, 0, Rg);
    gr.addColorStop(0, this.css(hz, .075 * I)); gr.addColorStop(.5, this.css(hz, .025 * I)); gr.addColorStop(1, this.css(hz, 0));
    ctx.fillStyle = gr; ctx.fillRect(-Rg, -Rg, 2 * Rg, 2 * Rg);
    ctx.restore();
    ctx.globalCompositeOperation = 'source-over'; ctx.globalAlpha = 1;
  }

  drawMeter(t, ph) {
    const c = this.meterRef.current; if (!c) return;
    if (this.mcv !== c) { this.mcv = c; this.mctx = c.getContext('2d'); this.md = Math.min(2, window.devicePixelRatio || 1); c.width = 440 * this.md; c.height = 5 * this.md; }
    const ctx = this.mctx; ctx.setTransform(this.md, 0, 0, this.md, 0, 0); ctx.clearRect(0, 0, 440, 5);
    const n = 56, gap = 2, w = (440 - gap * (n - 1)) / n, on = this.mix([236, 238, 242], [150, 186, 255], this.p.blue * .8);
    for (let i = 0; i < n; i++) {
      const x = i / (n - 1), pos = Math.abs(x - .5) * 2; let a = .09;
      if (ph === 'listening' || ph === 'speaking') { const lv = this.lvl * 1.05 + .03 * Math.sin(t * 11 + i * 1.7); if (pos < lv) a = .25 + .65 * (1 - pos / Math.max(lv, .01)); }
      else if (ph === 'processing') { if (x <= this.prog) a = .45; const sw = ((t * .7) % 1.4) - .2, dd = Math.abs(x - sw); if (dd < .07) a = Math.max(a, .85 - dd * 6); }
      ctx.fillStyle = this.css(on, Math.min(1, a)); ctx.fillRect(i * (w + gap), 0, w, 5);
    }
  }

}
