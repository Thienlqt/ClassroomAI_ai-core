async function parseResponse(response) {
  if (!response.ok) {
    let detail = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      detail = body.detail ?? detail;
    } catch {
      // Use the HTTP status fallback for non-JSON errors.
    }
    throw new Error(detail);
  }
  if (response.status === 204) return null;
  return response.json();
}

export async function getHealth() {
  return parseResponse(await fetch("/health"));
}

export async function sendMessage(sessionId, message) {
  return parseResponse(
    await fetch(`/v1/sessions/${encodeURIComponent(sessionId)}/messages`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    }),
  );
}

export async function sendActionResult(sessionId, callId, result) {
  return parseResponse(
    await fetch(
      `/v1/sessions/${encodeURIComponent(sessionId)}/actions/${encodeURIComponent(callId)}/result`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ result }),
      },
    ),
  );
}

export async function resetSession(sessionId) {
  return parseResponse(
    await fetch(`/v1/sessions/${encodeURIComponent(sessionId)}`, {
      method: "DELETE",
    }),
  );
}

export async function transcribeAudio(blob) {
  const extension = blob.type.includes("mp4") ? "m4a" : "webm";
  const form = new FormData();
  form.append("file", blob, `student.${extension}`);
  return parseResponse(
    await fetch("/v1/audio/transcriptions", { method: "POST", body: form }),
  );
}

export async function synthesizeSpeech(text, language = "en-US") {
  const response = await fetch("/v1/speech", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, language }),
  });
  if (!response.ok) await parseResponse(response);
  return response.blob();
}

export async function recognizeFaces(imageBase64) {
  return parseResponse(
    await fetch("/v1/faces/recognize", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ image_base64: imageBase64 }),
    }),
  );
}

export async function enrollFace(payload) {
  return parseResponse(
    await fetch("/v1/faces/enroll", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  );
}
