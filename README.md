# Journée d'Intégration 2026 — ATAST Student Section · ISIMM

Application web **100 % locale** pour gérer les équipes, les participants, les mini-jeux et les scores
d'une journée d'intégration, avec un **écran public** (podium, classement, équipes) synchronisé en direct.

Aucune connexion Internet n'est nécessaire une fois les dépendances installées : les données sont
enregistrées dans le navigateur de l'ordinateur (localStorage) et les polices sont incluses dans le projet.

---

## 1. Lancer l'application

Prérequis : **Node.js 18 ou plus récent** (https://nodejs.org).

### Le plus simple

- **Windows** : double-cliquez sur `lancer.bat`
- **macOS / Linux** : `./lancer.sh` (ou `bash lancer.sh`)

La première fois, le script installe les dépendances (connexion Internet requise **une seule fois**),
puis ouvre l'application dans le navigateur.

### À la main

```bash
npm install      # une seule fois
npm run dev      # lance l'application sur http://localhost:5173
```

Version optimisée (recommandée le jour J) :

```bash
npm start        # compile puis ouvre http://localhost:4173
```

---

## 2. Les adresses

| Adresse                         | Rôle                                               |
| ------------------------------- | -------------------------------------------------- |
| `http://localhost:5173/`        | Page d'accueil                                     |
| `http://localhost:5173/admin`   | Interface organisateurs (dashboard, scores…)       |
| `http://localhost:5173/display` | Écran public, à projeter (aucun bouton d'admin)    |

## 3. Le jour J : deux écrans

1. Ouvrez `/admin` sur l'écran de l'ordinateur.
2. Cliquez sur **Mode écran → Ouvrir l'écran public** : une nouvelle fenêtre s'ouvre sur `/display`.
3. Glissez cette fenêtre sur le projecteur et appuyez sur **F** (plein écran).
4. Chaque point ajouté dans l'admin apparaît instantanément sur l'écran public (animation, changement de
   position, « Nouveau leader »…). La page **Mode écran** de l'admin sert de télécommande.

> Par défaut (sans configuration Firebase, voir §4), les deux fenêtres doivent être dans le
> **même navigateur** du **même ordinateur** (synchronisation via `BroadcastChannel` + `localStorage`,
> sans serveur). Une fois Firebase configuré, ce n'est plus nécessaire : voir §4.

### Raccourcis clavier (écran public)

| Touche | Action                         |
| ------ | ------------------------------ |
| `P`    | Podium (lance la cérémonie)    |
| `R`    | Rejouer la cérémonie du podium |
| `L`    | Classement                     |
| `E`    | Équipes                        |
| `F`    | Plein écran                    |

## 4. Synchronisation multi-appareils (plusieurs animateurs)

Par défaut, l'application fonctionne en **local** : tout est enregistré uniquement dans le
navigateur d'un seul appareil (voir §3). Si plusieurs animateurs doivent gérer des mini-jeux en
parallèle — chacun sur son propre téléphone ou ordinateur — avec les scores synchronisés en direct
partout, activez la synchronisation Firebase :

1. Créez un projet gratuit sur [console.firebase.google.com](https://console.firebase.google.com).
2. **Build → Firestore Database → Create database** (mode production, région proche de vous).
3. Dans l'onglet **Rules** de Firestore, collez le contenu de `firestore.rules` (racine du dépôt)
   puis **Publish**.
4. **Project settings** (⚙️) → **General** → **Your apps** → **Add app** → **Web**, puis copiez les
   valeurs `firebaseConfig` qu'il vous donne dans `src/store/firebaseConfig.js`.
5. Redéployez (`npm run build` puis push, ou laissez le déploiement automatique s'en charger).

Une fois configuré : chaque animateur ouvre `/admin` sur son propre appareil (avec une connexion
Internet), toutes les modifications (équipes, scores, mini-jeux) se propagent instantanément à tous
les autres appareils et à l'écran public — sans rien changer côté code.

> **Sécurité** : les règles fournies (`allow read, write: if true`) n'ajoutent ni ne retirent
> d'accès par rapport à aujourd'hui — il n'y a déjà aucune connexion sur `/admin`. Elles étendent
> simplement le même niveau de confiance au réseau au lieu de le limiter à un seul appareil. Pour
> restreindre l'accès plus tard (ex. code d'accès partagé), c'est une fonctionnalité séparée.

Tant que `firebaseConfig.js` garde ses valeurs `REPLACE_ME`, l'application continue de fonctionner
exactement comme avant (mode local, §3) — rien ne casse si vous ne configurez pas Firebase.

## 5. Modifier un score (moins de 3 secondes)

- **Dashboard** : chaque équipe a ses boutons `-10 -5 -1 … +1 +5 +10`, un clic suffit.
- Bouton **⚡ Points** (toujours visible dans la barre latérale) : équipe + points + motif.
- **Page d'une équipe** : fixer directement un score, ou ajouter un événement (mini-jeu, bonus, pénalité).
- **Mini-jeux** : saisir les points de toutes les équipes d'un coup (« Attribuer les points »).
- **Annuler la dernière modification** : sur le dashboard (dernier changement global, un mini-jeu entier
  compte pour un seul changement) ou sur la page d'une équipe.

Le classement se recalcule tout seul ; les égalités partagent le même rang (1, 1, 3).

## 6. Avatars des équipes

À la création (ou modification) d'une équipe, choisissez un avatar parmi **83 icônes** réparties en
6 catégories : Animaux, Énergie, Combat, Tech & Science, Nature & Espace, Fun & Sport.

- L'avatar prend automatiquement la **couleur de l'équipe**.
- Une nouvelle équipe reçoit un avatar au hasard ; le bouton **Au hasard** en propose un autre.
- Les avatars déjà utilisés par une autre équipe apparaissent **grisés** (restent sélectionnables).
- La première case affiche simplement les **initiales** de l'équipe.
- Tout est intégré à l'application : aucun fichier à importer, fonctionne hors ligne.

La liste se modifie dans `src/data/avatars.js`.

## 7. Sauvegardes

**Paramètres → Sauvegarde** :

- **Exporter (JSON)** : sauvegarde complète, restaurable avec **Importer**.
- **Exporter (CSV)** : 3 fichiers lisibles dans Excel (classement, participants, historique).

Conseil : exportez un JSON avant et après l'événement. Les données vivent dans le navigateur : vider
les données du site ou changer de navigateur repart de zéro (d'où l'intérêt de l'export).

Au premier lancement, 8 équipes de démonstration sont chargées. Pour partir d'une page blanche :
**Paramètres → Zone sensible → Tout effacer**.

---

## 8. Structure du projet

```
public/brand/            logos ATAST (utilisés par défaut)
src/
  components/
    ui/                  Button, Modal, ConfirmDialog, Notification, Field, TeamAvatar, AvatarPicker,
                         AnimatedNumber, StatsCard, EmptyState, Ribbons, OrbitRings…
    admin/               Sidebar, Navbar, Leaderboard, QuickScoreRow, ScoreButtons, ScoreEditor,
                         HistoryList, TeamCard, TeamFormModal, ParticipantList, GameCard,
                         GameFormModal, AwardPointsModal, AddPointsModal, PageHeader
    display/             Podium, DisplayLeaderboard, DisplayTeams, LiveEventOverlay, StageBackground
  pages/
    Home.jsx             page d'accueil
    admin/               Dashboard, Teams, TeamDetail, Participants, Games, LeaderboardPage,
                         ScreenControl, Settings
    display/             DisplayScreen (écran public)
  layouts/AdminLayout.jsx
  store/                 store.js (choix du moteur), localStore.js (local), firestoreStore.js
                         (multi-appareils), firebaseConfig.js, actions.js, hooks.js
  hooks/                 useAnimatedNumber, useRankChanges, useScoreEvents, useKeyboardShortcuts…
  utils/                 ranking, exporters (JSON/CSV), sound (Web Audio), confetti, color, image…
  data/avatars.js        catalogue des avatars d'équipe
  data/demoData.js       équipes, participants et mini-jeux de démonstration
  styles/index.css       thème (variables de couleur, mode sombre)
```

**Stack** : React 18 · Vite 5 · Tailwind CSS 3 · Framer Motion · Lucide · canvas-confetti ·
police Saira (embarquée via Fontsource) · Firebase Firestore (synchro multi-appareils, optionnelle).

## 9. Identité visuelle

Inspirée des deux logos du club :

- **ATAST Student Section** : fond rouge framboise `#C4073D`, typographie large et géométrique en
  capitales, rubans blancs arrondis qui sortent des coins → fond de l'écran public, sidebar, cartes.
- **ATAST Club ISIMM** : globe bleu `#1F6FE0` et orbites orange `#F5921E` → anneaux orbitaux animés
  autour de l'année et du champion au podium.

La couleur principale se change dans **Paramètres** ; toute l'interface suit.
