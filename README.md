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

> Les deux fenêtres doivent être dans le **même navigateur** du **même ordinateur**
> (synchronisation via `BroadcastChannel` + `localStorage`, sans serveur).

### Raccourcis clavier (écran public)

| Touche | Action                         |
| ------ | ------------------------------ |
| `P`    | Podium (lance la cérémonie)    |
| `R`    | Rejouer la cérémonie du podium |
| `L`    | Classement                     |
| `E`    | Équipes                        |
| `F`    | Plein écran                    |

## 4. Modifier un score (moins de 3 secondes)

- **Dashboard** : chaque équipe a ses boutons `-10 -5 -1 … +1 +5 +10`, un clic suffit.
- Bouton **⚡ Points** (toujours visible dans la barre latérale) : équipe + points + motif.
- **Page d'une équipe** : fixer directement un score, ou ajouter un événement (mini-jeu, bonus, pénalité).
- **Mini-jeux** : saisir les points de toutes les équipes d'un coup (« Attribuer les points »).
- **Annuler la dernière modification** : sur le dashboard (dernier changement global, un mini-jeu entier
  compte pour un seul changement) ou sur la page d'une équipe.

Le classement se recalcule tout seul ; les égalités partagent le même rang (1, 1, 3).

## 5. Avatars des équipes

À la création (ou modification) d'une équipe, choisissez un avatar parmi **83 icônes** réparties en
6 catégories : Animaux, Énergie, Combat, Tech & Science, Nature & Espace, Fun & Sport.

- L'avatar prend automatiquement la **couleur de l'équipe**.
- Une nouvelle équipe reçoit un avatar au hasard ; le bouton **Au hasard** en propose un autre.
- Les avatars déjà utilisés par une autre équipe apparaissent **grisés** (restent sélectionnables).
- La première case affiche simplement les **initiales** de l'équipe.
- Tout est intégré à l'application : aucun fichier à importer, fonctionne hors ligne.

La liste se modifie dans `src/data/avatars.js`.

## 6. Sauvegardes

**Paramètres → Sauvegarde** :

- **Exporter (JSON)** : sauvegarde complète, restaurable avec **Importer**.
- **Exporter (CSV)** : 3 fichiers lisibles dans Excel (classement, participants, historique).

Conseil : exportez un JSON avant et après l'événement. Les données vivent dans le navigateur : vider
les données du site ou changer de navigateur repart de zéro (d'où l'intérêt de l'export).

Au premier lancement, 8 équipes de démonstration sont chargées. Pour partir d'une page blanche :
**Paramètres → Zone sensible → Tout effacer**.

---

## 7. Structure du projet

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
  store/                 store.js (persistance + synchro onglets), actions.js, hooks.js
  hooks/                 useAnimatedNumber, useRankChanges, useScoreEvents, useKeyboardShortcuts…
  utils/                 ranking, exporters (JSON/CSV), sound (Web Audio), confetti, color, image…
  data/avatars.js        catalogue des avatars d'équipe
  data/demoData.js       équipes, participants et mini-jeux de démonstration
  styles/index.css       thème (variables de couleur, mode sombre)
```

**Stack** : React 18 · Vite 5 · Tailwind CSS 3 · Framer Motion · Lucide · canvas-confetti ·
police Saira (embarquée via Fontsource).

## 8. Identité visuelle

Inspirée des deux logos du club :

- **ATAST Student Section** : fond rouge framboise `#C4073D`, typographie large et géométrique en
  capitales, rubans blancs arrondis qui sortent des coins → fond de l'écran public, sidebar, cartes.
- **ATAST Club ISIMM** : globe bleu `#1F6FE0` et orbites orange `#F5921E` → anneaux orbitaux animés
  autour de l'année et du champion au podium.

La couleur principale se change dans **Paramètres** ; toute l'interface suit.
