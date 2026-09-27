"""Bounded episode memory derived only from public observations/actions."""
from collections import Counter, deque
from copy import deepcopy


class EpisodeMemory:
    def __init__(self, limit=20):
        self.limit = limit
        self.episode = None
        self.reset(None)

    def reset(self, episode):
        self.episode = episode
        self.facts = deque(maxlen=self.limit)
        self.counts = Counter()
        self.previous = None
        self.last_action_time = -1
        self.seen_actions = set()
        self.strategy = ""
        self.strategy_time = None

    def update(self, episode, context):
        if episode != self.episode:
            self.reset(episode)
        obs = context['observation']
        def fact(kind, detail):
            self.counts[kind] += 1
            self.facts.append(dict(sim_ms=obs['sim_ms'], kind=kind, detail=detail))
        if self.previous:
            now = {p['id'] for p in obs['plants']}
            for p in self.previous['plants']:
                if p['id'] not in now:
                    fact('plant_disappeared', {k: p[k] for k in ('id', 'type', 'row', 'col')})
            old_mowers = {m['id']: m['state'] for m in self.previous['mowers']}
            new_mowers = {m['id']: m['state'] for m in obs['mowers']}
            for key, state in old_mowers.items():
                if new_mowers.get(key) != state:
                    fact('mower_changed', dict(id=key, before=state, after=new_mowers.get(key)))
            if obs['wave'] != self.previous['wave']:
                fact('wave_changed', obs['wave'])
        for action in context.get('past_actions', []):
            key = action['command_id']
            if key not in self.seen_actions and action['sim_ms'] >= self.last_action_time:
                self.seen_actions.add(key)
                if action['action']['type'] != 'WAIT' or not action['success']:
                    self.counts['executed_success' if action['success'] else 'executed_failure'] += 1
                    self.facts.append(dict(kind='execution', **deepcopy(action)))
        actions = context.get('past_actions', [])
        if actions:
            self.last_action_time = max(self.last_action_time, max(a['sim_ms'] for a in actions))
            self.seen_actions = {a['command_id'] for a in actions if a['sim_ms'] == self.last_action_time}
        self.previous = deepcopy(obs)

    def snapshot(self, facts=True, strategy=True):
        return dict(version='episode_memory_v1',
                    facts=list(deepcopy(self.facts)) if facts else [],
                    totals=dict(self.counts) if facts else {},
                    strategy=self.strategy if strategy else '',
                    strategy_sim_ms=self.strategy_time if strategy else None,
                    note='Bounded public facts, not complete history. Plant disappearance cause is unknown. Strategy is an intention, never proof of execution; current state overrides it.')
