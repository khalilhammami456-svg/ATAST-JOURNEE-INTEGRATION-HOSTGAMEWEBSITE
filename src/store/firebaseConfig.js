/**
 * Firebase project config for the multi-device sync.
 *
 * This is safe to commit: Firebase web config isn't a secret, it's a public
 * client identifier. Access control is enforced by Firestore Security Rules
 * (see firestore.rules), not by hiding these values — the Firebase docs say
 * so explicitly.
 *
 * To enable multi-device sync:
 * 1. Create a free project at https://console.firebase.google.com
 * 2. Build > Firestore Database > Create database (start in production mode,
 *    pick a region close to the event) — then paste the contents of
 *    firestore.rules (repo root) into the Rules tab and Publish.
 * 3. Project settings (gear icon) > General > "Your apps" > Add app > Web,
 *    then copy the firebaseConfig values it gives you into the object below.
 *
 * Until this is filled in, the app automatically falls back to the original
 * single-device, localStorage-only mode — nothing breaks in the meantime.
 */
export const firebaseConfig = {
  apiKey: 'AIzaSyCYWUKchy0wfGu2sawK5TNagg6ZEJC1-xo',
  authDomain: 'atast-d3725.firebaseapp.com',
  projectId: 'atast-d3725',
  storageBucket: 'atast-d3725.firebasestorage.app',
  messagingSenderId: '447275082453',
  appId: '1:447275082453:web:768db59615cab1258ff85c',
};

export const isFirebaseConfigured = Object.values(firebaseConfig).every(
  (value) => typeof value === 'string' && value.length > 0 && value !== 'REPLACE_ME',
);
