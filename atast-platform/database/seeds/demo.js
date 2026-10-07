'use strict';
/**
 * Demo data so the platform can be explored immediately.
 * DO NOT run in production: it creates accounts with known passwords.
 *
 *   npm run seed:demo
 */
const config = require('../../backend/config');
const db = require('../../backend/db/database');
const repo = require('../../backend/repositories');
const { hashPassword } = require('../../backend/services/auth');
const { pointsFor } = require('../../backend/services/points');
const { today } = require('../../backend/services/events');
const { uuid } = require('../../backend/utils');

if (config.isProduction) {
  console.error('Refusing to seed demo data in production.');
  process.exit(1);
}

const DEMO_ADMIN = { email: 'admin@atast.tn', password: 'AtastAdmin2026' };
const DEMO_MEMBER_PASSWORD = 'Membre2026';

const MEMBERS = [
  ['Yasmine Trabelsi', 'Passionnée de robotique, je construis des bras articulés avec Arduino.', 'github'],
  ['Mohamed Ben Salah', 'Étudiant en génie logiciel. Développement web et open source.', 'github'],
  ['Amira Chaabane', 'Data science et visualisation. Toujours partante pour un hackathon.', 'linkedin'],
  ['Oussama Gharbi', "Électronique embarquée et IoT. J'anime les ateliers capteurs.", null],
  ['Sarra Mejri', 'Astronomie amateur et photographie du ciel nocturne.', 'instagram'],
  ['Karim Jlassi', null, null],
  ['Nour Ayari', "Mathématiques appliquées, j'aime vulgariser.", 'linkedin'],
  ['Ahmed Hammami', 'Cybersécurité et CTF.', 'github'],
  ['Ines Bouzid', null, 'instagram'],
  ['Skander Mansouri', 'Impression 3D et modélisation.', null],
  ['Rania Khelifi', 'Intelligence artificielle appliquée à la santé.', 'linkedin'],
  ['Bilel Saidi', null, null],
  ['Meriem Ferchichi', 'Design d’interfaces et accessibilité.', 'facebook'],
  ['Hamza Dridi', 'Débutant motivé, curieux de tout.', null],
];

function shiftDate(days) {
  const d = new Date(`${today()}T12:00:00Z`);
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
}
const isoAt = (date, time = '10:00') => new Date(`${date}T${time}:00Z`).toISOString();
const slug = (name) => name.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[^a-z]+/g, '.');

async function main() {
  db.open();
  if (repo.users.findActiveByEmail(DEMO_ADMIN.email)) {
    console.log('Demo data already present — nothing to do.');
    return;
  }
  const adminHash = await hashPassword(DEMO_ADMIN.password);
  const memberHash = await hashPassword(DEMO_MEMBER_PASSWORD);

  db.transaction(() => {
    const adminId = uuid();
    const created = isoAt(shiftDate(-200));
    repo.users.insert({
      id: adminId, name: 'Bureau ATAST', email: DEMO_ADMIN.email, password_hash: adminHash, phone: '+21673500000',
      role: 'ADMIN', status: 'ACTIVE', created_at: created, updated_at: created,
    });

    const memberIds = MEMBERS.map(([name, description, social], i) => {
      const id = uuid();
      const at = isoAt(shiftDate(-180 + i * 7));
      const handle = slug(name).replace(/\./g, '-');
      repo.users.insert({
        id, name, email: `${slug(name)}@etudiant.isimm.tn`, password_hash: memberHash,
        phone: `+2162${String(1000000 + i * 73911).slice(0, 7)}`, role: 'MEMBER', status: 'ACTIVE', created_at: at, updated_at: at,
      });
      repo.users.updateProfile(id, {
        name, phone: `+2162${String(1000000 + i * 73911).slice(0, 7)}`, description,
        birthday: i % 3 === 0 ? `200${3 + (i % 4)}-0${1 + (i % 9)}-1${i % 9}` : null,
        instagram: social === 'instagram' ? `https://instagram.com/${handle}` : null,
        facebook: social === 'facebook' ? `https://facebook.com/${handle}` : null,
        github: social === 'github' ? `https://github.com/${handle}` : null,
        linkedin: social === 'linkedin' ? `https://linkedin.com/in/${handle}` : null,
      }, at);
      return id;
    });

    const ev = (o) => {
      const id = uuid();
      const at = isoAt(shiftDate(Math.min(o.offset - 14, -1)));
      repo.events.insert({
        id, title: o.title, description: o.description, type: o.type, date: shiftDate(o.offset), time: o.time,
        location: o.location, isFree: !o.price, price: o.price || 0, currency: 'TND', imageUrl: null,
        additionalInfo: o.info || null, status: o.status, createdBy: adminId, createdAt: at, updatedAt: at,
      });
      return { id, ...o };
    };

    const past = [
      ev({ title: "Réunion de rentrée du bureau", type: 'MEETING', offset: -60, time: '14:00', location: 'Salle de réunion, ISIMM', status: 'COMPLETED',
        description: "Présentation du programme de l'année, répartition des pôles et accueil des nouveaux membres." }),
      ev({ title: 'Initiation à Git et GitHub', type: 'SMALL', offset: -52, time: '10:00', location: 'Labo informatique 2, ISIMM', status: 'COMPLETED',
        description: 'Versionner son code, travailler à plusieurs sur un dépôt et ouvrir sa première pull request.' }),
      ev({ title: 'Atelier Arduino : capteurs et LED', type: 'SMALL', offset: -41, time: '14:30', location: 'Salle TP électronique, ISIMM', status: 'COMPLETED',
        description: 'Montage pas à pas : lire un capteur de température et piloter une matrice de LED.', info: 'Kits fournis par le club.' }),
      ev({ title: "Conférence : l'IA au service de la santé", type: 'MEDIUM', offset: -30, time: '15:00', location: 'Amphithéâtre B, ISIMM', status: 'COMPLETED',
        description: "Deux chercheuses présentent des cas concrets de diagnostic assisté par l'apprentissage automatique." }),
      ev({ title: 'Sortie à la Cité des Sciences de Tunis', type: 'MEDIUM', offset: -21, time: '07:30', location: 'Départ : parking ISIMM', status: 'COMPLETED', price: 25000,
        description: 'Visite du planétarium et des expositions interactives.', info: 'Le prix comprend le transport et les entrées.' }),
      ev({ title: 'Hackathon ATAST 24h', type: 'BIG', offset: -10, time: '09:00', location: 'Amphithéâtre A, ISIMM', status: 'COMPLETED', price: 10000,
        description: "24 heures pour prototyper une solution numérique à un problème local, en équipes de quatre.", info: 'Repas et boissons inclus.' }),
    ];
    ev({ title: 'Café scientifique', type: 'SMALL', offset: -35, time: '17:00', location: 'Cafétéria ISIMM', status: 'ARCHIVED',
      description: 'Séance annulée faute de salle disponible.' });

    const upcoming = [
      ev({ title: "Atelier Python pour l'analyse de données", type: 'SMALL', offset: 5, time: '14:00', location: 'Labo informatique 1, ISIMM', status: 'PUBLISHED',
        description: 'Pandas et Matplotlib sur un jeu de données réel : la consommation électrique de Monastir.', info: 'Apportez votre ordinateur portable.' }),
      ev({ title: 'Assemblée générale ATAST', type: 'MEETING', offset: 10, time: '16:00', location: 'Amphithéâtre B, ISIMM', status: 'PUBLISHED',
        description: 'Bilan du semestre et vote des projets du second semestre.' }),
      ev({ title: "Nuit de l'astronomie", type: 'MEDIUM', offset: 17, time: '19:30', location: 'Terrasse du bâtiment C, ISIMM', status: 'PUBLISHED',
        description: 'Observation de Saturne et de la Lune au télescope, avec un atelier de photographie du ciel.' }),
      ev({ title: 'Compétition de robotique inter-clubs', type: 'BIG', offset: 24, time: '08:30', location: 'Salle omnisport, Monastir', status: 'PUBLISHED', price: 15000,
        description: 'Course de robots suiveurs de ligne face aux clubs des autres instituts de la région.', info: 'Inscription par équipe de trois membres.' }),
    ];
    ev({ title: 'Workshop impression 3D', type: 'MEDIUM', offset: 38, time: '10:00', location: 'Fablab, ISIMM', status: 'DRAFT',
      description: 'Modéliser une pièce sur Fusion 360 et la lancer à l’impression.' });

    // Validated participations (points come from the event type only).
    const attend = [
      [0, [0, 1, 2, 3, 4, 6, 7, 10, 12]],
      [1, [0, 1, 2, 5, 7, 8, 11, 13]],
      [2, [0, 3, 4, 9, 13]],
      [3, [2, 6, 10, 12, 1]],
      [4, [0, 4, 6, 9, 3]],
      [5, [0, 1, 2, 3, 7, 10]],
    ];
    for (const [ei, members] of attend) {
      const e = past[ei];
      for (const mi of members) {
        const at = isoAt(shiftDate(e.offset), '18:00');
        repo.participations.insert({
          id: uuid(), eventId: e.id, memberId: memberIds[mi], status: 'VALIDATED', points: pointsFor(e.type),
          validatedAt: at, validatedBy: adminId, at,
        });
      }
    }
    // Registrations for upcoming events (no points yet).
    const reg = [[0, [1, 4, 5, 8, 13]], [2, [4, 6, 9]], [3, [0, 3, 7]]];
    for (const [ei, members] of reg) {
      for (const mi of members) {
        repo.participations.insert({
          id: uuid(), eventId: upcoming[ei].id, memberId: memberIds[mi], status: 'REGISTERED', points: 0,
          at: isoAt(shiftDate(-2)),
        });
      }
    }

    const msg = (title, content, days) => repo.messages.insert({
      id: uuid(), title, content, senderId: adminId, createdAt: isoAt(shiftDate(days), '09:15'),
    });
    msg('Bienvenue aux nouveaux membres',
      "Le bureau souhaite la bienvenue aux membres qui nous ont rejoints ce mois-ci. Pensez à compléter votre profil et à consulter le calendrier des événements.", -12);
    msg('Résultats du hackathon',
      "Merci aux 24 participants du hackathon ! Les points de participation ont été ajoutés au classement. Les projets primés seront présentés lors de l'assemblée générale.", -8);
    msg("Inscriptions ouvertes : nuit de l'astronomie",
      "Les places sont limitées par le nombre de télescopes disponibles. Inscrivez-vous depuis la page de l'événement avant la fin de la semaine.", -1);

    const sug = (mi, title, content, status, days) => {
      const id = uuid();
      repo.suggestions.insert({ id, memberId: memberIds[mi], title, content, at: isoAt(shiftDate(days), '20:00') });
      if (status !== 'NEW') repo.suggestions.setStatus(id, status, isoAt(shiftDate(days + 1), '10:00'));
    };
    sug(3, 'Atelier soudure', "Pourrait-on organiser un atelier d'initiation à la soudure électronique ? Beaucoup de membres n'ont jamais tenu un fer à souder.", 'NEW', -3);
    sug(7, 'Équipe CTF', "Je propose de monter une équipe pour participer aux compétitions de cybersécurité en ligne.", 'IN_REVIEW', -9);
    sug(12, null, 'Les supports des ateliers pourraient être partagés après chaque séance.', 'NEW', -1);
    sug(1, 'Horaires des ateliers', 'Les ateliers du samedi matin conviendraient mieux aux étudiants en stage.', 'RESOLVED', -25);

    const requests = [
      ['Firas Belhadj', 'firas.belhadj@etudiant.isimm.tn', '+21655123456', -2],
      ['Eya Romdhane', 'eya.romdhane@etudiant.isimm.tn', '+21698765432', -1],
      ['Wassim Kacem', 'wassim.kacem@gmail.com', '+21622334455', 0],
    ];
    for (const [name, email, phone, days] of requests) {
      repo.requests.insert({ id: uuid(), name, email, phone, password_hash: memberHash, created_at: isoAt(shiftDate(days), '11:00') });
    }
  });

  console.log('Demo data created.');
  console.log(`  Admin   : ${DEMO_ADMIN.email} / ${DEMO_ADMIN.password}`);
  console.log(`  Member  : yasmine.trabelsi@etudiant.isimm.tn / ${DEMO_MEMBER_PASSWORD}`);
  console.log(`  Pending : firas.belhadj@etudiant.isimm.tn / ${DEMO_MEMBER_PASSWORD} (awaiting review)`);
  db.close();
}

main();
