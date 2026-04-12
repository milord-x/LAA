class RecorderProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this._buffer = [];
    this._samples = 0;
    this._target = 16000 * 3; // 3 sec at 16kHz
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
      this.port.postMessage(merged.buffer, [merged.buffer]);
    }

    return true;
  }
}

registerProcessor("recorder-processor", RecorderProcessor);
