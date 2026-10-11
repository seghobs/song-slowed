/* All positions refer to the original recording, regardless of the selected side. */
const TempoTimeline = {
  toSource: (time, side, speed) => side !== 'A' ? time * speed : time,
  fromSource: (time, side, speed) => side !== 'A' ? time / speed : time,
  clamp: (time, duration) => Math.max(0, Math.min(time, Math.max(0, duration - 0.01))),
  validLoop: (start, end, duration) => Number.isFinite(start) && Number.isFinite(end) && start >= 0 && end <= duration && end - start >= 0.25,
};
if (typeof module !== 'undefined') module.exports = TempoTimeline;
