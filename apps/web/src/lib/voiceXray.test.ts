import assert from "node:assert/strict";
import { clampMs, getActiveLayerIndex } from "./voiceXray.js";

// time → layer at balanced 4-quadrant boundaries across 0 -> 196ms
assert.equal(getActiveLayerIndex(0), 0);
assert.equal(getActiveLayerIndex(42), 0);
assert.equal(getActiveLayerIndex(55), 0);
assert.equal(getActiveLayerIndex(56), 1);
assert.equal(getActiveLayerIndex(84), 1); // 84ms STT milestone
assert.equal(getActiveLayerIndex(99), 1);
assert.equal(getActiveLayerIndex(100), 2);
assert.equal(getActiveLayerIndex(112), 2); // 112ms Intent milestone
assert.equal(getActiveLayerIndex(147), 2);
assert.equal(getActiveLayerIndex(148), 3); // Layer 04 active across 148-196ms
assert.equal(getActiveLayerIndex(175), 3);
assert.equal(getActiveLayerIndex(196), 3); // 196ms Write milestone
assert.equal(getActiveLayerIndex(999), 3);
assert.equal(getActiveLayerIndex(-5), 0);
assert.equal(clampMs(300), 196);
assert.equal(clampMs(-10), 0);
assert.equal(clampMs(84.4), 84);
console.log("voiceXray: 17/17 pass");

