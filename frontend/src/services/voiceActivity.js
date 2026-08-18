export const DEFAULT_VOICE_ACTIVITY_SETTINGS = Object.freeze({
  calibrationMs: 650,
  speechConfirmationMs: 180,
  silenceToStopMs: 1200,
  noSpeechTimeoutMs: 8000,
  maximumRecordingMs: 30000,
  minimumSpeechRms: 0.008,
  startNoiseRatio: 2.6,
  continueNoiseRatio: 1.55,
  noiseFloorMinimum: 0.0005,
});

export function calculateRms(samples) {
  if (!samples.length) return 0;
  let sumSquares = 0;
  for (const sample of samples) sumSquares += sample * sample;
  return Math.sqrt(sumSquares / samples.length);
}

function percentile(values, fraction) {
  if (!values.length) return 0;
  const ordered = [...values].sort((a, b) => a - b);
  const index = Math.min(ordered.length - 1, Math.floor(ordered.length * fraction));
  return ordered[index];
}

export class VoiceActivityGate {
  constructor(settings = {}) {
    this.settings = { ...DEFAULT_VOICE_ACTIVITY_SETTINGS, ...settings };
    this.reset();
  }

  reset(startedAt = null) {
    this.startedAt = startedAt;
    this.lastUpdatedAt = startedAt;
    this.phase = "calibrating";
    this.calibrationLevels = [];
    this.noiseFloor = this.settings.noiseFloorMinimum;
    this.speechAboveThresholdMs = 0;
    this.lastVoiceAt = null;
    this.speechDetected = false;
    this.stopReason = null;
  }

  snapshot(level = 0) {
    return {
      phase: this.phase,
      level,
      noiseFloor: this.noiseFloor,
      startThreshold: Math.max(
        this.settings.minimumSpeechRms,
        this.noiseFloor * this.settings.startNoiseRatio,
      ),
      speechDetected: this.speechDetected,
      stopReason: this.stopReason,
    };
  }

  stop(reason, level) {
    this.phase = "stopped";
    this.stopReason = reason;
    return this.snapshot(level);
  }

  update(rawLevel, now) {
    const level = Number.isFinite(rawLevel) ? Math.max(0, rawLevel) : 0;
    if (this.startedAt === null) this.reset(now);
    const elapsed = Math.max(0, now - this.startedAt);
    const delta = Math.max(0, Math.min(now - this.lastUpdatedAt, 250));
    this.lastUpdatedAt = now;

    if (this.phase === "stopped") return this.snapshot(level);
    if (elapsed >= this.settings.maximumRecordingMs) {
      return this.stop(this.speechDetected ? "maximum-duration" : "no-speech", level);
    }

    if (this.phase === "calibrating") {
      this.calibrationLevels.push(level);
      if (elapsed < this.settings.calibrationMs) return this.snapshot(level);
      this.noiseFloor = Math.max(
        this.settings.noiseFloorMinimum,
        percentile(this.calibrationLevels, 0.35),
      );
      this.phase = "listening";
    }

    if (this.phase === "listening") {
      const startThreshold = Math.max(
        this.settings.minimumSpeechRms,
        this.noiseFloor * this.settings.startNoiseRatio,
      );
      if (level >= startThreshold) {
        this.speechAboveThresholdMs += delta;
      } else {
        this.speechAboveThresholdMs = Math.max(
          0,
          this.speechAboveThresholdMs - delta * 1.5,
        );
        // Follow gradual changes in room noise, but never adapt to a likely voice.
        this.noiseFloor = this.noiseFloor * 0.96 + level * 0.04;
      }

      if (this.speechAboveThresholdMs >= this.settings.speechConfirmationMs) {
        this.phase = "speaking";
        this.speechDetected = true;
        this.lastVoiceAt = now;
      } else if (elapsed >= this.settings.noSpeechTimeoutMs) {
        return this.stop("no-speech", level);
      }
    } else if (this.phase === "speaking") {
      const continueThreshold = Math.max(
        this.settings.minimumSpeechRms * 0.65,
        this.noiseFloor * this.settings.continueNoiseRatio,
      );
      if (level >= continueThreshold) this.lastVoiceAt = now;
      if (now - this.lastVoiceAt >= this.settings.silenceToStopMs) {
        return this.stop("silence", level);
      }
    }

    return this.snapshot(level);
  }
}
