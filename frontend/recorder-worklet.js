class RecorderProcessor extends AudioWorkletProcessor {
  constructor(options) {
    super();
    // sampleRate is the actual rate the AudioContext is running at (may differ from requested 16000)
    const actualRate = sampleRate; // global in AudioWorkletGlobalScope
    this._buffer = [];
    this._samples = 0;
    this._target = actualRate * 3; // 3 sec of actual samples
    this._actualRate = actualRate;
    // Send actual rate to main thread so it can be forwarded to backend
    this.port.postMessage({ type: "init", sampleRate: actualRate });
  }

  process(inputs) {
    const input = inputs[0];
    if (!input || !input[0]) return true;

    const channel = input[0];
    this._buffer.push(new Float32Array(channel));
    this._samples += channel.length;

    if (this._samples >= this._target) {
      const merged = new Float32Array(this._samples);
      let offset = 0;
      for (const buf of this._buffer) {
        merged.set(buf, offset);
        offset += buf.length;
      }
      this._buffer = [];
      this._samples = 0;
      // Transfer buffer without copy
      this.port.postMessage({ type: "chunk", buffer: merged.buffer, sampleRate: this._actualRate }, [merged.buffer]);
    }

    return true;
  }
}

registerProcessor("recorder-processor", RecorderProcessor);
