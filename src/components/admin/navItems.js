import { Gamepad2, House, Settings, Trophy, Tv, Users, UsersRound } from 'lucide-react';

export const NAV_ITEMS = [
  { to: '/admin', label: 'Dashboard', icon: House, end: true },
  { to: '/admin/teams', label: 'Équipes', icon: Users },
  { to: '/admin/participants', label: 'Participants', icon: UsersRound },
  { to: '/admin/games', label: 'Mini-jeux', icon: Gamepad2 },
  { to: '/admin/leaderboard', label: 'Classement', icon: Trophy },
  { to: '/admin/screen', label: 'Mode écran', icon: Tv },
  { to: '/admin/settings', label: 'Paramètres', icon: Settings },
];
