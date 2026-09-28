import { useMemo, useSyncExternalStore } from 'react';
import { getState, subscribe } from './store';
import { rankTeams } from '../utils/ranking';

export const useAppState = () => useSyncExternalStore(subscribe, getState);

export const useSettings = () => useAppState().settings;

export function useRankedTeams() {
  const { teams, participants } = useAppState();
  return useMemo(() => {
    const counts = participants.reduce((acc, participant) => {
      acc[participant.teamId] = (acc[participant.teamId] ?? 0) + 1;
      return acc;
    }, {});
    return rankTeams(teams).map((team) => ({ ...team, participantCount: counts[team.id] ?? 0 }));
  }, [teams, participants]);
}

export function useTeamsById() {
  const { teams } = useAppState();
  return useMemo(() => Object.fromEntries(teams.map((team) => [team.id, team])), [teams]);
}
