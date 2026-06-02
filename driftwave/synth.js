// synth.js — a generative ambient music engine built on the Web Audio API.
//
// Design notes:
//  * Scheduling uses the well-known "two clocks" pattern: a setInterval-driven
//    look-ahead loop queues note events slightly in the future against the
//    sample-accurate AudioContext clock, so timing is rock-solid even when the
//    main thread is busy.
//  * There are two voices: slow evolving "pads" (stacked detuned saws through a
//    lowpass filter) and a sparser plucked "melody" (triangle with a fast
//    decay). Both feed a shared reverb built from a synthesized impulse.

// Scale definitions as semitone offsets from the root.
export const SCALES = {
  'Major Pentatonic': [0, 2, 4, 7, 9],
  'Minor Pentatonic': [0, 3, 5, 7, 10],
  Dorian: [0, 2, 3, 5, 7, 9, 10],
  Lydian: [0, 2, 4, 6, 7, 9, 11],
  'Hirajoshi (JP)': [0, 2, 3, 7, 8],
  Whole_Tone: [0, 2, 4, 6, 8, 10],
};

export const ROOTS = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'];

// MIDI note number -> frequency in Hz.
function midiToFreq(m) {
  return 440 * Math.pow(2, (m - 69) / 12);
}

export class Driftwave {
  constructor() {
    this.ctx = null;
    this.running = false;
    this.params = {
      tempo: 78,        // beats per minute
      density: 0.55,    // probability a melody note fires on a step
      scaleName: 'Major Pentatonic',
      rootIndex: 9,     // A
      octave: 4,
      reverb: 0.45,
      volume: 0.7,
    };
    this._timer = null;
    this._nextNoteTime = 0;
    this._step = 0;
    this._lookahead = 0.1;        // seconds of scheduling horizon
    this._interval = 25;          // ms between scheduler ticks
  }

  // Lazily create the audio graph on first play (browsers require a user
  // gesture before an AudioContext can start).
  _ensureGraph() {
    if (this.ctx) return;
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    this.ctx = ctx;

    this.master = ctx.createGain();
    this.master.gain.value = this.params.volume;

    // A brick-wall-ish limiter catches the peaks when several pads, plucks and
    // the reverb tail stack up, so the mix never clips into harsh distortion.
    this.limiter = ctx.createDynamicsCompressor();
    this.limiter.threshold.value = -3;
    this.limiter.knee.value = 0;
    this.limiter.ratio.value = 20;
    this.limiter.attack.value = 0.003;
    this.limiter.release.value = 0.25;

    this.master.connect(this.limiter);
    this.limiter.connect(ctx.destination);

    // Dry/wet split for reverb.
    this.dry = ctx.createGain();
    this.wet = ctx.createGain();
    this.dry.connect(this.master);
    this.wet.connect(this.master);

    this.reverb = ctx.createConvolver();
    this.reverb.buffer = this._makeImpulse(3.2, 2.4);
    this.reverb.connect(this.wet);
    this._applyReverbMix();

    // Analyser for the visualizer.
    this.analyser = ctx.createAnalyser();
    this.analyser.fftSize = 1024;
    this.master.connect(this.analyser);

    // A gentle bus that both voices share before the dry/wet split.
    this.voiceBus = ctx.createGain();
    this.voiceBus.gain.value = 1;
    this.voiceBus.connect(this.dry);
    this.voiceBus.connect(this.reverb);
  }

  // Build a decaying-noise impulse response for a natural-sounding reverb.
  _makeImpulse(seconds, decay) {
    const rate = this.ctx.sampleRate;
    const length = Math.floor(rate * seconds);
    const impulse = this.ctx.createBuffer(2, length, rate);
    for (let ch = 0; ch < 2; ch++) {
      const data = impulse.getChannelData(ch);
      for (let i = 0; i < length; i++) {
        data[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / length, decay);
      }
    }
    return impulse;
  }

  _applyReverbMix() {
    if (!this.ctx) return;
    this.wet.gain.value = this.params.reverb;
    this.dry.gain.value = 1 - this.params.reverb * 0.6;
  }

  setParam(key, value) {
    this.params[key] = value;
    if (key === 'volume' && this.master) this.master.gain.value = value;
    if (key === 'reverb') this._applyReverbMix();
  }

  // Return the MIDI note for a given scale degree (can exceed the scale,
  // wrapping into higher octaves).
  _degreeToMidi(degree) {
    const scale = SCALES[this.params.scaleName];
    const root = 12 * (this.params.octave + 1) + this.params.rootIndex;
    const octaveShift = Math.floor(degree / scale.length);
    const idx = ((degree % scale.length) + scale.length) % scale.length;
    return root + scale[idx] + 12 * octaveShift;
  }

  // ---- Voices -----------------------------------------------------------

  _playPad(freq, time, duration) {
    const ctx = this.ctx;
    const g = ctx.createGain();
    const filter = ctx.createBiquadFilter();
    filter.type = 'lowpass';
    filter.frequency.setValueAtTime(420, time);
    filter.frequency.linearRampToValueAtTime(1100, time + duration * 0.5);
    filter.frequency.linearRampToValueAtTime(500, time + duration);
    filter.Q.value = 6;

    // Three slightly detuned sawtooth oscillators for a wide, breathing pad.
    const detunes = [-7, 0, 7];
    const oscs = detunes.map((d) => {
      const o = ctx.createOscillator();
      o.type = 'sawtooth';
      o.frequency.value = freq;
      o.detune.value = d;
      o.connect(filter);
      return o;
    });

    g.gain.setValueAtTime(0, time);
    g.gain.linearRampToValueAtTime(0.12, time + duration * 0.4); // slow swell
    g.gain.linearRampToValueAtTime(0, time + duration);
    filter.connect(g);
    g.connect(this.voiceBus);

    oscs.forEach((o) => { o.start(time); o.stop(time + duration + 0.05); });
  }

  _playPluck(freq, time) {
    const ctx = this.ctx;
    const o = ctx.createOscillator();
    o.type = 'triangle';
    o.frequency.value = freq;
    const g = ctx.createGain();
    g.gain.setValueAtTime(0.0001, time);
    g.gain.exponentialRampToValueAtTime(0.22, time + 0.01); // fast attack
    g.gain.exponentialRampToValueAtTime(0.0001, time + 1.6); // long decay
    o.connect(g);

    // Scatter plucks across the stereo field for a sense of space. Fall back to
    // a straight connection if StereoPannerNode isn't available.
    if (ctx.createStereoPanner) {
      const pan = ctx.createStereoPanner();
      pan.pan.value = Math.random() * 1.2 - 0.6;
      g.connect(pan);
      pan.connect(this.voiceBus);
    } else {
      g.connect(this.voiceBus);
    }

    o.start(time);
    o.stop(time + 1.7);
  }

  // ---- Scheduler --------------------------------------------------------

  _scheduleStep(step, time) {
    const beat = 60 / this.params.tempo;

    // Pads change every 4 beats, drawing a low chord root + fifth.
    if (step % 8 === 0) {
      const base = this._degreeToMidi(this._pickChordRoot());
      this._playPad(midiToFreq(base - 12), time, beat * 4);
      this._playPad(midiToFreq(base - 12 + 7), time, beat * 4);
    }

    // Melody: probabilistic plucks drawn from the scale.
    if (Math.random() < this.params.density) {
      const degree = this._pickMelodyDegree();
      this._playPluck(midiToFreq(this._degreeToMidi(degree)), time);
    }
  }

  _pickChordRoot() {
    // Wander gently among a few stable degrees.
    const choices = [0, 3, 4, 5];
    return choices[Math.floor(Math.random() * choices.length)];
  }

  _pickMelodyDegree() {
    // Bias toward stepwise motion around the current degree.
    if (this._lastDegree == null) this._lastDegree = 4;
    const move = [-2, -1, -1, 0, 1, 1, 2][Math.floor(Math.random() * 7)];
    this._lastDegree = Math.max(0, Math.min(13, this._lastDegree + move));
    return this._lastDegree;
  }

  _tick() {
    const beat = 60 / this.params.tempo;
    const stepDur = beat / 2; // eighth-note grid
    while (this._nextNoteTime < this.ctx.currentTime + this._lookahead) {
      this._scheduleStep(this._step, this._nextNoteTime);
      this._nextNoteTime += stepDur;
      this._step++;
    }
  }

  async start() {
    this._ensureGraph();
    if (this.ctx.state === 'suspended') await this.ctx.resume();
    if (this.running) return;
    this.running = true;
    this._step = 0;
    this._nextNoteTime = this.ctx.currentTime + 0.1;
    this._timer = setInterval(() => this._tick(), this._interval);
  }

  stop() {
    this.running = false;
    if (this._timer) clearInterval(this._timer);
    this._timer = null;
  }

  // Snapshot of the analyser's waveform for the visualizer (values 0..255).
  getWaveform() {
    if (!this.analyser) return null;
    const arr = new Uint8Array(this.analyser.frequencyBinCount);
    this.analyser.getByteTimeDomainData(arr);
    return arr;
  }

  getSpectrum() {
    if (!this.analyser) return null;
    const arr = new Uint8Array(this.analyser.frequencyBinCount);
    this.analyser.getByteFrequencyData(arr);
    return arr;
  }
}
