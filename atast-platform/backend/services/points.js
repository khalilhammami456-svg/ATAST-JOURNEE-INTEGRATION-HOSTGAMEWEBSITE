'use strict';
/**
 * Points engine — the central business rule (FR-08, FR-14).
 *   SMALL = 10, MEDIUM = 20, BIG = 30, MEETING = 0
 * The score is never stored as editable data: it is always derived from
 * VALIDATED participations (strategy 1 of "Score Calculation").
 */
const POINTS_BY_TYPE = Object.freeze({ SMALL: 10, MEDIUM: 20, BIG: 30, MEETING: 0 });

function pointsFor(type) {
  if (!Object.prototype.hasOwnProperty.call(POINTS_BY_TYPE, type)) {
    throw new Error(`Unknown event type: ${type}`);
  }
  return POINTS_BY_TYPE[type];
}

/** Score(member) = Σ Points(Type(event)) over validated participations. */
function computeScore(validatedEventTypes) {
  return validatedEventTypes.reduce((sum, type) => sum + pointsFor(type), 0);
}

/**
 * SQL expression deriving points from an event type column, generated from
 * the single constant above so SQL and JS can never disagree.
 */
function pointsSql(column) {
  const cases = Object.entries(POINTS_BY_TYPE).map(([t, p]) => `WHEN '${t}' THEN ${p}`).join(' ');
  return `(CASE ${column} ${cases} ELSE 0 END)`;
}

module.exports = { POINTS_BY_TYPE, pointsFor, computeScore, pointsSql };
