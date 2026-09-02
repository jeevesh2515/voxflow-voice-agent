import assert from "node:assert/strict";
import { clampMs, getActiveLayerIndex } from "./voiceXray.js";

// time → layer at hop boundaries (84/112/196 from brief)
assert.equal(getActiveLayerIndex(0), 0);
assert.equal(getActiveLayerIndex(42), 0);
assert.equal(getActiveLayerIndex(83), 0);
assert.equal(getActiveLayerIndex(83.6), 1); // rounds to 84
assert.equal(getActiveLayerIndex(84), 1);
assert.equal(getActiveLayerIndex(111), 1);
assert.equal(getActiveLayerIndex(112), 2);
assert.equal(getActiveLayerIndex(195), 2);
assert.equal(getActiveLayerIndex(196), 3);
assert.equal(getActiveLayerIndex(999), 3);
assert.equal(getActiveLayerIndex(-5), 0);
assert.equal(clampMs(300), 196);
assert.equal(clampMs(-10), 0);
assert.equal(clampMs(84.4), 84);
console.log("voiceXray: 14/14 pass");
