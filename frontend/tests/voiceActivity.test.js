import test from "node:test";
import assert from "node:assert/strict";

import {
  calculateRms,
  matchSpokenChoice,
  VoiceActivityGate,
} from "../src/services/voiceActivity.js";


test("calculateRms measures time-domain signal energy", () => {
  assert.equal(calculateRms(new Float32Array([0, 0, 0])), 0);
  assert.ok(Math.abs(calculateRms(new Float32Array([1, -1])) - 1) < 1e-6);
});


test("voice gate confirms speech and stops after sustained silence", () => {
  const gate = new VoiceActivityGate({
    calibrationMs: 100,
    speechConfirmationMs: 100,
    silenceToStopMs: 200,
    noSpeechTimeoutMs: 1000,
    maximumRecordingMs: 2000,
  });

  gate.update(0.001, 0);
  gate.update(0.001, 100);
  gate.update(0.03, 150);
  const speaking = gate.update(0.03, 250);
  assert.equal(speaking.phase, "speaking");
  assert.equal(speaking.speechDetected, true);

  gate.update(0.001, 350);
  const stopped = gate.update(0.001, 450);
  assert.equal(stopped.phase, "stopped");
  assert.equal(stopped.stopReason, "silence");
});


test("voice gate ignores a short noise spike and times out without speech", () => {
  const gate = new VoiceActivityGate({
    calibrationMs: 100,
    speechConfirmationMs: 120,
    noSpeechTimeoutMs: 500,
    maximumRecordingMs: 2000,
  });

  gate.update(0.001, 0);
  gate.update(0.001, 100);
  gate.update(0.04, 150);
  gate.update(0.001, 200);
  const stopped = gate.update(0.001, 500);

  assert.equal(stopped.phase, "stopped");
  assert.equal(stopped.speechDetected, false);
  assert.equal(stopped.stopReason, "no-speech");
});


test("spoken choices match labels and English or Vietnamese ordinals", () => {
  const choices = ["Eagle", "Fish", "Dog"];

  assert.equal(matchSpokenChoice("I choose the eagle", choices), "Eagle");
  assert.equal(matchSpokenChoice("the second answer", choices), "Fish");
  assert.equal(matchSpokenChoice("đáp án thứ ba", choices), "Dog");
  assert.equal(matchSpokenChoice("eagle or fish", choices), null);
});
