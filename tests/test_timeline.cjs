const assert = require('node:assert/strict');
const timeline = require('../static/timeline.js');
for (const speed of [0.5, 0.75, 1, 1.25, 2]) {
  for (const time of [0, 10, 123.4]) {
    const b = timeline.fromSource(time, 'B', speed);
    assert.ok(Math.abs(timeline.toSource(b, 'B', speed) - time) < 1e-9);
    assert.equal(timeline.fromSource(time, 'C', speed), b);
    assert.ok(Math.abs(timeline.toSource(b, 'C', speed) - time) < 1e-9);
    assert.equal(timeline.fromSource(time, 'A', speed), time);
  }
}
assert.equal(timeline.fromSource(30, 'B', 0.75), 40);
assert.equal(timeline.toSource(40, 'B', 0.75), 30);
assert.equal(timeline.validLoop(10, 20, 30), true);
assert.equal(timeline.validLoop(20, 10, 30), false);
assert.equal(timeline.validLoop(0, 31, 30), false);
assert.equal(timeline.validLoop(10, 10.1, 30), false);
assert.equal(timeline.validLoop(NaN, 10, 30), false);
assert.equal(timeline.clamp(-1, 30), 0);
assert.equal(timeline.clamp(50, 30), 29.99);
console.log('A/B zaman eşleme ve döngü testleri geçti.');
