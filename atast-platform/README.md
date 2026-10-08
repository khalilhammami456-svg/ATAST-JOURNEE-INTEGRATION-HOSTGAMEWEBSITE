# ATAST Club — plateforme de gestion

Site officiel du club ATAST (ISIMM), réalisé selon `documentation/documentation.tex` (SRS + TDD) :
adhésions, membres, événements, participations et points, classement, messages et suggestions,
avec une séparation stricte **Admin / Member** vérifiée côté serveur.

## Démarrage rapide

Prérequis : **Node.js 22.13 ou plus récent** (aucune base de données à installer : SQLite est intégré à Node).

```bash
npm install
npm run seed:demo     # facultatif : données de démonstration
npm start             # http://localhost:3000
```

Comptes de démonstration (créés par `seed:demo`, à ne jamais utiliser en production) :

| Rôle | Email | Mot de passe |
|---|---|---|
| Admin | `admin@atast.tn` | `AtastAdmin2026` |
| Membre | `yasmine.trabelsi@etudiant.isimm.tn` | `Membre2026` |
| Demande en attente | `firas.belhadj@etudiant.isimm.tn` | `Membre2026` |

### Créer le premier administrateur (production)

Aucun visiteur ne peut obtenir le rôle ADMIN depuis le site : les administrateurs se créent en ligne de commande.

```bash
cp .env.example .env      # puis remplir les valeurs
ADMIN_NAME="Bureau ATAST" ADMIN_EMAIL=bureau@atast.tn ADMIN_PHONE=+21673000000 \
ADMIN_PASSWORD='mot-de-passe-solide-2026' npm run create-admin
```

### Tests

```bash
npm test     # 41 tests : unitaires, intégration API de bout en bout et synchronisation entre appareils
```

## Ce qui est implémenté (correspondance avec le cahier des charges)

| Exigence | Implémentation |
|---|---|
| FR-01 à FR-04 Adhésion | `/register` crée une demande `PENDING` ; l'admin accepte (compte `MEMBER` actif) ou refuse avec motif. Le motif est affiché à la personne si elle tente de se connecter. |
| FR-05, FR-06 Membres (admin) | `/admin/members` (recherche nom/email, filtre statut, pagination) et fiche complète avec historique et score. Suspension / désactivation logique (historique conservé). |
| FR-07 à FR-12 Événements | Formulaire complet (type, date, heure, lieu, image, gratuit/payant + devise, infos, statut). Archivage logique. Un changement de type recalcule les points dans la même transaction. |
| FR-08, FR-14 Points | `SMALL=10, MEDIUM=20, BIG=30, MEETING=0` définis une seule fois (`backend/services/points.js`). Le score est **toujours calculé** à partir des participations validées : il n'existe aucune colonne « score » modifiable. |
| FR-13 Participations | Le membre s'inscrit (0 point) ; l'admin valide (points attribués une seule fois) ou enregistre directement une présence. Index unique contre les doublons. |
| FR-15, FR-16 Messages / suggestions | Annonce globale stockée une fois et lue par tous ; boîte à suggestions avec statuts `NEW / READ / IN_REVIEW / RESOLVED` visibles par le membre. |
| FR-17, FR-18 Espace membre | Accueil (score, rang, événements à venir, annonces) ; menu ouvert par l'icône en haut à droite. |
| FR-19 Confidentialité | Les réponses publiques ne contiennent jamais email, téléphone ni date de naissance (filtré côté serveur, testé). |
| FR-20 à FR-23 Profil | Édition, liens sociaux validés côté serveur (domaine vérifié), photo facultative avec avatar par défaut, changement de mot de passe séparé (déconnecte les autres appareils). |
| Cotisations (extension) | Import Excel/CSV avec aperçu, acceptation automatique des cotisants, suivi par saison, exports Excel, sauvegarde : voir la section « Cotisations, import Excel et acceptation automatique ». |
| FR-24 Classement | Score décroissant, égalités départagées par le nom puis la date d'inscription. Les admins ne sont pas classés. |

### Sécurité (NFR-01, chapitre « Security Threat Model »)

- Mots de passe hachés avec **bcrypt** (coût 12 par défaut) ; comparaison à temps constant même pour un email inconnu.
- Sessions serveur : cookie `HttpOnly`, `SameSite=Lax`, `Secure` en production ; seul le hash SHA-256 du jeton est stocké ; révocation à la désactivation.
- **RBAC côté serveur** : `authenticate() → authorize(ADMIN) → contrôleur`. Un membre qui appelle une route admin reçoit **HTTP 403**.
- **CSRF** : en-tête personnalisé obligatoire, contrôle de l'`Origin` et jeton CSRF par session.
- **XSS** : le frontend n'insère jamais de contenu utilisateur en HTML (`textContent` uniquement) + CSP stricte (`script-src 'self'`, aucun script inline).
- **Injections** : requêtes SQL paramétrées uniquement ; validation et liste blanche de champs sur chaque entrée (impossible d'envoyer `role` ou `score`).
- **Uploads** : JPEG/PNG/WebP vérifiés par signature binaire (pas par le nom ni le MIME annoncé), taille limitée et configurable, nom généré par le serveur, stockage hors du dossier public, servis uniquement aux utilisateurs connectés avec `nosniff`.
- Limitation du débit (connexion, inscription, API) ; journal d'audit des actions sensibles, sans secret.
- Transactions pour toutes les opérations critiques (acceptation, validation, recalcul des points…).

### Interface (UI/UX)

- Identité tirée du logo : bleu de la sphère, bleu nuit du mot « ATAST », orange des orbites (réservé aux points et au score).
- Typographies auto-hébergées : **Exo 2** (titres, chiffres — écho au lettrage italique du logo) et **Lexend** (texte, conçue pour la lisibilité).
- Élément signature : le score du membre affiché dans une sphère entourée d'une orbite.
- Responsive (mobile, tablette, desktop), navigation clavier, focus visible, libellés explicites, erreurs reliées aux champs (`aria-describedby`), mouvement réduit respecté, contrastes AA.
- États vides, chargements, erreurs réseau / serveur / session expirée gérés sur chaque page.

## Cotisations, import Excel et acceptation automatique

Le bureau n'a plus à valider à la main chaque personne qui a déjà payé : la liste du trésorier est importée, et ceux qui s'y trouvent sont acceptés automatiquement.

**Menu Administration → Cotisations**

1. **Télécharger le modèle** (ou utiliser son propre fichier : colonnes `Nom complet` (ou `Nom` + `Prénom`), `Email`, `Téléphone`, et facultativement `Montant`, `Date de paiement`, `Référence`). Fichiers `.xlsx` ou `.csv` (séparateur `;` ou `,`, UTF-8 ou Windows-1252) ; les titres sont reconnus sans tenir compte des accents ni des majuscules.
2. **Choisir la saison** (année universitaire, ex. `2026-2027`, qui change en septembre) puis **déposer le fichier** : un **aperçu ligne par ligne** s'affiche et *rien n'est enregistré*.
3. **Confirmer** : tout est écrit en une seule transaction. L'import peut être **annulé** depuis l'historique (les personnes pas encore inscrites quittent la liste ; les membres déjà créés restent membres).

Ce que devient chaque ligne :

| Résultat | Signification |
|---|---|
| À ajouter | Personne ajoutée à la liste des cotisants. Elle sera acceptée automatiquement à son inscription. |
| Acceptée automatiquement | Une demande d'adhésion en attente correspond (même email et même téléphone) : le compte membre est créé tout de suite. |
| Déjà membre | Le membre existe déjà : la cotisation est enregistrée sur son compte (renouvellement). |
| Déjà enregistrée / Doublon | Même email déjà présent dans la saison, ou deux fois dans le fichier : ignorée. |
| À traiter à la main | Compte suspendu ou désactivé, ou adresse d'un administrateur : jamais réactivé automatiquement. |
| Erreur | Email, téléphone, montant ou date illisible : la ligne est ignorée et le motif est affiché. |

**Acceptation automatique à l'inscription.** Quand quelqu'un s'inscrit avec un email *et* un téléphone présents dans la liste, sa demande passe directement à `ACCEPTED`, il peut se connecter immédiatement et sa cotisation est rattachée à son compte (journal d'audit : `MEMBERSHIP_AUTO_ACCEPTED`). Le téléphone est exigé en plus de l'email pour que connaître l'adresse de quelqu'un ne suffise pas à prendre sa place ; `AUTO_ACCEPT_REQUIRE_PHONE=false` supprime cette exigence (déconseillé). En cas de téléphone différent, la demande reste en attente et l'administrateur voit « Sur la liste des cotisations ».

**Gestion des membres et de la base**

- La liste **Membres** affiche la cotisation de la saison (payée / non payée), se filtre par cotisation et s'**exporte en Excel** (nom, email, téléphone, naissance, statut, score, cotisation, date, montant, référence).
- La fiche d'un membre permet de **corriger ses informations** (nom, email, téléphone, naissance ; l'email actif reste unique) et d'**enregistrer un paiement** à la main. Le score et le rôle ne sont jamais modifiables.
- **Ajouter une personne** à la main (sans fichier) est possible depuis la page Cotisations.
- Le tableau de bord indique les cotisations payées, les membres sans cotisation à relancer et les personnes payées mais pas encore inscrites.
- **Sauvegarde** : `npm run backup` crée un instantané cohérent de la base (même site en ligne) dans `database/backups/` et garde les 14 derniers (`BACKUP_DIR`, `BACKUP_KEEP`). Restauration : arrêter le serveur, copier la sauvegarde sur `database/atast.sqlite`, relancer. Copier aussi `uploads/` (photos).

Sécurité des fichiers importés : accès réservé aux administrateurs (HTTP 403 pour un membre), type reconnu par le contenu et non par l'extension, taille limitée (`IMPORT_MAX_BYTES`, 2 Mo) et nombre de lignes limité (`IMPORT_MAX_ROWS`, 2000), archive `.xlsx` inspectée avant décompression (protection contre les « bombes zip »), aucune cellule n'est interprétée comme une formule, fichier traité en mémoire et jamais conservé.

## Synchronisation entre appareils (temps réel)

Toutes les données vivent sur le serveur ; chaque appareil connecté (téléphone, ordinateur, autre onglet) garde en plus un flux **Server-Sent Events** ouvert sur `GET /api/sync`. Dès qu'une modification est enregistrée, les autres appareils se mettent à jour en moins d'une seconde, sans recharger la page.

| Ce qui se passe | Ce que voient les autres appareils |
|---|---|
| L'admin valide ou retire une participation | Le membre reçoit une notification sur **tous** ses appareils ; son score, l'accueil, le classement et la page de l'événement se mettent à jour partout |
| Un événement est créé, modifié, publié ou archivé | Bibliothèque des événements, accueil et pages d'administration à jour |
| Nouvelle demande d'adhésion, nouvelle suggestion | La liste et le compteur de la barre latérale des admins s'actualisent |
| Message envoyé à tous | L'annonce apparaît sur l'accueil des membres, avec une notification |
| Statut d'une suggestion changé | L'auteur est prévenu et sa boîte à suggestions se met à jour |
| Profil ou photo modifiés sur un appareil | Les autres appareils du membre, la liste des membres et le classement se mettent à jour |
| Changement de mot de passe | Les **autres** appareils sont déconnectés immédiatement |
| Compte suspendu ou désactivé | Toutes les sessions ouvertes de ce membre sont fermées |
| Connexion / déconnexion dans un onglet | Les autres onglets du même navigateur suivent (BroadcastChannel) |

Garanties :

- **Confidentialité** : le flux ne transporte que des noms de sujets (`events`, `scoreboard`…) et des identifiants, jamais de données personnelles. Chaque appareil relit ensuite les données par l'API habituelle, avec ses propres permissions. Les sujets d'administration ne sont envoyés qu'aux admins, les notifications personnelles qu'à la personne concernée.
- **Cohérence** : une notification n'est envoyée qu'après la validation de la transaction en base ; une opération refusée n'annonce rien.
- **Saisies protégées** : une mise à jour en direct ne remplace jamais un formulaire en cours de saisie. La page propose « Actualiser » et conserve le texte tapé.
- **Coupures** : en cas de perte réseau, de mise en veille du téléphone ou de redémarrage du serveur, l'appareil affiche « Reconnexion… » / « Hors ligne », se reconnecte seul (délai croissant jusqu'à 15 s) puis rattrape tout ce qui a changé entre-temps.

Derrière Nginx, laissez passer le flux sans mise en tampon :

```nginx
location /api/sync {
    proxy_pass http://127.0.0.1:3000;
    proxy_http_version 1.1;
    proxy_set_header Connection "";
    proxy_buffering off;
    proxy_read_timeout 1h;
}
```

## Architecture

```
backend/
  app.js, server.js       Express : sécurité HTTP, API REST sous /api, service du frontend
  config/                 configuration par variables d'environnement
  db/                     connexion SQLite + exécution des migrations
  routes/                 routes REST (guards RBAC)
  controllers/            HTTP ⇄ services
  services/               logique métier (points, adhésions, événements, communication, audit, fichiers, sync temps réel)
  repositories/           seul endroit contenant du SQL
  validators/             validation serveur
  middleware/             authentification, autorisation, CSRF, uploads, erreurs, rate limiting
database/
  migrations/             001_init.sql (schéma : prix gratuit/payant, unicité des participations, email actif unique),
                          002_subscriptions.sql (cotisations, lots d'import)
  backup.js               sauvegarde cohérente de la base (npm run backup)
  seeds/                  create-admin.js, demo.js
frontend/                 SPA sans étape de build (modules ES)
  css/                    tokens, base, composants, layouts, pages
  js/app, services, state, components, layouts, pages
tests/                    tests unitaires et d'intégration (node:test)
documentation/            documentation.tex
```

### Choix techniques documentés

Le cahier des charges laisse la stack ouverte. Choix retenus pour un club de taille modérée :

- **SQLite (module `node:sqlite` intégré)** plutôt que PostgreSQL : zéro installation, sauvegarde = copie d'un fichier. Tout le SQL est isolé dans `backend/repositories/`, la migration vers PostgreSQL ne touche donc que cette couche et le schéma.
- **Frontend sans framework ni build** : quelques kilo-octets de JavaScript modulaire, compatible avec une CSP stricte.
- **Score calculé à la demande** (stratégie 1 du document) ; `points_awarded` est conservé sur chaque participation et resynchronisé en transaction lors d'un changement de type.

## Déploiement sur Render

Le fichier `render.yaml` (à la racine du dépôt) décrit le service : Node 22, disque persistant monté sur `/var/data` (base SQLite + photos), contrôle de santé `/healthz`, HTTPS fourni par Render.

> ⚠️ Un **disque persistant n'existe que sur les offres payantes** de Render (Starter, environ 7 $/mois + le disque). Sur l'offre gratuite le système de fichiers est effacé à chaque déploiement : toute la base serait perdue. Une seule instance : un disque ne se partage pas.

1. Sur render.com : **New → Blueprint**, connecter le dépôt GitHub et choisir la branche à déployer (par exemple `main` après fusion). Render lit `render.yaml` et crée le service `atast-platform` avec son disque.
2. Attendre la fin du premier déploiement. Le site est disponible sur `https://atast-platform.onrender.com` (adresse indiquée sur la page du service). Les tables de la base sont créées automatiquement au démarrage.
3. Créer le premier administrateur : service → **Shell** :
   ```bash
   ADMIN_NAME="Bureau ATAST" ADMIN_EMAIL=bureau@atast.tn ADMIN_PHONE=+21673000000 ADMIN_PASSWORD='un-mot-de-passe-solide-2026' npm run create-admin
   ```
   (n'utilisez jamais `seed:demo` en production).
4. Se connecter, ouvrir **Cotisations**, importer la liste Excel.
5. Nom de domaine personnalisé (facultatif) : service → **Settings → Custom Domains**, puis définir la variable `APP_URL=https://votre-domaine`.
6. **Sauvegardes** : activer et vérifier les instantanés du disque dans le tableau de bord Render, et lancer régulièrement `npm run backup` depuis le Shell (copies dans `/var/data/backups` si `BACKUP_DIR=/var/data/backups`). Télécharger une copie hors de Render de temps en temps.

## Production

1. Placer l'application derrière un reverse proxy HTTPS (Nginx, Caddy…), `NODE_ENV=production` et `APP_URL=https://…`.
2. Sauvegarder régulièrement `database/atast.sqlite` (ex. `sqlite3 atast.sqlite ".backup sauvegarde.sqlite"`) et le dossier `uploads/`, puis tester la restauration.
3. Garder `.env` hors du dépôt et dans un gestionnaire de secrets.
